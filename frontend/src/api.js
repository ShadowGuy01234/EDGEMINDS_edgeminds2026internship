import API_BASE from "./config";

async function fetchJson(endpoint, options = {}) {
  // Clean up paths: strip trailing slash from base and leading slash from endpoint
  const base = API_BASE.replace(/\/$/, "");
  const path = endpoint.replace(/^\//, "");
  const url = `${base}/${path}`;
  
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });
  
  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch (e) {
      errorData = { message: `HTTP Error ${response.status}` };
    }
    throw new Error(errorData.message || errorData.detail || "An error occurred");
  }
  
  return response.json();
}

export async function ingestRepo(repoPath) {
  return fetchJson("/ingest", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath }),
  });
}

export async function submitQuery(query) {
  return fetchJson("/query", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export async function getStatus() {
  return fetchJson("/status");
}

export async function getFiles() {
  return fetchJson("/files");
}

export async function getHistory() {
  return fetchJson("/history");
}

export async function streamExplanation(traceResult, onChunk, onComplete, onError) {
  try {
    const base = API_BASE.replace(/\/$/, "");
    const url = `${base}/query/explain`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: traceResult.query || "",
        tool_used: traceResult.tool_used,
        seed: traceResult.seed,
        dependents: traceResult.dependents || [],
        dependencies: traceResult.dependencies || [],
        symbol_matches: traceResult.symbol_matches || []
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      const chunk = decoder.decode(value, { stream: true });
      onChunk(chunk);
    }
    onComplete();
  } catch (err) {
    onError(err);
  }
}

export async function streamSymbolExplanation(symbol, onChunk, onComplete, onError) {
  try {
    const base = API_BASE.replace(/\/$/, "");
    const url = `${base}/symbol/explain`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        file_path: symbol.file_path,
        symbol_name: symbol.name,
        kind: symbol.kind
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      
      for (const line of lines) {
        const cleanedLine = line.trim();
        if (!cleanedLine) continue;
        
        if (cleanedLine.startsWith("data: [DONE]")) {
          onComplete();
          return;
        }
        
        if (cleanedLine.startsWith("data: ")) {
          try {
            const parsed = JSON.parse(cleanedLine.substring(6));
            if (parsed.chunk) {
              onChunk(parsed.chunk);
            } else if (parsed.error) {
              onError(new Error(parsed.error));
            }
          } catch (e) {
            console.error("SSE parse error", e);
          }
        }
      }
    }
    onComplete();
  } catch (err) {
    onError(err);
  }
}

export async function streamSymbolImpact(symbol, onChunk, onComplete, onError) {
  try {
    const base = API_BASE.replace(/\/$/, "");
    const url = `${base}/symbol/impact`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        file_path: symbol.file_path,
        symbol_name: symbol.name,
        kind: symbol.kind
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      
      for (const line of lines) {
        const cleanedLine = line.trim();
        if (!cleanedLine) continue;
        
        if (cleanedLine.startsWith("data: [DONE]")) {
          onComplete();
          return;
        }
        
        if (cleanedLine.startsWith("data: ")) {
          try {
            const parsed = JSON.parse(cleanedLine.substring(6));
            if (parsed.chunk) {
              onChunk(parsed.chunk);
            } else if (parsed.error) {
              onError(new Error(parsed.error));
            }
          } catch (e) {
            console.error("SSE parse error", e);
          }
        }
      }
    }
    onComplete();
  } catch (err) {
    onError(err);
  }
}

export async function getSymbolCode(symbol) {
  return fetchJson("/symbol/code", {
    method: "POST",
    body: JSON.stringify({
      file_path: symbol.file_path,
      symbol_name: symbol.name,
      kind: symbol.kind
    })
  });
}

export async function streamSymbolChat(symbolName, symbolCode, history, userMessage, onChunk, onComplete, onError) {
  try {
    const base = API_BASE.replace(/\/$/, "");
    const url = `${base}/chat/stream`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        symbol_name: symbolName,
        symbol_code: symbolCode,
        history: history,
        user_message: userMessage
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      
      for (const line of lines) {
        const cleanedLine = line.trim();
        if (!cleanedLine) continue;
        
        if (cleanedLine.startsWith("data: [DONE]")) {
          onComplete();
          return;
        }
        
        if (cleanedLine.startsWith("data: ")) {
          try {
            const parsed = JSON.parse(cleanedLine.substring(6));
            if (parsed.chunk) {
              onChunk(parsed.chunk);
            } else if (parsed.error) {
              onError(new Error(parsed.error));
            }
          } catch (e) {
            console.error("SSE parse error", e);
          }
        }
      }
    }
    onComplete();
  } catch (err) {
    onError(err);
  }
}
