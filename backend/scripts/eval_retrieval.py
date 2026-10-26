"""Çalışan API üzerinden arama başarımını ölçer (Recall@1, Recall@5, MRR, skor dağılımı, eşik önerisi).

Kullanım (kök dizinden):
  python backend/scripts/eval_retrieval.py [--api-url URL] [--json sonuc.json]
                                           [--template "bir fotoğraf: {q}"] [--template-en "a photo of {q}"]
Ön koşul: demo verisi seed_demo.py ile yüklenmiş olmalı. İlanlar başlıkla eşlenir (items.json key <-> API id).
Sorgular demo_data/queries.json'dan okunur; görsel sorgular images/queries altındaki küçültülmüş kopyalardır.
"""
import argparse
import json
import os
import platform
import statistics
import sys
from pathlib import Path

import httpx
import numpy as np

REPO_DIR = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_DIR / "demo_data"
TOP_K = 50


def search(client, *, query=None, image_path=None, category=None):
    data = {"top_k": str(TOP_K)}
    if query:
        data["query"] = query
    if category:
        data["category"] = category
    files = {"image": (image_path.name, image_path.read_bytes(), "image/jpeg")} if image_path else None
    r = client.post("/api/search", data=data, files=files)
    r.raise_for_status()
    return r.json()


def evaluate(client, id_to_key, cases):
    """cases: [{"label", "expected", "query"|"image_path"}] -> sorgu başına sonuç listesi."""
    rows = []
    for c in cases:
        resp = search(client, query=c.get("query"), image_path=c.get("image_path"), category=c.get("category"))
        ranked = [(id_to_key.get(r["item"]["id"], "?"), r["score"]) for r in resp["results"]]
        keys = [k for k, _ in ranked]
        rank = keys.index(c["expected"]) + 1 if c["expected"] in keys else None
        correct = next((s for k, s in ranked if k == c["expected"]), None)
        wrong = next((s for k, s in ranked if k != c["expected"]), None)
        rows.append({
            "label": c["label"], "expected": c["expected"], "rank": rank,
            "correct_score": correct, "best_wrong_score": wrong,
            "wrong_scores": [s for k, s in ranked if k != c["expected"]],
            "top1": keys[0] if keys else None, "took_ms": resp["took_ms"],
        })
    return rows


def metrics(rows):
    n = len(rows)
    r1 = sum(1 for r in rows if r["rank"] == 1) / n
    r5 = sum(1 for r in rows if r["rank"] and r["rank"] <= 5) / n
    mrr = sum(1 / r["rank"] for r in rows if r["rank"]) / n
    return {"n": n, "R@1": round(r1, 3), "R@5": round(r5, 3), "MRR": round(mrr, 3)}


def dist(values):
    v = np.asarray([x for x in values if x is not None], dtype=float)
    if not len(v):
        return None
    return {"n": int(len(v)), "min": round(float(v.min()), 4), "p10": round(float(np.percentile(v, 10)), 4),
            "median": round(float(np.median(v)), 4), "p90": round(float(np.percentile(v, 90)), 4),
            "max": round(float(v.max()), 4)}


def youden(pos, neg):
    """TPR - FPR'yi en büyük yapan eşik (0.005 adımlı tarama; eşitlikte küçük olan)."""
    best = None
    for t in np.round(np.arange(0.10, 0.50, 0.005), 3):
        tpr, fpr = float((pos >= t).mean()), float((neg >= t).mean())
        if best is None or tpr - fpr > best["J"] + 1e-9:
            best = {"t": float(t), "TPR": round(tpr, 3), "FPR": round(fpr, 3), "J": round(tpr - fpr, 3)}
    return best


def suggest_thresholds(rows):
    """Metin skorlarından eşik önerisi (API metin ve görsel için tek, ortak eşik kullanır).

    pos = doğru ilanın skoru; neg_all = sorgu başına bütün yanlış ilanların skorları;
    neg_best = sorgu başına en iyi (en yüksek skorlu) yanlış ilanın skoru.
    match_medium: doğru vs. bütün yanlışlar için Youden J'yi en büyük yapan eşik
                  ("orta" = ilgisiz ilanların çoğundan ayrışıyor).
    match_high:  neg_best'in p90'ı, 0.005'e yukarı yuvarlanmış
                 ("yüksek" = en benzer yanlış ilan bile en çok %10 olasılıkla buraya çıkıyor).
    """
    pos = np.array([r["correct_score"] for r in rows if r["correct_score"] is not None])
    neg_all = np.array([s for r in rows for s in r["wrong_scores"]])
    neg_best = np.array([r["best_wrong_score"] for r in rows if r["best_wrong_score"] is not None])
    med = youden(pos, neg_all)
    j_best = youden(pos, neg_best)
    high = float(np.ceil(np.percentile(neg_best, 90) / 0.005 - 1e-9) * 0.005)
    high = max(high, med["t"] + 0.01)
    return {
        "match_medium": round(med["t"], 3), "medium_TPR": med["TPR"], "medium_FPR_all": med["FPR"],
        "medium_FPR_best": round(float((neg_best >= med["t"]).mean()), 3), "medium_J": med["J"],
        "match_high": round(high, 3), "high_TPR": round(float((pos >= high).mean()), 3),
        "high_FPR_best": round(float((neg_best >= high).mean()), 3),
        "high_FPR_all": round(float((neg_all >= high).mean()), 3),
        "youden_vs_best_wrong": j_best,
    }


def level_counts(rows, high, medium):
    def lvl(s):
        return "yüksek" if s >= high else "orta" if s >= medium else "düşük"
    out = {}
    for name, field in (("doğru", "correct_score"), ("en iyi yanlış", "best_wrong_score")):
        c = {"yüksek": 0, "orta": 0, "düşük": 0}
        for r in rows:
            if r[field] is not None:
                c[lvl(r[field])] += 1
        out[name] = c
    return out


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(x) for x in row) + " |" for row in rows]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Arama başarımı değerlendirmesi")
    parser.add_argument("--api-url", default=os.environ.get("API_URL", "http://localhost:8000"))
    parser.add_argument("--json", dest="json_out", help="Sonuçların yazılacağı JSON dosyası")
    parser.add_argument("--template", default="{q}", help='TR sorgu şablonu, ör. "bir fotoğraf: {q}"')
    parser.add_argument("--template-en", default="{q}", help='EN sorgu şablonu, ör. "a photo of {q}"')
    parser.add_argument("--category-map", help="key -> kategori JSON dosyası; verilirse metin sorgularında kategori filtresi uygulanır")
    args = parser.parse_args()

    items = json.loads((DEMO_DIR / "items.json").read_text("utf-8"))
    queries = json.loads((DEMO_DIR / "queries.json").read_text("utf-8"))
    cat_map = json.loads(Path(args.category_map).read_text("utf-8")) if args.category_map else {}

    with httpx.Client(base_url=args.api_url, timeout=120) as client:
        health = client.get("/health").json()
        api_items = client.get("/api/items", params={"limit": 100}).json()["items"]
        by_title = {i["title"]: i["id"] for i in api_items}
        missing = [it["key"] for it in items if it["title"] not in by_title]
        if missing:
            sys.exit(f"API'de olmayan ilanlar (önce seed_demo.py çalıştırın): {missing}")
        id_to_key = {by_title[it["title"]]: it["key"] for it in items}
        extra = len(api_items) - len(items)

        tr_cases = [{"label": t["q"], "expected": t["expected"], "query": args.template.format(q=t["q"]),
                     "category": cat_map.get(t["expected"])} for t in queries["text"]]
        en_cases = [{"label": t["q_en"], "expected": t["expected"], "query": args.template_en.format(q=t["q_en"]),
                     "category": cat_map.get(t["expected"])} for t in queries["text"]]
        img_cases = [{"label": Path(i["file"]).name, "expected": i["expected"], "image_path": DEMO_DIR / i["file"]}
                     for i in queries["image"]]
        res = {"TR metin": evaluate(client, id_to_key, tr_cases),
               "EN metin": evaluate(client, id_to_key, en_cases),
               "Görsel": evaluate(client, id_to_key, img_cases)}

    text_rows = res["TR metin"] + res["EN metin"]
    summary = {name: metrics(rows) for name, rows in res.items()}
    dists = {
        "Metin (TR+EN) doğru": dist(r["correct_score"] for r in text_rows),
        "Metin (TR+EN) en iyi yanlış": dist(r["best_wrong_score"] for r in text_rows),
        "Metin (TR+EN) tüm yanlışlar": dist(s for r in text_rows for s in r["wrong_scores"]),
        "TR doğru": dist(r["correct_score"] for r in res["TR metin"]),
        "TR en iyi yanlış": dist(r["best_wrong_score"] for r in res["TR metin"]),
        "Görsel doğru": dist(r["correct_score"] for r in res["Görsel"]),
        "Görsel en iyi yanlış": dist(r["best_wrong_score"] for r in res["Görsel"]),
        "Görsel tüm yanlışlar": dist(s for r in res["Görsel"] for s in r["wrong_scores"]),
    }
    thr = suggest_thresholds(text_rows)
    levels_text = level_counts(text_rows, thr["match_high"], thr["match_medium"])
    levels_img = level_counts(res["Görsel"], thr["match_high"], thr["match_medium"])
    took = [r["took_ms"] for rows in res.values() for r in rows]
    failures = [{"tür": name, **r} for name, rows in res.items() for r in rows if r["rank"] != 1]

    out = {
        "api_url": args.api_url, "item_count": health["item_count"], "extra_items_in_api": extra,
        "template_tr": args.template, "template_en": args.template_en, "category_filter": bool(cat_map),
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "summary": summary, "score_distribution": dists, "threshold_suggestion": thr,
        "levels_with_suggestion": {"metin": levels_text, "görsel": levels_img},
        "api_took_ms": {"median": round(statistics.median(took), 1), "max": round(max(took), 1)},
        "failures": failures,
        "per_query": {k: [{f: v for f, v in r.items() if f != "wrong_scores"} for r in rows] for k, rows in res.items()},
    }

    print("# Arama başarımı\n")
    print(f"API: {args.api_url} | item_count={health['item_count']} | şablon TR=`{args.template}` EN=`{args.template_en}`"
          f" | kategori filtresi={'açık' if cat_map else 'kapalı'}\n")
    print(md_table(["Sorgu türü", "n", "R@1", "R@5", "MRR"],
                   [[k, v["n"], v["R@1"], v["R@5"], v["MRR"]] for k, v in summary.items()]))
    print("\n## Skor dağılımı\n")
    print(md_table(["Küme", "n", "min", "p10", "medyan", "p90", "maks"],
                   [[k, *(v[f] for f in ("n", "min", "p10", "median", "p90", "max"))] for k, v in dists.items() if v]))
    print("\n## Eşik önerisi (metin skorlarından)\n")
    print(f"- match_medium = {thr['match_medium']} (doğru vs. tüm yanlışlar Youden J={thr['medium_J']}): doğruların "
          f"{thr['medium_TPR']:.0%}'i, tüm yanlışların {thr['medium_FPR_all']:.0%}'i, en iyi yanlışların "
          f"{thr['medium_FPR_best']:.0%}'i bu eşiği geçiyor")
    print(f"- match_high = {thr['match_high']} (en iyi yanlışların p90'ı): doğruların {thr['high_TPR']:.0%}'i, "
          f"en iyi yanlışların {thr['high_FPR_best']:.0%}'i, tüm yanlışların {thr['high_FPR_all']:.0%}'i bu eşiği geçiyor")
    jb = thr["youden_vs_best_wrong"]
    print(f"- Karşılaştırma: doğru vs. en iyi yanlış için en iyi eşik {jb['t']} (J={jb['J']}); "
          f"J küçükse skor tek başına doğruyu en benzer yanlıştan ayıramıyor, ayrımı sıralama yapıyor")
    print(f"- Bu eşiklerle metin düzeyleri: {levels_text}")
    print(f"- Bu eşiklerle görsel düzeyleri: {levels_img}")
    print(f"- API took_ms medyan {out['api_took_ms']['median']}, maks {out['api_took_ms']['max']}")
    print("\n## Başarısız sorgular (doğru ilan 1. sırada değil)\n")
    print(md_table(["Tür", "Sorgu", "Beklenen", "Sıra", "1. sıradaki", "Doğru skor", "En iyi yanlış"],
                   [[f["tür"], f["label"], f["expected"], f["rank"] or ">50", f["top1"], f["correct_score"],
                     f["best_wrong_score"]] for f in failures]))

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, ensure_ascii=False, indent=2), "utf-8")
        print(f"\nJSON: {args.json_out}")


if __name__ == "__main__":
    main()
