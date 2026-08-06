import { CandidateItem, NewReadingLog } from "../types";

interface GoogleBookItem {
  id: string;
  volumeInfo: {
    title: string;
    authors?: string[];
    publisher?: string;
    industryIdentifiers?: Array<{ type: string; identifier: string }>;
    language?: string;
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

function buildQuery(title?: string, author?: string, isbn?: string): string {
  const parts: string[] = [];
  const cleanTitle = title?.trim();
  const cleanAuthor = author?.trim();
  const cleanIsbn = isbn?.trim();

  if (cleanIsbn && cleanIsbn !== "---") {
    parts.push(`isbn:${cleanIsbn.replace(/[^0-9X]/gi, "")}`);
  }
  if (cleanTitle && cleanTitle !== "---") {
    parts.push(`intitle:${cleanTitle}`);
  }
  if (cleanAuthor && cleanAuthor !== "---") {
    parts.push(`inauthor:${cleanAuthor}`);
  }

  return parts.join("+");
}

const GOOGLE_BOOKS_API_KEY = import.meta.env.VITE_GOOGLE_BOOKS_API_KEY || "";

function buildGoogleBooksUrl(queryStr: string, maxResults = 5, langRestrict = "ja"): string {
  let url = `https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(
    queryStr
  )}&maxResults=${maxResults}`;
  if (langRestrict) {
    url += `&langRestrict=${encodeURIComponent(langRestrict)}`;
  }
  if (GOOGLE_BOOKS_API_KEY) {
    url += `&key=${encodeURIComponent(GOOGLE_BOOKS_API_KEY)}`;
  }
  return url;
}

function cleanString(str: string): string {
  return str
    .toLowerCase()
    .replace(/[【】『』「」［］\[\]（）()・：:　\s_\-—－]/g, "")
    .trim();
}

function scoreGoogleBookCandidate(
  volume: GoogleBookItem["volumeInfo"],
  targetTitle: string,
  targetAuthor?: string | null
): number {
  let score = 0;
  const candTitle = volume.title || "";
  const normTargetTitle = cleanString(targetTitle);
  const normCandTitle = cleanString(candTitle);

  // Exact title match
  if (normCandTitle === normTargetTitle) {
    score += 100;
  } else if (normCandTitle.startsWith(normTargetTitle)) {
    score += 60;
  } else if (normCandTitle.includes(normTargetTitle)) {
    score += 30;
  } else {
    // Title doesn't contain target title
    score -= 40;
  }

  // Noise penalty for derivative works (unless target explicitly requested them)
  const noiseKeywords = ["超訳", "解説", "まんが", "コミック", "を読む", "入門", "要約", "ガイド", "要点"];
  for (const kw of noiseKeywords) {
    if (candTitle.includes(kw) && !targetTitle.includes(kw)) {
      score -= 50;
    }
  }

  // Author match
  if (targetAuthor && targetAuthor.trim() && targetAuthor !== "---") {
    const normTargetAuthor = cleanString(targetAuthor);
    const candAuthors = (volume.authors || []).map(cleanString);
    const hasAuthorMatch = candAuthors.some(
      (a) => a.includes(normTargetAuthor) || normTargetAuthor.includes(a)
    );
    if (hasAuthorMatch) {
      score += 80;
    } else if (candAuthors.length > 0) {
      // Author provided but candidate authors don't match
      score -= 60;
    }
  }

  // Valid ISBN bonus
  const isbn = extractIsbn(volume.industryIdentifiers);
  if (isbn && isbn.length >= 10) {
    score += 20;
  }

  // Valid Japanese publisher bonus
  if (volume.publisher && !/google|bccks|unknown|出版/i.test(volume.publisher)) {
    score += 15;
  }

  return score;
}

/** OpenBD Japanese Official Book Metadata API (100% accurate publisher/author) */
export async function fetchOpenBdByIsbn(isbn: string): Promise<{
  title?: string;
  author?: string;
  publisher?: string;
} | null> {
  const cleanIsbn = isbn.replace(/[^0-9X]/gi, "");
  if (cleanIsbn.length < 10) return null;
  try {
    const res = await fetch(`https://api.openbd.jp/v1/get?isbn=${cleanIsbn}`);
    if (!res.ok) return null;
    const data = await res.json();
    if (Array.isArray(data) && data[0]?.summary) {
      const s = data[0].summary;
      return {
        title: s.title || undefined,
        author: s.author || undefined,
        publisher: s.publisher || undefined,
      };
    }
  } catch {
    // Ignore OpenBD network errors
  }
  return null;
}

export async function searchBooksFlexible(
  title?: string,
  author?: string,
  maxResults = 5
): Promise<CandidateItem[]> {
  const queryStr = buildQuery(title, author);
  if (!queryStr) return [];

  const url = buildGoogleBooksUrl(queryStr, maxResults, "ja");

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Google Books API error: ${res.status}`);
    const data = await res.json();

    if (data.items && data.items.length > 0) {
      const results: CandidateItem[] = [];
      for (const item of data.items) {
        const volume = (item as GoogleBookItem).volumeInfo;
        let resolvedPublisher = volume.publisher || null;
        let resolvedAuthor = volume.authors ? volume.authors.join(", ") : author?.trim() || null;
        const resolvedIsbn = extractIsbn(volume.industryIdentifiers);

        if (resolvedPublisher && /google\s*play|bccks|kobo/i.test(resolvedPublisher)) {
          resolvedPublisher = null;
        }

        if (resolvedIsbn) {
          const obd = await fetchOpenBdByIsbn(resolvedIsbn);
          if (obd?.publisher) resolvedPublisher = obd.publisher;
          if (obd?.author && (!volume.authors || volume.authors.length === 0)) {
            resolvedAuthor = obd.author;
          }
        }

        results.push({
          tempId: `candidate_gb_${item.id}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          title: volume.title || title?.trim() || "Untitled",
          author: resolvedAuthor,
          publisher: resolvedPublisher,
          isbn: resolvedIsbn,
          source: "google_books" as const,
        });
      }
      return results;
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
  const url = buildGoogleBooksUrl(queryStr, 5, "ja");

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Google Books API error: ${res.status}`);
    const data = await res.json();

    if (data.items && data.items.length > 0) {
      // Pick best candidate
      let bestItem = data.items[0];
      let bestScore = -Infinity;
      for (const it of data.items) {
        const sc = scoreGoogleBookCandidate(it.volumeInfo, cleanTitle, cleanAuthor);
        if (sc > bestScore) {
          bestScore = sc;
          bestItem = it;
        }
      }

      const volume = bestItem.volumeInfo;
      let resolvedPublisher = volume.publisher || null;
      let resolvedAuthor = volume.authors ? volume.authors.join(", ") : cleanAuthor || null;
      const resolvedIsbn = extractIsbn(volume.industryIdentifiers);

      // Verify with OpenBD if ISBN exists for accurate Japanese publisher
      if (resolvedIsbn) {
        const obd = await fetchOpenBdByIsbn(resolvedIsbn);
        if (obd?.publisher) resolvedPublisher = obd.publisher;
        if (obd?.author && !cleanAuthor) resolvedAuthor = obd.author;
      }

      return {
        title: volume.title || cleanTitle,
        author: resolvedAuthor,
        publisher: resolvedPublisher,
        isbn: resolvedIsbn,
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

/** Fetch high-accuracy bibliographic fill data (author, publisher, isbn).
 *  Used by the Auto-Fill batch process.
 *  Uses compound query + top-5 scoring + OpenBD validation for pristine Japanese metadata. */
export async function fetchBibliographyForTitle(
  title: string,
  author?: string | null,
  isbn?: string | null
): Promise<{
  author: string | null;
  publisher: string | null;
  isbn: string | null;
} | null> {
  const cleanTitle = title.trim();
  const cleanAuthor = author && author !== "---" ? author.trim() : undefined;
  const cleanIsbn = isbn && isbn !== "---" ? isbn.trim() : undefined;

  // 1. Direct OpenBD check if ISBN already exists
  if (cleanIsbn) {
    const obd = await fetchOpenBdByIsbn(cleanIsbn);
    if (obd && (obd.author || obd.publisher)) {
      return {
        author: obd.author || null,
        publisher: obd.publisher || null,
        isbn: cleanIsbn,
      };
    }
  }

  // 2. Google Books API with compound query & top 5 candidate scoring
  const query = buildQuery(cleanTitle, cleanAuthor, cleanIsbn);
  const url = buildGoogleBooksUrl(query, 5, "ja");

  const fetchWithRetry = async (retryCount = 0): Promise<Response | null> => {
    try {
      const res = await fetch(url);
      if (res.status === 429 && retryCount < 2) {
        console.warn(`[AutoFill] Rate limited (429) for "${title}". Backing off 3s (retry ${retryCount + 1}/2)...`);
        await new Promise((resolve) => setTimeout(resolve, 3000));
        return fetchWithRetry(retryCount + 1);
      }
      return res;
    } catch (err) {
      if (retryCount < 2) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        return fetchWithRetry(retryCount + 1);
      }
      throw err;
    }
  };

  try {
    const res = await fetchWithRetry();
    if (!res || !res.ok) {
      if (res && res.status !== 429) {
        console.warn(`[AutoFill] Google Books API ${res.status} for "${title}"`);
      }
      return null;
    }
    const data = await res.json();
    if (!data.items || data.items.length === 0) return null;

    // Evaluate all candidates and select highest scoring match
    let bestItem = data.items[0];
    let bestScore = -Infinity;

    for (const it of data.items) {
      const score = scoreGoogleBookCandidate(it.volumeInfo, cleanTitle, cleanAuthor);
      if (score > bestScore) {
        bestScore = score;
        bestItem = it;
      }
    }

    // If best score is too negative, avoid low-quality mismatch
    if (bestScore < 0) {
      console.warn(`[AutoFill] Low confidence match rejected for "${title}" (score: ${bestScore})`);
      return null;
    }

    const volume = (bestItem as GoogleBookItem).volumeInfo;
    let resolvedPublisher = volume.publisher || null;
    let resolvedAuthor = volume.authors ? volume.authors.join(", ") : null;
    const resolvedIsbn = extractIsbn(volume.industryIdentifiers);

    // Clean noisy publisher names like "Google Play Books" or "BCCKS"
    if (resolvedPublisher && /google\s*play|bccks|kobo/i.test(resolvedPublisher)) {
      resolvedPublisher = null;
    }

    // If an ISBN is found, verify and refine publisher name via OpenBD
    if (resolvedIsbn) {
      const obd = await fetchOpenBdByIsbn(resolvedIsbn);
      if (obd?.publisher) {
        resolvedPublisher = obd.publisher;
      }
      if (obd?.author && !cleanAuthor) {
        resolvedAuthor = obd.author;
      }
    }

    return {
      author: resolvedAuthor,
      publisher: resolvedPublisher,
      isbn: resolvedIsbn,
    };
  } catch (err) {
    console.warn(`[AutoFill] fetch error for "${title}":`, err);
    return null;
  }
}
