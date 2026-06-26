import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import IngestPanel from "./components/IngestPanel";
import HistorySidebar from "./components/HistorySidebar";
import TracePanel from "./components/TracePanel";
import { getStatus, getHistory, submitQuery, streamExplanation } from "./api";

export default function App() {
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [currentTrace, setCurrentTrace] = useState(null);
  const [activeQueryId, setActiveQueryId] = useState(null);
  const [queryInput, setQueryInput] = useState("");
  const [isLoadingTrace, setIsLoadingTrace] = useState(false);
  const [traceError, setTraceError] = useState("");
  const [explanation, setExplanation] = useState("");
  const [isStreamingExplanation, setIsStreamingExplanation] = useState(false);

  const refreshData = async () => {
    try {
      const s = await getStatus();
      setStatus(s);
    } catch (e) {
      console.error("Failed to get status:", e);
    }

    try {
      const h = await getHistory();
      setHistory(h.history || []);
    } catch (e) {
      console.error("Failed to get history:", e);
    }
  };

  useEffect(() => {
    // Initial fetch
    refreshData();

    // Poll status every 30 seconds
    const interval = setInterval(async () => {
      try {
        const s = await getStatus();
        setStatus(s);
      } catch (e) {
        console.error("Failed polling status:", e);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const handleQuerySubmit = async (e) => {
    if (e) e.preventDefault();
    if (!queryInput.trim()) return;

    setIsLoadingTrace(true);
    setTraceError("");
    setCurrentTrace(null);
    setActiveQueryId(null);

    try {
      const res = await submitQuery(queryInput.trim());
      setCurrentTrace(res);
      
      // Refresh history immediately so sidebar gets updated
      const h = await getHistory();
      setHistory(h.history || []);
      
      // Select the newly created history item if available
      if (h.history && h.history.length > 0) {
        setActiveQueryId(h.history[0].id);
      }
      setQueryInput("");

      // Trigger explanation stream asynchronously
      setExplanation("");
      setIsStreamingExplanation(true);
      streamExplanation(
        res,
        (chunk) => {
          setExplanation((prev) => prev + chunk);
        },
        () => {
          setIsStreamingExplanation(false);
        },
        (err) => {
          console.error("Explanation stream error:", err);
          setExplanation("Failed to generate code explanation.");
          setIsStreamingExplanation(false);
        }
      );
    } catch (err) {
      setTraceError(err.message || "Query execution failed.");
    } finally {
      setIsLoadingTrace(false);
    }
  };

  const handleSelectQuery = (historyItem) => {
    setActiveQueryId(historyItem.id);
    setTraceError("");
    if (historyItem.result) {
      setCurrentTrace(historyItem.result);
      
      // Trigger explanation stream for selected query
      setExplanation("");
      setIsStreamingExplanation(true);
      streamExplanation(
        historyItem.result,
        (chunk) => {
          setExplanation((prev) => prev + chunk);
        },
        () => {
          setIsStreamingExplanation(false);
        },
        (err) => {
          console.error("Explanation stream error:", err);
          setExplanation("Failed to generate code explanation.");
          setIsStreamingExplanation(false);
        }
      );
    } else {
      // Fallback if result isn't pre-loaded in the DB record
      setQueryInput(historyItem.query);
    }
  };

  const handleIngestSuccess = () => {
    refreshData();
    setTraceError("");
    setCurrentTrace(null);
    setActiveQueryId(null);
  };

  return (
    <div className="w-screen h-screen flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header Bar */}
      <Header status={status} />

      {/* Collapsible Ingest Panel */}
      <IngestPanel status={status} onIngestSuccess={handleIngestSuccess} />

      {/* Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden w-full">
        {/* Left Query History Sidebar */}
        <HistorySidebar 
          history={history} 
          activeQueryId={activeQueryId} 
          onSelectQuery={handleSelectQuery} 
        />

        {/* Right Canvas Area */}
        <main className="flex-1 h-full flex flex-col overflow-hidden bg-zinc-950/45">
          {/* Query prompt input bar */}
          <div className="p-6 border-b border-zinc-900/60 shrink-0 bg-zinc-950/30">
            <form onSubmit={handleQuerySubmit} className="flex items-center space-x-3 w-full max-w-4xl mx-auto">
              <div className="flex-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-4 w-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <input
                  type="text"
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  disabled={isLoadingTrace || !status?.index_loaded}
                  placeholder={
                    status?.index_loaded 
                      ? "Search codebase... (e.g. 'What breaks if I change middleware?')" 
                      : "Please ingest a repository first before queries"
                  }
                  className="w-full bg-zinc-900/60 border border-zinc-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-mono"
                />
              </div>

              <button
                type="submit"
                disabled={isLoadingTrace || !queryInput.trim() || !status?.index_loaded}
                className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-mono font-medium px-6 py-3 rounded-xl transition-all shadow-md active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none select-none flex items-center space-x-2"
              >
                <span>Run Query</span>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </button>
            </form>

            {/* Error banner if query fails */}
            {traceError && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg max-w-4xl mx-auto flex items-center space-x-2">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500 shrink-0" />
                <span className="text-xs text-red-400 font-mono">Error: {traceError}</span>
              </div>
            )}
          </div>

          {/* Trace Canvas Panel */}
          <div className="flex-1 overflow-hidden">
            <TracePanel 
              trace={currentTrace} 
              isLoading={isLoadingTrace} 
              explanation={explanation}
              isStreamingExplanation={isStreamingExplanation}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
