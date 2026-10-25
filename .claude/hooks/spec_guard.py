#!/usr/bin/env python3
"""PreToolUse koruması: şartname yasaklarını kod ve komut seviyesinde engeller.
Çıkış kodu 2 = işlem engellenir, stderr Claude'a geri bildirilir."""
import json
import os
import re
import sys

CODE_EXT = (".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".txt", ".yml", ".yaml",
            ".toml", ".cfg", ".ini", ".conf", ".sh", ".env.example")
CODE_NAMES = ("Dockerfile", "docker-compose.yml", "requirements.txt", "package.json")

FORBIDDEN_CODE = [
    (r"ultralytics", "YOLO/ultralytics yasak (şartname md. 2)"),
    (r"\byolo", "YOLO ailesi yasak (şartname md. 2)"),
    (r"\bopenai\b", "OpenAI API/SDK yasak (şartname md. 4)"),
    (r"\banthropic\b", "Claude/Anthropic API ürün içinde yasak (şartname md. 4)"),
    (r"generativeai|generativelanguage|vertexai", "Gemini/Vertex API yasak (şartname md. 4)"),
    (r"\bgroq\b|\bcohere\b|\breplicate\b|\btogether\.ai\b", "Bulut AI servisi yasak (şartname md. 4)"),
    (r"api-inference\.huggingface|InferenceClient", "HF Inference API (bulut) yasak (şartname md. 4)"),
    (r"\.cuda\(|device\s*=\s*['\"]cuda", "GPU varsayılamaz; yalnızca CPU (şartname md. 1)"),
]

FORBIDDEN_BASH = [
    (r"git\s+push\b.*(--force|\s-f\b|--force-with-lease)", "Force push yasak (şartname md. 7)"),
    (r"git\s+commit\b.*--(date|no-verify)", "Commit tarihi/hook atlama yasak (şartname md. 7)"),
    (r"GIT_(AUTHOR|COMMITTER)_DATE", "Commit tarihi değiştirmek yasak (şartname md. 7)"),
    (r"(pip|uv)\s+install\b.*\b(ultralytics|openai|anthropic|google-generativeai|groq|cohere)\b",
     "Yasaklı paket kurulumu (şartname md. 2/4)"),
    (r"npm\s+(i|install|add)\b.*\b(openai|@anthropic-ai|@google/generative-ai)\b",
     "Yasaklı paket kurulumu (şartname md. 4)"),
    (r"git\s+add\b.*(^|\s)\.env(\s|$)", ".env depoya eklenemez (şartname md. 6)"),
]


def block(msg: str) -> None:
    print(f"ŞARTNAME KORUMASI: {msg}. CLAUDE.md'deki MUTLAK YASAKLAR'a bak; "
          f"gerekiyorsa kullanıcıya sor.", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}

    if tool == "Bash":
        cmd = ti.get("command", "")
        for pat, msg in FORBIDDEN_BASH:
            if re.search(pat, cmd, re.IGNORECASE):
                block(msg)
        sys.exit(0)

    path = ti.get("file_path", "") or ""
    norm = path.replace("\\", "/")
    if "/.claude/" in norm or norm.startswith(".claude/") or norm.endswith(".md"):
        sys.exit(0)
    base = os.path.basename(norm)
    if base == ".env":
        block(".env dosyasına yazılmaz; .env.example kullan")
    if not (norm.endswith(CODE_EXT) or base in CODE_NAMES):
        sys.exit(0)

    if tool == "Write":
        texts = [ti.get("content", "")]
    elif tool == "Edit":
        texts = [ti.get("new_string", "")]
    elif tool == "MultiEdit":
        texts = [e.get("new_string", "") for e in ti.get("edits", [])]
    else:
        texts = []
    blob = "\n".join(texts)
    for pat, msg in FORBIDDEN_CODE:
        if re.search(pat, blob, re.IGNORECASE):
            block(f"{msg} ({path})")
    sys.exit(0)


if __name__ == "__main__":
    main()
