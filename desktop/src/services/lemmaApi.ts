import { invoke } from "@tauri-apps/api/core";
import { CandidateItem, CentroidRequestItem } from "../types";

export interface CentroidResponseItem {
  id?: string;
  item_id?: string;
  title: string;
  author?: string;
  publisher?: string;
  source?: string;
  isbn?: string;
  year?: number;
  origin?: number;
  style?: number;
  renown?: number;
  distance?: number;
  status?: number;
}

export async function extractCentroid(items: CentroidRequestItem[]): Promise<CandidateItem[]> {
  if (items.length === 0) return [];

  const apiUrl = import.meta.env.VITE_LEMMA_API_URL || "http://192.168.0.130:8000";

  // Invoke native Rust command to bypass browser WebView CORS limitations completely
  const data = await invoke<CentroidResponseItem[]>("extract_centroid_api", {
    items,
    apiUrl,
  });

  return data.map((item, idx) => ({
    tempId: `candidate_lemma_${Date.now()}_${idx}_${Math.random().toString(36).slice(2, 6)}`,
    title: item.title,
    author: item.author || null,
    publisher: item.publisher || item.source || null,
    isbn: item.isbn || null,
    source: "lemma_centroid" as const,
    distance: item.distance,
  }));
}

export interface ExtractConceptsResponse {
  tags: string[];
}

export async function extractConceptsFromNote(note: string): Promise<string[]> {
  if (!note || note.trim().length === 0) return [];
  const apiUrl = import.meta.env.VITE_LEMMA_API_URL || "http://192.168.0.130:8000";

  // Invoke native Rust command to bypass browser WebView CORS limitations completely
  const tags = await invoke<string[]>("extract_concepts_api", {
    note,
    apiUrl,
  });

  return Array.isArray(tags) ? tags : [];
}


