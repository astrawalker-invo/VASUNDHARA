import { useState, useEffect } from "react";
import { fetchRotationEvaluation, fetchCustomRotationEvaluation, fetchCrops } from "./api";
import type {
  FarmerProfile,
  RotationEvaluationResponse,
  RotationStrategy,
  CropInfo,
  CustomRotationEvaluationResponse,
} from "./types";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from "recharts";

interface RotationLabProps {
  lat: number;
  lon: number;
  baselineRainfall?: number | null;
  climateData?: any;
}

const CATEGORIES = [
  { id: "all", label: "All Crops" },
  { id: "cereals_millets", label: "Cereals & Millets" },
  { id: "pulses", label: "Pulses & Legumes (BNF)" },
  { id: "oilseeds", label: "Oilseeds" },
  { id: "vegetables", label: "Vegetables" },
  { id: "roots_tubers", label: "Roots & Tubers" },
  { id: "fruits", label: "Fruits & Berries" },
  { id: "spices_aromatics", label: "Spices & Herbs" },
  { id: "industrial_fibre", label: "Industrial & Fibre" },
  { id: "forage_cover", label: "Forage & Cover" },
  { id: "medicinal_indigenous", label: "Medicinal & Regional" },
];

export default function RotationLab({
  lat,
  lon,
  baselineRainfall,
  climateData,
}: RotationLabProps) {
  const [subTab, setSubTab] = useState<"recommendations" | "custom" | "explorer">("recommendations");

  const [profile, setProfile] = useState<FarmerProfile>({
    area_acres: 2.5,
    soil_type: "alluvial",
    soil_ph: 7.2,
    organic_carbon_pct: 0.55,
    irrigation: "assured_tubewell",
    current_rotation: "rice_wheat",
    priority: "water_conservation",
  });

  const [evaluation, setEvaluation] = useState<RotationEvaluationResponse | null>(null);
  const [allCrops, setAllCrops] = useState<Record<string, CropInfo>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Phase 6 Development Features State
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [showCompareModal, setShowCompareModal] = useState<boolean>(false);
  const [showReportModal, setShowReportModal] = useState<boolean>(false);
  const [expandedExplanationId, setExpandedExplanationId] = useState<string | null>(null);

  // Custom Rotation Builder State
  const [customKharif, setCustomKharif] = useState<string>("rice");
  const [customRabi, setCustomRabi] = useState<string>("chickpea");
  const [customZaid, setCustomZaid] = useState<string>("green_gram");
  const [useZaid, setUseZaid] = useState<boolean>(false);
  const [customEval, setCustomEval] = useState<CustomRotationEvaluationResponse | null>(null);
  const [customLoading, setCustomLoading] = useState<boolean>(false);
  const [customError, setCustomError] = useState<string | null>(null);

  // Crop Explorer State
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedSeason, setSelectedSeason] = useState<string>("all");
  const [selectedFamily, setSelectedFamily] = useState<string>("all");
  const [selectedZone, setSelectedZone] = useState<string>("all");
  const [cropDetailPage, setCropDetailPage] = useState<number>(1);
  const [selectedCropModal, setSelectedCropModal] = useState<CropInfo | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");

  const runEvaluation = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: FarmerProfile = {
        ...profile,
        lat,
        lon,
        climate_summary: climateData || undefined,
      };
      const res = await fetchRotationEvaluation(payload);
      setEvaluation(res);
      if (res.crops && Object.keys(res.crops).length > 0) {
        setAllCrops(res.crops);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to evaluate rotation strategies");
    } finally {
      setLoading(false);
    }
  };

  const loadAllCrops = async () => {
    try {
      const crops = await fetchCrops();
      setAllCrops(crops);
    } catch (e) {
      console.error("Failed to fetch full crops list:", e);
    }
  };

  const runCustomEvaluation = async () => {
    setCustomLoading(true);
    setCustomError(null);
    try {
      const cropIds = [customKharif, customRabi];
      if (useZaid && customZaid && customZaid !== "none") {
        cropIds.push(customZaid);
      }
      const payload: FarmerProfile = {
        ...profile,
        lat,
        lon,
        climate_summary: climateData || undefined,
      };
      const res = await fetchCustomRotationEvaluation(cropIds, payload);
      setCustomEval(res);
    } catch (err: any) {
      setCustomError(err?.message || "Custom rotation evaluation failed");
    } finally {
      setCustomLoading(false);
    }
  };

  useEffect(() => {
    runEvaluation();
  }, [profile.priority, profile.irrigation, profile.soil_type, lat, lon, climateData]);

  useEffect(() => {
    loadAllCrops();
  }, []);

  const toggleCompare = (stratId: string) => {
    setSelectedForCompare((prev) => {
      if (prev.includes(stratId)) {
        return prev.filter((id) => id !== stratId);
      }
      if (prev.length >= 3) {
        return [...prev.slice(1), stratId];
      }
      return [...prev, stratId];
    });
  };

  // Available Families and Zones
  const availableFamilies = Array.from(
    new Set(Object.values(allCrops).map((c) => c.crop_family).filter(Boolean))
  ).sort();

  const availableZones = [
    "temperate", "subtropical", "tropical", "arid_semiarid", "mediterranean", "continental", "boreal", "highland"
  ];

  // Filter crops for Explorer
  const filteredCrops = Object.values(allCrops).filter((c) => {
    if (selectedCategory !== "all") {
      const matchPrimary = c.primary_category === selectedCategory;
      const matchCat = c.categories.includes(selectedCategory);
      const matchAlias =
        (selectedCategory === "cereals_millets" && (c.categories.includes("cereal") || c.categories.includes("millet"))) ||
        (selectedCategory === "pulses" && (c.categories.includes("pulse") || c.categories.includes("legume"))) ||
        (selectedCategory === "oilseeds" && c.categories.includes("oilseed")) ||
        (selectedCategory === "vegetables" && c.categories.includes("vegetable")) ||
        (selectedCategory === "roots_tubers" && (c.categories.includes("root_tuber") || c.categories.includes("root_crop"))) ||
        (selectedCategory === "fruits" && c.categories.includes("fruit")) ||
        (selectedCategory === "spices_aromatics" && (c.categories.includes("spice") || c.categories.includes("aromatic"))) ||
        (selectedCategory === "industrial_fibre" && (c.categories.includes("commercial") || c.categories.includes("industrial") || c.categories.includes("fibre") || c.categories.includes("fiber"))) ||
        (selectedCategory === "forage_cover" && (c.categories.includes("forage") || c.categories.includes("cover_crop"))) ||
        (selectedCategory === "medicinal_indigenous" && (c.categories.includes("medicinal") || c.categories.includes("traditional")));
      if (!matchPrimary && !matchCat && !matchAlias) return false;
    }
    if (selectedFamily !== "all" && c.crop_family !== selectedFamily) {
      return false;
    }
    if (selectedSeason !== "all" && c.season !== selectedSeason && !c.season.includes(selectedSeason) && c.season !== "all_season") {
      return false;
    }
    if (selectedZone !== "all") {
      const zones = c.climatic_zones || [];
      if (!zones.some((z) => z.toLowerCase().includes(selectedZone.toLowerCase()))) {
        return false;
      }
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = c.id.toLowerCase().includes(q);
      const matchName = c.name.toLowerCase().includes(q);
      const matchSci = c.scientific_name.toLowerCase().includes(q);
      const matchFam = c.crop_family.toLowerCase().includes(q);
      const matchSyn = c.synonyms?.some((s) => s.toLowerCase().includes(q));
      if (!matchId && !matchName && !matchSci && !matchFam && !matchSyn) return false;
    }
    return true;
  });

  const PAGE_SIZE = 24;
  const totalCropPages = Math.ceil(filteredCrops.length / PAGE_SIZE) || 1;
  const paginatedCrops = filteredCrops.slice((cropDetailPage - 1) * PAGE_SIZE, cropDetailPage * PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* Farmer Profile Editor Card */}
      <div className="bg-white rounded-lg border border-[#e5dfd3] p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[#f0ebe0] pb-3 mb-4">
          <div>
            <h3 className="text-base font-bold text-[#1b4332] flex items-center gap-2">
              <span>🌾</span> Field Profile & Farmer Priorities
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Specify your farm conditions. VASUNDHARA computes multi-criteria trade-offs dynamically tailored to your goals.
            </p>
            <div className="mt-2 inline-flex items-center gap-2 px-2.5 py-1 bg-[#e8f5e9] border border-[#a5d6a7] rounded text-[11px] text-[#1b4332]">
              <span className="font-bold">🛰️ NASA Climate Grounding:</span>
              <span>Active at {lat.toFixed(4)}°N, {lon.toFixed(4)}°E</span>
              {baselineRainfall != null && (
                <span className="text-[#2e7d32]">| Baseline Rainfall: {Math.round(baselineRainfall)} mm</span>
              )}
              {climateData?.march_temperature?.t2m_max != null && (
                <span className={climateData.march_temperature.t2m_max > 32 ? "text-amber-700 font-semibold" : "text-[#2e7d32]"}>
                  | March Tmax: {climateData.march_temperature.t2m_max.toFixed(1)}°C
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] bg-[#d8f3dc] text-[#1b4332] px-2.5 py-1 rounded font-semibold uppercase tracking-wider">
              {profile.priority.replace("_", " ")}
            </span>
            <button
              onClick={() => setShowReportModal(true)}
              className="bg-[#1b4332] hover:bg-[#2d6a4f] text-white text-xs font-semibold px-3 py-1.5 rounded transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
            >
              <span>📄</span> Export Summary Report
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Farm Priority */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Farmer Priority:
            </label>
            <select
              value={profile.priority}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  priority: e.target.value as any,
                })
              }
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-[#faf9f5] font-medium text-gray-800 focus:ring-1 focus:ring-[#2d6a4f]"
            >
              <option value="water_conservation">Water Conservation (Dryland Priority)</option>
              <option value="soil_improvement">Soil Health & Nitrogen Building</option>
              <option value="income_stability">Income & Market Price Stability</option>
              <option value="balanced">Balanced Multi-Objective</option>
            </select>
            <span className="text-[10px] text-gray-400">Shifts weights across the 5 evaluation dimensions</span>
          </div>

          {/* Soil Type */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Soil Texture:
            </label>
            <select
              value={profile.soil_type}
              onChange={(e) => setProfile({ ...profile, soil_type: e.target.value })}
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-[#faf9f5] font-medium text-gray-800"
            >
              <option value="alluvial">Alluvial (Indo-Gangetic / Riverine Plains)</option>
              <option value="black_cotton">Black Cotton / Regur (Deccan / Central India Vertisol)</option>
              <option value="red_laterite">Red / Laterite (Peninsular / Southern / Plateau Soils)</option>
              <option value="clay_loam">Clay Loam (Heavy Lowland / Deltaic Basin)</option>
              <option value="sandy_loam">Sandy Loam (Light Upland / Semi-Arid)</option>
              <option value="silt_loam">Silt Loam (Riverine Floodplain)</option>
            </select>
            <span className="text-[10px] text-gray-400">Tests crop drainage and rooting adaptability</span>
          </div>

          {/* Irrigation Availability */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Irrigation Infrastructure:
            </label>
            <select
              value={profile.irrigation}
              onChange={(e) => setProfile({ ...profile, irrigation: e.target.value })}
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-[#faf9f5] font-medium text-gray-800"
            >
              <option value="assured_tubewell">Assured Tubewell (Electric / Diesel Borewell)</option>
              <option value="assured_canal">Assured Canal Command</option>
              <option value="partial">Partial / Supplemental (1-2 critical irrigations)</option>
              <option value="rainfed">Entirely Rainfed / Residual Moisture</option>
            </select>
            <span className="text-[10px] text-gray-400">Directly affects dry-season feasibility</span>
          </div>

          {/* Soil pH & Organic Carbon (Optional) */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Soil pH & Organic Carbon (Optional):
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                step="0.1"
                min="4"
                max="10"
                value={profile.soil_ph !== null ? profile.soil_ph : ""}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    soil_ph: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                placeholder="pH (opt)"
                className="w-1/2 text-xs px-2 py-1.5 border border-gray-300 rounded bg-[#faf9f5]"
              />
              <input
                type="number"
                step="0.05"
                min="0.1"
                max="5"
                value={profile.organic_carbon_pct !== null ? profile.organic_carbon_pct : ""}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    organic_carbon_pct: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                placeholder="OC % (opt)"
                className="w-1/2 text-xs px-2 py-1.5 border border-gray-300 rounded bg-[#faf9f5]"
              />
            </div>
            <span className="text-[10px] text-gray-400">Soil health card values (if tested)</span>
          </div>
        </div>

        {/* Target Context */}
        <div className="mt-4 pt-3 border-t border-[#f0ebe0] flex flex-wrap items-center justify-between text-xs text-gray-600 gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span>Agro-Climatic Zone: <strong className="text-[#1b4332]">{evaluation?.detected_region?.name || "Global Agro-Climatic Zone"}</strong></span>
            <span className="text-gray-400">•</span>
            <span>Target Location: <strong className="text-[#1b4332]">{lat >= 0 ? `${lat.toFixed(4)}°N` : `${Math.abs(lat).toFixed(4)}°S`}, {lon >= 0 ? `${lon.toFixed(4)}°E` : `${Math.abs(lon).toFixed(4)}°W`}</strong></span>
          </div>
          <button
            onClick={runEvaluation}
            className="bg-[#2d6a4f] hover:bg-[#1b4332] text-white text-xs font-semibold px-3 py-1.5 rounded transition-colors shadow-xs cursor-pointer"
          >
            Re-evaluate Pathways
          </button>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex border-b border-[#e5dfd3] bg-white rounded-t-lg px-3 pt-2 gap-2 text-xs font-semibold">
        <button
          onClick={() => setSubTab("recommendations")}
          className={`px-4 py-2.5 border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
            subTab === "recommendations"
              ? "border-[#2d6a4f] text-[#2d6a4f] bg-[#f8f6f0] rounded-t font-bold"
              : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          <span>🎯</span> Recommended Pathways
        </button>
        <button
          onClick={() => setSubTab("custom")}
          className={`px-4 py-2.5 border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
            subTab === "custom"
              ? "border-[#2d6a4f] text-[#2d6a4f] bg-[#f8f6f0] rounded-t font-bold"
              : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          <span>🧪</span> Custom Rotation Builder
        </button>
        <button
          onClick={() => setSubTab("explorer")}
          className={`px-4 py-2.5 border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
            subTab === "explorer"
              ? "border-[#2d6a4f] text-[#2d6a4f] bg-[#f8f6f0] rounded-t font-bold"
              : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          <span>📚</span> Global Crop Explorer ({Object.keys(allCrops).length || 1232})
        </button>
      </div>

      {/* SUB-TAB 1: DYNAMIC RECOMMENDATIONS */}
      {subTab === "recommendations" && (
        <>
          {/* Header Action Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[#faf9f5] p-3 rounded-lg border border-[#e5dfd3]">
            <div className="text-xs text-gray-700">
              Select any 2 or 3 strategies to compare them side by side across water, soil, duration, and economic trade-offs.
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={selectedForCompare.length < 2}
                onClick={() => setShowCompareModal(true)}
                className={`text-xs font-semibold px-3 py-1.5 rounded transition-all flex items-center gap-1.5 cursor-pointer ${
                  selectedForCompare.length >= 2
                    ? "bg-[#2d6a4f] hover:bg-[#1b4332] text-white shadow-xs"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }`}
              >
                <span>⚖️</span> Compare Selected ({selectedForCompare.length}/3)
              </button>
              {selectedForCompare.length > 0 && (
                <button
                  onClick={() => setSelectedForCompare([])}
                  className="text-xs text-gray-500 hover:text-gray-800 underline cursor-pointer"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {loading && (
            <div className="flex flex-col items-center justify-center py-16 bg-white rounded-lg shadow-xs border border-[#e5dfd3]">
              <div className="w-8 h-8 border-3 border-[#2d6a4f] border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-3 text-xs text-[#52796f] font-medium">Evaluating rotation agronomics & trade-offs across 53 crops...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r shadow-xs">
              <span className="text-xs text-red-700 font-medium">{error}</span>
            </div>
          )}

          {!loading && evaluation && (
            <>
              {/* Strategy Comparison Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {evaluation.rotations.map((strat: RotationStrategy, idx: number) => {
                  const isChecked = selectedForCompare.includes(strat.id);
                  const isExplaining = expandedExplanationId === strat.id;

                  return (
                    <div
                      key={strat.id}
                      className={`bg-white rounded-lg border shadow-xs flex flex-col justify-between overflow-hidden transition-all ${
                        idx === 0
                          ? "border-[#2d6a4f] ring-2 ring-[#2d6a4f]"
                          : isChecked
                          ? "border-[#52796f] ring-1 ring-[#52796f]"
                          : "border-[#e5dfd3]"
                      }`}
                    >
                      {/* Card Header */}
                      <div className="p-4 bg-[#faf9f5] border-b border-[#e5dfd3]">
                        <div className="flex justify-between items-start gap-2">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              {idx === 0 && (
                                <span className="text-[10px] font-bold uppercase tracking-wider text-[#1b4332] bg-[#d8f3dc] px-2 py-0.5 rounded border border-[#b7e4c7]">
                                  ★ Rank #1 for {profile.priority.replace("_", " ")}
                                </span>
                              )}
                              <label className="flex items-center gap-1.5 text-[11px] text-gray-600 cursor-pointer select-none">
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => toggleCompare(strat.id)}
                                  className="rounded border-gray-300 text-[#2d6a4f] focus:ring-[#2d6a4f]"
                                />
                                <span className="font-medium text-gray-700">Compare</span>
                              </label>
                            </div>
                            <h4 className="font-bold text-[#1b4332] text-sm">{strat.name}</h4>
                            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{strat.description}</p>
                          </div>
                          <div
                            className={`text-base font-bold px-2 py-1 rounded-md border font-mono ${getScoreColor(
                              strat.overall_score
                            )}`}
                          >
                            {strat.overall_score}
                            <span className="text-[9px] block font-normal text-center">Score</span>
                          </div>
                        </div>
                      </div>

                      {/* Card Body: Criteria breakdown & Visual Timeline */}
                      <div className="p-4 space-y-3 flex-1">
                        {/* Agronomic Specs Bar */}
                        <div className="grid grid-cols-3 gap-2 bg-[#f8f6f0] p-2 rounded text-center border border-[#e5dfd3]">
                          <div>
                            <div className="text-[9px] text-gray-500 uppercase font-semibold">Total Water</div>
                            <div className="text-xs font-bold text-[#1b4332] mt-0.5">{strat.water_demand_mm} mm</div>
                          </div>
                          <div>
                            <div className="text-[9px] text-gray-500 uppercase font-semibold">Duration & Turnaround</div>
                            <div className="text-xs font-bold text-sky-800 mt-0.5">
                              {strat.total_duration_days}d ({strat.turnaround_days ?? (365 - strat.total_duration_days)}d buf)
                            </div>
                          </div>
                          <div>
                            <div className="text-[9px] text-gray-500 uppercase font-semibold">N-Fixed</div>
                            <div className="text-xs font-bold text-emerald-800 mt-0.5">
                              {strat.nitrogen_fixed_kg_ha > 0 ? `+${strat.nitrogen_fixed_kg_ha} kg/ha` : "None"}
                            </div>
                          </div>
                        </div>

                        {/* Visual Crop Rotation Timeline (Gantt style) */}
                        <RotationTimelineBar strat={strat} />

                        {/* Warnings if any */}
                        {strat.warnings && strat.warnings.length > 0 && (
                          <div className="bg-amber-50 border border-amber-200 p-2 rounded text-[11px] text-amber-800">
                            <strong>⚠️ Agronomic Warnings:</strong>
                            <ul className="list-disc list-inside mt-0.5 space-y-0.5">
                              {strat.warnings.map((w, wi) => (
                                <li key={wi}>{w}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Individual Criteria Bars */}
                        <div className="space-y-1.5">
                          <div className="text-[11px] font-bold text-[#1b4332]">5-Criteria Breakdown:</div>
                          {[
                            { label: "Water Sustainability", key: "water_sustainability", color: "bg-blue-600" },
                            { label: "Soil Health & N-Fix", key: "soil_health", color: "bg-emerald-600" },
                            { label: "Duration & Calendar", key: "duration_fit", color: "bg-purple-600" },
                            { label: "Economic Stability", key: "economic_stability", color: "bg-amber-600" },
                            { label: "Climate Resilience", key: "climate_resilience", color: "bg-teal-600" },
                          ].map((crit) => {
                            const score = (strat.criteria_scores as any)[crit.key];
                            return (
                              <div key={crit.key} className="text-[10px]">
                                <div className="flex justify-between text-gray-600 mb-0.5">
                                  <span>{crit.label}</span>
                                  <span className="font-mono font-semibold">{score}/100</span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-1.5">
                                  <div
                                    className={`h-1.5 rounded-full ${crit.color}`}
                                    style={{ width: `${score}%` }}
                                  ></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {/* Transparent Ranking Inspector */}
                        <div className="pt-2 border-t border-gray-100">
                          <button
                            onClick={() => setExpandedExplanationId(isExplaining ? null : strat.id)}
                            className="text-[11px] text-[#2d6a4f] hover:text-[#1b4332] font-semibold flex items-center justify-between w-full py-1 cursor-pointer"
                          >
                            <span>🔍 Why is this ranked #{idx + 1}?</span>
                            <span>{isExplaining ? "▲" : "▼"}</span>
                          </button>

                          {isExplaining && (
                            <div className="mt-2 p-2.5 bg-[#faf9f5] rounded border border-[#e5dfd3] text-[11px] space-y-2">
                              <p className="text-gray-700 leading-relaxed font-medium">
                                {strat.rationale}
                              </p>
                              <div className="text-[10px] text-gray-600">
                                <strong>Weighted Multi-Objective Calculation:</strong>
                                <div className="mt-1 font-mono text-[9px] bg-white p-1.5 rounded border border-gray-200">
                                  Score = (Water × {Math.round((strat.weights_used?.water_sustainability || 0.2) * 100)}%) + (Soil × {Math.round((strat.weights_used?.soil_health || 0.2) * 100)}%) + (Duration × {Math.round((strat.weights_used?.duration_fit || 0.2) * 100)}%) + (Econ × {Math.round((strat.weights_used?.economic_stability || 0.2) * 100)}%) + (Climate × {Math.round((strat.weights_used?.climate_resilience || 0.2) * 100)}%) = <strong>{strat.overall_score}</strong>
                                </div>
                              </div>
                              <div className="text-[10px] text-gray-500">
                                Priority selected: <strong>{profile.priority.replace("_", " ")}</strong>. Regional adaptation: <strong>{strat.regional_suitability || "High"} in Bihar</strong>.
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Card Footer: Key Benefits */}
                      <div className="p-3 bg-[#faf9f5] border-t border-[#e5dfd3] text-[11px] text-gray-600">
                        <div className="font-semibold text-gray-700 mb-1">Key Agronomic Upside:</div>
                        <p className="text-gray-600 line-clamp-2">
                          {strat.benefits?.[0] || "Well-balanced crop diversification pathway."}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Comparative Water Demand Chart */}
              <div className="bg-white rounded-lg border border-[#e5dfd3] p-5 shadow-xs">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4 border-b border-[#f0ebe0] pb-3">
                  <div>
                    <h4 className="font-bold text-[#1b4332] text-sm">
                      Cumulative Water Demand vs. Baseline Monsoon Rainfall
                    </h4>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Compares total crop water requirement ($ET_c$) against average seasonal rainfall and irrigation threshold.
                    </p>
                  </div>
                  {baselineRainfall && (
                    <span className="text-xs text-[#1b4332] bg-[#d8f3dc] px-2.5 py-1 rounded font-semibold">
                      Rainfall Baseline: {Math.round(baselineRainfall)} mm
                    </span>
                  )}
                </div>

                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={evaluation.rotations.map((r) => ({
                        name: r.name.split("→")[0].trim().split(" ")[0] + " → " + (r.name.split("→")[1]?.trim().split(" ")[0] || ""),
                        water: r.water_demand_mm,
                        score: r.criteria_scores.water_sustainability,
                      }))}
                      margin={{ top: 10, right: 20, left: 0, bottom: 25 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" />
                      <YAxis tick={{ fontSize: 11 }} label={{ value: "Water (mm)", angle: -90, position: "insideLeft", fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e5dfd3", fontSize: 12 }}
                        formatter={(val: any) => [`${val} mm`, "Water Requirement"]}
                      />
                      <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                      <ReferenceLine y={700} stroke="#2d6a4f" strokeDasharray="3 3" label={{ value: "Semi-Arid Dryland (700mm)", fill: "#2d6a4f", fontSize: 10 }} />
                      <ReferenceLine y={1200} stroke="#b91c1c" strokeDasharray="3 3" label={{ value: "Mean Monsoon (1200mm)", fill: "#b91c1c", fontSize: 10 }} />
                      <Bar dataKey="water" name="Crop Water Demand (mm)" fill="#1b4332" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {/* SUB-TAB 2: CUSTOM ROTATION BUILDER */}
      {subTab === "custom" && (
        <div className="bg-white rounded-lg border border-[#e5dfd3] p-5 shadow-xs space-y-6">
          <div>
            <h3 className="text-base font-bold text-[#1b4332] flex items-center gap-2">
              <span>🧪</span> Custom Rotation Builder (Select from 53 Crops)
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Select any Kharif, Rabi, and optional Zaid crop sequence to evaluate its calendar duration fit,
              water requirement, biological nitrogen fixation, and multi-criteria score.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 bg-[#faf9f5] p-4 rounded-lg border border-[#e5dfd3]">
            {/* Kharif Crop */}
            <div>
              <label className="block text-xs font-bold text-emerald-900 mb-1">
                Kharif Crop (Monsoon: June – Oct):
              </label>
              <select
                value={customKharif}
                onChange={(e) => setCustomKharif(e.target.value)}
                className="w-full text-xs px-2.5 py-2 border border-gray-300 rounded bg-white text-gray-800"
              >
                {Object.values(allCrops)
                  .filter((c) => c.season.includes("kharif") || c.season === "annual" || c.season === "all_season")
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.crop_family}) - {c.typical_water_mm}mm
                    </option>
                  ))}
              </select>
              {allCrops[customKharif] && (
                <div className="mt-1.5 text-[10px] text-gray-500 space-y-0.5">
                  <div>Duration: <strong>{allCrops[customKharif].typical_duration} days</strong></div>
                  <div>Water: <strong>{allCrops[customKharif].typical_water_mm} mm</strong></div>
                  <div>Root: <strong>{allCrops[customKharif].root_type}</strong></div>
                </div>
              )}
            </div>

            {/* Rabi Crop */}
            <div>
              <label className="block text-xs font-bold text-amber-900 mb-1">
                Rabi Crop (Winter: Nov – March):
              </label>
              <select
                value={customRabi}
                onChange={(e) => setCustomRabi(e.target.value)}
                className="w-full text-xs px-2.5 py-2 border border-gray-300 rounded bg-white text-gray-800"
              >
                {Object.values(allCrops)
                  .filter((c) => c.season.includes("rabi") || c.season === "all_season")
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.crop_family}) - {c.typical_water_mm}mm
                    </option>
                  ))}
              </select>
              {allCrops[customRabi] && (
                <div className="mt-1.5 text-[10px] text-gray-500 space-y-0.5">
                  <div>Duration: <strong>{allCrops[customRabi].typical_duration} days</strong></div>
                  <div>Water: <strong>{allCrops[customRabi].typical_water_mm} mm</strong></div>
                  <div>N-Fix: <strong>{allCrops[customRabi].nitrogen_fixation_kg_ha ? `${allCrops[customRabi].nitrogen_fixation_kg_ha} kg/ha` : "None"}</strong></div>
                </div>
              )}
            </div>

            {/* Zaid Crop (Optional) */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-bold text-sky-900">
                  Zaid Crop (Summer: April – May):
                </label>
                <label className="flex items-center gap-1 text-[11px] text-gray-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useZaid}
                    onChange={(e) => setUseZaid(e.target.checked)}
                    className="rounded border-gray-300 text-[#2d6a4f]"
                  />
                  <span>Enable 3-Crop</span>
                </label>
              </div>

              <select
                disabled={!useZaid}
                value={customZaid}
                onChange={(e) => setCustomZaid(e.target.value)}
                className={`w-full text-xs px-2.5 py-2 border rounded ${
                  useZaid ? "bg-white text-gray-800 border-gray-300" : "bg-gray-100 text-gray-400 border-gray-200"
                }`}
              >
                {Object.values(allCrops)
                  .filter((c) => c.season.includes("zaid") || c.categories.includes("catch_crop") || c.season === "all_season")
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.crop_family}) - {c.typical_water_mm}mm
                    </option>
                  ))}
              </select>
              {useZaid && allCrops[customZaid] && (
                <div className="mt-1.5 text-[10px] text-gray-500 space-y-0.5">
                  <div>Duration: <strong>{allCrops[customZaid].typical_duration} days</strong></div>
                  <div>Water: <strong>{allCrops[customZaid].typical_water_mm} mm</strong></div>
                  <div>N-Fix: <strong>{allCrops[customZaid].nitrogen_fixation_kg_ha ? `${allCrops[customZaid].nitrogen_fixation_kg_ha} kg/ha` : "None"}</strong></div>
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={runCustomEvaluation}
              disabled={customLoading}
              className="bg-[#1b4332] hover:bg-[#2d6a4f] text-white text-xs font-bold px-5 py-2.5 rounded shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
            >
              {customLoading ? "Simulating Rotation..." : "Run Scientific Rotation Evaluation"}
            </button>
          </div>

          {customError && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r text-xs text-red-700">
              {customError}
            </div>
          )}

          {customEval && (
            <div className="mt-6 border border-[#2d6a4f] rounded-lg p-5 bg-[#faf9f5] space-y-4 shadow-xs">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[#e5dfd3] pb-3">
                <div>
                  <span className="text-[10px] uppercase font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">
                    Custom Sequence Evaluation
                  </span>
                  <h4 className="text-base font-bold text-[#1b4332] mt-1">{customEval.evaluation.name}</h4>
                </div>
                <div className={`text-xl font-bold px-3 py-1 rounded border font-mono ${getScoreColor(customEval.evaluation.overall_score)}`}>
                  {customEval.evaluation.overall_score} / 100
                </div>
              </div>

              {/* Agronomic Summary Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white p-3 rounded border border-[#e5dfd3] text-center text-xs">
                <div>
                  <div className="text-gray-400 font-semibold uppercase text-[10px]">Total Water</div>
                  <div className="font-bold text-[#1b4332] mt-0.5">{customEval.evaluation.water_demand_mm} mm</div>
                </div>
                <div>
                  <div className="text-gray-400 font-semibold uppercase text-[10px]">Total Duration</div>
                  <div className="font-bold text-sky-800 mt-0.5">{customEval.evaluation.total_duration_days} days</div>
                </div>
                <div>
                  <div className="text-gray-400 font-semibold uppercase text-[10px]">Annual Turnaround</div>
                  <div className="font-bold text-purple-800 mt-0.5">{customEval.evaluation.turnaround_days} days buffer</div>
                </div>
                <div>
                  <div className="text-gray-400 font-semibold uppercase text-[10px]">Biological N-Fix</div>
                  <div className="font-bold text-emerald-800 mt-0.5">
                    {customEval.evaluation.nitrogen_fixed_kg_ha > 0 ? `+${customEval.evaluation.nitrogen_fixed_kg_ha} kg/ha` : "None"}
                  </div>
                </div>
              </div>

              {/* Visual Timeline for Custom Rotation */}
              <RotationTimelineBar strat={customEval.evaluation} />

              {/* Warnings if any */}
              {customEval.evaluation.warnings && customEval.evaluation.warnings.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 p-3 rounded text-xs text-amber-800 space-y-1">
                  <strong>⚠️ Agronomic Warnings & Constraints:</strong>
                  <ul className="list-disc list-inside space-y-0.5">
                    {customEval.evaluation.warnings.map((w, wi) => (
                      <li key={wi}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Criteria Progress Bars */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-gray-800">5-Criteria Score Breakdown:</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Object.entries(customEval.evaluation.criteria_scores).map(([k, score]) => (
                    <div key={k} className="bg-white p-2.5 rounded border border-gray-200 text-xs">
                      <div className="flex justify-between font-semibold text-gray-700 capitalize">
                        <span>{k.replace("_", " ")}</span>
                        <span>{score}/100</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2 mt-1.5">
                        <div
                          className="bg-[#2d6a4f] h-2 rounded-full transition-all"
                          style={{ width: `${score}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 3: GLOBAL CROP EXPLORER */}
      {subTab === "explorer" && (
        <div className="bg-white rounded-lg border border-[#e5dfd3] p-5 shadow-xs space-y-5">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <h3 className="text-base font-bold text-[#1b4332] flex items-center gap-2">
                <span>📚</span> Global Crop Database ({filteredCrops.length} of {Object.keys(allCrops).length || 1232} Crops)
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Scientific agronomic compendium across 10 global categories, 56 botanical families, and 205 biological nitrogen-fixing species.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
              <input
                type="text"
                placeholder="Search by crop name, scientific name, or family..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCropDetailPage(1);
                }}
                className="text-xs px-3 py-1.5 border border-gray-300 rounded bg-[#faf9f5] w-full sm:w-64"
              />
              <select
                value={selectedFamily}
                onChange={(e) => {
                  setSelectedFamily(e.target.value);
                  setCropDetailPage(1);
                }}
                className="text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-[#faf9f5]"
              >
                <option value="all">All Families ({availableFamilies.length})</option>
                {availableFamilies.map((fam) => (
                  <option key={fam} value={fam}>{fam}</option>
                ))}
              </select>
              <select
                value={selectedZone}
                onChange={(e) => {
                  setSelectedZone(e.target.value);
                  setCropDetailPage(1);
                }}
                className="text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-[#faf9f5]"
              >
                <option value="all">All Climates</option>
                {availableZones.map((z) => (
                  <option key={z} value={z}>{z.replace("_", " ").toUpperCase()}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Category & Season Filter Pills */}
          <div className="space-y-2">
            <div className="flex gap-1.5 flex-wrap">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => {
                    setSelectedCategory(cat.id);
                    setCropDetailPage(1);
                  }}
                  className={`text-xs px-3 py-1 rounded-full transition-all cursor-pointer ${
                    selectedCategory === cat.id
                      ? "bg-[#1b4332] text-white font-semibold shadow-xs"
                      : "bg-[#f8f6f0] text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1.5 text-xs text-gray-500 flex-wrap">
              <span className="font-semibold text-gray-700">Season:</span>
              {[
                { id: "all", label: "All Seasons" },
                { id: "kharif", label: "Kharif (Monsoon)" },
                { id: "rabi", label: "Rabi (Winter)" },
                { id: "zaid", label: "Zaid (Summer)" },
                { id: "annual", label: "Annual / Perennial" },
              ].map((s) => (
                <button
                  key={s.id}
                  onClick={() => {
                    setSelectedSeason(s.id);
                    setCropDetailPage(1);
                  }}
                  className={`px-2 py-0.5 rounded text-[11px] transition-all cursor-pointer ${
                    selectedSeason === s.id
                      ? "bg-[#2d6a4f] text-white font-bold"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Crops Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paginatedCrops.map((crop) => (
              <div
                key={crop.id}
                onClick={() => setSelectedCropModal(crop)}
                className="border border-[#e5dfd3] rounded-lg p-4 bg-[#ffffff] hover:border-[#2d6a4f] hover:shadow-md transition-all flex flex-col justify-between cursor-pointer"
              >
                <div>
                  <div className="flex justify-between items-start gap-2">
                    <div>
                      <h4 className="font-bold text-[#1b4332] text-sm hover:underline">{crop.name}</h4>
                      <div className="text-[11px] text-gray-500 italic">{crop.scientific_name}</div>
                    </div>
                    <span className="text-[10px] font-mono bg-[#f0ebe0] text-gray-700 px-2 py-0.5 rounded">
                      {crop.crop_family}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                    {crop.categories.map((cat) => (
                      <span
                        key={cat}
                        className="text-[9px] bg-emerald-50 text-emerald-800 px-1.5 py-0.5 rounded border border-emerald-200 uppercase font-medium"
                      >
                        {cat}
                      </span>
                    ))}
                    <span className="text-[9px] bg-sky-50 text-sky-800 px-1.5 py-0.5 rounded border border-sky-200 uppercase font-medium">
                      {crop.season}
                    </span>
                  </div>

                  {/* Key Stats */}
                  <div className="grid grid-cols-3 gap-1.5 mt-3 bg-[#faf9f5] p-2 rounded text-center text-[10px] border border-[#e5dfd3]">
                    <div>
                      <div className="text-gray-400 font-semibold">Duration</div>
                      <div className="font-bold text-gray-800 mt-0.5">{crop.typical_duration} d</div>
                    </div>
                    <div>
                      <div className="text-gray-400 font-semibold">Water Need</div>
                      <div className="font-bold text-blue-800 mt-0.5">{crop.typical_water_mm} mm</div>
                    </div>
                    <div>
                      <div className="text-gray-400 font-semibold">N-Fixation</div>
                      <div className="font-bold text-emerald-800 mt-0.5">
                        {crop.nitrogen_fixation_kg_ha && crop.nitrogen_fixation_kg_ha > 0
                          ? `${crop.nitrogen_fixation_kg_ha} kg/ha`
                          : "N/A"}
                      </div>
                    </div>
                  </div>

                  <div className="mt-2 space-y-1 text-[11px] text-gray-600">
                    <div>
                      <strong>Root:</strong> {crop.root_type} ({crop.root_depth_range_cm?.[0]}–{crop.root_depth_range_cm?.[1]} cm)
                    </div>
                    <div>
                      <strong>Tolerances:</strong> Drought: {crop.drought_tolerance}/5 • Waterlog: {crop.waterlogging_tolerance}/5
                    </div>
                    <div>
                      <strong>Suitability:</strong>{" "}
                      <span className="font-semibold uppercase text-emerald-700">
                        {crop.regional_suitability?.global || crop.regional_suitability?.bihar || "High"}
                      </span>
                    </div>
                  </div>

                  {/* Limitations */}
                  {crop.limitations && crop.limitations.length > 0 && (
                    <div className="mt-2 text-[10px] text-gray-500 bg-amber-50 p-1.5 rounded border border-amber-100">
                      <strong>Agronomic Caveat:</strong> {crop.limitations[0]}
                    </div>
                  )}
                </div>

                <div className="mt-3 pt-2 border-t border-gray-100 flex justify-between text-[9px] text-gray-400">
                  <span>Source: {crop.data_source?.split(" ")[0]} ({crop.source_year})</span>
                  <span>Confidence: <strong className="text-emerald-700 uppercase">{crop.data_confidence}</strong></span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-[#e5dfd3] text-xs text-gray-600">
            <div>
              Showing <span className="font-semibold text-gray-900">{paginatedCrops.length}</span> of{" "}
              <span className="font-semibold text-gray-900">{filteredCrops.length}</span> crops (Page {cropDetailPage} of {totalCropPages})
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCropDetailPage((p) => Math.max(1, p - 1))}
                disabled={cropDetailPage === 1}
                className="px-3 py-1 border rounded bg-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-100 font-medium"
              >
                Previous
              </button>
              <span className="px-2 font-mono font-semibold text-[#1b4332]">{cropDetailPage} / {totalCropPages}</span>
              <button
                onClick={() => setCropDetailPage((p) => Math.min(totalCropPages, p + 1))}
                disabled={cropDetailPage === totalCropPages}
                className="px-3 py-1 border rounded bg-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-100 font-medium"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Side-by-Side Comparison Modal */}
      {showCompareModal && evaluation && (
        <ComparisonModal
          selectedIds={selectedForCompare}
          rotations={evaluation.rotations}
          priority={profile.priority}
          onClose={() => setShowCompareModal(false)}
        />
      )}

      {/* Exportable Farmer Summary Report Modal */}
      {showReportModal && evaluation && (
        <FarmerReportModal
          profile={profile}
          rotations={evaluation.rotations}
          lat={lat}
          lon={lon}
          baselineRainfall={baselineRainfall}
          onClose={() => setShowReportModal(false)}
        />
      )}

      {/* Crop Detail Modal */}
      {selectedCropModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setSelectedCropModal(null)}
        >
          <div
            className="bg-white rounded-xl max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto shadow-2xl border border-gray-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start border-b pb-3">
              <div>
                <h3 className="text-xl font-bold text-[#1b4332]">{selectedCropModal.name}</h3>
                <p className="text-xs text-gray-500 italic">{selectedCropModal.scientific_name}</p>
              </div>
              <button
                onClick={() => setSelectedCropModal(null)}
                className="text-gray-400 hover:text-gray-600 text-lg font-bold px-2 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="bg-[#faf9f5] p-2.5 rounded border">
                <div className="text-gray-400 font-semibold uppercase text-[10px]">Family</div>
                <div className="font-bold text-gray-800">{selectedCropModal.crop_family}</div>
              </div>
              <div className="bg-[#faf9f5] p-2.5 rounded border">
                <div className="text-gray-400 font-semibold uppercase text-[10px]">Duration</div>
                <div className="font-bold text-gray-800">{selectedCropModal.typical_duration} days</div>
              </div>
              <div className="bg-[#faf9f5] p-2.5 rounded border">
                <div className="text-gray-400 font-semibold uppercase text-[10px]">Water Need</div>
                <div className="font-bold text-blue-800">{selectedCropModal.typical_water_mm} mm</div>
              </div>
              <div className="bg-[#faf9f5] p-2.5 rounded border">
                <div className="text-gray-400 font-semibold uppercase text-[10px]">N-Fixation</div>
                <div className="font-bold text-emerald-800">
                  {selectedCropModal.nitrogen_fixation_kg_ha && selectedCropModal.nitrogen_fixation_kg_ha > 0
                    ? `${selectedCropModal.nitrogen_fixation_kg_ha} kg N/ha`
                    : "None (Non-legume)"}
                </div>
              </div>
            </div>

            {selectedCropModal.synonyms && selectedCropModal.synonyms.length > 0 && (
              <div className="text-xs">
                <span className="font-semibold text-gray-700">Synonyms & Vernacular:</span>{" "}
                <span className="text-gray-600">{selectedCropModal.synonyms.join(", ")}</span>
              </div>
            )}

            <div className="text-xs space-y-2 border-t pt-3">
              <div>
                <strong>Root Architecture:</strong> {selectedCropModal.root_type} ({selectedCropModal.root_depth_range_cm?.[0]}–{selectedCropModal.root_depth_range_cm?.[1]} cm)
              </div>
              <div>
                <strong>Tolerances:</strong> Drought: {selectedCropModal.drought_tolerance}/5 • Waterlogging: {selectedCropModal.waterlogging_tolerance}/5 • Salinity: {selectedCropModal.salinity_tolerance || 2}/5
              </div>
              {selectedCropModal.suitable_preceding_crops && selectedCropModal.suitable_preceding_crops.length > 0 && (
                <div>
                  <strong>Suitable Preceding Crops:</strong> {selectedCropModal.suitable_preceding_crops.join(", ")}
                </div>
              )}
              {selectedCropModal.suitable_succeeding_crops && selectedCropModal.suitable_succeeding_crops.length > 0 && (
                <div>
                  <strong>Suitable Succeeding Crops:</strong> {selectedCropModal.suitable_succeeding_crops.join(", ")}
                </div>
              )}
              {selectedCropModal.rotation_restrictions && selectedCropModal.rotation_restrictions.length > 0 && (
                <div className="text-amber-800 bg-amber-50 p-2 rounded border border-amber-200">
                  <strong>Rotation Restriction:</strong> {selectedCropModal.rotation_restrictions.join("; ")}
                </div>
              )}
              {selectedCropModal.pest_disease_risks && selectedCropModal.pest_disease_risks.length > 0 && (
                <div className="text-rose-800 bg-rose-50 p-2 rounded border border-rose-200">
                  <strong>Key Pest & Disease Risks:</strong> {selectedCropModal.pest_disease_risks.join("; ")}
                </div>
              )}
              {selectedCropModal.limitations && selectedCropModal.limitations.length > 0 && (
                <div className="text-gray-700 bg-gray-50 p-2 rounded border">
                  <strong>Agronomic Notes:</strong> {selectedCropModal.limitations.join("; ")}
                </div>
              )}
            </div>

            <div className="border-t pt-3 flex justify-between items-center text-[11px] text-gray-500">
              <div>Source: {selectedCropModal.data_source} ({selectedCropModal.source_year})</div>
              <div>Confidence: <span className="font-bold uppercase text-emerald-700">{selectedCropModal.data_confidence}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Global Scientific Heuristic Notice */}
      <div className="bg-[#fefce8] border-l-4 border-amber-500 p-4 rounded-r shadow-xs text-xs text-amber-900">
        <strong>Important Agronomic Disclaimer:</strong> {evaluation?.disclaimer || DISCLAIMER_TEXT}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Component: Visual Crop Rotation Timeline (Gantt Chart style)
// -------------------------------------------------------------
function RotationTimelineBar({ strat }: { strat: RotationStrategy }) {
  const turnaround = strat.turnaround_days ?? Math.max(0, 365 - strat.total_duration_days);
  const isCompressed = turnaround < 25 && strat.total_duration_days > 240;

  return (
    <div className="bg-white p-2.5 rounded border border-[#e5dfd3] space-y-1.5">
      <div className="flex justify-between items-center text-[10px]">
        <span className="font-bold text-gray-700 flex items-center gap-1">
          <span>📅</span> Annual Rotation Timeline (June → May)
        </span>
        <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${
          isCompressed ? "bg-amber-100 text-amber-900 border border-amber-300" : "bg-emerald-50 text-emerald-800"
        }`}>
          {turnaround} days turnaround buffer
        </span>
      </div>

      {/* Visual Gantt Bar */}
      <div className="w-full bg-gray-100 h-6 rounded flex overflow-hidden border border-gray-200 text-[9px] font-bold text-white text-center leading-6">
        {/* Kharif Segment */}
        <div
          className="bg-[#2d6a4f] hover:bg-[#1b4332] transition-colors truncate px-1 cursor-help"
          style={{ width: strat.crops && strat.crops.length >= 3 ? "38%" : "48%" }}
          title={`Kharif: ${strat.kharif_crop || "Kharif Crop"}`}
        >
          {strat.kharif_crop?.split(" ")[0] || "Kharif"}
        </div>

        {/* Turnaround gap */}
        <div
          className="bg-gray-200 text-gray-500 text-[8px] flex items-center justify-center font-normal px-0.5"
          style={{ width: "8%" }}
          title={`Turnaround Window: ~${Math.round(turnaround / (strat.crops?.length || 2))} days`}
        >
          gap
        </div>

        {/* Rabi Segment */}
        <div
          className="bg-[#b45309] hover:bg-[#92400e] transition-colors truncate px-1 cursor-help"
          style={{ width: strat.crops && strat.crops.length >= 3 ? "34%" : "44%" }}
          title={`Rabi: ${strat.rabi_crop || "Rabi Crop"}`}
        >
          {strat.rabi_crop?.split(" ")[0] || "Rabi"}
        </div>

        {/* Optional Zaid Segment */}
        {strat.crops && strat.crops.length >= 3 && (
          <>
            <div
              className="bg-gray-200 text-gray-500 text-[8px] flex items-center justify-center font-normal px-0.5"
              style={{ width: "6%" }}
            >
              gap
            </div>
            <div
              className="bg-[#0284c7] hover:bg-[#0369a1] transition-colors truncate px-1 cursor-help"
              style={{ width: "14%" }}
              title={`Zaid / Summer Catch Crop: ${strat.zaid_crop || "Zaid Crop"}`}
            >
              {strat.zaid_crop?.split(" ")[0] || "Zaid"}
            </div>
          </>
        )}
      </div>

      {/* Month Labels */}
      <div className="flex justify-between text-[8px] text-gray-400 font-mono px-0.5">
        <span>Jun</span>
        <span>Aug</span>
        <span>Oct</span>
        <span>Dec</span>
        <span>Feb</span>
        <span>Apr</span>
        <span>May</span>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Component: Side-by-Side Comparison Modal
// -------------------------------------------------------------
function ComparisonModal({
  selectedIds,
  rotations,
  priority,
  onClose,
}: {
  selectedIds: string[];
  rotations: RotationStrategy[];
  priority: string;
  onClose: () => void;
}) {
  const selectedStrats = rotations.filter((r) => selectedIds.includes(r.id));

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-xs">
      <div className="bg-white rounded-xl shadow-2xl border border-gray-300 w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 bg-[#1b4332] text-white flex justify-between items-center">
          <div>
            <h3 className="text-base font-bold flex items-center gap-2">
              <span>⚖️</span> Side-by-Side Strategy Comparison
            </h3>
            <p className="text-xs text-[#d8f3dc]">
              Comparing {selectedStrats.length} candidate rotation pathways for {priority.replace("_", " ")} priority.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-[#2d6a4f] px-2.5 py-1 rounded text-sm font-bold cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Modal Body: Comparison Table */}
        <div className="p-5 overflow-y-auto space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {selectedStrats.map((strat, sIdx) => (
              <div
                key={strat.id}
                className="border border-[#e5dfd3] rounded-lg p-4 bg-[#faf9f5] flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex justify-between items-start">
                    <span className="text-[10px] font-bold uppercase text-[#1b4332] bg-[#d8f3dc] px-2 py-0.5 rounded">
                      Option {sIdx + 1}
                    </span>
                    <span className={`text-base font-bold font-mono px-2 py-0.5 rounded border ${getScoreColor(strat.overall_score)}`}>
                      {strat.overall_score}
                    </span>
                  </div>
                  <h4 className="font-bold text-sm text-[#1b4332] mt-1.5">{strat.name}</h4>
                  <p className="text-xs text-gray-500 mt-0.5">{strat.description}</p>
                </div>

                {/* Quantitative Metric Comparison */}
                <div className="space-y-2 bg-white p-3 rounded border border-gray-200 text-xs">
                  <div className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">Water Demand:</span>
                    <strong className="text-[#1b4332]">{strat.water_demand_mm} mm</strong>
                  </div>
                  <div className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">Duration:</span>
                    <strong className="text-sky-800">{strat.total_duration_days} days</strong>
                  </div>
                  <div className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">Turnaround Buffer:</span>
                    <strong className="text-purple-800">{strat.turnaround_days ?? (365 - strat.total_duration_days)} days</strong>
                  </div>
                  <div className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">Biological N-Fix:</span>
                    <strong className="text-emerald-800">
                      {strat.nitrogen_fixed_kg_ha > 0 ? `+${strat.nitrogen_fixed_kg_ha} kg/ha` : "None"}
                    </strong>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-gray-500">Regional Fit:</span>
                    <strong className="uppercase text-emerald-700">{strat.regional_suitability || "High"}</strong>
                  </div>
                </div>

                {/* 5-Criteria Ratings */}
                <div className="space-y-1 text-[11px]">
                  <div className="font-bold text-gray-700 mb-1">Sub-Scores:</div>
                  {[
                    { label: "Water", val: strat.criteria_scores.water_sustainability },
                    { label: "Soil Health", val: strat.criteria_scores.soil_health },
                    { label: "Duration Fit", val: strat.criteria_scores.duration_fit },
                    { label: "Economic", val: strat.criteria_scores.economic_stability },
                    { label: "Climate", val: strat.criteria_scores.climate_resilience },
                  ].map((c) => (
                    <div key={c.label} className="flex justify-between text-gray-600">
                      <span>{c.label}:</span>
                      <span className="font-mono font-bold">{c.val}</span>
                    </div>
                  ))}
                </div>

                {/* Benefits & Disadvantages */}
                <div className="text-[11px] space-y-1.5 pt-2 border-t border-gray-200">
                  <div>
                    <strong className="text-emerald-800">Key Upside:</strong>
                    <p className="text-gray-600 mt-0.5">{strat.benefits?.[0]}</p>
                  </div>
                  <div>
                    <strong className="text-amber-800">Primary Trade-off:</strong>
                    <p className="text-gray-600 mt-0.5">{strat.disadvantages?.[0]}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-gray-50 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="bg-[#1b4332] hover:bg-[#2d6a4f] text-white text-xs font-semibold px-4 py-2 rounded cursor-pointer"
          >
            Close Comparison
          </button>
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Component: Exportable Farmer Summary Report Modal
// -------------------------------------------------------------
function FarmerReportModal({
  profile,
  rotations,
  lat,
  lon,
  baselineRainfall,
  onClose,
}: {
  profile: FarmerProfile;
  rotations: RotationStrategy[];
  lat: number;
  lon: number;
  baselineRainfall?: number | null;
  onClose: () => void;
}) {
  const topRotations = rotations.slice(0, 3);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-xs">
      <div className="bg-white rounded-xl shadow-2xl border border-gray-300 w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Modal Header with Action */}
        <div className="p-4 bg-[#1b4332] text-white flex justify-between items-center print:hidden">
          <div>
            <h3 className="text-base font-bold flex items-center gap-2">
              <span>📄</span> Exportable Farmer Advisory Report
            </h3>
            <p className="text-xs text-[#d8f3dc]">Print or save as PDF for extension distribution and farmer consultation.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="bg-[#40916c] hover:bg-[#52b788] text-white text-xs font-bold px-3 py-1.5 rounded transition-all cursor-pointer flex items-center gap-1.5"
            >
              <span>🖨️</span> Print / Save PDF
            </button>
            <button
              onClick={onClose}
              className="text-white hover:bg-[#2d6a4f] px-2 py-1 rounded text-sm font-bold cursor-pointer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Printable Report Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-[#1c1915]" id="printable-farmer-report">
          {/* Official Advisory Header */}
          <div className="border-b-2 border-[#1b4332] pb-4 flex justify-between items-start">
            <div>
              <div className="text-xs font-bold text-[#2d6a4f] uppercase tracking-wider">
                VASUNDHARA • PRECISION AGRO-CLIMATIC INTELLIGENCE
              </div>
              <h2 className="text-xl font-bold text-[#1b4332] mt-0.5">
                Seasonal Crop Rotation Advisory Report
              </h2>
              <p className="text-xs text-gray-600 mt-1">
                Pilot Agro-Ecological Region: <strong>Bihar Alluvial Plains & Eastern Gangetic Basin</strong>
              </p>
            </div>
            <div className="text-right text-xs text-gray-500">
              <div>Date Generated: <strong>{new Date().toLocaleDateString("en-IN")}</strong></div>
              <div>Coordinates: <span className="font-mono text-gray-800">{lat.toFixed(4)}°N, {lon.toFixed(4)}°E</span></div>
            </div>
          </div>

          {/* Farm Profile Summary Box */}
          <div className="bg-[#faf9f5] border border-[#e5dfd3] rounded-lg p-4">
            <h4 className="text-xs font-bold text-[#1b4332] uppercase mb-2">1. Farm & Field Profile Parameters</h4>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
              <div>
                <span className="text-gray-500 block">Farm Area:</span>
                <strong>{profile.area_acres} Acres</strong>
              </div>
              <div>
                <span className="text-gray-500 block">Soil Texture:</span>
                <strong className="capitalize">{profile.soil_type.replace("_", " ")}</strong>
              </div>
              <div>
                <span className="text-gray-500 block">Irrigation Access:</span>
                <strong className="capitalize">{profile.irrigation.replace("_", " ")}</strong>
              </div>
              <div>
                <span className="text-gray-500 block">Farmer Goal:</span>
                <strong className="text-[#2d6a4f] uppercase font-bold">{profile.priority.replace("_", " ")}</strong>
              </div>
              <div>
                <span className="text-gray-500 block">Monsoon Baseline:</span>
                <strong>{baselineRainfall ? `${Math.round(baselineRainfall)} mm` : "1050 mm"}</strong>
              </div>
            </div>
          </div>

          {/* Top Recommended Pathways */}
          <div>
            <h4 className="text-xs font-bold text-[#1b4332] uppercase mb-2">2. Top Recommended Rotation Strategies</h4>
            <div className="space-y-3">
              {topRotations.map((strat, i) => (
                <div key={strat.id} className="border border-[#e5dfd3] rounded-lg p-3 bg-white space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[10px] font-bold text-white bg-[#1b4332] px-2 py-0.5 rounded mr-2">
                        Rank #{i + 1}
                      </span>
                      <strong className="text-sm text-[#1b4332]">{strat.name}</strong>
                    </div>
                    <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                      Overall: {strat.overall_score}/100
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-2 text-[11px] bg-[#f8f6f0] p-2 rounded text-center">
                    <div>
                      <span className="text-gray-500 block text-[9px]">Water Demand</span>
                      <strong>{strat.water_demand_mm} mm</strong>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-[9px]">Duration</span>
                      <strong>{strat.total_duration_days} days</strong>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-[9px]">Turnaround Buffer</span>
                      <strong>{strat.turnaround_days ?? (365 - strat.total_duration_days)} days</strong>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-[9px]">N-Fixed</span>
                      <strong>{strat.nitrogen_fixed_kg_ha > 0 ? `+${strat.nitrogen_fixed_kg_ha} kg/ha` : "None"}</strong>
                    </div>
                  </div>

                  <div className="text-[11px] text-gray-700 space-y-1">
                    <div><strong>Agronomic Benefit:</strong> {strat.benefits?.[0]}</div>
                    {strat.warnings && strat.warnings.length > 0 && (
                      <div className="text-amber-800">
                        <strong>Management Advisory:</strong> {strat.warnings[0]}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Agronomic Best Practices Checklist */}
          <div className="bg-[#f0f7f4] border border-[#b7e4c7] rounded-lg p-4 text-xs text-[#1b4332] space-y-2">
            <h4 className="font-bold uppercase text-[11px]">3. Key Management Recommendations for Eastern Gangetic Plains</h4>
            <ul className="list-disc list-inside space-y-1 text-gray-700">
              <li><strong>Zero-Tillage Relay:</strong> For post-rice Rabi pulses (chickpea/lentil), practice zero-tillage relay sowing (utera/para) into residual moisture to escape soil hardpan delays.</li>
              <li><strong>Terminal Heat Escape:</strong> Complete wheat sowing before November 20 to ensure grain filling finishes before late-February/March heatwaves (&gt; 32°C).</li>
              <li><strong>Rhizobial Inoculation:</strong> Inoculate all pulse seeds with appropriate Rhizobium and Phosphate Solubilizing Bacteria (PSB) strains to ensure active biological nodulation.</li>
              <li><strong>Groundwater Stewardship:</strong> Monitor tubewell extraction in intensive 3-crop vegetable rotations; adopt furrow or drip irrigation to conserve shallow aquifers.</li>
            </ul>
          </div>

          {/* Official Disclaimers */}
          <div className="text-[10px] text-gray-500 border-t border-gray-200 pt-3 leading-relaxed">
            <strong>Advisory Notice:</strong> VASUNDHARA recommendations are scientific heuristic estimates derived from regional ICAR/BAU agricultural compendia and NASA Earth-observation baselines. They provide comparative risk and trade-off analysis and do not guarantee market prices, government procurement, or yields. Consult your local district Krishi Vigyan Kendra (KVK) and block agricultural officer for soil testing and seed variety certification.
          </div>
        </div>
      </div>
    </div>
  );
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-emerald-800 bg-emerald-50 border-emerald-300";
  if (score >= 65) return "text-[#2d6a4f] bg-[#d8f3dc] border-[#b7e4c7]";
  if (score >= 50) return "text-amber-800 bg-amber-50 border-amber-300";
  return "text-rose-800 bg-rose-50 border-rose-300";
}

const DISCLAIMER_TEXT =
  "VASUNDHARA evaluations are heuristic agronomic models based on regional crop science parameters and historical climate observations worldwide. They provide comparative trade-off analysis and do not guarantee specific crop yields, market prices, or soil fertility outcomes. A crop being present in the database does not mean it is suitable for every region or farm. Local field testing and regional agricultural extension advice must always guide on-farm decisions.";
