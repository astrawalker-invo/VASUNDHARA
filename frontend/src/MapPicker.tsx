import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Configure Leaflet marker icon without requiring direct png module imports
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const PAN_INDIA_LOCATIONS = [
  // Northern Plains & Hills
  { name: "Patna", lat: 25.5941, lon: 85.1376, desc: "Middle Gangetic Plain (Bihar)" },
  { name: "Gaya", lat: 24.7914, lon: 85.0002, desc: "South Bihar Semi-Arid Zone" },
  { name: "Muzaffarpur", lat: 26.1209, lon: 85.3647, desc: "North Bihar Alluvial Plains" },
  { name: "Purnia", lat: 25.7771, lon: 87.4753, desc: "Eastern Sub-Himalayan Alluvial" },
  { name: "Ludhiana", lat: 30.9010, lon: 75.8573, desc: "Trans-Gangetic Plains (Punjab)" },
  { name: "Karnal", lat: 29.6857, lon: 76.9905, desc: "Trans-Gangetic Plains (Haryana)" },
  { name: "Meerut", lat: 28.9845, lon: 77.7064, desc: "Upper Gangetic Plains (Western UP)" },
  { name: "Varanasi", lat: 25.3176, lon: 82.9739, desc: "Middle Gangetic Plains (Eastern UP)" },
  { name: "Lucknow", lat: 26.8467, lon: 80.9462, desc: "Central Alluvial Plains (UP)" },
  { name: "Gorakhpur", lat: 26.7606, lon: 83.3732, desc: "Terai-Adjacent Eastern UP" },
  { name: "Dehradun", lat: 30.3165, lon: 78.0322, desc: "Western Himalayan Valley" },
  // Southern Peninsula & Coastal
  { name: "Chennai", lat: 13.0827, lon: 80.2707, desc: "Southern Peninsular Coastal (Tamil Nadu)" },
  { name: "Coimbatore", lat: 11.0168, lon: 76.9558, desc: "Western Agro-Zone (Tamil Nadu)" },
  { name: "Thanjavur", lat: 10.7870, lon: 79.1378, desc: "Cauvery Delta Rice Bowl (Tamil Nadu)" },
  { name: "Madurai", lat: 9.9252, lon: 78.1198, desc: "Southern Dry Agro-Zone (Tamil Nadu)" },
  { name: "Bengaluru", lat: 12.9716, lon: 77.5946, desc: "Southern Dry Zone (Karnataka)" },
  { name: "Mysuru", lat: 12.2958, lon: 76.6394, desc: "Southern Transition Zone (Karnataka)" },
  { name: "Belagavi", lat: 15.8497, lon: 74.4977, desc: "Northern Transition Zone (Karnataka)" },
  { name: "Kochi", lat: 9.9312, lon: 76.2673, desc: "Humid Tropical Coastal (Kerala)" },
  // Deccan Plateau & East Coast
  { name: "Hyderabad", lat: 17.3850, lon: 78.4867, desc: "Southern Telangana Plateau" },
  { name: "Warangal", lat: 17.9689, lon: 79.5941, desc: "Central Telangana Red/Black Soils" },
  { name: "Vijayawada", lat: 16.5062, lon: 80.6480, desc: "Krishna-Godavari Alluvial Delta (AP)" },
  { name: "Guntur", lat: 16.3067, lon: 80.4365, desc: "Cotton & Chilli Vertisol Bowl (AP)" },
  { name: "Visakhapatnam", lat: 17.6868, lon: 83.2185, desc: "North Coastal Andhra" },
  { name: "Kurnool", lat: 15.8281, lon: 78.0373, desc: "Rayalaseema Semi-Arid (AP)" },
  // Western & Central India
  { name: "Mumbai", lat: 19.0760, lon: 72.8777, desc: "Konkan Coastal Agro-Zone (Maharashtra)" },
  { name: "Pune", lat: 18.5204, lon: 73.8567, desc: "Western Ghats Scarcity Zone (Maharashtra)" },
  { name: "Nagpur", lat: 21.1458, lon: 79.0882, desc: "Vidarbha Black Soil / Cotton-Soybean (MH)" },
  { name: "Nashik", lat: 19.9975, lon: 73.7898, desc: "North Maharashtra Transition / Horticulture" },
  { name: "Aurangabad", lat: 19.8762, lon: 75.3433, desc: "Marathwada Drought-Prone Vertisol (MH)" },
  { name: "Indore", lat: 22.7196, lon: 75.8577, desc: "Malwa Plateau Soybean-Wheat (MP)" },
  { name: "Bhopal", lat: 23.2599, lon: 77.4126, desc: "Central Plateau & Hill Region (MP)" },
  { name: "Jabalpur", lat: 23.1815, lon: 79.9864, desc: "Kymore Plateau & Satpura Hills (MP)" },
  { name: "Ahmedabad", lat: 23.0225, lon: 72.5714, desc: "North Gujarat Semi-Arid Zone" },
  { name: "Rajkot", lat: 22.3039, lon: 70.8022, desc: "Saurashtra Groundnut-Cotton Belt (Gujarat)" },
  { name: "Surat", lat: 21.1702, lon: 72.8311, desc: "South Gujarat Heavy Rainfall Coastal" },
  { name: "Jaipur", lat: 26.9124, lon: 75.7873, desc: "Semi-Arid Eastern Plain (Rajasthan)" },
  { name: "Jodhpur", lat: 26.2389, lon: 73.0243, desc: "Arid Western Agro-Zone (Rajasthan)" },
  // Eastern India & Northeast
  { name: "Kolkata", lat: 22.5726, lon: 88.3639, desc: "Lower Gangetic Plain Delta (West Bengal)" },
  { name: "Burdwan", lat: 23.2324, lon: 87.8615, desc: "Bengal Rice Bowl (West Bengal)" },
  { name: "Bhubaneswar", lat: 20.2961, lon: 85.8245, desc: "East Coast Plain (Odisha)" },
  { name: "Cuttack", lat: 20.4625, lon: 85.8828, desc: "Mahanadi Delta Rice Zone (Odisha)" },
  { name: "Raipur", lat: 21.2514, lon: 81.6296, desc: "Chhattisgarh Plains Rice Bowl" },
  { name: "Ranchi", lat: 23.3441, lon: 85.3096, desc: "Chota Nagpur Plateau (Jharkhand)" },
  { name: "Guwahati", lat: 26.1445, lon: 91.7362, desc: "Brahmaputra Valley (Assam)" },
];

const QUICK_JUMP_HUBS = [
  { name: "🇮🇳 New Delhi", lat: 28.6139, lon: 77.2090 },
  { name: "🇺🇸 Corn Belt (Iowa)", lat: 41.5868, lon: -93.6250 },
  { name: "🇧🇷 Cerrado (Brazil)", lat: -12.6819, lon: -56.9211 },
  { name: "🇫🇷 Paris Basin", lat: 48.8566, lon: 2.3522 },
  { name: "🇪🇸 Seville (Medit.)", lat: 37.3891, lon: -5.9845 },
  { name: "🇰🇪 Nakuru (Kenya)", lat: -0.3031, lon: 36.0800 },
  { name: "🇺🇦 Kyiv (Steppe)", lat: 50.4501, lon: 30.5234 },
  { name: "🇦🇺 Murray-Darling", lat: -35.1082, lon: 147.3598 },
  { name: "🇦🇷 Pampas (Argentina)", lat: -34.6037, lon: -58.3816 },
  { name: "🇪🇬 Cairo (Nile)", lat: 30.0444, lon: 31.2357 },
];

interface MapPickerProps {
  lat: number;
  lon: number;
  onLocationChange: (lat: number, lon: number) => void;
  startYear: number;
  endYear: number;
}

export default function MapPicker({
  lat,
  lon,
  onLocationChange,
  startYear,
  endYear,
}: MapPickerProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [clickNotice, setClickNotice] = useState<string | null>(null);
  const [searching, setSearching] = useState<boolean>(false);

  // Initialize Leaflet map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [lat, lon],
        zoom: 7,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map);

      const marker = L.marker([lat, lon]).addTo(map);
      marker
        .bindPopup(
          `<div style="font-size: 12px;"><b>Active Coordinate</b><br/>Lat: ${lat >= 0 ? lat.toFixed(4) + "°N" : Math.abs(lat).toFixed(4) + "°S"}<br/>Lon: ${lon >= 0 ? lon.toFixed(4) + "°E" : Math.abs(lon).toFixed(4) + "°W"}</div>`
        )
        .openPopup();

      map.on("click", (e: L.LeafletMouseEvent) => {
        const newLat = parseFloat(e.latlng.lat.toFixed(4));
        const newLon = parseFloat(e.latlng.lng.toFixed(4));
        onLocationChange(newLat, newLon);
        setClickNotice(`Map pin moved to ${newLat >= 0 ? newLat.toFixed(4) + "°N" : Math.abs(newLat).toFixed(4) + "°S"}, ${newLon >= 0 ? newLon.toFixed(4) + "°E" : Math.abs(newLon).toFixed(4) + "°W"}`);
        setTimeout(() => setClickNotice(null), 3500);
      });

      mapInstanceRef.current = map;
      markerRef.current = marker;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        markerRef.current = null;
      }
    };
  }, []);

  // Update map marker when lat/lon change from outside (presets or inputs)
  useEffect(() => {
    if (mapInstanceRef.current && markerRef.current) {
      markerRef.current.setLatLng([lat, lon]);
      mapInstanceRef.current.flyTo([lat, lon], Math.max(mapInstanceRef.current.getZoom(), 8), {
        duration: 1.2,
      });
      markerRef.current
        .setPopupContent(
          `<div style="font-size: 12px;"><b>Active Coordinate</b><br/>Lat: ${lat >= 0 ? lat.toFixed(4) + "°N" : Math.abs(lat).toFixed(4) + "°S"}<br/>Lon: ${lon >= 0 ? lon.toFixed(4) + "°E" : Math.abs(lon).toFixed(4) + "°W"}</div>`
        )
        .openPopup();
    }
  }, [lat, lon]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;

    // 1. Check if user entered "lat, lon" or "lat lon"
    const coordParts = query.split(/[\s,]+/);
    if (coordParts.length === 2) {
      const parsedLat = parseFloat(coordParts[0]);
      const parsedLon = parseFloat(coordParts[1]);
      if (
        !isNaN(parsedLat) &&
        !isNaN(parsedLon) &&
        parsedLat >= -90 &&
        parsedLat <= 90 &&
        parsedLon >= -180 &&
        parsedLon <= 180
      ) {
        onLocationChange(parsedLat, parsedLon);
        setClickNotice(`Coordinates: ${parsedLat}°N, ${parsedLon}°E`);
        setSearchQuery("");
        setTimeout(() => setClickNotice(null), 3500);
        return;
      }
    }

    // 2. Check pre-configured Pan-Indian agricultural locations
    const found = PAN_INDIA_LOCATIONS.find((loc) =>
      loc.name.toLowerCase().includes(query.toLowerCase())
    );
    if (found) {
      onLocationChange(found.lat, found.lon);
      setClickNotice(`Found: ${found.name} (${found.desc})`);
      setSearchQuery("");
      setTimeout(() => setClickNotice(null), 3500);
      return;
    }

    // 3. Fallback to OpenStreetMap Nominatim geocoding (covers any global district/city/town)
    setSearching(true);
    try {
      const geoUrl = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(
        query
      )}`;
      const res = await fetch(geoUrl, {
        headers: { "Accept-Language": "en" },
      });
      if (res.ok) {
        const data = await res.json();
        if (data && data.length > 0) {
          const newLat = parseFloat(parseFloat(data[0].lat).toFixed(4));
          const newLon = parseFloat(parseFloat(data[0].lon).toFixed(4));
          onLocationChange(newLat, newLon);
          const shortName = data[0].display_name.split(",").slice(0, 2).join(", ");
          setClickNotice(`Located: ${shortName}`);
          setSearchQuery("");
          setTimeout(() => setClickNotice(null), 3500);
          return;
        }
      }
      setClickNotice(`No location found for "${query}". Try city/region name or lat, lon.`);
      setTimeout(() => setClickNotice(null), 4000);
    } catch (err) {
      setClickNotice(`Search error. Please enter lat, lon directly.`);
      setTimeout(() => setClickNotice(null), 4000);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg border border-[#e5dfd3] shadow-xs space-y-3">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
        <div>
          <h3 className="font-bold text-[#1b4332] text-sm flex items-center gap-1.5">
            <span>🗺️</span> Global Farm Location Selector
          </h3>
          <p className="text-xs text-gray-500">
            Click anywhere on world map or search any city/region worldwide to move pin & refresh NASA Earth analytics
          </p>
        </div>

        {/* Search input */}
        <form onSubmit={handleSearch} className="flex items-center gap-1.5 w-full sm:w-auto">
          <input
            type="text"
            placeholder="Search any city, region or 'lat, lon'..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            disabled={searching}
            className="text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-[#faf9f5] w-full sm:w-64 focus:outline-[#2d6a4f]"
          />
          <button
            type="submit"
            disabled={searching}
            className="bg-[#2d6a4f] hover:bg-[#1b4332] text-white text-xs font-semibold px-3 py-1.5 rounded transition-colors whitespace-nowrap shadow-xs disabled:opacity-50"
          >
            {searching ? "Locating..." : "Locate"}
          </button>
        </form>
      </div>

      {/* Quick Location Pills */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[11px] font-semibold text-gray-500 uppercase">Global Hubs:</span>
        {QUICK_JUMP_HUBS.map((loc) => (
          <button
            key={loc.name}
            onClick={() => onLocationChange(loc.lat, loc.lon)}
            className={`text-[11px] px-2 py-0.5 rounded border transition-colors ${
              Math.abs(lat - loc.lat) < 0.01 && Math.abs(lon - loc.lon) < 0.01
                ? "bg-[#2d6a4f] text-white border-[#1b4332] font-semibold"
                : "bg-[#f8f6f0] text-[#2d6a4f] hover:bg-[#e9e4d9] border-[#d8d2c4]"
            }`}
          >
            {loc.name}
          </button>
        ))}
      </div>

      {/* Map Container */}
      <div className="relative w-full h-72 rounded-md overflow-hidden border border-[#d8d2c4]">
        <div ref={mapContainerRef} className="w-full h-full z-0" />
        {clickNotice && (
          <div className="absolute top-2 left-2 z-10 bg-[#1b4332] text-white text-xs px-3 py-1.5 rounded shadow-md border border-[#40916c] animate-fade-in">
            {clickNotice}
          </div>
        )}
      </div>

      {/* Coordinate & Period Status Bar */}
      <div className="flex flex-wrap justify-between items-center text-xs bg-[#f8f6f0] p-2.5 rounded border border-[#e5dfd3] gap-2">
        <div className="flex items-center gap-3">
          <span className="text-gray-600">
            Selected Point: <strong className="text-[#1b4332]">{lat.toFixed(4)}°N, {lon.toFixed(4)}°E</strong>
          </span>
          <span className="text-gray-400">|</span>
          <span className="text-gray-600">
            Active Period: <strong className="text-[#1b4332]">{startYear}–{endYear}</strong>
          </span>
        </div>
        <div className="text-gray-500 text-[11px]">
          Source: OpenStreetMap &bull; Single-cell query
        </div>
      </div>
    </div>
  );
}
