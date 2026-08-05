import React, { useEffect, useState } from "react";
import { CandidateItem } from "../types";

interface InferenceModalProps {
  isOpen: boolean;
  results: CandidateItem[];
  onClose: () => void;
  onAddCandidate: (candidate: CandidateItem) => Promise<void>;
}

export const InferenceModal: React.FC<InferenceModalProps> = ({
  isOpen,
  results,
  onClose,
  onAddCandidate,
}) => {
  const [addedTempIds, setAddedTempIds] = useState<Set<string>>(new Set());
  const [addingId, setAddingId] = useState<string | null>(null);

  // Reset added set when new results arrive
  useEffect(() => {
    setAddedTempIds(new Set());
  }, [results]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || results.length === 0) return null;

  const handleAdd = async (candidate: CandidateItem) => {
    if (addedTempIds.has(candidate.tempId) || addingId) return;

    setAddingId(candidate.tempId);
    try {
      await onAddCandidate(candidate);
      setAddedTempIds((prev) => new Set([...prev, candidate.tempId]));
    } catch (err) {
      console.error("Failed to add inferred book to log:", err);
    } finally {
      setAddingId(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 select-none animate-in fade-in duration-100"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl border border-[#00e5ff]/60 bg-[#030814] p-6 shadow-[0_0_35px_rgba(0,229,255,0.18)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-cyan-900/60 pb-3 mb-4">
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <span className="font-mono text-[#00e5ff] font-bold text-sm tracking-wider">
                // INFERENCE BUFFER [CENTROID MATCH]
              </span>
              <span className="font-mono text-cyan-600 text-xs">[384-DIM LATENT SPACE]</span>
            </div>
            <span className="font-mono text-[10px] text-cyan-700 mt-0.5">
              Select books to commit directly to your local reading log database.
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="font-mono text-cyan-600 hover:text-cyan-300 text-xs px-2.5 py-1 border border-cyan-950 hover:border-cyan-800 transition-colors cursor-pointer"
          >
            [ ESC ✕ CLOSE ]
          </button>
        </div>

        {/* Results List */}
        <div className="space-y-2.5 max-h-[60vh] overflow-y-auto pr-1">
          {results.map((item, idx) => {
            const isAdded = addedTempIds.has(item.tempId);
            const isAdding = addingId === item.tempId;

            return (
              <div
                key={item.tempId}
                className={`border p-3 flex items-center justify-between transition-colors ${
                  isAdded
                    ? "border-emerald-900/50 bg-emerald-950/20"
                    : "border-cyan-900/40 bg-[#061224] hover:border-cyan-700/80 hover:bg-[#091830]"
                }`}
              >
                {/* Left: Score Badge & Title/Author Info */}
                <div className="flex items-center space-x-3.5 flex-1 min-w-0 mr-3">
                  <div className="flex flex-col items-center justify-center shrink-0">
                    <span className="font-mono text-[9px] text-cyan-600 mb-0.5">
                      #{idx + 1} DIST
                    </span>
                    <span className="font-mono text-[10px] font-bold border border-[#00e5ff]/50 bg-[#00e5ff]/10 text-[#00e5ff] px-2 py-0.5 whitespace-nowrap">
                      [ {item.distance !== undefined ? item.distance.toFixed(4) : "0.0000"} ]
                    </span>
                  </div>

                  <div className="flex flex-col min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-sans font-medium text-sm text-[#e0f7fa] truncate">
                        {item.title}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2 text-xs font-sans mt-0.5">
                      <span className="text-slate-300 truncate">
                        {item.author || "Unknown Author"}
                      </span>
                      {item.publisher && (
                        <>
                          <span className="text-cyan-900">•</span>
                          <span className="text-slate-500 text-[11px] truncate">
                            {item.publisher}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Commit Button */}
                <div className="shrink-0">
                  {isAdded ? (
                    <span className="font-mono inline-block border border-emerald-500/50 bg-emerald-950/60 text-emerald-400 text-xs px-3 py-1.5 font-bold tracking-wider">
                      [ ADDED ✓ ]
                    </span>
                  ) : (
                    <button
                      type="button"
                      disabled={isAdding}
                      onClick={() => handleAdd(item)}
                      className="font-mono border border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff] hover:bg-[#00e5ff] hover:text-[#020408] text-xs px-3 py-1.5 font-bold tracking-wider transition-colors cursor-pointer disabled:opacity-50"
                    >
                      {isAdding ? "[ COMMITTING... ]" : "[ + ADD TO LOG ]"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-cyan-900/60 pt-3.5 mt-4">
          <div className="font-mono text-xs text-cyan-600">
            BUFFER COMMITTED: <span className="text-emerald-400 font-bold">{addedTempIds.size}</span> / {results.length} ITEMS
          </div>

          <div className="flex items-center space-x-2.5">
            <button
              type="button"
              onClick={onClose}
              className="font-mono text-xs font-bold border border-cyan-800 bg-transparent text-cyan-400 hover:border-[#00e5ff] hover:text-[#00e5ff] px-4 py-2 transition-colors cursor-pointer"
            >
              [ PURGE BUFFER / CLOSE ]
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
