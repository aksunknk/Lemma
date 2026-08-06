import React, { useState } from "react";
import { extractCentroid } from "../services/lemmaApi";
import { CandidateItem, ReadingLog } from "../types";

interface FooterBarProps {
  logs: ReadingLog[];
  onInferenceCompleted: (results: CandidateItem[]) => void;
  onExportCsv: () => Promise<void>;
  onImportCsv: () => Promise<void>;
  setStatusMessage: (msg: string) => void;
}

export const FooterBar: React.FC<FooterBarProps> = ({
  logs,
  onInferenceCompleted,
  onExportCsv,
  onImportCsv,
  setStatusMessage,
}) => {
  const [isExtracting, setIsExtracting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const resonantLogs = logs.filter((l) => l.resonance === 1);
  const resonanceCount = resonantLogs.length;

  const isDateValid = (val: string | null | undefined): boolean => {
    if (!val) return false;
    const trimmed = val.trim();
    return trimmed !== "" && trimmed !== "---" && trimmed !== "null" && trimmed !== "undefined";
  };

  const extractLogDate = (log: ReadingLog): string | null => {
    if (isDateValid(log.finished_at)) {
      return log.finished_at!.trim();
    }
    if (isDateValid(log.started_at)) {
      return log.started_at!.trim();
    }
    return null;
  };

  const handleExtractCentroid = async () => {
    if (resonanceCount === 0 || isExtracting) return;

    setIsExtracting(true);
    setStatusMessage(`CALCULATING CENTROID FOR ${resonanceCount} RESONANT TITLES...`);

    try {
      const items = resonantLogs.map((l) => ({
        title: l.title,
        date: extractLogDate(l),
      }));
      const candidates = await extractCentroid(items);

      if (candidates.length === 0) {
        setStatusMessage("LEMMA API: NO RECOMMENDATIONS RETURNED");
      } else {
        onInferenceCompleted(candidates);
        setStatusMessage(`LEMMA API: CENTROID INFERENCE BUFFER READY [${candidates.length} CANDIDATES]`);
      }
    } catch (err) {
      console.error("Centroid extraction error:", err);
      setStatusMessage(`INFERENCE ERROR: ${String(err)}`);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleExport = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    try {
      await onExportCsv();
    } finally {
      setIsSyncing(false);
    }
  };

  const handleImport = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    try {
      await onImportCsv();
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <footer className="border-t border-cyan-900/40 bg-[#020408] px-4 py-2.5 font-mono text-xs text-[#00e5ff] select-none flex items-center justify-between">
      {/* Left: Resonance Pool Visualizer */}
      <div className="flex items-center space-x-3 overflow-hidden mr-4">
        <div className="flex items-center space-x-2 whitespace-nowrap">
          <span className="text-cyan-600 font-bold">RESONANCE POOL:</span>
          <span
            className={`border px-2 py-0.5 text-[11px] font-bold ${
              resonanceCount > 0
                ? "border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff]"
                : "border-cyan-900/50 bg-cyan-950/20 text-cyan-700"
            }`}
          >
            [ {resonanceCount} {resonanceCount === 1 ? "ITEM" : "ITEMS"} ]
          </span>
        </div>

        {/* Resonant titles ticker / tags */}
        <div className="flex items-center space-x-2 overflow-x-auto no-scrollbar text-[11px]">
          {resonantLogs.length > 0 ? (
            resonantLogs.map((l) => (
              <span
                key={l.id}
                className="font-sans border border-cyan-800/40 bg-cyan-950/30 text-cyan-200 px-2 py-0.5 whitespace-nowrap truncate max-w-[180px]"
                title={`${l.title} (${l.author || "Unknown"})`}
              >
                {l.title}
              </span>
            ))
          ) : (
            <span className="text-cyan-800 text-[11px] italic font-mono">
              // Click [● RES] on any book in the grid to add it to the resonance pool
            </span>
          )}
        </div>
      </div>

      {/* Right: CSV Sync & Centroid Inference Actions */}
      <div className="flex items-center space-x-2.5 whitespace-nowrap">
        {/* CSV Sync Button Group */}
        <button
          type="button"
          disabled={isSyncing}
          onClick={handleImport}
          className="border border-cyan-900/80 bg-[#040c18] px-2.5 py-1.5 text-[11px] font-semibold text-cyan-400 hover:border-[#00e5ff] hover:text-[#00e5ff] hover:bg-[#00e5ff]/10 transition-colors cursor-pointer"
          title="Import logs from a CSV file"
        >
          [CSV IMPORT]
        </button>

        <button
          type="button"
          disabled={isSyncing || logs.length === 0}
          onClick={handleExport}
          className="border border-cyan-900/80 bg-[#040c18] px-2.5 py-1.5 text-[11px] font-semibold text-cyan-400 hover:border-[#00e5ff] hover:text-[#00e5ff] hover:bg-[#00e5ff]/10 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          title="Export all logs to a CSV file"
        >
          [CSV EXPORT]
        </button>

        <span className="text-cyan-900 select-none">|</span>

        {/* Centroid Inference Trigger */}
        <button
          type="button"
          disabled={resonanceCount === 0 || isExtracting}
          onClick={handleExtractCentroid}
          className={`border px-3.5 py-1.5 text-xs font-bold tracking-wider uppercase transition-colors ${
            resonanceCount > 0 && !isExtracting
              ? "border-[#00e5ff] bg-[#00e5ff] text-[#020408] hover:bg-transparent hover:text-[#00e5ff] cursor-pointer"
              : "border-cyan-950 bg-transparent text-cyan-800 cursor-not-allowed"
          }`}
        >
          {isExtracting
            ? "[ EXTRACTING... ]"
            : resonanceCount > 0
            ? "[ EXTRACT CENTROID ]"
            : "[ POOL EMPTY ]"}
        </button>
      </div>
    </footer>
  );
};
