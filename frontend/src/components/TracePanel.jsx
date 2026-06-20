import React, { useState, useEffect } from "react";
import { streamSymbolExplanation } from "../api";

// Function to clean up SLM markdown quirks (Setext headers)
const sanitizeMarkdown = (text) => {
  if (!text) return "";
  // Remove lines that are just equal signs (Setext H1) or dashes (Setext H2)
  return text
    .replace(/(^|\n)[=]{3,}\s*(\n|$)/g, '\n')
    .replace(/(^|\n)[-]{3,}\s*(\n|$)/g, '\n');
};

export default function TracePanel({ trace, isLoading, explanation, isStreamingExplanation }) {
  const [activeSymbol, setActiveSymbol] = useState(null);
  const [streamedText, setStreamedText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    setActiveSymbol(null);
    setStreamedText("");
    setIsStreaming(false);
  }, [trace]);

  const handleExplainClick = async (symbol) => {
    const symbolKey = `${symbol.file_path}::${symbol.name}::${symbol.kind}`;
    if (activeSymbol === symbolKey) {
      setActiveSymbol(null);
      setStreamedText("");
      setIsStreaming(false);
      return;
    }

    setActiveSymbol(symbolKey);
    setStreamedText("");
    setIsStreaming(true);

    streamSymbolExplanation(
      symbol,
      (chunk) => {
        setStreamedText((prev) => prev + chunk);
      },
      () => {
        setIsStreaming(false);
      },
      (err) => {
        console.error("Symbol explanation stream error:", err);
        setStreamedText(`Failed to generate code explanation: ${err.message}`);
        setIsStreaming(false);
      }
    );
  };

  if (isLoading) {
    return (
      <div className="flex-1 h-full flex flex-col items-center justify-center text-center p-8 bg-zinc-950/20">
        <div className="relative flex items-center justify-center mb-4">
          <div className="animate-ping absolute h-8 w-8 rounded-full bg-violet-500 opacity-75"></div>
          <div className="relative rounded-full h-8 w-8 bg-violet-600 flex items-center justify-center shadow-lg">
            <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
        </div>
        <p className="text-sm text-zinc-400 font-mono">Running intent routing and search execution...</p>
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="flex-1 h-full flex flex-col items-center justify-center text-center p-8 bg-zinc-950/20">
        <div className="h-16 w-16 rounded-2xl bg-zinc-900/50 border border-zinc-800 flex items-center justify-center mb-4 shadow-inner">
          <svg className="w-8 h-8 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-zinc-300 font-mono mb-1">No Trace Loaded</h3>
        <p className="text-xs text-zinc-500 max-w-sm font-mono leading-relaxed">
          Type a code query above or click a historical badge from the sidebar to inspect dependencies.
        </p>
      </div>
    );
  }

  if (trace.no_match) {
    return (
      <div className="flex-1 h-full flex flex-col items-center justify-center text-center p-8 bg-zinc-950/20">
        <div className="h-16 w-16 rounded-2xl bg-red-950/10 border border-red-900/20 flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-red-500/80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-red-400 font-mono mb-1">No Matches Found</h3>
        <p className="text-xs text-zinc-500 max-w-sm font-mono leading-relaxed">
          We couldn't resolve any indexed files or code symbols matching your search term: "{trace.keywords?.join(", ")}"
        </p>
      </div>
    );
  }

  const getKindBadgeColor = (kind) => {
    switch (kind?.toLowerCase()) {
      case "class":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "function":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "method":
        return "bg-teal-500/10 text-teal-400 border-teal-500/30";
      case "export":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-zinc-800 text-zinc-400 border-zinc-700";
    }
  };

  const getLayerBadgeColor = (layer) => {
    switch (layer?.toLowerCase()) {
      case "backend":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/30";
      case "frontend":
        return "bg-pink-500/10 text-pink-400 border-pink-500/30";
      case "shared":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "test":
        return "bg-yellow-500/10 text-yellow-400 border-yellow-500/30";
      default:
        return "bg-zinc-800 text-zinc-400 border-zinc-700";
    }
  };

  const getFileIcon = (filePath) => {
    if (filePath?.endsWith(".py")) return "🐍";
    if (filePath?.endsWith(".ts") || filePath?.endsWith(".tsx")) return "🟦";
    if (filePath?.endsWith(".js") || filePath?.endsWith(".jsx")) return "🟨";
    return "📄";
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-6 space-y-6 bg-zinc-950/20">
      {/* Query Detail Header */}
      <div className="glass-panel rounded-xl p-5 glow-indigo relative overflow-hidden">
        <div className="absolute top-0 right-0 p-3 flex space-x-2">
          {/* Tool Badge */}
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 uppercase">
            Tool: {trace.tool_used}
          </span>
          {/* Routed Badge */}
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-800 text-zinc-300 border border-zinc-700 uppercase">
            Routed By: {trace.routed_by}
          </span>
          {/* Depth Capped Badge */}
          {trace.depth_capped && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30 uppercase">
              ⚠️ Depth Capped (3 Hops)
            </span>
          )}
        </div>

        <div>
          <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider block mb-1">Active Query Trace</span>
          <h2 className="text-base font-semibold text-zinc-100 mb-3 font-sans break-words pr-48 leading-snug">
            "{trace.query || "Direct Trace"}"
          </h2>

          <div className="flex items-center space-x-6 text-xs text-zinc-400 font-mono">
            <div>
              Keywords:{" "}
              <span className="text-zinc-200">
                {trace.keywords && trace.keywords.length > 0 ? trace.keywords.join(", ") : "None"}
              </span>
            </div>
            <div className="h-3 w-px bg-zinc-800" />
            <div>
              Ollama SLM: <span className="text-zinc-300">{trace.slm_latency_ms || 0}ms</span>
            </div>
            <div className="h-3 w-px bg-zinc-800" />
            <div>
              Search Execution: <span className="text-zinc-300">{trace.execution_ms || 0}ms</span>
            </div>
          </div>
        </div>
      </div>

      {/* Codebase NLP Explanation */}
      {(explanation || isStreamingExplanation) && (
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-zinc-400 font-mono uppercase tracking-wider px-1">
            Architectural Explanation
          </h3>
          <div className="glass-panel rounded-xl p-5 border-violet-500/20 relative overflow-hidden bg-zinc-950/45 shadow-lg shadow-violet-500/5">
            <p className="text-sm text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap">
              {explanation}
              {isStreamingExplanation && (
                <span className="inline-block w-1.5 h-3.5 ml-1 bg-violet-400 animate-pulse align-middle" />
              )}
            </p>
          </div>
        </div>
      )}

      {/* Dependency Graph Canvas */}
      {trace.tool_used !== "vector" && (
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-zinc-400 font-mono uppercase tracking-wider px-1">
            Dependency Flow Trace
          </h3>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Column 1: Upstream Dependents */}
            <div className="glass-panel rounded-xl p-4 flex flex-col min-h-[250px] max-h-[450px]">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-900/50 mb-3 shrink-0">
                <span className="text-[11px] font-mono font-bold text-zinc-400 uppercase tracking-wide">
                  Upstream Dependents
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 bg-zinc-900 rounded border border-zinc-800 text-zinc-400">
                  {trace.dependents?.length || 0} files
                </span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {!trace.dependents || trace.dependents.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-center p-4">
                    <span className="text-xs text-zinc-600 font-mono">No dependents import this file.</span>
                  </div>
                ) : (
                  trace.dependents.map((dep, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-zinc-900/30 border border-zinc-800/80 flex items-center justify-between">
                      <div className="min-w-0 flex-1 pr-2">
                        <div className="flex items-center space-x-1.5 mb-0.5">
                          <span className="text-xs">{getFileIcon(dep.file_path)}</span>
                          <span className="text-xs font-semibold text-zinc-300 truncate block">
                            {dep.file_path.split("/").pop()}
                          </span>
                        </div>
                        <span className="text-[9px] font-mono text-zinc-500 block truncate">
                          {dep.file_path}
                        </span>
                      </div>
                      <span className="text-[9px] font-mono font-medium px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                        {dep.hop} {dep.hop === 1 ? "hop" : "hops"}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Column 2: Anchor Seed Card */}
            <div className="flex flex-col items-center justify-center min-h-[250px] max-h-[450px]">
              {trace.seed ? (
                <div className="glass-panel border-violet-500/30 bg-violet-950/5 p-5 rounded-xl w-full text-center relative glow-violet border-2 flex flex-col justify-start items-center py-6 overflow-y-auto max-h-[450px]">
                  {/* Connector Line visuals */}
                  <div className="absolute left-0 top-1/2 w-4 border-t border-dashed border-violet-500/40 transform -translate-x-full hidden lg:block" />
                  <div className="absolute right-0 top-1/2 w-4 border-t border-dashed border-violet-500/40 transform translate-x-full hidden lg:block" />

                  <span className="text-[9px] font-mono font-bold text-violet-400 uppercase tracking-widest px-2 py-0.5 rounded-full bg-violet-500/10 border border-violet-500/30 mb-3 shrink-0">
                    Anchor Seed
                  </span>

                  <h4 className="text-lg font-bold text-white mb-1 tracking-tight break-all shrink-0">
                    {trace.seed.symbol || trace.seed.file_path.split("/").pop()}
                  </h4>

                  <div className="flex items-center justify-center space-x-2 mb-4 shrink-0">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border inline-block ${getKindBadgeColor(trace.seed.kind)}`}>
                      {trace.seed.kind || "file"}
                    </span>
                    {trace.seed.layer && (
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border inline-block ${getLayerBadgeColor(trace.seed.layer)}`}>
                        {trace.seed.layer}
                      </span>
                    )}
                  </div>

                  <div className="text-zinc-400 font-mono text-xs w-full text-center truncate px-4 shrink-0">
                    <span className="text-zinc-600">File:</span> {trace.seed.file_path}
                  </div>

                  {trace.seed.similarity !== undefined && (
                    <div className="mt-3 text-[10px] font-mono text-zinc-500 shrink-0">
                      Similarity: <span className="text-violet-400 font-bold">{(trace.seed.similarity * 100).toFixed(1)}%</span>
                    </div>
                  )}


                </div>
              ) : (
                <div className="glass-panel rounded-xl p-6 w-full text-center">
                  <span className="text-xs text-zinc-500 font-mono">No seed file defined.</span>
                </div>
              )}
            </div>

            {/* Column 3: Downstream Dependencies */}
            <div className="glass-panel rounded-xl p-4 flex flex-col min-h-[250px] max-h-[450px]">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-900/50 mb-3 shrink-0">
                <span className="text-[11px] font-mono font-bold text-zinc-400 uppercase tracking-wide">
                  Downstream Dependencies
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 bg-zinc-900 rounded border border-zinc-800 text-zinc-400">
                  {trace.dependencies?.length || 0} files
                </span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {!trace.dependencies || trace.dependencies.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-center p-4">
                    <span className="text-xs text-zinc-600 font-mono">No downstream dependencies resolved.</span>
                  </div>
                ) : (
                  trace.dependencies.map((dep, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-zinc-900/30 border border-zinc-800/80 flex items-center justify-between">
                      <div className="min-w-0 flex-1 pr-2">
                        <div className="flex items-center space-x-1.5 mb-0.5">
                          <span className="text-xs">{getFileIcon(dep.file_path)}</span>
                          <span className="text-xs font-semibold text-zinc-300 truncate block">
                            {dep.file_path.split("/").pop()}
                          </span>
                        </div>
                        <span className="text-[9px] font-mono text-zinc-500 block truncate">
                          {dep.file_path}
                        </span>
                      </div>
                      <span className="text-[9px] font-mono font-medium px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 shrink-0">
                        {dep.hop} {dep.hop === 1 ? "hop" : "hops"}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Semantic Matches List */}
      {trace.tool_used !== "graph" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-xs font-semibold text-zinc-400 font-mono uppercase tracking-wider">
              Semantic Symbol Matches
            </h3>
            <span className="text-[10px] font-mono text-zinc-500">
              Top {trace.symbol_matches?.length || 0} matches
            </span>
          </div>

          <div className="glass-panel rounded-xl overflow-hidden">
            {!trace.symbol_matches || trace.symbol_matches.length === 0 ? (
              <div className="p-6 text-center text-xs text-zinc-600 font-mono">
                No symbol matches found.
              </div>
            ) : (
              <div className="divide-y divide-zinc-900/60">
                {trace.symbol_matches.map((match, idx) => {
                  const symbolKey = `${match.file_path}::${match.name}::${match.kind}`;
                  const isStreamActive = activeSymbol === symbolKey;
                  return (
                    <div 
                      key={idx} 
                      className={`transition-colors duration-150 ${isStreamActive ? 'bg-zinc-900/40' : 'hover:bg-zinc-900/20'}`}
                    >
                      <div 
                        onClick={() => handleExplainClick(match)}
                        className="p-3.5 flex items-center justify-between select-none cursor-pointer"
                      >
                        <div className="min-w-0 pr-4">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="text-sm font-semibold font-mono text-zinc-100 truncate block">
                              {match.name}
                            </span>
                            <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border font-medium uppercase ${getKindBadgeColor(match.kind)}`}>
                              {match.kind}
                            </span>
                            {match.layer && (
                              <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border font-medium uppercase ${getLayerBadgeColor(match.layer)}`}>
                                {match.layer}
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-zinc-400 font-mono block truncate">
                            {getFileIcon(match.file_path)} {match.file_path}
                          </span>
                        </div>

                        <div className="flex items-center space-x-4 shrink-0">
                          <div className="text-right">
                            <div className="text-xs font-mono font-bold text-violet-400">
                              {(match.similarity * 100).toFixed(1)}%
                            </div>
                            <span className="text-[9px] text-zinc-500 font-mono">similarity</span>
                          </div>
                          <svg 
                            className={`w-4 h-4 text-zinc-500 transition-transform duration-200 ${isStreamActive ? 'rotate-90 text-violet-400' : ''}`} 
                            fill="none" 
                            viewBox="0 0 24 24" 
                            stroke="currentColor"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                      </div>

                      {isStreamActive && (
                        <div className="px-4 pb-4 border-t border-zinc-900/50 pt-3 animate-[fadeIn_0.2s_ease-out] text-left">
                          <div className="bg-zinc-950/60 p-4 rounded-lg border border-zinc-800/40 shadow-inner">
                            <span className="text-[10px] font-mono font-bold text-violet-400 uppercase tracking-widest block mb-2">Code Explanation (On-Demand RAG)</span>
                            <pre className="text-xs text-zinc-300 font-sans leading-relaxed whitespace-pre-wrap">
                              {sanitizeMarkdown(streamedText)}
                              {isStreaming && (
                                <span className="inline-block w-1.5 h-3.5 ml-1 bg-violet-400 animate-pulse align-middle" />
                              )}
                            </pre>
                            {isStreaming && !streamedText && (
                              <p className="text-[10px] text-zinc-500 font-mono mt-1 animate-pulse">Generating explanation...</p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
