async function request(
  url,
  options = {},
) {
  const response = await fetch(
    url,
    options,
  );

  const contentType = (
    response.headers.get(
      "content-type"
    ) || ""
  );

  const payload = (
    contentType.includes(
      "application/json"
    )
      ? await response.json()
      : await response.text()
  );

  if (!response.ok) {
    const detail = (
      typeof payload === "object"
      && payload
        ? payload.detail
          || JSON.stringify(payload)
        : payload
          || response.statusText
    );

    throw new Error(detail);
  }

  return payload;
}


export function getWorkspaceSummary() {
  return request(
    "/api/workspace/summary"
  );
}


export function getDatasets(
  limit = 50,
) {
  return request(
    `/api/datasets?limit=${limit}`
  );
}


export function getDatasetProfile(
  datasetId,
) {
  return request(
    "/api/datasets/"
    + encodeURIComponent(datasetId)
    + "/profile"
  );
}


export function getRuns(
  limit = 60,
  datasetId = null,
) {
  const params = new URLSearchParams({
    limit: String(limit),
  });

  if (datasetId) {
    params.set(
      "dataset_id",
      datasetId,
    );
  }

  return request(
    `/api/runs?${params.toString()}`
  );
}


export function getRun(runId) {
  return request(
    "/api/runs/"
    + encodeURIComponent(runId)
  );
}


export function getRunInterpretation(
  runId,
) {
  return request(
    "/api/runs/"
    + encodeURIComponent(runId)
    + "/interpretation"
  );
}


export function getInterpreterStatus() {
  return request(
    "/api/system/llm-status"
  );
}


export function getSupabaseStatus() {
  return request(
    "/api/system/supabase-check"
  );
}


export function uploadDataset(file) {
  const body = new FormData();
  body.append(
    "file",
    file,
  );

  return request(
    "/api/datasets/upload",
    {
      method: "POST",
      body,
    },
  );
}


export function runDecision(
  datasetId,
  configuration,
) {
  return request(
    "/api/runs/"
    + encodeURIComponent(datasetId),
    {
      method: "POST",
      headers: {
        "Content-Type": (
          "application/json"
        ),
      },
      body: JSON.stringify(
        configuration
      ),
    },
  );
}


export function explainRun(runId) {
  return request(
    "/api/runs/"
    + encodeURIComponent(runId)
    + "/explain",
    {
      method: "POST",
    },
  );
}


export function askRun(
  runId,
  question,
) {
  return request(
    "/api/runs/"
    + encodeURIComponent(runId)
    + "/chat",
    {
      method: "POST",
      headers: {
        "Content-Type": (
          "application/json"
        ),
      },
      body: JSON.stringify({
        question,
      }),
    },
  );
}
