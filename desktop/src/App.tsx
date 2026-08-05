import React, { useEffect, useRef, useState } from "react";
import { ZeroRoutingInput } from "./components/ZeroRoutingInput";
import { TheGrid } from "./components/TheGrid";
import { FooterBar } from "./components/FooterBar";
import { EditModal } from "./components/EditModal";
import { InferenceModal } from "./components/InferenceModal";
import {
  getLogs,
  addLog,
  updateLog,
  deleteLog,
} from "./services/tauriCommands";
import { exportLogsToCsv, importLogsFromCsv } from "./services/csvSync";
import { fetchBibliographyForTitle } from "./services/googleBooks";
import { CandidateItem, LogStatus, ReadingLog, UpdateLogPayload } from "./types";

export const App: React.FC = () => {
  const [logs, setLogs] = useState<ReadingLog[]>([]);
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [editingLog, setEditingLog] = useState<ReadingLog | null>(null);
  const [inferenceResults, setInferenceResults] = useState<CandidateItem[]>([]);
  const [isInferenceModalOpen, setIsInferenceModalOpen] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>("SYSTEM INITIALIZING...");
  // Auto-Fill progress: null = idle, { done, total } = running
  const [autoFillProgress, setAutoFillProgress] = useState<{ done: number; total: number } | null>(null);
  const autoFillRunning = useRef(false);

  // Load logs on startup
  const fetchAllLogs = async () => {
    try {
      const data = await getLogs();
      setLogs(data);
      setStatusMessage(`SQLITE DATABASE SYNCHRONIZED [${data.length} LOGS LOADED]`);
    } catch (err) {
      console.error("Failed to load logs:", err);
      setStatusMessage(`STORAGE ERROR: ${String(err)}`);
    }
  };

  useEffect(() => {
    fetchAllLogs();
  }, []);

  const handleLogAdded = (newLog: ReadingLog) => {
    setLogs((prev) => [newLog, ...prev.filter((l) => l.id !== newLog.id)]);
  };

  const handleCandidatesAdded = (newCandidates: CandidateItem[]) => {
    setCandidates((prev) => {
      const existingIds = new Set(prev.map((c) => c.tempId));
      const filtered = newCandidates.filter((c) => !existingIds.has(c.tempId));
      return [...filtered, ...prev];
    });
  };

  const handleAddCandidate = async (candidate: CandidateItem) => {
    try {
      setStatusMessage(`COMMITTING CANDIDATE [${candidate.title}] TO SQLITE...`);
      const saved = await addLog({
        title: candidate.title,
        author: candidate.author,
        publisher: candidate.publisher,
        isbn: candidate.isbn,
        status: "unread",
        resonance: 0,
      });

      // Remove from candidate pool and add to saved logs
      setCandidates((prev) => prev.filter((c) => c.tempId !== candidate.tempId));
      handleLogAdded(saved);
      setStatusMessage(`COMMITTED CANDIDATE [${saved.title}] TO DATABASE`);
    } catch (err) {
      console.error("Failed to add candidate:", err);
      setStatusMessage(`DATABASE INSERT ERROR: ${String(err)}`);
    }
  };

  const handleDismissCandidate = (tempId: string) => {
    setCandidates((prev) => prev.filter((c) => c.tempId !== tempId));
    setStatusMessage("CANDIDATE ROW DISMISSED");
  };

  const handleInferenceCompleted = (results: CandidateItem[]) => {
    setInferenceResults(results);
    setIsInferenceModalOpen(true);
    setStatusMessage(`INFERENCE BUFFER LOADED [${results.length} RECOMMENDATIONS AVAILABLE]`);
  };

  const handleAddInferredCandidate = async (candidate: CandidateItem) => {
    try {
      const saved = await addLog({
        title: candidate.title,
        author: candidate.author,
        publisher: candidate.publisher,
        isbn: candidate.isbn,
        status: "unread",
        resonance: 0,
      });

      handleLogAdded(saved);
      setStatusMessage(`COMMITTED INFERRED BOOK [${saved.title}] TO DATABASE`);
    } catch (err) {
      console.error("Failed to add inferred candidate:", err);
      setStatusMessage(`DATABASE INSERT ERROR: ${String(err)}`);
      throw err;
    }
  };

  const handleToggleResonance = async (log: ReadingLog) => {
    const nextResonance = log.resonance === 1 ? 0 : 1;
    try {
      const updated = await updateLog({
        id: log.id,
        resonance: nextResonance,
      });
      setLogs((prev) => prev.map((l) => (l.id === log.id ? updated : l)));
      setStatusMessage(
        `RESONANCE TOGGLED: [${log.title}] -> ${
          nextResonance === 1 ? "ACTIVE (IN POOL)" : "OFF"
        }`
      );
    } catch (err) {
      console.error("Failed to toggle resonance:", err);
      setStatusMessage(`UPDATE ERROR: ${String(err)}`);
    }
  };

  const handleCycleStatus = async (log: ReadingLog) => {
    const cycleMap: Record<LogStatus, LogStatus> = {
      unread: "reading",
      reading: "read",
      read: "abandoned",
      abandoned: "unread",
    };
    const nextStatus = cycleMap[log.status] || "unread";

    try {
      const updated = await updateLog({
        id: log.id,
        status: nextStatus,
      });
      setLogs((prev) => prev.map((l) => (l.id === log.id ? updated : l)));
      setStatusMessage(
        `STATUS UPDATED: [${log.title}] -> [${nextStatus.toUpperCase()}]`
      );
    } catch (err) {
      console.error("Failed to cycle status:", err);
      setStatusMessage(`UPDATE ERROR: ${String(err)}`);
    }
  };

  const handleDeleteLog = async (id: string) => {
    try {
      await deleteLog(id);
      setLogs((prev) => prev.filter((l) => l.id !== id));
      setStatusMessage(`PURGED LOG ENTRY [${id.slice(0, 8)}] FROM DATABASE`);
    } catch (err) {
      console.error("Failed to delete log:", err);
      setStatusMessage(`DELETE ERROR: ${String(err)}`);
    }
  };

  const handleSaveEditLog = async (payload: UpdateLogPayload) => {
    try {
      const updated = await updateLog(payload);
      setLogs((prev) => prev.map((l) => (l.id === payload.id ? updated : l)));
      setStatusMessage(`SAVED RECORD MODIFICATIONS FOR [${updated.title}]`);
    } catch (err) {
      console.error("Failed to save edit:", err);
      setStatusMessage(`EDIT SAVE ERROR: ${String(err)}`);
      throw err;
    }
  };

  const handleExportCsv = async () => {
    try {
      setStatusMessage("OPENING EXPORT DIALOG...");
      const savedPath = await exportLogsToCsv(logs);
      if (savedPath) {
        setStatusMessage(`CSV EXPORT SUCCESS: [${savedPath}]`);
      } else {
        setStatusMessage("CSV EXPORT CANCELLED");
      }
    } catch (err) {
      console.error("CSV Export error:", err);
      setStatusMessage(`CSV EXPORT FAILED: ${String(err)}`);
    }
  };

  const handleImportCsv = async () => {
    try {
      setStatusMessage("OPENING IMPORT DIALOG...");
      const result = await importLogsFromCsv();
      if (result) {
        await fetchAllLogs();
        setStatusMessage(`CSV IMPORT SUCCESS: INGESTED ${result.count} RECORDS`);
      } else {
        setStatusMessage("CSV IMPORT CANCELLED");
      }
    } catch (err) {
      console.error("CSV Import error:", err);
      setStatusMessage(`CSV IMPORT FAILED: ${String(err)}`);
    }
  };

  // ── AUTO-FILL BATCH ─────────────────────────────────────────────────────────
  // Targets records where author OR isbn is absent.
  // Fetches Google Books 1 title at a time with a 1000–1500ms jitter delay.
  const runAutoFill = async () => {
    if (autoFillRunning.current) return;

    const targets = logs.filter(
      (l) => !l.author || !l.isbn
    );
    if (targets.length === 0) {
      setStatusMessage("AUTO-FILL: NO INCOMPLETE RECORDS FOUND");
      return;
    }

    autoFillRunning.current = true;
    setAutoFillProgress({ done: 0, total: targets.length });
    setStatusMessage(`AUTO-FILL INITIATED [${targets.length} RECORDS TARGETED]`);

    let filled = 0;
    for (const log of targets) {
      try {
        const bib = await fetchBibliographyForTitle(log.title);
        if (bib && (bib.author || bib.publisher || bib.isbn)) {
          const payload: UpdateLogPayload = {
            id: log.id,
            author: bib.author ?? log.author,
            publisher: bib.publisher ?? log.publisher,
            isbn: bib.isbn ?? log.isbn,
          };
          const updated = await updateLog(payload);
          setLogs((prev) => prev.map((l) => (l.id === log.id ? updated : l)));
          filled++;
        }
      } catch (err) {
        // Silent skip — log to console only
        console.warn(`[AutoFill] skipped "${log.title}":`, err);
      }

      // Advance progress counter
      setAutoFillProgress((prev) =>
        prev ? { done: prev.done + 1, total: prev.total } : null
      );

      // Jitter delay 1000–1500ms to respect rate limits
      await new Promise((resolve) =>
        setTimeout(resolve, 1000 + Math.floor(Math.random() * 500))
      );
    }

    autoFillRunning.current = false;
    setAutoFillProgress(null);
    setStatusMessage(`AUTO-FILL COMPLETE: ${filled}/${targets.length} RECORDS ENRICHED`);
  };
  // ────────────────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen w-screen flex-col bg-[#020408] text-[#00e5ff] overflow-hidden font-mono antialiased">
      {/* 1. Header & Zero-Routing Command Port */}
      <ZeroRoutingInput
        onLogAdded={handleLogAdded}
        onCandidatesAdded={handleCandidatesAdded}
        statusMessage={statusMessage}
        setStatusMessage={setStatusMessage}
      />

      {/* 2. Central Tabular Data Grid */}
      <TheGrid
        candidates={candidates}
        logs={logs}
        onAddCandidate={handleAddCandidate}
        onDismissCandidate={handleDismissCandidate}
        onToggleResonance={handleToggleResonance}
        onCycleStatus={handleCycleStatus}
        onDeleteLog={handleDeleteLog}
        onEditLog={(log) => setEditingLog(log)}
        onAutoFill={runAutoFill}
        autoFillProgress={autoFillProgress}
      />

      {/* 3. Footer with Resonance Pool & Centroid Trigger */}
      <FooterBar
        logs={logs}
        onInferenceCompleted={handleInferenceCompleted}
        onExportCsv={handleExportCsv}
        onImportCsv={handleImportCsv}
        setStatusMessage={setStatusMessage}
      />

      {/* 4. Cyberpunk Edit Modal */}
      <EditModal
        log={editingLog}
        isOpen={editingLog !== null}
        onClose={() => setEditingLog(null)}
        onSave={handleSaveEditLog}
        onDelete={handleDeleteLog}
      />

      {/* 5. Centroid Inference Dedicated Overlay Modal */}
      <InferenceModal
        isOpen={isInferenceModalOpen}
        results={inferenceResults}
        onClose={() => setIsInferenceModalOpen(false)}
        onAddCandidate={handleAddInferredCandidate}
      />
    </div>
  );
};

export default App;
