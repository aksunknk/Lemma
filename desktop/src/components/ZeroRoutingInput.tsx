import React, { useState } from "react";
import { searchByComposite, searchByAuthor } from "../services/googleBooks";
import { addLog } from "../services/tauriCommands";
import { CandidateItem, ReadingLog } from "../types";

interface ZeroRoutingInputProps {
  onLogAdded: (log: ReadingLog) => void;
  onCandidatesAdded: (candidates: CandidateItem[]) => void;
  statusMessage: string;
  setStatusMessage: (msg: string) => void;
}

export const ZeroRoutingInput: React.FC<ZeroRoutingInputProps> = ({
  onLogAdded,
  onCandidatesAdded,
  statusMessage,
  setStatusMessage,
}) => {
  const [titleInput, setTitleInput] = useState("");
  const [authorInput, setAuthorInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async () => {
    const cleanTitle = titleInput.trim();
    const cleanAuthor = authorInput.trim();

    if (!cleanTitle && !cleanAuthor) {
      setStatusMessage("INPUT ERROR: SPECIFY TITLE OR AUTHOR");
      return;
    }

    if (isProcessing) return;
    setIsProcessing(true);

    try {
      if (cleanTitle) {
        // Case A: Title provided (with or without author) -> High-precision search & direct SQLite commit
        const queryLabel = cleanAuthor ? `[${cleanTitle} / ${cleanAuthor}]` : `[${cleanTitle}]`;
        setStatusMessage(`RESOLVING BIBLIOGRAPHIC DATA FOR ${queryLabel}...`);

        const newLogData = await searchByComposite(cleanTitle, cleanAuthor || undefined);

        setStatusMessage(`COMMITTING [${newLogData.title}] TO SQLITE...`);
        const saved = await addLog(newLogData);

        onLogAdded(saved);
        setStatusMessage(`COMMITTED [${saved.title}] (${saved.author || "Unknown"}) TO LOCAL SQLITE`);
        setTitleInput("");
        setAuthorInput("");
      } else if (cleanAuthor) {
        // Case B: Author only -> Fetch candidate pool for selection
        setStatusMessage(`FETCHING CANDIDATES FOR AUTHOR [${cleanAuthor}]...`);
        const candidates = await searchByAuthor(cleanAuthor);

        if (candidates.length === 0) {
          setStatusMessage(`NO CANDIDATES FOUND FOR AUTHOR [${cleanAuthor}]`);
        } else {
          onCandidatesAdded(candidates);
          setStatusMessage(`INJECTED ${candidates.length} CANDIDATE ROWS FOR [${cleanAuthor}] INTO THE GRID`);
          setAuthorInput("");
        }
      }
    } catch (err) {
      console.error(err);
      setStatusMessage(`EXECUTION ERROR: ${String(err)}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSubmit();
    }
  };

  return (
    <header className="border-b border-cyan-900/40 bg-[#020408] px-4 py-3 select-none">
      {/* Top system status line */}
      <div className="flex items-center justify-between font-mono text-xs tracking-wider text-cyan-600 mb-2 pb-1.5 border-b border-cyan-950/60">
        <div className="flex items-center space-x-3">
          <span className="font-bold text-[#00e5ff]">LEMMA // DESKTOP</span>
          <span className="text-cyan-800">|</span>
          <span className="text-cyan-500">SQLITE: ONLINE</span>
          <span className="text-cyan-800">|</span>
          <span className="text-cyan-500">RESONANCE ENGINE: READY</span>
        </div>
        <div className="text-[11px] text-cyan-400 font-medium truncate max-w-[500px]">
          {statusMessage || "STATUS: IDLE // READY FOR INPUT"}
        </div>
      </div>

      {/* ZeroRoutingInput Dual-Port Command Bar */}
      <div className="flex items-center space-x-2">
        <div className="flex flex-1 items-center border border-cyan-800/60 bg-[#040914] px-3 py-2 text-sm transition-all duration-150 focus-within:border-[#00e5ff] focus-within:ring-1 focus-within:ring-[#00e5ff]/40 focus-within:bg-[#051024]">
          <span className="font-mono text-[#00e5ff] text-xs font-bold mr-2.5 select-none tracking-widest whitespace-nowrap">
            PORT://
          </span>

          {/* Title Input Port */}
          <div className="flex items-center flex-3 mr-3">
            <span className="font-mono text-[10px] text-cyan-500 font-semibold uppercase mr-2 select-none">
              TITLE:
            </span>
            <input
              type="text"
              className="w-full bg-transparent font-sans text-cyan-100 placeholder-cyan-700/80 text-xs sm:text-sm outline-none border-none caret-[#00e5ff]"
              placeholder={isProcessing ? "PROCESSING..." : "Book title (e.g. こころ)..."}
              value={titleInput}
              disabled={isProcessing}
              onChange={(e) => setTitleInput(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
            />
          </div>

          <span className="text-cyan-900 mx-2 select-none">|</span>

          {/* Author Input Port */}
          <div className="flex items-center flex-2">
            <span className="font-mono text-[10px] text-cyan-500 font-semibold uppercase mr-2 select-none">
              AUTHOR:
            </span>
            <input
              type="text"
              className="w-full bg-transparent font-sans text-cyan-100 placeholder-cyan-700/80 text-xs sm:text-sm outline-none border-none caret-[#00e5ff]"
              placeholder={isProcessing ? "..." : "Author / 著者 (optional or query)..."}
              value={authorInput}
              disabled={isProcessing}
              onChange={(e) => setAuthorInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>
        </div>

        {/* Action Commit Button */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isProcessing || (!titleInput.trim() && !authorInput.trim())}
          className={`border px-3.5 py-2.5 font-mono text-xs font-bold tracking-wider uppercase transition-colors whitespace-nowrap ${
            !isProcessing && (titleInput.trim() || authorInput.trim())
              ? "border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff] hover:bg-[#00e5ff] hover:text-[#020408] cursor-pointer"
              : "border-cyan-950 bg-transparent text-cyan-900 cursor-not-allowed"
          }`}
        >
          {isProcessing ? "[ ... ]" : "[ ENTER ↵ ]"}
        </button>
      </div>

      {/* Syntax Guide Footnote */}
      <div className="flex justify-between items-center font-mono text-[10px] text-cyan-700/90 mt-1.5 tracking-wider">
        <span>
          [DISPATCH] Title only: Instant Add | Author only: Fetch Candidates | Both: Precision Match
        </span>
        <span className="text-cyan-800">DUAL-PORT ZERO-ROUTING</span>
      </div>
    </header>
  );
};
