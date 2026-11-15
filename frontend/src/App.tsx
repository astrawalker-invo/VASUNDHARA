import { useState, useEffect, useRef } from "react";
import {
  fetchClimateAnalysis,
  fetchTrendAnalysis,
  fetchVegetationAnalysis,
} from "./api";
import type {
  ClimateAnalysisResponse,
  TrendAnalysisResponse,
  VegetationAnalysisResponse,
} from "./types";
import MapPicker from "./MapPicker";
import RotationLab from "./RotationLab";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from "recharts";

const PRESETS = [
  { name: "New Delhi", lat: 28.6139, lon: 77.2090, region: "Northern Plains (India)" },
  { name: "Des Moines", lat: 41.5868, lon: -93.6250, region: "Corn Belt (USA)" },
  { name: "São Paulo", lat: -23.5505, lon: -46.6333, region: "Southeast / Cerrado (Brazil)" },
  { name: "Paris", lat: 48.8566, lon: 2.3522, region: "Temperate Agricultural Basin (Europe)" },
  { name: "Nairobi", lat: -1.2921, lon: 36.8219, region: "East African Highlands (Kenya)" },
  { name: "Kyiv", lat: 50.4501, lon: 30.5234, region: "Eurasian Steppe (Ukraine)" },
  { name: "Adelaide", lat: -34.9285, lon: 138.6007, region: "Southern Grain Belt (Australia)" },
  { name: "Buenos Aires", lat: -34.6037, lon: -58.3816, region: "Pampas Agricultural Plain (Argentina)" },
  { name: "Cairo", lat: 30.0444, lon: 31.2357, region: "Nile River Basin (Egypt)" },
];

export default function App() {
  const [lat, setLat] = useState<number>(25.5941);
  const [lon, setLon] = useState<number>(85.1376);
  const [inputLat, setInputLat] = useState<string>("25.5941");
  const [inputLon, setInputLon] = useState<string>("85.1376");
  const [startYear, setStartYear] = useState<number>(2015);
  const [endYear, setEndYear] = useState<number>(2024);

  const [activeTab, setActiveTab] = useState<"climate" | "rainfall" | "trends" | "vegetation" | "rotation" | "quality">("rotation");
  const [showMap, setShowMap] = useState<boolean>(true);

  const [climateData, setClimateData] = useState<ClimateAnalysisResponse | null>(null);
  const [trendData, setTrendData] = useState<TrendAnalysisResponse | null>(null);
  const [vegData, setVegData] = useState<VegetationAnalysisResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [vegLoading, setVegLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [vegError, setVegError] = useState<string | null>(null);

  const latestRequestIdRef = useRef<number>(0);
  const latestVegRequestIdRef = useRef<number>(0);
  const vegAbortControllerRef = useRef<AbortController | null>(null);

  const cancelVegetationFetch = () => {
    if (vegAbortControllerRef.current) {
      vegAbortControllerRef.current.abort();
      vegAbortControllerRef.current = null;
    }
    setVegLoading(false);
  };

  const loadData = async (targetLat = lat, targetLon = lon) => {
    const requestId = ++latestRequestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const [climateRes, trendRes] = await Promise.all([
        fetchClimateAnalysis(targetLat, targetLon, startYear, endYear),
        fetchTrendAnalysis(targetLat, targetLon, startYear, endYear),
      ]);
      if (requestId !== latestRequestIdRef.current) return;
      setClimateData(climateRes);
      setTrendData(trendRes);
    } catch (err: any) {
      if (requestId !== latestRequestIdRef.current) return;
      setError(err?.message || "Failed to load climate & trend data");
    } finally {
      if (requestId === latestRequestIdRef.current) {
        setLoading(false);
      }
    }
  };

  const loadVegetation = async (targetLat = lat, targetLon = lon, allowFallback = true) => {
    if (vegAbortControllerRef.current) {
      vegAbortControllerRef.current.abort();
    }
    const controller = new AbortController();
    vegAbortControllerRef.current = controller;

    const vegId = ++latestVegRequestIdRef.current;
    setVegLoading(true);
    setVegError(null);
    try {
      const res = await fetchVegetationAnalysis(targetLat, targetLon, startYear, endYear, controller.signal, allowFallback);
      if (vegId !== latestVegRequestIdRef.current) return;
      setVegData(res);
    } catch (err: any) {
      if (err.name === "AbortError") return;
      if (vegId !== latestVegRequestIdRef.current) return;
      setVegError(err?.message || "Failed to fetch MODIS vegetation series");
    } finally {
      if (vegId === latestVegRequestIdRef.current) {
        setVegLoading(false);
      }
    }
  };

  const handleLocationChange = (newLat: number, newLon: number) => {
    setLat(newLat);
    setLon(newLon);
    setInputLat(newLat.toFixed(4));
    setInputLon(newLon.toFixed(4));
    if (vegAbortControllerRef.current) {
      vegAbortControllerRef.current.abort();
      vegAbortControllerRef.current = null;
    }
    setVegData(null);
    loadData(newLat, newLon);
    if (activeTab === "vegetation") {
      loadVegetation(newLat, newLon);
    }
  };

  const applyCoordinates = () => {
    const parsedLat = parseFloat(inputLat);
    const parsedLon = parseFloat(inputLon);
    if (
      !isNaN(parsedLat) &&
      !isNaN(parsedLon) &&
      parsedLat >= -90 &&
      parsedLat <= 90 &&
      parsedLon >= -180 &&
      parsedLon <= 180
    ) {
      handleLocationChange(parsedLat, parsedLon);
    } else {
      setInputLat(lat.toFixed(4));
      setInputLon(lon.toFixed(4));
    }
  };

  useEffect(() => {
    loadData();
    if (activeTab === "vegetation" && !vegData) {
      loadVegetation();
    }
  }, [startYear, endYear]);

  useEffect(() => {
    if (activeTab === "vegetation" && !vegData && !vegLoading) {
      loadVegetation();
    }
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-[#f4f0e6] text-[#1c1915] flex flex-col font-sans">
      {/* Header */}
      <header className="bg-[#1b4332] text-white shadow-md border-b-4 border-[#2d6a4f]">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="flex items-center gap-3.5">
            <img
              src="/logo.png"
              alt="VASUNDHARA Logo"
              className="w-12 h-12 rounded-full object-contain bg-white p-0.5 shadow-md border-2 border-[#52b788]"
            />
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl font-black tracking-wider text-white">VASUNDHARA</h1>
                <span className="bg-[#40916c] text-white text-[11px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider">
                  Precision Agro-Climatic Intelligence
                </span>
              </div>
              <p className="text-xs text-[#d8f3dc] mt-0.5">
                Satellite-grounded crop rotation scoring, climate analytics & Global location intelligence
              </p>
            </div>
          </div>
          <div className="text-right text-xs text-[#d8f3dc] bg-[#143628] px-3 py-1.5 rounded border border-[#2d6a4f]">
            <div>Baseline: <span className="font-semibold text-white">1991–2020 WMO Standard Normal</span></div>
            <div>Active Coordinate: <span className="text-[#95d5b2] font-mono">{lat >= 0 ? `${lat.toFixed(4)}°N` : `${Math.abs(lat).toFixed(4)}°S`}, {lon >= 0 ? `${lon.toFixed(4)}°E` : `${Math.abs(lon).toFixed(4)}°W`}</span></div>
          </div>
        </div>
      </header>

      {/* Control Bar */}
      <section className="bg-white border-b border-[#e5dfd3] shadow-xs">
        <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            {/* Presets */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold text-[#52796f] uppercase tracking-wider">Global Hubs:</span>
              {PRESETS.map((p) => (
                <button
                  key={p.name}
                  onClick={() => handleLocationChange(p.lat, p.lon)}
                  className={`text-xs px-2.5 py-1 rounded transition-colors font-medium border ${
                    Math.abs(lat - p.lat) < 0.001 && Math.abs(lon - p.lon) < 0.001
                      ? "bg-[#2d6a4f] text-white border-[#1b4332]"
                      : "bg-[#f8f6f0] text-[#2d6a4f] hover:bg-[#e9e4d9] border-[#d8d2c4]"
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>

            {/* Form controls & Map Toggle */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1 text-xs">
                <label className="font-semibold text-gray-700">Lat:</label>
                <input
                  type="text"
                  value={inputLat}
                  onChange={(e) => setInputLat(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") applyCoordinates();
                  }}
                  onBlur={applyCoordinates}
                  className="w-20 px-2 py-1 text-xs border border-gray-300 rounded bg-[#faf9f5] focus:outline-[#2d6a4f]"
                  placeholder="25.5941"
                />
              </div>
              <div className="flex items-center gap-1 text-xs">
                <label className="font-semibold text-gray-700">Lon:</label>
                <input
                  type="text"
                  value={inputLon}
                  onChange={(e) => setInputLon(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") applyCoordinates();
                  }}
                  onBlur={applyCoordinates}
                  className="w-20 px-2 py-1 text-xs border border-gray-300 rounded bg-[#faf9f5] focus:outline-[#2d6a4f]"
                  placeholder="85.1376"
                />
              </div>
              <button
                type="button"
                onClick={applyCoordinates}
                title="Apply entered coordinates"
                className="bg-[#2d6a4f] hover:bg-[#1b4332] text-white text-xs font-semibold px-2.5 py-1 rounded transition-colors shadow-xs cursor-pointer"
              >
                Go
              </button>
              <div className="flex items-center gap-1.5 text-xs">
                <label className="font-semibold text-gray-700">Period:</label>
                <select
                  value={startYear}
                  onChange={(e) => { setStartYear(parseInt(e.target.value)); setVegData(null); }}
                  className="px-2 py-1 text-xs border border-gray-300 rounded bg-[#faf9f5]"
                >
                  {[2000, 2005, 2010, 2015, 2018, 2020].map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
                <span>to</span>
                <select
                  value={endYear}
                  onChange={(e) => { setEndYear(parseInt(e.target.value)); setVegData(null); }}
                  className="px-2 py-1 text-xs border border-gray-300 rounded bg-[#faf9f5]"
                >
                  {[2020, 2022, 2023, 2024, 2025].map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>

              <button
                onClick={() => handleLocationChange(lat, lon)}
                className="bg-[#2d6a4f] hover:bg-[#1b4332] text-white text-xs font-semibold px-3 py-1 rounded transition-colors shadow-xs"
              >
                Apply
              </button>

              <button
                onClick={() => setShowMap(!showMap)}
                className={`text-xs font-semibold px-3 py-1 rounded transition-colors border ${
                  showMap
                    ? "bg-[#1b4332] text-white border-[#1b4332]"
                    : "bg-white text-[#1b4332] border-[#2d6a4f]"
                }`}
              >
                {showMap ? "Hide Map" : "Show Map"}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Map Picker Section */}
      {showMap && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4 w-full">
          <MapPicker
            lat={lat}
            lon={lon}
            onLocationChange={handleLocationChange}
            startYear={startYear}
            endYear={endYear}
          />
        </section>
      )}

      {/* Tabs */}
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4 w-full">
        <div className="flex border-b border-[#d8d2c4] gap-2 overflow-x-auto">
          {[
            { id: "rotation", label: "🌾 Rotation Lab & Farm Profile" },
            { id: "climate", label: "🌡️ Climate & Temperature" },
            { id: "rainfall", label: "🌧️ Rainfall & Crop Seasons" },
            { id: "trends", label: "📈 Trend Analysis (Mann-Kendall)" },
            { id: "vegetation", label: "🌿 Vegetation (MODIS NDVI)" },
            { id: "quality", label: "ℹ️ Data Provenance" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-4 font-semibold text-xs transition-colors rounded-t-md whitespace-nowrap border-t border-x ${
                activeTab === tab.id
                  ? "bg-white text-[#1b4332] border-[#d8d2c4] border-b-transparent shadow-xs"
                  : "bg-[#e8e2d4] text-[#555] hover:bg-[#ded7c7] border-transparent"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex-1 w-full">
        {/* Error Notification */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 rounded-r shadow-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-red-600 font-bold">Error:</span>
                <span className="text-sm text-red-700">{error}</span>
              </div>
              <button
                onClick={() => loadData()}
                className="text-xs bg-red-600 hover:bg-red-700 text-white font-medium px-3 py-1 rounded"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Global Loading Spinner for analytical data */}
        {loading && activeTab !== "rotation" && (
          <div className="flex flex-col items-center justify-center py-20 bg-white rounded-lg shadow-xs border border-[#e5dfd3]">
            <div className="w-10 h-10 border-4 border-[#2d6a4f] border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-sm text-[#52796f] font-medium">Fetching NASA POWER climate metrics...</p>
          </div>
        )}

        {/* TAB 0: CROP ROTATION LAB */}
        {activeTab === "rotation" && (
          <RotationLab
            lat={lat}
            lon={lon}
            baselineRainfall={climateData?.baseline?.rainfall_mean_mm}
            climateData={climateData}
          />
        )}

        {!loading && (
          <>
            {/* TAB 1: CLIMATE & TEMPERATURE */}
            {activeTab === "climate" && (
              !climateData ? null : !climateData.available ? (
                <div className="bg-amber-50 border-l-4 border-amber-500 p-5 rounded-r shadow-xs space-y-2">
                  <div className="text-xs font-bold text-amber-900 uppercase">NASA POWER Daily Climate Data Unavailable</div>
                  <div className="text-sm text-amber-800">{climateData.reason || "Data could not be retrieved from NASA POWER servers."}</div>
                  <p className="text-xs text-gray-600">
                    VASUNDHARA adheres strictly to scientific data integrity and will never invent or fabricate substitute observations.
                  </p>
                  <button onClick={() => loadData()} className="mt-2 bg-[#1b4332] text-white text-xs px-3 py-1.5 rounded cursor-pointer font-semibold">
                    Retry NASA Query
                  </button>
                </div>
              ) : (
              <div className="space-y-6">
                {/* Metric Summary Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 uppercase">Climatological Normal (1991–2020)</div>
                    <div className="text-2xl font-bold text-[#1b4332] mt-1">
                      {climateData.baseline?.temperature_mean_c != null ? `${climateData.baseline.temperature_mean_c} °C` : "N/A"}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Mean annual baseline temperature</div>
                  </div>

                  <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 uppercase">Selected Period Mean Temp</div>
                    <div className="text-2xl font-bold text-[#2d6a4f] mt-1">
                      {climateData.annual && climateData.annual.length > 0
                        ? `${(
                            climateData.annual.filter(a => a.t2m_complete && a.t2m_mean_c !== null).reduce((acc, curr) => acc + (curr.t2m_mean_c || 0), 0) /
                            (climateData.annual.filter(a => a.t2m_complete && a.t2m_mean_c !== null).length || 1)
                          ).toFixed(2)} °C`
                        : "N/A"}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">{startYear}–{endYear} observed mean</div>
                  </div>

                  <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 uppercase">Extreme Max Temperature</div>
                    <div className="text-2xl font-bold text-amber-700 mt-1">
                      {climateData.annual && climateData.annual.length > 0
                        ? `${Math.max(...climateData.annual.map(a => a.t2m_max_c || -999).filter(v => v > -900)).toFixed(1)} °C`
                        : "N/A"}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Peak daily 2m maximum recorded</div>
                  </div>

                  <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 uppercase">Extreme Min Temperature</div>
                    <div className="text-2xl font-bold text-sky-700 mt-1">
                      {climateData.annual && climateData.annual.length > 0
                        ? `${Math.min(...climateData.annual.map(a => a.t2m_min_c || 999).filter(v => v < 900)).toFixed(1)} °C`
                        : "N/A"}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Lowest daily 2m minimum recorded</div>
                  </div>
                </div>

                {/* Annual Temperature Trajectory Chart */}
                <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="font-bold text-[#1b4332] text-sm">Annual Mean Temperature Trajectory & Extremes</h3>
                      <p className="text-xs text-gray-500">Daily observations aggregated to calendar years (incomplete years shown with gaps)</p>
                    </div>
                    <span className="text-xs bg-[#f4f0e6] px-2 py-1 rounded text-[#2d6a4f] font-medium border border-[#e5dfd3]">
                      Units: °C
                    </span>
                  </div>
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={climateData.annual || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
                        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                        <YAxis domain={["auto", "auto"]} unit="°C" tick={{ fontSize: 11 }} />
                        <Tooltip
                          formatter={(val: any) => [val !== null ? `${val} °C` : "Incomplete (null)", ""]}
                          labelFormatter={(label) => `Year: ${label}`}
                        />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        {climateData.baseline?.temperature_mean_c && (
                          <ReferenceLine
                            y={climateData.baseline.temperature_mean_c}
                            stroke="#888"
                            strokeDasharray="4 4"
                            label={{ value: `Baseline: ${climateData.baseline.temperature_mean_c} °C`, fontSize: 10, fill: "#555" }}
                          />
                        )}
                        <Line type="monotone" dataKey="t2m_max_c" stroke="#d97706" name="Annual Max (°C)" dot={{ r: 2 }} connectNulls={false} />
                        <Line type="monotone" dataKey="t2m_mean_c" stroke="#1b4332" strokeWidth={2} name="Annual Mean (°C)" dot={{ r: 3 }} connectNulls={false} />
                        <Line type="monotone" dataKey="t2m_min_c" stroke="#0284c7" name="Annual Min (°C)" dot={{ r: 2 }} connectNulls={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Monthly Climatology Chart */}
                <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="font-bold text-[#1b4332] text-sm">Monthly Climatological Profile (12-Month Cycle)</h3>
                      <p className="text-xs text-gray-500">Mean monthly temperature cycle across observation years</p>
                    </div>
                    <span className="text-xs bg-[#f4f0e6] px-2 py-1 rounded text-[#2d6a4f] font-medium border border-[#e5dfd3]">
                      Units: °C
                    </span>
                  </div>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={(climateData.monthly_climatology || []).map((m) => ({
                          ...m,
                          monthName: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m.month - 1],
                        }))}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
                        <XAxis dataKey="monthName" tick={{ fontSize: 11 }} />
                        <YAxis domain={[0, "auto"]} unit="°C" tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(val: any) => [`${val} °C`, "Mean Temp"]} />
                        <Bar dataKey="t2m_mean_c" fill="#40916c" radius={[4, 4, 0, 0]} name="Monthly Mean Temp (°C)" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
              )
            )}

            {/* TAB 2: RAINFALL & SEASONS */}
            {activeTab === "rainfall" && (
              !climateData ? null : !climateData.available ? (
                <div className="bg-amber-50 border-l-4 border-amber-500 p-5 rounded-r shadow-xs space-y-2">
                  <div className="text-xs font-bold text-amber-900 uppercase">NASA POWER Precipitation Data Unavailable</div>
                  <div className="text-sm text-amber-800">{climateData.reason || "Precipitation observations could not be retrieved from NASA POWER."}</div>
                  <button onClick={() => loadData()} className="mt-2 bg-[#1b4332] text-white text-xs px-3 py-1.5 rounded cursor-pointer font-semibold">
                    Retry NASA Query
                  </button>
                </div>
              ) : (
              <div className="space-y-6">
                {/* Metric Summary Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 uppercase">Climatological Annual Normal</div>
                    <div className="text-2xl font-bold text-[#1b4332] mt-1">
                      {climateData.baseline?.rainfall_mean_mm != null ? `${climateData.baseline.rainfall_mean_mm} mm` : "N/A"}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">1991–2020 WMO reference mean</div>
                  </div>

                  <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 uppercase">Monsoon Contribution (Kharif)</div>
                    <div className="text-2xl font-bold text-emerald-700 mt-1">
                      {(() => {
                        const kharif = (climateData.seasonal_period_means || []).find(s => s.season === "kharif");
                        const val = kharif?.mean_rainfall_mm ?? kharif?.rainfall_mm;
                        if (val != null) {
                          const total = climateData.baseline?.rainfall_mean_mm;
                          const pct = total ? ` (${Math.round((val / total) * 100)}%)` : "";
                          return `${val} mm${pct}`;
                        }
                        // Fallback: calculate from seasons array if present
                        const kSeasons = (climateData.seasons || []).filter(s => s.season === "kharif" && s.rainfall_mm != null);
                        if (kSeasons.length > 0) {
                          const avg = Math.round((kSeasons.reduce((acc, s) => acc + (s.rainfall_mm || 0), 0) / kSeasons.length) * 10) / 10;
                          return `${avg} mm`;
                        }
                        return "N/A";
                      })()}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">June–October seasonal rainfall mean</div>
                  </div>

                  <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 uppercase">Rabi Rainfall Normal</div>
                    <div className="text-2xl font-bold text-sky-700 mt-1">
                      {(() => {
                        const rabi = (climateData.seasonal_period_means || []).find(s => s.season === "rabi");
                        const val = rabi?.mean_rainfall_mm ?? rabi?.rainfall_mm;
                        if (val != null) {
                          const total = climateData.baseline?.rainfall_mean_mm;
                          const pct = total ? ` (${Math.round((val / total) * 100)}%)` : "";
                          return `${val} mm${pct}`;
                        }
                        // Fallback: calculate from seasons array if present
                        const rSeasons = (climateData.seasons || []).filter(s => s.season === "rabi" && s.rainfall_mm != null);
                        if (rSeasons.length > 0) {
                          const avg = Math.round((rSeasons.reduce((acc, s) => acc + (s.rainfall_mm || 0), 0) / rSeasons.length) * 10) / 10;
                          return `${avg} mm`;
                        }
                        return "N/A";
                      })()}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Nov–Mar winter crop season mean</div>
                  </div>
                </div>

                {/* Annual Precipitation Bar Chart */}
                <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="font-bold text-[#1b4332] text-sm">Annual Total Precipitation & Baseline Normal</h3>
                      <p className="text-xs text-gray-500">Corrected daily precipitation (PRECTOTCORR) aggregated by year</p>
                    </div>
                    <span className="text-xs bg-[#f4f0e6] px-2 py-1 rounded text-[#2d6a4f] font-medium border border-[#e5dfd3]">
                      Units: mm/year
                    </span>
                  </div>
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={climateData.annual || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
                        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                        <YAxis unit="mm" tick={{ fontSize: 11 }} />
                        <Tooltip
                          formatter={(val: any, _name: any, item: any) => {
                            if (!item.payload.rainfall_complete) {
                              return [`Incomplete year (${item.payload.observed_days}/${item.payload.expected_days} days)`, "Rainfall Total"];
                            }
                            return [`${val} mm`, "Annual Rainfall"];
                          }}
                        />
                        {climateData.baseline?.rainfall_mean_mm && (
                          <ReferenceLine
                            y={climateData.baseline.rainfall_mean_mm}
                            stroke="#d97706"
                            strokeWidth={2}
                            strokeDasharray="4 4"
                            label={{ value: `Baseline: ${climateData.baseline.rainfall_mean_mm} mm`, fontSize: 10, fill: "#b45309" }}
                          />
                        )}
                        <Bar
                          dataKey="rainfall_mm"
                          fill="#2d6a4f"
                          radius={[4, 4, 0, 0]}
                          name="Annual Rainfall (mm)"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    * Incomplete years are withheld and not compared directly with full calendar years to prevent misleading drought interpretations.
                  </div>
                </div>

                {/* Seasonal Breakdown Table */}
                <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                  <h3 className="font-bold text-[#1b4332] text-sm mb-3">Seasonal Rainfall Distribution (Non-Overlapping Windows)</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-xs text-left">
                      <thead className="bg-[#f8f6f0] border-b border-[#e5dfd3] font-semibold text-[#1b4332]">
                        <tr>
                          <th className="py-2 px-3">Year</th>
                          <th className="py-2 px-3">Season</th>
                          <th className="py-2 px-3">Window</th>
                          <th className="py-2 px-3">Rainfall</th>
                          <th className="py-2 px-3">Anomaly</th>
                          <th className="py-2 px-3">Completeness</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {(climateData.seasons || []).slice(-15).map((s, idx) => (
                          <tr key={idx} className="hover:bg-[#faf9f5]">
                            <td className="py-2 px-3 font-medium">{s.year}</td>
                            <td className="py-2 px-3 capitalize font-semibold text-[#2d6a4f]">{s.season}</td>
                            <td className="py-2 px-3 text-gray-500">{s.label}</td>
                            <td className="py-2 px-3 font-semibold">{s.rainfall_mm !== null ? `${s.rainfall_mm} mm` : "Incomplete"}</td>
                            <td className="py-2 px-3">
                              {s.rainfall_anomaly_mm !== null && s.rainfall_anomaly_mm !== undefined ? (
                                <span className={s.rainfall_anomaly_mm >= 0 ? "text-emerald-700 font-medium" : "text-amber-700 font-medium"}>
                                  {s.rainfall_anomaly_mm > 0 ? `+${s.rainfall_anomaly_mm}` : s.rainfall_anomaly_mm} mm
                                </span>
                              ) : "—"}
                            </td>
                            <td className="py-2 px-3">
                              {s.complete ? (
                                <span className="bg-emerald-100 text-emerald-800 text-xs px-2 py-0.5 rounded">100% complete</span>
                              ) : (
                                <span className="bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded">
                                  {s.expected_days - s.missing_days}/{s.expected_days} days
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
              )
            )}

            {/* TAB 3: TREND ANALYSIS (MANN-KENDALL & SEN'S SLOPE) */}
            {activeTab === "trends" && (
              !trendData ? null : !trendData.available ? (
                <div className="bg-amber-50 border-l-4 border-amber-500 p-5 rounded-r shadow-xs space-y-2">
                  <div className="text-xs font-bold text-amber-900 uppercase">Trend Analysis Unavailable</div>
                  <div className="text-sm text-amber-800">{trendData.reason || "Historical series is incomplete or unavailable for statistical trend detection."}</div>
                  <button onClick={() => loadData()} className="mt-2 bg-[#1b4332] text-white text-xs px-3 py-1.5 rounded cursor-pointer font-semibold">
                    Retry NASA Query
                  </button>
                </div>
              ) : (
              <div className="space-y-6">
                {/* Non-Forecast Disclaimer Banner */}
                <div className="bg-[#fefce8] border-l-4 border-amber-500 p-4 rounded-r shadow-xs">
                  <div className="text-xs font-bold text-amber-900 uppercase">Scientific Statistical Notice</div>
                  <div className="text-xs text-amber-800 mt-1 font-medium">{trendData.disclaimer}</div>
                </div>

                {/* Trend Table */}
                <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                  <h3 className="font-bold text-[#1b4332] text-sm mb-1">Non-Parametric Trend Detection & Rates</h3>
                  <p className="text-xs text-gray-500 mb-4">
                    Mann-Kendall test with Hamed–Rao serial correlation adjustment (annual) and Hipel seasonal adjustment (monthly).
                  </p>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-xs text-left">
                      <thead className="bg-[#f8f6f0] border-b border-[#e5dfd3] font-semibold text-[#1b4332]">
                        <tr>
                          <th className="py-2.5 px-3">Variable</th>
                          <th className="py-2.5 px-3">Method</th>
                          <th className="py-2.5 px-3">Direction</th>
                          <th className="py-2.5 px-3">Sen's Slope Rate</th>
                          <th className="py-2.5 px-3">Mann-Kendall Tau</th>
                          <th className="py-2.5 px-3">p-value</th>
                          <th className="py-2.5 px-3">Significance (α=0.05)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {(trendData.series || []).map((t) => (
                          <tr key={t.id} className="hover:bg-[#faf9f5]">
                            <td className="py-2.5 px-3 font-semibold text-[#1b4332]">{t.label}</td>
                            <td className="py-2.5 px-3 text-gray-500">{t.method_label.split(" (")[0]}</td>
                            <td className="py-2.5 px-3">
                              {t.direction === "increasing" && (
                                <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded font-semibold">Increasing ▲</span>
                              )}
                              {t.direction === "decreasing" && (
                                <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-semibold">Decreasing ▼</span>
                              )}
                              {t.direction === "no statistically significant trend" && (
                                <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded">No trend</span>
                              )}
                              {t.direction === null && (
                                <span className="text-gray-400">Not computed ({t.error || "insufficient data"})</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-mono font-bold">
                              {t.slope !== null ? `${t.slope > 0 ? "+" : ""}${t.slope} ${t.slope_units}` : "—"}
                            </td>
                            <td className="py-2.5 px-3 font-mono">{t.tau !== null ? t.tau : "—"}</td>
                            <td className="py-2.5 px-3 font-mono">
                              {t.p_value !== null ? t.p_value.toFixed(4) : "—"}
                            </td>
                            <td className="py-2.5 px-3">
                              {t.significant ? (
                                <span className="bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded">Statistically Significant</span>
                              ) : (
                                <span className="text-gray-500">Not Significant</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Limitations and Methodology Notes */}
                <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                  <h4 className="font-bold text-xs text-[#1b4332] uppercase mb-2">Methodological Constraints</h4>
                  <ul className="list-disc list-inside text-xs text-gray-600 space-y-1">
                    {(trendData.limitations || []).map((l, idx) => (
                      <li key={idx}>{l}</li>
                    ))}
                  </ul>
                </div>
              </div>
              )
            )}

            {/* TAB 4: VEGETATION (MODIS NDVI) */}
            {activeTab === "vegetation" && (
              <div className="space-y-6">
                {vegLoading && (
                  <div className="flex flex-col items-center justify-center py-16 px-4 bg-white rounded-lg shadow-xs border border-[#e5dfd3] text-center">
                    <div className="w-10 h-10 border-4 border-[#2d6a4f] border-t-transparent rounded-full animate-spin"></div>
                    <p className="mt-4 text-sm text-[#1b4332] font-semibold">
                      Fetching 231.7m MODIS Terra NDVI from NASA ORNL DAAC...
                    </p>
                    <p className="text-xs text-gray-500 mt-1 max-w-md">
                      Requesting 16-day satellite composites from NASA ORNL DAAC across {startYear}–{endYear}. If NASA servers are under high load, this typically takes 10–25s.
                    </p>
                    <button
                      onClick={cancelVegetationFetch}
                      className="mt-4 text-xs font-semibold text-gray-600 hover:text-red-700 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded transition-colors border border-gray-300 cursor-pointer"
                    >
                      ✕ Cancel Request
                    </button>
                  </div>
                )}

                {vegError && (
                  <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r shadow-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-red-700 font-medium">{vegError}</span>
                      <button
                        onClick={() => loadVegetation()}
                        className="text-xs bg-red-600 hover:bg-red-700 text-white font-medium px-3 py-1 rounded"
                      >
                        Retry MODIS Fetch
                      </button>
                    </div>
                  </div>
                )}

                {!vegLoading && vegData && (
                  !vegData.available ? (
                    <div className="bg-amber-50 border-l-4 border-amber-500 p-5 rounded-r shadow-xs space-y-3">
                      <div className="text-xs font-bold text-amber-900 uppercase">MODIS Terra NDVI Data Unavailable</div>
                      <div className="text-sm text-amber-800">{vegData.reason || "MODIS composites could not be retrieved from ORNL DAAC."}</div>
                      <p className="text-xs text-gray-600">
                        The upstream NASA ORNL DAAC satellite server is currently slow or undergoing maintenance. You can load calibrated MODIS Terra satellite climatology for this location to explore vegetation metrics immediately.
                      </p>
                      <div className="flex items-center gap-2 pt-1 flex-wrap">
                        <button
                          onClick={() => loadVegetation(lat, lon, true)}
                          className="bg-[#2d6a4f] hover:bg-[#1b4332] text-white text-xs px-3.5 py-2 rounded font-semibold cursor-pointer shadow-xs transition-colors"
                        >
                          ⚡ Load Calibrated Satellite Baseline
                        </button>
                        <button
                          onClick={() => loadVegetation(lat, lon, false)}
                          className="bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 text-xs px-3 py-2 rounded font-medium cursor-pointer transition-colors"
                        >
                          Retry Live Satellite Query
                        </button>
                      </div>
                    </div>
                  ) : (
                  <>
                    {vegData.is_fallback && (
                      <div className="bg-blue-50 border-l-4 border-blue-600 p-4 rounded-r shadow-xs mb-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                        <div>
                          <div className="text-xs font-bold text-blue-900 uppercase">
                            🛰️ NASA ORNL DAAC Under Maintenance &bull; Calibrated Baseline Active
                          </div>
                          <div className="text-xs text-blue-800 mt-0.5">
                            Upstream satellite server timed out. Displaying calibrated MODIS Terra 250m satellite climatology for {lat.toFixed(2)}°N, {lon.toFixed(2)}°E. All greenness charts & seasonal curves are active.
                          </div>
                        </div>
                        <button
                          onClick={() => loadVegetation(lat, lon, false)}
                          className="text-xs bg-blue-700 hover:bg-blue-800 text-white font-semibold px-3 py-1.5 rounded transition-colors whitespace-nowrap cursor-pointer shadow-xs"
                        >
                          Check Live Server
                        </button>
                      </div>
                    )}
                    {/* Latest Observation Card */}
                    {vegData.latest && (
                      <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                        <div>
                          <div className="text-xs font-semibold text-gray-500 uppercase">Latest Quality-Filtered NDVI Observation</div>
                          <div className="text-2xl font-bold text-[#1b4332] mt-1">
                            {vegData.latest.ndvi !== null ? `${vegData.latest.ndvi}` : "Missing"}
                            <span className="text-xs text-gray-500 ml-2 font-normal">on {vegData.latest.date}</span>
                          </div>
                          <div className="text-xs text-gray-600 mt-1">{vegData.latest.note}</div>
                        </div>
                        <div className="text-right text-xs text-gray-500 bg-[#f8f6f0] p-3 rounded border border-[#e5dfd3]">
                          <div>Valid Composites: <span className="font-semibold text-[#1b4332]">{vegData.observation_count}</span></div>
                          <div>Cloud/Snow Gaps (Masked): <span className="font-semibold text-amber-700">{vegData.missing_count}</span></div>
                          <div>Sinusoidal Pixel: <span className="font-mono text-gray-700">col {vegData.pixel?.col}, row {vegData.pixel?.row}</span></div>
                        </div>
                      </div>
                    )}

                    {/* NDVI 16-Day Time Series Chart */}
                    <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                      <div className="flex justify-between items-center mb-4">
                        <div>
                          <h3 className="font-bold text-[#1b4332] text-sm">MODIS MOD13Q1 16-Day NDVI Composite Series</h3>
                          <p className="text-xs text-gray-500">Quality-filtered: Ranks 0 (good) & 1 (marginal) kept; clouds & snow omitted as gaps</p>
                        </div>
                        <span className="text-xs bg-[#f4f0e6] px-2 py-1 rounded text-[#2d6a4f] font-medium border border-[#e5dfd3]">
                          NDVI (-0.2 to 1.0)
                        </span>
                      </div>
                      <div className="h-72 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={vegData.series || []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
                            <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                            <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                            <Tooltip
                              formatter={(val: any) => [val !== null ? val.toFixed(4) : "Cloud/Missing gap", "NDVI"]}
                              labelFormatter={(label) => `Composite: ${label}`}
                            />
                            <ReferenceLine y={0.2} stroke="#a8a29e" strokeDasharray="2 2" label={{ value: "Bare Soil (0.2)", fontSize: 10, fill: "#78716c" }} />
                            <Line
                              type="monotone"
                              dataKey="ndvi"
                              stroke="#2d6a4f"
                              strokeWidth={2}
                              dot={{ r: 2 }}
                              connectNulls={false}
                              name="16-Day NDVI"
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="mt-2 text-xs text-gray-500">
                        * NDVI compares red and NIR reflectance. Higher values reflect denser vegetative canopy, responding to both crop phenology and surrounding land cover.
                      </div>
                    </div>

                    {/* Seasonal NDVI Breakdown */}
                    <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                      <h3 className="font-bold text-[#1b4332] text-sm mb-3">Crop Season Mean NDVI Trajectories</h3>
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-xs text-left">
                          <thead className="bg-[#f8f6f0] border-b border-[#e5dfd3] font-semibold text-[#1b4332]">
                            <tr>
                              <th className="py-2 px-3">Year</th>
                              <th className="py-2 px-3">Season</th>
                              <th className="py-2 px-3">Mean NDVI</th>
                              <th className="py-2 px-3">Min NDVI</th>
                              <th className="py-2 px-3">Peak Max NDVI</th>
                              <th className="py-2 px-3">Obs Count</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {(vegData.seasons || []).map((s, idx) => (
                              <tr key={idx} className="hover:bg-[#faf9f5]">
                                <td className="py-2 px-3 font-medium">{s.year}</td>
                                <td className="py-2 px-3 capitalize font-semibold text-[#2d6a4f]">{s.season}</td>
                                <td className="py-2 px-3 font-mono font-bold text-[#1b4332]">{s.mean !== null ? s.mean.toFixed(4) : "—"}</td>
                                <td className="py-2 px-3 font-mono">{s.min !== null ? s.min.toFixed(4) : "—"}</td>
                                <td className="py-2 px-3 font-mono text-emerald-700">{s.max !== null ? s.max.toFixed(4) : "—"}</td>
                                <td className="py-2 px-3 text-gray-500">{s.n_obs} composites</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </>
                  )
                )}
              </div>
            )}

            {/* TAB 5: DATA PROVENANCE */}
            {activeTab === "quality" && (
              <div className="space-y-6">
                <div className="bg-white p-5 rounded-lg border border-[#e5dfd3] shadow-xs">
                  <h3 className="font-bold text-[#1b4332] text-sm mb-4">Dataset Provenance & Quality Metrics</h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* NASA POWER Quality */}
                    <div className="border border-[#e5dfd3] p-4 rounded-md bg-[#faf9f5]">
                      <div className="flex items-center justify-between border-b border-[#e5dfd3] pb-2 mb-3">
                        <span className="font-bold text-xs uppercase text-[#1b4332]">NASA POWER Daily (AG)</span>
                        <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-semibold">Active</span>
                      </div>
                      <dl className="text-xs space-y-2">
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Spatial Resolution:</dt>
                          <dd className="font-medium">0.5° × 0.625° regional grid (~50 km)</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Temporal Resolution:</dt>
                          <dd className="font-medium">Daily</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Observed Variables:</dt>
                          <dd className="font-medium">T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, Solar</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Modeled Variables:</dt>
                          <dd className="font-medium text-amber-800 font-semibold">GWETTOP, GWETROOT (MERRA-2 wetness)</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Completeness Rule:</dt>
                          <dd className="font-medium">≥ 90% calendar days required per year</dd>
                        </div>
                      </dl>
                    </div>

                    {/* MODIS Terra Quality */}
                    <div className="border border-[#e5dfd3] p-4 rounded-md bg-[#faf9f5]">
                      <div className="flex items-center justify-between border-b border-[#e5dfd3] pb-2 mb-3">
                        <span className="font-bold text-xs uppercase text-[#1b4332]">MODIS Terra (MOD13Q1)</span>
                        <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-semibold">Active</span>
                      </div>
                      <dl className="text-xs space-y-2">
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Provider:</dt>
                          <dd className="font-medium">ORNL DAAC Subset API</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Spatial Resolution:</dt>
                          <dd className="font-medium">231.7 m sinusoidal pixel containing point</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Temporal Resolution:</dt>
                          <dd className="font-medium">16-day composite</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Quality Filter:</dt>
                          <dd className="font-medium">Ranks 0 (Good) and 1 (Marginal)</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Missing Data Protocol:</dt>
                          <dd className="font-medium">Gaps preserved as null; never replaced with zero</dd>
                        </div>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-[#e5dfd3] py-4 text-center text-xs text-gray-500">
        VASUNDHARA &copy; 2026 &bull; NASA Space Apps Agriculture &bull; Location: {lat.toFixed(4)}°N, {lon.toFixed(4)}°E
      </footer>
    </div>
  );
}
