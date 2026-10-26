import type {
  CreateItemParams,
  Item,
  ItemList,
  ListParams,
  LostReportCreated,
  LostReportParams,
  Meta,
  ReportMatches,
  SearchParams,
  SearchResponse,
} from "./types";

const API_URL: string = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");
const TIMEOUT_MS = 60_000;

export const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readDetail(res: Response): Promise<string | null> {
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail) return detail;
    }
  } catch {
    // gövde JSON değil
  }
  return null;
}

// Uygulamadaki TEK fetch çağrısı.
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "İstek zaman aşımına uğradı. Lütfen tekrar deneyin.");
    }
    throw new ApiError(0, "Sunucuya ulaşılamadı.");
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    if (res.status === 503) {
      throw new ApiError(503, "Model yükleniyor, birkaç saniye sonra tekrar deneyin.");
    }
    const detail = await readDetail(res);
    throw new ApiError(
      res.status,
      detail ?? `Beklenmeyen bir hata oluştu (kod ${res.status}).`,
    );
  }
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError(res.status, "Sunucudan geçersiz bir yanıt alındı.");
  }
}

export function getMeta(): Promise<Meta> {
  return request<Meta>("/api/meta");
}

export function listItems(params: ListParams = {}): Promise<ItemList> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.location) qs.set("location", params.location);
  if (params.category) qs.set("category", params.category);
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  const suffix = qs.toString();
  return request<ItemList>(`/api/items${suffix ? `?${suffix}` : ""}`);
}

export function searchItems(params: SearchParams): Promise<SearchResponse> {
  const form = new FormData();
  if (params.query) form.append("query", params.query);
  if (params.image) form.append("image", params.image);
  if (params.location) form.append("location", params.location);
  if (params.category) form.append("category", params.category);
  if (params.include_returned !== undefined) {
    form.append("include_returned", String(params.include_returned));
  }
  if (params.top_k !== undefined) form.append("top_k", String(params.top_k));
  return request<SearchResponse>("/api/search", { method: "POST", body: form });
}

export function createItem(params: CreateItemParams): Promise<Item> {
  const form = new FormData();
  form.append("image", params.image);
  form.append("title", params.title);
  form.append("description", params.description);
  form.append("location", params.location);
  form.append("found_date", params.found_date);
  form.append("dropoff_point", params.dropoff_point);
  return request<Item>("/api/items", { method: "POST", body: form });
}

export function createLostReport(params: LostReportParams): Promise<LostReportCreated> {
  const form = new FormData();
  if (params.query) form.append("query", params.query);
  if (params.image) form.append("image", params.image);
  if (params.location) form.append("location", params.location);
  return request<LostReportCreated>("/api/lost-reports", { method: "POST", body: form });
}

export function getReportMatches(code: string): Promise<ReportMatches> {
  return request<ReportMatches>(`/api/lost-reports/${encodeURIComponent(code)}/matches`);
}

// Göreli image_url'yi API adresiyle birleştirir.
export function imageSrc(item: Pick<Item, "image_url">): string {
  return /^https?:\/\//.test(item.image_url) ? item.image_url : `${API_URL}${item.image_url}`;
}

// İstemci tarafı ön kontrol; hata varsa Türkçe mesaj, yoksa null.
export function validateImage(file: File, maxMb: number): string | null {
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    return "Desteklenmeyen dosya türü. JPEG, PNG veya WebP yükleyin.";
  }
  if (file.size > maxMb * 1024 * 1024) {
    return `Dosya çok büyük. En fazla ${maxMb} MB yükleyebilirsiniz.`;
  }
  return null;
}
