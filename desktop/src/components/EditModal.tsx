import React, { useState, useEffect } from "react";
import { CandidateItem, LogStatus, ReadingLog, UpdateLogPayload } from "../types";
import { searchBooksFlexible } from "../services/googleBooks";

interface EditModalProps {
  log: ReadingLog | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (payload: UpdateLogPayload) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export const EditModal: React.FC<EditModalProps> = ({
  log,
  isOpen,
  onClose,
  onSave,
  onDelete,
}) => {
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [publisher, setPublisher] = useState("");
  const [isbn, setIsbn] = useState("");
  const [status, setStatus] = useState<LogStatus>("unread");
  const [resonance, setResonance] = useState(0);
  const [startedAt, setStartedAt] = useState("");
  const [finishedAt, setFinishedAt] = useState("");
  const [notes, setNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);

  // Candidate API search state
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [isSearchingCandidates, setIsSearchingCandidates] = useState(false);
  const [candidateFeedback, setCandidateFeedback] = useState<string | null>(null);
  const [showCandidates, setShowCandidates] = useState(false);
  const [lastAppliedId, setLastAppliedId] = useState<string | null>(null);

  useEffect(() => {
    if (log) {
      setTitle(log.title);
      setAuthor(log.author || "");
      setPublisher(log.publisher || "");
      setIsbn(log.isbn || "");
      setStatus(log.status);
      setResonance(log.resonance);
      setStartedAt(log.started_at || "");
      setFinishedAt(log.finished_at || "");
      setNotes(log.notes || "");
      setIsConfirmingDelete(false);
      setCandidates([]);
      setCandidateFeedback(null);
      setShowCandidates(false);
      setLastAppliedId(null);
    }
  }, [log, isOpen]);

  // Support ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isSaving) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, isSaving]);

  if (!isOpen || !log) return null;

  const handleSearchCandidates = async (e?: React.MouseEvent) => {
    if (e) e.preventDefault();
    const queryTitle = title.trim();
    const queryAuthor = author.trim();
    if (!queryTitle && !queryAuthor) {
      setCandidateFeedback("SPECIFY TITLE OR AUTHOR TO QUERY API");
      setShowCandidates(true);
      return;
    }

    setIsSearchingCandidates(true);
    setCandidateFeedback(null);
    setShowCandidates(true);

    try {
      const results = await searchBooksFlexible(queryTitle || undefined, queryAuthor || undefined, 6);
      setCandidates(results);
      if (results.length === 0) {
        setCandidateFeedback("NO MATCHING CANDIDATES FOUND");
      } else {
        setCandidateFeedback(`FOUND ${results.length} CANDIDATE(S) — CLICK TO POPULATE`);
      }
    } catch (err) {
      console.error("Candidate lookup error:", err);
      setCandidateFeedback("API QUERY FAILED");
    } finally {
      setIsSearchingCandidates(false);
    }
  };

  const handleApplyCandidate = (c: CandidateItem) => {
    setTitle(c.title);
    setAuthor(c.author || "");
    setPublisher(c.publisher || "");
    setIsbn(c.isbn || "");
    setLastAppliedId(c.tempId);
    setCandidateFeedback(`APPLIED: "${c.title}"`);
  };

  const handleSetTodayStarted = () => {
    setStartedAt(new Date().toISOString().slice(0, 10));
  };

  const handleSetTodayFinished = () => {
    setFinishedAt(new Date().toISOString().slice(0, 10));
  };

  const handleStatusSelect = (newStatus: LogStatus) => {
    setStatus(newStatus);
    const today = new Date().toISOString().slice(0, 10);
    if (newStatus === "reading" && !startedAt) {
      setStartedAt(today);
    }
    if (newStatus === "read" && !finishedAt) {
      setFinishedAt(today);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || isSaving) return;

    setIsSaving(true);
    try {
      await onSave({
        id: log.id,
        title: title.trim(),
        author: author.trim() || null,
        publisher: publisher.trim() || null,
        isbn: isbn.trim() || null,
        status,
        resonance,
        started_at: startedAt.trim() || null,
        finished_at: finishedAt.trim() || null,
        notes: notes.trim() || null,
      });
      onClose();
    } catch (err) {
      console.error("Failed to update log:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!isConfirmingDelete) {
      setIsConfirmingDelete(true);
      return;
    }
    setIsSaving(true);
    try {
      await onDelete(log.id);
      onClose();
    } catch (err) {
      console.error("Failed to delete log:", err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 select-none animate-in fade-in duration-100"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl max-h-[92vh] overflow-y-auto border border-[#00e5ff]/60 bg-[#030814] p-6 shadow-[0_0_35px_rgba(0,229,255,0.18)] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-cyan-900/60 pb-3 mb-4 shrink-0">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-[#00e5ff] font-bold text-sm tracking-wider">
              EDIT_RECORD://{log.id.slice(0, 8)}
            </span>
            <span className="font-mono text-cyan-700 text-xs">[SCHEMA_V2.1 + CONTEXT]</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="font-mono text-cyan-600 hover:text-cyan-300 text-sm px-2 py-0.5 border border-transparent hover:border-cyan-800 transition-colors cursor-pointer"
          >
            [ESC ✕]
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="space-y-3.5 flex-1">
          {/* Title + API Search Button */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider">
                Title <span className="text-rose-400">*</span>
              </label>
              <button
                type="button"
                onClick={handleSearchCandidates}
                disabled={isSearchingCandidates || (!title.trim() && !author.trim())}
                className="font-mono text-[10px] px-2.5 py-0.5 border border-cyan-700/70 bg-cyan-950/40 text-cyan-300 hover:border-[#00e5ff] hover:text-[#00e5ff] hover:bg-cyan-900/40 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isSearchingCandidates ? "[ 🔍 SEARCHING API... ]" : "[ 🔍 QUERY CANDIDATES ]"}
              </button>
            </div>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-cyan-900/80 bg-[#061224] px-3 py-2 font-sans text-sm text-[#e0f7fa] placeholder-cyan-800 focus:border-[#00e5ff] focus:ring-1 focus:ring-[#00e5ff]/30 focus:outline-none"
            />
          </div>

          {/* Candidate Search Panel / Drawer */}
          {showCandidates && (
            <div className="border border-cyan-800/70 bg-[#020610] p-3 space-y-2 rounded-xs animate-in fade-in duration-150">
              <div className="flex items-center justify-between font-mono text-[10px] border-b border-cyan-950 pb-1.5">
                <span className="text-cyan-400 font-bold tracking-wider">
                  // API CANDIDATE POOL [{candidates.length} RESULTS]
                </span>
                <div className="flex items-center space-x-2">
                  {candidateFeedback && (
                    <span className="text-emerald-400 font-medium truncate max-w-[280px]">
                      {candidateFeedback}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => setShowCandidates(false)}
                    className="text-cyan-600 hover:text-cyan-300 cursor-pointer"
                  >
                    [✕ CLOSE]
                  </button>
                </div>
              </div>

              {candidates.length > 0 ? (
                <div className="max-h-48 overflow-y-auto space-y-1 pr-1 divide-y divide-cyan-950/60">
                  {candidates.map((c) => {
                    const isSelected = lastAppliedId === c.tempId;
                    return (
                      <div
                        key={c.tempId}
                        onClick={() => handleApplyCandidate(c)}
                        className={`pt-1.5 first:pt-0 flex items-center justify-between group p-2 transition-colors cursor-pointer border ${
                          isSelected
                            ? "border-emerald-500/80 bg-emerald-950/30"
                            : "border-transparent hover:bg-[#05152c] hover:border-cyan-700/50"
                        }`}
                      >
                        <div className="flex-1 min-w-0 pr-3">
                          <div
                            className={`font-sans text-xs font-semibold truncate ${
                              isSelected ? "text-emerald-300" : "text-cyan-100 group-hover:text-[#00e5ff]"
                            }`}
                          >
                            {c.title}
                          </div>
                          <div className="font-mono text-[10px] text-cyan-500/80 flex items-center space-x-2 mt-0.5 truncate">
                            <span>{c.author || "著者不明"}</span>
                            <span className="text-cyan-800">|</span>
                            <span>{c.publisher || "出版社不明"}</span>
                            {c.isbn && (
                              <>
                                <span className="text-cyan-800">|</span>
                                <span className="text-cyan-600">ISBN: {c.isbn}</span>
                              </>
                            )}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleApplyCandidate(c);
                          }}
                          className={`font-mono text-[10px] px-2 py-1 border transition-all whitespace-nowrap cursor-pointer shrink-0 ${
                            isSelected
                              ? "border-emerald-500 bg-emerald-500 text-[#020408] font-bold"
                              : "border-cyan-800 bg-cyan-950/60 text-cyan-300 group-hover:border-[#00e5ff] group-hover:bg-[#00e5ff] group-hover:text-[#020408]"
                          }`}
                        >
                          {isSelected ? "[ APPLIED ✓ ]" : "[ APPLY ↵ ]"}
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                !isSearchingCandidates && (
                  <div className="font-mono text-xs text-cyan-700 py-2 text-center">
                    NO CANDIDATES FOUND. TRY REFINING TITLE OR AUTHOR.
                  </div>
                )
              )}
            </div>
          )}

          {/* Author & Publisher */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider mb-1">
                Author
              </label>
              <input
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="---"
                className="w-full border border-cyan-900/80 bg-[#061224] px-3 py-2 font-sans text-xs text-slate-200 placeholder-cyan-800 focus:border-[#00e5ff] focus:outline-none"
              />
            </div>
            <div>
              <label className="block font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider mb-1">
                Publisher
              </label>
              <input
                type="text"
                value={publisher}
                onChange={(e) => setPublisher(e.target.value)}
                placeholder="---"
                className="w-full border border-cyan-900/80 bg-[#061224] px-3 py-2 font-sans text-xs text-slate-200 placeholder-cyan-800 focus:border-[#00e5ff] focus:outline-none"
              />
            </div>
          </div>

          {/* Personal Context / Reading Notes (Textarea) */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider">
                // PERSONAL CONTEXT / READING NOTES
              </label>
              <span className="font-mono text-[10px] text-cyan-600">
                [ {notes.length} CHARS ]
              </span>
            </div>
            <textarea
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Why did you resonate with this book? Record striking quotes, key insights, thesis reflections, page markers..."
              className="w-full border border-cyan-900/80 bg-[#061224] p-3 font-sans text-xs text-[#e0f7fa] placeholder-cyan-900 leading-relaxed focus:border-[#00e5ff] focus:ring-1 focus:ring-[#00e5ff]/30 focus:outline-none resize-y"
            />
          </div>

          {/* ISBN & Resonance Status */}
          <div className="grid grid-cols-2 gap-3 items-center">
            <div>
              <label className="block font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider mb-1">
                ISBN
              </label>
              <input
                type="text"
                value={isbn}
                onChange={(e) => setIsbn(e.target.value)}
                placeholder="---"
                className="w-full border border-cyan-900/80 bg-[#061224] px-3 py-2 font-mono text-xs text-cyan-200 placeholder-cyan-800 focus:border-[#00e5ff] focus:outline-none"
              />
            </div>
            <div>
              <label className="block font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider mb-1">
                Resonance Pool
              </label>
              <button
                type="button"
                onClick={() => setResonance((prev) => (prev === 1 ? 0 : 1))}
                className={`w-full py-2 px-3 font-mono text-xs font-bold tracking-wider border transition-colors ${
                  resonance === 1
                    ? "border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff] hover:bg-[#00e5ff]/30"
                    : "border-cyan-900/60 bg-[#061224] text-cyan-700 hover:text-cyan-400 hover:border-cyan-700"
                }`}
              >
                {resonance === 1 ? "[● RESONANCE ACTIVE]" : "[○ RESONANCE OFF]"}
              </button>
            </div>
          </div>

          {/* Reading Status Selector */}
          <div>
            <label className="block font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider mb-1.5">
              Reading Lifecycle Status
            </label>
            <div className="grid grid-cols-4 gap-2 font-mono text-xs">
              <button
                type="button"
                onClick={() => handleStatusSelect("unread")}
                className={`py-1.5 border text-center font-semibold transition-colors ${
                  status === "unread"
                    ? "border-slate-400 bg-slate-800/80 text-slate-100"
                    : "border-slate-900 bg-slate-950/40 text-slate-500 hover:text-slate-300"
                }`}
              >
                [UNREAD]
              </button>
              <button
                type="button"
                onClick={() => handleStatusSelect("reading")}
                className={`py-1.5 border text-center font-semibold transition-colors ${
                  status === "reading"
                    ? "border-emerald-400 bg-emerald-950/70 text-emerald-300"
                    : "border-emerald-950/40 bg-transparent text-emerald-800 hover:text-emerald-500"
                }`}
              >
                [READING]
              </button>
              <button
                type="button"
                onClick={() => handleStatusSelect("read")}
                className={`py-1.5 border text-center font-semibold transition-colors ${
                  status === "read"
                    ? "border-sky-400 bg-sky-950/70 text-sky-300"
                    : "border-sky-950/40 bg-transparent text-sky-800 hover:text-sky-500"
                }`}
              >
                [READ]
              </button>
              <button
                type="button"
                onClick={() => handleStatusSelect("abandoned")}
                className={`py-1.5 border text-center font-semibold transition-colors ${
                  status === "abandoned"
                    ? "border-rose-400 bg-rose-950/70 text-rose-300"
                    : "border-rose-950/40 bg-transparent text-rose-900 hover:text-rose-500"
                }`}
              >
                [ABANDONED]
              </button>
            </div>
          </div>

          {/* Started At & Finished At Timestamps */}
          <div className="grid grid-cols-2 gap-3 pt-1 border-t border-cyan-950/80">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider">
                  Started At
                </label>
                <div className="space-x-1.5 font-mono text-[10px]">
                  <button
                    type="button"
                    onClick={handleSetTodayStarted}
                    className="text-cyan-500 hover:text-[#00e5ff] cursor-pointer"
                  >
                    [Today]
                  </button>
                  {startedAt && (
                    <button
                      type="button"
                      onClick={() => setStartedAt("")}
                      className="text-slate-500 hover:text-rose-400 cursor-pointer"
                    >
                      [Clear]
                    </button>
                  )}
                </div>
              </div>
              <input
                type="date"
                value={startedAt}
                onChange={(e) => setStartedAt(e.target.value)}
                className="w-full border border-cyan-900/80 bg-[#061224] px-3 py-1.5 font-mono text-xs text-cyan-200 focus:border-[#00e5ff] focus:outline-none"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-mono text-[11px] font-bold text-cyan-400 uppercase tracking-wider">
                  Finished At
                </label>
                <div className="space-x-1.5 font-mono text-[10px]">
                  <button
                    type="button"
                    onClick={handleSetTodayFinished}
                    className="text-cyan-500 hover:text-[#00e5ff] cursor-pointer"
                  >
                    [Today]
                  </button>
                  {finishedAt && (
                    <button
                      type="button"
                      onClick={() => setFinishedAt("")}
                      className="text-slate-500 hover:text-rose-400 cursor-pointer"
                    >
                      [Clear]
                    </button>
                  )}
                </div>
              </div>
              <input
                type="date"
                value={finishedAt}
                onChange={(e) => setFinishedAt(e.target.value)}
                className="w-full border border-cyan-900/80 bg-[#061224] px-3 py-1.5 font-mono text-xs text-cyan-200 focus:border-[#00e5ff] focus:outline-none"
              />
            </div>
          </div>

          {/* Action Buttons: Delete on Left, Save / Cancel on Right */}
          <div className="flex items-center justify-between pt-3 border-t border-cyan-900/50 mt-3 shrink-0">
            <button
              type="button"
              onClick={handleDelete}
              disabled={isSaving}
              className={`font-mono text-xs font-bold px-3 py-2 border transition-colors cursor-pointer ${
                isConfirmingDelete
                  ? "border-rose-500 bg-rose-950/80 text-rose-300 hover:bg-rose-900"
                  : "border-rose-950/60 bg-transparent text-rose-700 hover:border-rose-600 hover:text-rose-400"
              }`}
            >
              {isConfirmingDelete ? "[CONFIRM PURGE ⚠]" : "[DELETE RECORD]"}
            </button>

            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isSaving}
                className="font-mono text-xs text-cyan-600 border border-cyan-950 px-3 py-2 hover:border-cyan-800 hover:text-cyan-400 transition-colors cursor-pointer"
              >
                [CANCEL]
              </button>
              <button
                type="submit"
                disabled={isSaving || !title.trim()}
                className="font-mono text-xs font-bold px-4 py-2 border border-[#00e5ff] bg-[#00e5ff] text-[#020408] hover:bg-transparent hover:text-[#00e5ff] transition-colors cursor-pointer disabled:opacity-50"
              >
                {isSaving ? "[SAVING...]" : "[SAVE CHANGES ↵]"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
