import { CandidateItem, NewReadingLog } from "../types";

interface GoogleBookItem {
  id: string;
  volumeInfo: {
    title: string;
    authors?: string[];
    publisher?: string;
    industryIdentifiers?: Array<{ type: string; identifier: string }>;
  };
}

function extractIsbn(identifiers?: Array<{ type: string; identifier: string }>): string | null {
  if (!identifiers || identifiers.length === 0) return null;
  const isbn13 = identifiers.find((i) => i.type === "ISBN_13");
  if (isbn13) return isbn13.identifier;
  const isbn10 = identifiers.find((i) => i.type === "ISBN_10");
  if (isbn10) return isbn10.identifier;
  return identifiers[0].identifier;
}

function buildQuery(title?: string, author?: string): string {
  const parts: string[] = [];
  const cleanTitle = title?.trim();
  const cleanAuthor = author?.trim();

  if (cleanTitle) {
    parts.push(`intitle:${cleanTitle}`);
  }
  if (cleanAuthor) {
    parts.push(`inauthor:${cleanAuthor}`);
  }

  return parts.join("+");
}

export async function searchBooksFlexible(
  title?: string,
  author?: string,
  maxResults = 5
): Promise<CandidateItem[]> {
  const queryStr = buildQuery(title, author);
  if (!queryStr) return [];

  const url = `https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(
    queryStr
  )}&maxResults=${maxResults}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Google Books API error: ${res.status}`);
    const data = await res.json();

    if (data.items && data.items.length > 0) {
      return data.items.map((item: GoogleBookItem) => {
        const volume = item.volumeInfo;
        return {
          tempId: `candidate_gb_${item.id}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          title: volume.title || title?.trim() || "Untitled",
          author: volume.authors ? volume.authors.join(", ") : author?.trim() || null,
          publisher: volume.publisher || null,
          isbn: extractIsbn(volume.industryIdentifiers),
          source: "google_books" as const,
        };
      });
    }
  } catch (err) {
    console.warn("Google Books searchBooksFlexible error:", err);
  }

  return [];
}

export async function searchByComposite(title: string, author?: string): Promise<NewReadingLog> {
  const cleanTitle = title.trim();
  const cleanAuthor = author?.trim();

  const queryStr = buildQuery(cleanTitle, cleanAuthor);
  const url = `https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(
    queryStr
  )}&maxResults=1`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Google Books API error: ${res.status}`);
    const data = await res.json();

    if (data.items && data.items.length > 0) {
      const item: GoogleBookItem = data.items[0];
      const volume = item.volumeInfo;
      return {
        title: volume.title || cleanTitle,
        author: volume.authors ? volume.authors.join(", ") : cleanAuthor || null,
        publisher: volume.publisher || null,
        isbn: extractIsbn(volume.industryIdentifiers),
        status: "unread",
        resonance: 0,
        started_at: null,
        finished_at: null,
      };
    }
  } catch (err) {
    console.warn("Google Books API fallback to input values:", err);
  }

  // Fallback to user-supplied values
  return {
    title: cleanTitle,
    author: cleanAuthor || null,
    publisher: null,
    isbn: null,
    status: "unread",
    resonance: 0,
    started_at: null,
    finished_at: null,
  };
}

export async function searchByTitle(title: string): Promise<NewReadingLog> {
  return searchByComposite(title);
}

export async function searchByAuthor(author: string): Promise<CandidateItem[]> {
  return searchBooksFlexible(undefined, author, 5);
}

/** Fetch only bibliographic fill data (author, publisher, isbn) for a single title.
 *  Used exclusively by the Auto-Fill batch process. Returns null if nothing found. */
export async function fetchBibliographyForTitle(title: string): Promise<{
  author: string | null;
  publisher: string | null;
  isbn: string | null;
} | null> {
  const query = `intitle:${title.trim()}`;
  const url = `https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(query)}&maxResults=1`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.warn(`[AutoFill] Google Books API ${res.status} for "${title}"`);
      return null;
    }
    const data = await res.json();
    if (!data.items || data.items.length === 0) return null;
    const volume = (data.items[0] as GoogleBookItem).volumeInfo;
    return {
      author: volume.authors ? volume.authors.join(", ") : null,
      publisher: volume.publisher || null,
      isbn: extractIsbn(volume.industryIdentifiers),
    };
  } catch (err) {
    console.warn(`[AutoFill] fetch error for "${title}":`, err);
    return null;
  }
}
