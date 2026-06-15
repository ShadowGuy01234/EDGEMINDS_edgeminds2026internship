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
