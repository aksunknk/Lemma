import { save, open } from "@tauri-apps/plugin-dialog";
import { writeTextFile, readTextFile } from "@tauri-apps/plugin-fs";
import { ReadingLog, NewReadingLog, LogStatus } from "../types";
import { batchAddLogs } from "./tauriCommands";

function escapeCsvField(val: string | number | null | undefined): string {
  if (val === null || val === undefined) return "";
  const str = String(val);
  if (str.includes(",") || str.includes('"') || str.includes("\n") || str.includes("\r")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function parseCsv(content: string): Array<Record<string, string>> {
  // Strip UTF-8 BOM if present
  const clean = content.charCodeAt(0) === 0xfeff ? content.slice(1) : content;

  const lines: string[][] = [];
  let currentRow: string[] = [];
  let currentField = "";
  let insideQuotes = false;

  for (let i = 0; i < clean.length; i++) {
    const char = clean[i];
    const nextChar = clean[i + 1];

    if (char === '"') {
      if (insideQuotes && nextChar === '"') {
        currentField += '"';
        i++; // skip escaped quote
      } else {
        insideQuotes = !insideQuotes;
      }
    } else if (char === "," && !insideQuotes) {
      currentRow.push(currentField.trim());
      currentField = "";
    } else if ((char === "\r" || char === "\n") && !insideQuotes) {
      if (char === "\r" && nextChar === "\n") {
        i++;
      }
      currentRow.push(currentField.trim());
      currentField = "";
      if (currentRow.some((f) => f.length > 0)) {
        lines.push(currentRow);
      }
      currentRow = [];
    } else {
      currentField += char;
    }
  }

  if (currentField.length > 0 || currentRow.length > 0) {
    currentRow.push(currentField.trim());
    if (currentRow.some((f) => f.length > 0)) {
      lines.push(currentRow);
    }
  }

  if (lines.length === 0) return [];

  const headers = lines[0].map((h) => h.toLowerCase());
  const results: Array<Record<string, string>> = [];

  for (let i = 1; i < lines.length; i++) {
    const row = lines[i];
    const record: Record<string, string> = {};
    headers.forEach((header, index) => {
      record[header] = row[index] || "";
    });
    results.push(record);
  }

  return results;
}

export async function exportLogsToCsv(logs: ReadingLog[]): Promise<string | null> {
  const filePath = await save({
    defaultPath: `lemma_reading_logs_${new Date().toISOString().slice(0, 10)}.csv`,
    filters: [
      {
        name: "CSV Document (*.csv)",
        extensions: ["csv"],
      },
    ],
  });

  if (!filePath) return null;

  const headers = [
    "id",
    "isbn",
    "title",
    "author",
    "publisher",
    "status",
    "resonance",
    "started_at",
    "finished_at",
    "notes",
    "tags",
    "updated_at",
  ];

  const rows = logs.map((log) => [
    escapeCsvField(log.id),
    escapeCsvField(log.isbn),
    escapeCsvField(log.title),
    escapeCsvField(log.author),
    escapeCsvField(log.publisher),
    escapeCsvField(log.status),
    escapeCsvField(log.resonance),
    escapeCsvField(log.started_at),
    escapeCsvField(log.finished_at),
    escapeCsvField(log.notes),
    escapeCsvField(log.tags),
    escapeCsvField(log.updated_at),
  ]);

  const csvBody = [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
  // Prepend UTF-8 BOM for seamless Excel compatibility
  const csvContentWithBom = "\uFEFF" + csvBody;

  await writeTextFile(filePath, csvContentWithBom);
  return filePath;
}

export async function importLogsFromCsv(): Promise<{ count: number; path: string } | null> {
  const selected = await open({
    multiple: false,
    filters: [
      {
        name: "CSV Document (*.csv)",
        extensions: ["csv"],
      },
    ],
  });

  if (!selected || typeof selected !== "string") return null;

  const rawContent = await readTextFile(selected);
  const parsedRecords = parseCsv(rawContent);

  if (parsedRecords.length === 0) {
    throw new Error("CSV file is empty or formatted incorrectly");
  }

  const validStatuses: Set<LogStatus> = new Set(["unread", "reading", "read", "abandoned"]);

  const logsToInsert: NewReadingLog[] = parsedRecords
    .filter((rec) => rec.title && rec.title.trim().length > 0)
    .map((rec) => {
      const rawStatus = (rec.status || "").toLowerCase().trim() as LogStatus;
      const status: LogStatus = validStatuses.has(rawStatus) ? rawStatus : "unread";
      const resonance = rec.resonance === "1" || rec.resonance === "true" ? 1 : 0;

      return {
        id: rec.id?.trim() || undefined,
        isbn: rec.isbn?.trim() || null,
        title: rec.title.trim(),
        author: rec.author?.trim() || null,
        publisher: rec.publisher?.trim() || null,
        status,
        resonance,
        started_at: rec.started_at?.trim() || null,
        finished_at: rec.finished_at?.trim() || null,
        notes: rec.notes?.trim() || null,
        tags: rec.tags?.trim() || null,
      };
    });

  if (logsToInsert.length === 0) {
    throw new Error("No valid book entries with titles found in CSV");
  }

  const count = await batchAddLogs(logsToInsert);
  return { count, path: selected };
}
