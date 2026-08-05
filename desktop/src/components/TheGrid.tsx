import React, { useMemo, useState } from "react";
import { CandidateItem, LogStatus, ReadingLog } from "../types";

type FilterTab = "all" | "reading" | "read" | "unread" | "abandoned" | "resonating";
type SortField = "updated_at" | "title" | "author" | "period" | "isbn" | "status" | "resonance" | "notes";
type SortDirection = "asc" | "desc";

interface TheGridProps {
  candidates: CandidateItem[];
  logs: ReadingLog[];
  onAddCandidate: (candidate: CandidateItem) => void;
  onDismissCandidate: (tempId: string) => void;
  onToggleResonance: (log: ReadingLog) => void;
  onCycleStatus: (log: ReadingLog) => void;
  onDeleteLog: (id: string) => void;
  onEditLog: (log: ReadingLog) => void;
}

export const TheGrid: React.FC<TheGridProps> = ({
  candidates,
  logs,
  onAddCandidate,
  onDismissCandidate,
  onToggleResonance,
  onCycleStatus,
  onDeleteLog,
  onEditLog,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [sortField, setSortField] = useState<SortField>("updated_at");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // Tab counts for quick metrics
  const tabCounts = useMemo(() => {
    return {
      all: logs.length,
      reading: logs.filter((l) => l.status === "reading").length,
      read: logs.filter((l) => l.status === "read").length,
      unread: logs.filter((l) => l.status === "unread").length,
      abandoned: logs.filter((l) => l.status === "abandoned").length,
      resonating: logs.filter((l) => l.resonance === 1).length,
    };
  }, [logs]);

  // Handle column header clicks for multi-directional sorting
  const handleSortHeaderClick = (field: SortField) => {
    if (sortField === field) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else {
        // Reset to default
        setSortField("updated_at");
        setSortDirection("desc");
      }
    } else {
      setSortField(field);
      setSortDirection(field === "title" || field === "author" ? "asc" : "desc");
    }
  };

  // Filter and Sort Logs
  const processedLogs = useMemo(() => {
    let result = [...logs];

    // 1. Tab Filter
    if (activeTab === "reading") {
      result = result.filter((l) => l.status === "reading");
    } else if (activeTab === "read") {
      result = result.filter((l) => l.status === "read");
    } else if (activeTab === "unread") {
      result = result.filter((l) => l.status === "unread");
    } else if (activeTab === "abandoned") {
      result = result.filter((l) => l.status === "abandoned");
    } else if (activeTab === "resonating") {
      result = result.filter((l) => l.resonance === 1);
    }

    // 2. Search Query Filter (Title, Author, Publisher, ISBN, Notes)
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter((l) => {
        return (
          l.title.toLowerCase().includes(q) ||
          (l.author && l.author.toLowerCase().includes(q)) ||
          (l.publisher && l.publisher.toLowerCase().includes(q)) ||
          (l.isbn && l.isbn.toLowerCase().includes(q)) ||
          (l.notes && l.notes.toLowerCase().includes(q))
        );
      });
    }

    // 3. Sorting
    result.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "title":
          cmp = a.title.localeCompare(b.title, "ja");
          break;
        case "author":
          cmp = (a.author || "").localeCompare(b.author || "", "ja");
          break;
        case "period":
          cmp = (a.started_at || a.finished_at || "").localeCompare(
            b.started_at || b.finished_at || ""
          );
          break;
        case "isbn":
          cmp = (a.isbn || "").localeCompare(b.isbn || "");
          break;
        case "status":
          cmp = a.status.localeCompare(b.status);
          break;
        case "resonance":
          cmp = a.resonance - b.resonance;
          break;
        case "notes":
          cmp = (a.notes ? 1 : 0) - (b.notes ? 1 : 0);
          break;
        case "updated_at":
        default:
          cmp = a.updated_at.localeCompare(b.updated_at);
          break;
      }
      return sortDirection === "asc" ? cmp : -cmp;
    });

    return result;
  }, [logs, activeTab, searchQuery, sortField, sortDirection]);

  const getStatusBadge = (status: LogStatus) => {
    switch (status) {
      case "reading":
        return (
          <span
            className="font-mono inline-block border border-emerald-500/40 bg-emerald-950/40 text-emerald-400 px-2 py-0.5 text-[11px] font-semibold tracking-wider uppercase cursor-pointer hover:border-emerald-300 hover:bg-emerald-900/50 transition-colors"
            title="Click to cycle status"
          >
            [READING]
          </span>
        );
      case "read":
        return (
          <span
            className="font-mono inline-block border border-sky-500/40 bg-sky-950/40 text-sky-400 px-2 py-0.5 text-[11px] font-semibold tracking-wider uppercase cursor-pointer hover:border-sky-300 hover:bg-sky-900/50 transition-colors"
            title="Click to cycle status"
          >
            [READ]
          </span>
        );
      case "abandoned":
        return (
          <span
            className="font-mono inline-block border border-rose-500/40 bg-rose-950/40 text-rose-400 px-2 py-0.5 text-[11px] font-semibold tracking-wider uppercase cursor-pointer hover:border-rose-300 hover:bg-rose-900/50 transition-colors"
            title="Click to cycle status"
          >
            [ABANDONED]
          </span>
        );
      case "unread":
      default:
        return (
          <span
            className="font-mono inline-block border border-slate-700/50 bg-slate-900/50 text-slate-400 px-2 py-0.5 text-[11px] font-semibold tracking-wider uppercase cursor-pointer hover:border-slate-500 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            title="Click to cycle status"
          >
            [UNREAD]
          </span>
        );
    }
  };

  const getResonanceBadge = (resonance: number) => {
    if (resonance === 1) {
      return (
        <span
          className="font-mono inline-block border border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff] px-2 py-0.5 text-[11px] font-bold tracking-wider cursor-pointer hover:bg-[#00e5ff]/35 transition-colors"
          title="Click to toggle resonance"
        >
          [● RES]
        </span>
      );
    }
    return (
      <span
        className="font-mono inline-block border border-cyan-900/40 bg-transparent text-cyan-700 px-2 py-0.5 text-[11px] tracking-wider cursor-pointer hover:border-cyan-600 hover:text-cyan-400 transition-colors"
        title="Click to toggle resonance"
      >
        [○ ---]
      </span>
    );
  };

  const renderSortIndicator = (field: SortField) => {
    if (sortField !== field) return null;
    return (
      <span className="text-[#00e5ff] ml-1 font-bold">
        {sortDirection === "asc" ? "▲" : "▼"}
      </span>
    );
  };

  return (
    <main className="flex-1 overflow-auto bg-[#020408] p-4 select-none flex flex-col">
      {/* HUD Control Bar: Quick Filter & Status Tabs */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2.5 border border-cyan-900/50 bg-[#030a16] p-2.5">
        {/* Left: Status Filter Tabs */}
        <div className="flex items-center space-x-1.5 overflow-x-auto no-scrollbar font-mono text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={`px-2.5 py-1 border transition-colors cursor-pointer ${
              activeTab === "all"
                ? "border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff] font-bold"
                : "border-cyan-950 bg-transparent text-cyan-600 hover:border-cyan-800 hover:text-cyan-300"
            }`}
          >
            [ALL ({tabCounts.all})]
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("reading")}
            className={`px-2.5 py-1 border transition-colors cursor-pointer ${
              activeTab === "reading"
                ? "border-emerald-400 bg-emerald-950/70 text-emerald-300 font-bold"
                : "border-emerald-950/40 bg-transparent text-emerald-700 hover:text-emerald-400"
            }`}
          >
            [READING ({tabCounts.reading})]
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("read")}
            className={`px-2.5 py-1 border transition-colors cursor-pointer ${
              activeTab === "read"
                ? "border-sky-400 bg-sky-950/70 text-sky-300 font-bold"
                : "border-sky-950/40 bg-transparent text-sky-700 hover:text-sky-400"
            }`}
          >
            [READ ({tabCounts.read})]
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("unread")}
            className={`px-2.5 py-1 border transition-colors cursor-pointer ${
              activeTab === "unread"
                ? "border-slate-400 bg-slate-800/80 text-slate-200 font-bold"
                : "border-slate-900 bg-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            [UNREAD ({tabCounts.unread})]
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("abandoned")}
            className={`px-2.5 py-1 border transition-colors cursor-pointer ${
              activeTab === "abandoned"
                ? "border-rose-400 bg-rose-950/70 text-rose-300 font-bold"
                : "border-rose-950/40 bg-transparent text-rose-800 hover:text-rose-400"
            }`}
          >
            [ABANDONED ({tabCounts.abandoned})]
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("resonating")}
            className={`px-2.5 py-1 border transition-colors cursor-pointer ${
              activeTab === "resonating"
                ? "border-[#00e5ff] bg-[#00e5ff]/25 text-[#00e5ff] font-bold shadow-[0_0_10px_rgba(0,229,255,0.2)]"
                : "border-cyan-900/60 bg-transparent text-cyan-500 hover:text-[#00e5ff]"
            }`}
          >
            [● RESONATING ({tabCounts.resonating})]
          </button>
        </div>

        {/* Right: Quick Search Input */}
        <div className="flex items-center space-x-2 shrink-0">
          <div className="relative flex items-center">
            <span className="font-mono text-[10px] text-cyan-600 mr-1.5 select-none">
              FILTER://
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search title, author, notes..."
              className="border border-cyan-900/80 bg-[#061224] px-2.5 py-1 font-sans text-xs text-[#e0f7fa] placeholder-cyan-800 focus:border-[#00e5ff] focus:outline-none w-56 transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-1.5 font-mono text-[10px] text-cyan-600 hover:text-rose-400 cursor-pointer"
                title="Clear filter"
              >
                [✕]
              </button>
            )}
          </div>
          <span className="font-mono text-[10px] text-cyan-700 whitespace-nowrap">
            SHOWING {processedLogs.length}/{logs.length}
          </span>
        </div>
      </div>

      {/* Main Grid Container */}
      <div className="border border-cyan-900/40 bg-[#020408] flex-1">
        {/* Grid Header with Clickable Sorting */}
        <div className="grid grid-cols-12 gap-3 border-b border-cyan-900/50 bg-[#040c18] px-4 py-2.5 font-mono text-[11px] font-bold tracking-wider text-cyan-400">
          <div
            className="col-span-1 text-center cursor-pointer hover:text-[#00e5ff] transition-colors"
            onClick={() => handleSortHeaderClick("resonance")}
            title="Sort by Resonance"
          >
            RES {renderSortIndicator("resonance")}
          </div>
          <div
            className="col-span-1 text-center cursor-pointer hover:text-[#00e5ff] transition-colors"
            onClick={() => handleSortHeaderClick("status")}
            title="Sort by Status"
          >
            STATUS {renderSortIndicator("status")}
          </div>
          <div
            className="col-span-4 cursor-pointer hover:text-[#00e5ff] transition-colors"
            onClick={() => handleSortHeaderClick("title")}
            title="Sort by Title"
          >
            TITLE {renderSortIndicator("title")}
          </div>
          <div
            className="col-span-2 cursor-pointer hover:text-[#00e5ff] transition-colors"
            onClick={() => handleSortHeaderClick("author")}
            title="Sort by Author"
          >
            AUTHOR {renderSortIndicator("author")}
          </div>
          <div
            className="col-span-2 cursor-pointer hover:text-[#00e5ff] transition-colors"
            onClick={() => handleSortHeaderClick("period")}
            title="Sort by Date / Period"
          >
            PERIOD / PUBLISHER {renderSortIndicator("period")}
          </div>
          <div
            className="col-span-1 text-right cursor-pointer hover:text-[#00e5ff] transition-colors"
            onClick={() => handleSortHeaderClick("isbn")}
            title="Sort by ISBN"
          >
            ISBN {renderSortIndicator("isbn")}
          </div>
          <div className="col-span-1 text-center">ACTION</div>
        </div>

        {/* Temporary Candidate Rows (from ZeroRouting author search) */}
        {candidates.map((cand) => (
          <div
            key={cand.tempId}
            onClick={() => onAddCandidate(cand)}
            className="grid grid-cols-12 gap-3 border-b border-dashed border-cyan-800/40 bg-cyan-950/10 px-4 py-3 text-xs transition-colors duration-75 cursor-pointer hover:bg-[#0a1829] group items-center"
          >
            <div className="col-span-2 flex items-center justify-center">
              <span className="font-mono border border-dashed border-[#00e5ff]/60 bg-[#00e5ff]/10 px-2 py-0.5 text-[10px] text-[#00e5ff] tracking-tight whitespace-nowrap font-bold">
                [ CANDIDATE ]
              </span>
            </div>
            <div className="col-span-4 flex items-center space-x-2 truncate">
              <span className="font-sans font-medium text-[13px] text-cyan-200 group-hover:text-[#00e5ff] truncate">
                {cand.title}
              </span>
              <span className="font-mono text-[10px] text-cyan-500/70 whitespace-nowrap">
                ▸ click to add
              </span>
            </div>
            <div className="col-span-2 truncate flex items-center font-sans text-[12px] text-slate-300">
              {cand.author || "---"}
            </div>
            <div className="col-span-2 truncate flex items-center font-sans text-[12px] text-slate-400">
              {cand.publisher || "---"}
            </div>
            <div className="col-span-1 truncate flex items-center justify-end font-mono text-[11px] text-slate-500">
              {cand.isbn || "---"}
            </div>
            <div
              className="col-span-1 flex items-center justify-center"
              onClick={(e) => {
                e.stopPropagation();
                onDismissCandidate(cand.tempId);
              }}
            >
              <button
                type="button"
                className="font-mono border border-cyan-900/50 px-2 py-0.5 text-[10px] text-cyan-600 hover:border-rose-500 hover:bg-rose-950/30 hover:text-rose-400 transition-colors cursor-pointer"
                title="Dismiss candidate"
              >
                [×]
              </button>
            </div>
          </div>
        ))}

        {/* Filtered & Sorted Saved Reading Logs */}
        {processedLogs.map((log) => {
          const isResonating = log.resonance === 1;
          const hasDates = log.started_at || log.finished_at;
          const hasNotes = Boolean(log.notes && log.notes.trim().length > 0);

          return (
            <div
              key={log.id}
              onDoubleClick={() => onEditLog(log)}
              className={`grid grid-cols-12 gap-3 border-b border-cyan-900/30 px-4 py-2.5 text-xs items-center hover:bg-[#0a1424] cursor-pointer group transition-colors duration-75 ${
                isResonating ? "bg-cyan-950/15" : "bg-transparent"
              }`}
              title="Double-click to open edit modal"
            >
              {/* Resonance Toggle */}
              <div
                className="col-span-1 flex items-center justify-center"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleResonance(log);
                }}
              >
                {getResonanceBadge(log.resonance)}
              </div>

              {/* Status Cycle */}
              <div
                className="col-span-1 flex items-center justify-center"
                onClick={(e) => {
                  e.stopPropagation();
                  onCycleStatus(log);
                }}
              >
                {getStatusBadge(log.status)}
              </div>

              {/* Title & Notes Indicator */}
              <div className="col-span-4 flex items-center space-x-2 truncate">
                <span className="font-sans font-medium text-[13px] text-[#e0f7fa] tracking-normal leading-snug truncate group-hover:text-[#00e5ff] transition-colors">
                  {log.title}
                </span>

                {/* Personal Notes Indicator */}
                {hasNotes && (
                  <span
                    className="font-mono text-[9px] border border-cyan-500/50 bg-cyan-950/50 text-[#00e5ff] px-1.5 py-0.2 shrink-0 tracking-tighter"
                    title={`Notes: ${log.notes}`}
                  >
                    [NOTE]
                  </span>
                )}
              </div>

              {/* Author */}
              <div className="col-span-2 font-sans text-[12px] text-slate-300 tracking-normal truncate">
                {log.author || "---"}
              </div>

              {/* Period / Publisher */}
              <div className="col-span-2 truncate flex flex-col justify-center">
                {hasDates ? (
                  <div className="font-mono text-[10px] text-cyan-400/90 truncate flex items-center space-x-1">
                    <span>{log.started_at ? log.started_at.slice(5) : "..."}</span>
                    <span className="text-cyan-700">➔</span>
                    <span>{log.finished_at ? log.finished_at.slice(5) : "..."}</span>
                  </div>
                ) : (
                  <span className="font-sans text-[12px] text-slate-400 truncate">
                    {log.publisher || "---"}
                  </span>
                )}
                {hasDates && log.publisher && (
                  <span className="font-sans text-[10px] text-slate-500 truncate">
                    {log.publisher}
                  </span>
                )}
              </div>

              {/* ISBN */}
              <div className="col-span-1 text-right font-mono text-[11px] text-cyan-600/80 truncate">
                {log.isbn || "---"}
              </div>

              {/* Actions: Edit & Delete */}
              <div className="col-span-1 flex items-center justify-center space-x-1">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditLog(log);
                  }}
                  className="font-mono border border-cyan-950 px-1.5 py-0.5 text-[10px] text-cyan-600 hover:border-[#00e5ff] hover:text-[#00e5ff] hover:bg-[#00e5ff]/10 transition-colors cursor-pointer"
                  title="Edit details & notes"
                >
                  [EDIT]
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteLog(log.id);
                  }}
                  className="font-mono border border-cyan-950 px-1.5 py-0.5 text-[10px] text-cyan-800 hover:border-rose-500 hover:bg-rose-950/40 hover:text-rose-400 transition-colors cursor-pointer"
                  title="Delete log"
                >
                  [✕]
                </button>
              </div>
            </div>
          );
        })}

        {/* Empty State when no results found under current filters */}
        {processedLogs.length === 0 && candidates.length === 0 && (
          <div className="p-12 text-center font-mono text-xs tracking-wider text-cyan-700">
            <p className="mb-2">// NO MATCHING RECORDS</p>
            <p className="text-[11px] text-cyan-800">
              {searchQuery || activeTab !== "all"
                ? "Try clearing the search query or switching status filter tabs."
                : "Type a book title or author in LEMMA://PORT to commit your first reading log."}
            </p>
          </div>
        )}
      </div>
    </main>
  );
};
