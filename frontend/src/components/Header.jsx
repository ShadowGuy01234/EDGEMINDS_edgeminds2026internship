import React from "react";

export default function Header({ status }) {
  const env = status?.env || "dev";
  const ram = status?.memory_used_mb || 0;
  const ollamaReachable = status?.ollama_reachable ?? false;
  const indexLoaded = status?.index_loaded ?? false;

  return (
    <header className="glass-panel w-full py-4 px-6 flex items-center justify-between border-b border-zinc-800 shrink-0">
      {/* Brand */}
      <div className="flex items-center space-x-3">
        <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-between p-2 shadow-lg glow-violet">
          <span className="font-mono font-bold text-white text-base tracking-tighter">CG</span>
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white m-0 leading-none">
            CodeGenome<span className="text-violet-400 font-medium font-mono">.Edge</span>
          </h1>
          <p className="text-[10px] text-zinc-400 leading-none mt-1 font-mono uppercase tracking-widest">
            Offline Repo Intelligence
          </p>
        </div>
      </div>

      {/* Info Stats */}
      <div className="flex items-center space-x-6">
        {/* Connection status */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-zinc-400 font-mono">Ollama:</span>
          <div className="flex items-center space-x-1.5">
            <span className={`h-2.5 w-2.5 rounded-full ${ollamaReachable ? "bg-emerald-500 animate-pulse" : "bg-red-500"}`} />
            <span className="text-xs font-mono text-zinc-300">
              {ollamaReachable ? (status?.ollama_model || "llama3.2:1b") : "Disconnected"}
            </span>
          </div>
        </div>

        {/* RAM Usage */}
        <div className="flex items-center space-x-2 border-l border-zinc-800 pl-6">
          <span className="text-xs text-zinc-400 font-mono">RAM:</span>
          <span className="text-xs font-mono font-medium text-zinc-300">
            {ram ? `${ram} MB` : "N/A"}
          </span>
          {env === "prod" && (
            <span className="text-[10px] text-zinc-500 font-mono">/ 3.2 GB Limit</span>
          )}
        </div>

        {/* Env Badge */}
        <div className="border-l border-zinc-800 pl-6">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-medium uppercase border ${
            env === "prod" 
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" 
              : "bg-amber-500/10 text-amber-400 border-amber-500/30"
          }`}>
            {env} ENVIRONMENT
          </span>
        </div>
      </div>
    </header>
  );
}
