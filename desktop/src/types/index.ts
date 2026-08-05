export type LogStatus = "unread" | "reading" | "read" | "abandoned";

export interface ReadingLog {
  id: string;
  isbn: string | null;
  title: string;
  author: string | null;
  publisher: string | null;
  status: LogStatus;
  resonance: number; // 0 or 1
  started_at: string | null;
  finished_at: string | null;
  notes: string | null;
  updated_at: string;
}

export interface NewReadingLog {
  id?: string | null;
  isbn?: string | null;
  title: string;
  author?: string | null;
  publisher?: string | null;
  status?: LogStatus;
  resonance?: number;
  started_at?: string | null;
  finished_at?: string | null;
  notes?: string | null;
}

export interface UpdateLogPayload {
  id: string;
  title?: string | null;
  author?: string | null;
  publisher?: string | null;
  isbn?: string | null;
  status?: LogStatus | null;
  resonance?: number | null;
  started_at?: string | null;
  finished_at?: string | null;
  notes?: string | null;
}

export interface CandidateItem {
  tempId: string;
  title: string;
  author: string | null;
  publisher: string | null;
  isbn: string | null;
  source: "google_books" | "lemma_centroid";
  distance?: number;
  notes?: string | null;
}
