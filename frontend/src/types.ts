// docs/PLAN.md "API sözleşmesi" ile birebir.

export type ItemStatus = "bekliyor" | "teslim_edildi";
export type MatchLevel = "yüksek" | "orta" | "düşük";

export interface Item {
  id: string;
  title: string;
  description: string;
  location: string;
  found_date: string; // YYYY-MM-DD
  dropoff_point: string;
  image_url: string; // göreli: /uploads/<uuid>.jpg
  category: string;
  category_score: number;
  color: string;
  faces_blurred: number;
  status: ItemStatus;
  created_at: string;
}

export interface Meta {
  locations: string[];
  dropoff_points: string[];
  categories: string[];
  colors: string[];
  max_upload_mb: number;
}

export interface ItemList {
  items: Item[];
  total: number;
}

export interface SearchResult {
  item: Item;
  score: number;
  match_level: MatchLevel;
}

export interface SearchResponse {
  results: SearchResult[];
  took_ms: number;
}

export interface ListParams {
  status?: ItemStatus;
  location?: string;
  category?: string;
  limit?: number;
  offset?: number;
}

export interface SearchParams {
  query?: string;
  image?: File | null;
  location?: string;
  category?: string;
  include_returned?: boolean;
  top_k?: number;
}

export interface CreateItemParams {
  image: File;
  title: string;
  description: string;
  location: string;
  found_date: string;
  dropoff_point: string;
}

export interface LostReportParams {
  query?: string;
  image?: File | null;
  location?: string;
}

export interface LostReportCreated {
  tracking_code: string;
}

export interface ReportMatches {
  created_at: string;
  query_text: string;
  matches: SearchResult[];
}
