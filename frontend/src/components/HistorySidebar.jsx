import React from "react";

export default function HistorySidebar({ history, activeQueryId, onSelectQuery }) {
  const getToolBadgeColor = (tool) => {
    switch (tool) {
      case "graph":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "vector":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
      case "hybrid":
        return "bg-violet-500/10 text-violet-400 border-violet-500/30";
      default:
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/30";
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return "";
    try {
      const date = new Date(ts.replace(" ", "T")); // handle SQLite format
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (e) {
      return ts;
    }
  };

  return (
    <aside className="w-80 h-full border-r border-zinc-800 bg-zinc-950/60 backdrop-blur-md flex flex-col shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-xs font-semibold text-zinc-400 font-mono uppercase tracking-wider">
          Query History
        </h2>
        <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700">
          {history.length}
        </span>
      </div>

      {/* Query List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {history.length === 0 ? (
          <div className="h-40 flex flex-col items-center justify-center text-center p-4">
            <svg className="w-8 h-8 text-zinc-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <p className="text-xs text-zinc-500 font-mono">No queries executed yet.</p>
          </div>
        ) : (
          history.map((item) => {
            const isActive = item.id === activeQueryId;
            return (
              <div
                key={item.id}
                onClick={() => onSelectQuery(item)}
                className={`group p-3 rounded-lg border text-left cursor-pointer transition-all relative overflow-hidden ${
                  isActive
                    ? "bg-violet-500/10 border-violet-500/40 shadow-sm"
                    : "bg-zinc-900/30 border-zinc-800 hover:bg-zinc-900/60 hover:border-zinc-700"
                }`}
              >
                {/* Active Indicator bar */}
                {isActive && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-violet-500 to-indigo-500 rounded-r" />
                )}

                {/* Query Text */}
                <p className="text-xs font-medium text-zinc-200 line-clamp-2 mb-2 break-words leading-relaxed group-hover:text-white transition-colors">
                  {item.query}
                </p>

                {/* Stats Row */}
                <div className="flex items-center justify-between text-[9px] font-mono text-zinc-500 mt-1">
                  <div className="flex items-center space-x-1.5">
                    {/* Tool Badge */}
                    <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium border uppercase ${getToolBadgeColor(item.tool_used)}`}>
                      {item.tool_used}
                    </span>
                    {/* Routed By */}
                    <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium border uppercase ${
                      item.routed_by === "slm" 
                        ? "bg-zinc-800 text-zinc-300 border-zinc-700" 
                        : "bg-amber-500/10 text-amber-500 border-amber-500/20"
                    }`}>
                      {item.routed_by}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 text-zinc-400">
                    <span>{item.execution_ms}ms</span>
                    <span>•</span>
                    <span>{formatTimestamp(item.timestamp)}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
