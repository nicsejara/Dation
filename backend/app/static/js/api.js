async function request(url, options = {}) {
  const response = await fetch(url, options);

  let payload = null;
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload
        ? payload.detail || JSON.stringify(payload)
        : payload || response.statusText;

    throw new Error(detail);
  }

  return payload;
}

export function getWorkspaceSummary() {
  return request("/api/workspace/summary");
}

export function getDatasets(limit = 25) {
  return request(`/api/datasets?limit=${limit}`);
}

export function getRuns(limit = 40, datasetId = null) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (datasetId) params.set("dataset_id", datasetId);

  return request(`/api/runs?${params.toString()}`);
}

export function getRun(runId) {
  return request(`/api/runs/${encodeURIComponent(runId)}`);
}

export function getInterpreterStatus() {
  return request("/api/system/llm-status");
}

export function getSupabaseStatus() {
  return request("/api/system/supabase-check");
}

export function uploadDataset(file) {
  const body = new FormData();
  body.append("file", file);

  return request("/api/datasets/upload", {
    method: "POST",
    body,
  });
}

export function runDecision(datasetId, objective) {
  const params = new URLSearchParams({ objective });

  return request(
    `/api/runs/${encodeURIComponent(datasetId)}?${params.toString()}`,
    { method: "POST" }
  );
}

export function explainRun(runId) {
  return request(
    `/api/runs/${encodeURIComponent(runId)}/explain`,
    { method: "POST" }
  );
}

export function askRun(runId, question) {
  return request(
    `/api/runs/${encodeURIComponent(runId)}/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }
  );
}
