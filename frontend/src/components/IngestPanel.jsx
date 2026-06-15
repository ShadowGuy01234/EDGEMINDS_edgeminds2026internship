import React, { useState } from "react";
import { ingestRepo } from "../api";

export default function IngestPanel({ status, onIngestSuccess }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [repoPath, setRepoPath] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successData, setSuccessData] = useState(null);

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!repoPath.trim()) {
      setError("Please enter a valid directory path.");
      return;
    }
    
    setIsLoading(true);
    setError("");
    setSuccessData(null);
    
    try {
      const res = await ingestRepo(repoPath.trim());
      setSuccessData(res);
      setRepoPath("");
      if (onIngestSuccess) {
        onIngestSuccess();
      }
    } catch (err) {
      setError(err.message || "Ingestion failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full border-b border-zinc-800 shrink-0 bg-zinc-950/20">
      {/* Trigger Bar */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-2.5 flex items-center justify-between cursor-pointer hover:bg-zinc-900/30 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <span className="text-zinc-400 text-xs font-mono">Current Repo:</span>
          <span className="text-zinc-200 text-xs font-mono font-medium truncate max-w-lg">
            {status?.repo_path || "None Indexed"}
          </span>
        </div>
        <div className="flex items-center space-x-2 text-xs text-violet-400 hover:text-violet-300 font-mono">
          <span>{isExpanded ? "Collapse Ingest" : "Ingest New Repository"}</span>
          <svg 
            className={`w-3.5 h-3.5 transform transition-transform ${isExpanded ? "rotate-180" : ""}`} 
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Collapsible Content */}
      {isExpanded && (
        <div className="px-6 pb-6 pt-2 border-t border-zinc-900/50 bg-zinc-950/40">
          <form onSubmit={handleIngest} className="flex flex-col space-y-3 max-w-3xl">
            <h3 className="text-xs font-semibold text-zinc-400 font-mono uppercase tracking-wider">
              Index Local Repository
            </h3>
            <div className="flex space-x-3">
              <input
                type="text"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                disabled={isLoading}
                placeholder="e.g. d:/repo/my-app (use absolute path)"
                className="flex-1 bg-zinc-900/80 border border-zinc-800 rounded-lg px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-violet-500 transition-colors disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !repoPath.trim()}
                className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-mono text-xs font-medium px-5 py-2.5 rounded-lg transition-all shadow-md active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
              >
                {isLoading ? (
                  <span className="flex items-center space-x-2">
                    <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Ingesting...</span>
                  </span>
                ) : "Start Ingestion"}
              </button>
            </div>
          </form>

          {/* Feedback messages */}
          {error && (
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg max-w-3xl">
              <span className="text-xs text-red-400 font-mono">Error: {error}</span>
            </div>
          )}

          {successData && (
            <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg max-w-3xl">
              <h4 className="text-xs font-semibold text-emerald-400 font-mono mb-1">
                Ingestion Completed Successfully!
              </h4>
              <div className="grid grid-cols-3 gap-4 mt-2 text-[11px] text-zinc-300 font-mono">
                <div>Files Parsed: <span className="text-white font-bold">{successData.files_parsed}</span></div>
                <div>Symbols Indexed: <span className="text-white font-bold">{successData.symbols_indexed}</span></div>
                <div>Time Taken: <span className="text-white font-bold">{(successData.duration_ms / 1000).toFixed(2)}s</span></div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
