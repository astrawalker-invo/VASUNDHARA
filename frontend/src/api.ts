import type {
  NdviResponse,
  PowerResponse,
  ProgressEvent,
  ClimateAnalysisResponse,
  TrendAnalysisResponse,
  VegetationAnalysisResponse,
  FarmerProfile,
  RotationEvaluationResponse,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export async function fetchPower(lat: number, lon: number, startYear: number, endYear: number, signal?: AbortSignal): Promise<PowerResponse> {
  const q = new URLSearchParams({ lat: String(lat), lon: String(lon), start_year: String(startYear), end_year: String(endYear) });
  const res = await fetch(`${API_BASE}/api/data/power?${q}`, { signal });
  if (!res.ok) throw new Error(`POWER request failed (${res.status})`);
  return res.json();
}

export async function fetchClimateAnalysis(
  lat: number,
  lon: number,
  startYear: number,
  endYear: number,
  signal?: AbortSignal,
): Promise<ClimateAnalysisResponse> {
  const q = new URLSearchParams({ lat: String(lat), lon: String(lon), start_year: String(startYear), end_year: String(endYear) });
  const res = await fetch(`${API_BASE}/api/analysis/climate?${q}`, { signal });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Climate analysis failed (${res.status})`);
  }
  return res.json();
}

export async function fetchTrendAnalysis(
  lat: number,
  lon: number,
  startYear: number,
  endYear: number,
  signal?: AbortSignal,
): Promise<TrendAnalysisResponse> {
  const q = new URLSearchParams({ lat: String(lat), lon: String(lon), start_year: String(startYear), end_year: String(endYear) });
  const res = await fetch(`${API_BASE}/api/analysis/trends?${q}`, { signal });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Trend analysis failed (${res.status})`);
  }
  return res.json();
}

export async function fetchVegetationAnalysis(
  lat: number,
  lon: number,
  startYear: number,
  endYear: number,
  signal?: AbortSignal,
  fallback: boolean = true,
): Promise<VegetationAnalysisResponse> {
  const q = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    start_year: String(startYear),
    end_year: String(endYear),
    fallback: fallback ? "true" : "false",
  });
  const res = await fetch(`${API_BASE}/api/analysis/vegetation?${q}`, { signal });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Vegetation analysis failed (${res.status})`);
  }
  return res.json();
}

export async function fetchRotationEvaluation(
  profile: FarmerProfile,
  signal?: AbortSignal,
): Promise<RotationEvaluationResponse> {
  const res = await fetch(`${API_BASE}/api/rotation/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
    signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Rotation evaluation failed (${res.status})`);
  }
  return res.json();
}

export async function fetchCrops(
  params?: { category?: string; season?: string; region?: string; q?: string },
  signal?: AbortSignal,
): Promise<Record<string, any>> {
  const q = new URLSearchParams();
  if (params?.category) q.set("category", params.category);
  if (params?.season) q.set("season", params.season);
  if (params?.region) q.set("region", params.region);
  if (params?.q) q.set("q", params.q);

  const url = q.toString() ? `${API_BASE}/api/rotation/crops?${q}` : `${API_BASE}/api/rotation/crops`;
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`Failed to fetch crop database (${res.status})`);
  return res.json();
}

export async function fetchCustomRotationEvaluation(
  cropIds: string[],
  profile: FarmerProfile,
  signal?: AbortSignal,
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/rotation/evaluate-custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      crop_ids: cropIds,
      area_acres: profile.area_acres,
      soil_type: profile.soil_type,
      soil_ph: profile.soil_ph,
      organic_carbon_pct: profile.organic_carbon_pct,
      irrigation: profile.irrigation,
      priority: profile.priority,
      lat: profile.lat,
      lon: profile.lon,
      climate_summary: profile.climate_summary,
    }),
    signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Custom rotation evaluation failed (${res.status})`);
  }
  return res.json();
}


export async function fetchNdvi(
  lat: number, lon: number, startYear: number, endYear: number,
  signal: AbortSignal, onProgress: (event: ProgressEvent) => void,
): Promise<NdviResponse> {
  const q = new URLSearchParams({ lat: String(lat), lon: String(lon), start_year: String(startYear), end_year: String(endYear) });
  const res = await fetch(`${API_BASE}/api/data/ndvi/stream?${q}`, { signal, headers: { Accept: "text/event-stream" } });
  if (!res.ok || !res.body) throw new Error(`NDVI request failed (${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: NdviResponse | null = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      const event = JSON.parse(line.slice(5).trim()) as ProgressEvent & { result?: NdviResponse };
      if (event.step === "result" && event.result) result = event.result;
      else onProgress(event);
    }
  }
  if (!result) throw new Error("The MODIS stream ended without a result");
  return result;
}
