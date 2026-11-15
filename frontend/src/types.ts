export type Meta = {
  name: string;
  source_url: string;
  resolution: string;
  period_start: string;
  period_end: string;
  n_obs: number;
  kind: "observed" | "modeled" | "assumed";
  retrieved_at: string;
};

export type PowerResponse = {
  available: boolean;
  name?: string;
  reason?: string;
  dates?: string[];
  columns?: Record<string, (number | null)[]>;
  cell?: { lat: number; lon: number; lat_size_deg: number; lon_size_deg: number };
  meta?: {
    overall: Meta;
    sources?: string[];
    modeled_vars: string[];
    non_null_counts: Record<string, number>;
  };
};

export type NdviResponse = {
  available: boolean;
  name?: string;
  reason?: string;
  dates?: string[];
  ndvi?: (number | null)[];
  reliability?: (number | null)[];
  meta?: Meta;
};

export type ProgressEvent = {
  step: string;
  message?: string;
  done?: number;
  total?: number;
};

export type AnnualClimateRow = {
  year: number;
  t2m_mean_c: number | null;
  t2m_complete: boolean;
  t2m_anomaly_c?: number | null;
  t2m_max_c: number | null;
  t2m_min_c: number | null;
  rainfall_mm: number | null;
  rainfall_complete: boolean;
  rainfall_anomaly_mm?: number | null;
  rh2m_mean_pct: number | null;
  solar_mean_mj: number | null;
  gwettop_mean: number | null;
  gwetroot_mean: number | null;
  expected_days: number;
  observed_days: number;
  missing_days: number;
  completeness: number;
};

export type MonthlyClimateRow = {
  year: number;
  month: number;
  t2m_mean_c: number | null;
  t2m_complete: boolean;
  rainfall_mm: number | null;
  rainfall_complete: boolean;
  t2m_anomaly_c?: number | null;
  rainfall_anomaly_mm?: number | null;
  missing_days: number;
};

export type SeasonRow = {
  year: number;
  season: "zaid" | "kharif" | "rabi";
  label: string;
  rainfall_mm: number | null;
  complete: boolean;
  expected_days: number;
  missing_days: number;
  rainfall_anomaly_mm?: number | null;
};

export type BaselineInfo = {
  start_year: number;
  end_year: number;
  kind: string;
  temperature_kind: string;
  rainfall_kind: string;
  temperature_years: number;
  rainfall_years: number;
  temperature_mean_c: number | null;
  rainfall_mean_mm: number | null;
  temperature_std_c: number | null;
  rainfall_std_mm: number | null;
  label: string;
  note: string;
};

export type ClimateAnalysisResponse = {
  available: boolean;
  name?: string;
  reason?: string;
  location?: { lat: number; lon: number; source: string };
  requested_period?: { start_year: number; end_year: number; start: string; end: string };
  baseline?: BaselineInfo;
  annual?: AnnualClimateRow[];
  monthly?: MonthlyClimateRow[];
  monthly_climatology?: {
    month: number;
    t2m_mean_c: number | null;
    rainfall_mm: number | null;
    n_years_temperature: number;
    n_years_rainfall: number;
  }[];
  seasons?: SeasonRow[];
  seasonal_period_means?: { season: string; label: string; mean_rainfall_mm?: number | null; rainfall_mm?: number | null; n_years?: number; n_seasons?: number }[];
  quality?: {
    product: string;
    source: string;
    source_url: string;
    observation_period: { start: string; end: string };
    spatial_resolution: string;
    temporal_resolution: string;
    variables: {
      id: string;
      label: string;
      units: string;
      kind: string;
      missing_days: number;
      observed_days: number;
      expected_days: number;
    }[];
  };
  notes?: string[];
};

export type TrendSeries = {
  id: string;
  label: string;
  method: string;
  method_label: string;
  accounts_for: string;
  n: number;
  omitted_years: number[];
  first_year: number | null;
  last_year: number | null;
  direction: "increasing" | "decreasing" | "no statistically significant trend" | null;
  significant: boolean | null;
  p_value: number | null;
  z: number | null;
  tau: number | null;
  slope: number | null;
  slope_units: string;
  fit?: { year: number; value: number }[];
  limitations: string;
  error?: string | null;
};

export type TrendAnalysisResponse = {
  available: boolean;
  name?: string;
  reason?: string;
  location?: { lat: number; lon: number; source: string };
  requested_period?: { start_year: number; end_year: number };
  alpha?: number;
  disclaimer?: string;
  series?: TrendSeries[];
  limitations?: string[];
  quality?: {
    product: string;
    source: string;
    source_url: string;
    observation_period: { start: string; end: string };
    spatial_resolution: string;
    temporal_resolution: string;
    kind: string;
  };
};

export type VegetationSeasonRow = {
  year: number;
  season: "zaid" | "kharif" | "rabi";
  label: string;
  mean: number | null;
  min: number | null;
  max: number | null;
  n_obs: number;
  n_missing: number;
};

export type VegetationAnalysisResponse = {
  available: boolean;
  is_fallback?: boolean;
  fallback_notice?: string;
  name?: string;
  reason?: string;
  location?: { lat: number; lon: number; source: string };
  requested_period?: { start_year: number; end_year: number };
  interpretation?: string;
  spatial_resolution?: string;
  temporal_resolution?: string;
  quality_filter?: string;
  series?: { date: string; ndvi: number | null; reliability: number | null }[];
  annual?: { year: number; mean: number | null; min: number | null; max: number | null; n_obs: number; n_missing: number }[];
  seasons?: VegetationSeasonRow[];
  seasonal_means?: { season: string; label: string; mean_ndvi: number | null; n_seasons: number }[];
  season_changes?: {
    from_season: string;
    from_year: number;
    to_season: string;
    to_year: number;
    from_label: string;
    to_label: string;
    delta: number | null;
  }[];
  latest?: { date: string; ndvi: number | null; note: string } | null;
  period_max?: { date: string; ndvi: number } | null;
  period_min?: { date: string; ndvi: number } | null;
  observation_count?: number;
  missing_count?: number;
  reliability_counts?: Record<string, number>;
  pixel?: { col: number; row: number; cellsize_m: number };
  quality?: {
    product: string;
    source: string;
    source_url: string;
    retrieved_at: string;
    observation_period: { start: string | null; end: string | null };
    units: string;
    spatial_resolution: string;
    temporal_resolution: string;
    missing_count: number;
    observation_count: number;
    kind: string;
  };
  limitations?: string[];
  notes?: string[];
};

export type CropInfo = {
  id: string;
  name: string;
  scientific_name: string;
  synonyms?: string[];
  categories: string[];
  primary_category?: string;
  crop_family: string;
  season: string;
  duration_range_days: [number, number];
  typical_duration: number;
  water_need_range_mm: [number, number];
  typical_water_mm: number;
  nitrogen_fixation_range_kg_ha: [number, number] | null;
  nitrogen_fixation_kg_ha: number | null;
  root_type: string;
  root_depth_range_cm: [number, number];
  soil_cover_rating: number;
  drought_tolerance: number;
  waterlogging_tolerance: number;
  salinity_tolerance?: number;
  market_stability: string;
  n_feeder: string;
  suitable_soils: string[];
  regional_suitability: Record<string, string>;
  climatic_zones?: string[];
  data_source: string;
  source_year: string;
  data_confidence: string;
  limitations: string[];
  pest_disease_risks?: string[];
  rotation_restrictions?: string[];
  suitable_preceding_crops?: string[];
  suitable_succeeding_crops?: string[];
};

export type FarmerProfile = {
  area_acres: number;
  soil_type: string;
  soil_ph: number | null;
  organic_carbon_pct: number | null;
  irrigation: string;
  current_rotation: string;
  priority: "water_conservation" | "soil_improvement" | "income_stability" | "balanced";
  source?: string;
  lat?: number | null;
  lon?: number | null;
  climate_summary?: any;
};

export type RotationStrategy = {
  id: string;
  name: string;
  description: string;
  crops?: string[];
  crop_ids?: string[];
  kharif_crop?: string | null;
  rabi_crop?: string | null;
  zaid_crop?: string | null;
  overall_score: number;
  criteria_scores: {
    water_sustainability: number;
    soil_health: number;
    duration_fit: number;
    economic_stability: number;
    climate_resilience: number;
  };
  weights_used: Record<string, number>;
  water_demand_mm: number;
  rabi_water_demand_mm: number;
  nitrogen_fixed_kg_ha: number;
  total_duration_days: number;
  turnaround_days?: number;
  regional_suitability?: string;
  warnings?: string[];
  benefits: string[];
  disadvantages: string[];
  assumptions: string[];
  rationale: string;
};

export type RotationEvaluationResponse = {
  farmer_profile: FarmerProfile;
  rotations: RotationStrategy[];
  crops: Record<string, CropInfo>;
  weights: Record<string, number>;
  disclaimer: string;
  detected_region?: { key: string; name: string };
};

export type CustomRotationEvaluationResponse = {
  farmer_profile: FarmerProfile;
  evaluation: RotationStrategy;
  weights: Record<string, number>;
  disclaimer: string;
};


