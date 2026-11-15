# ROTATION IQ — COMPREHENSIVE TESTING & VERIFICATION SUITE

This document outlines the testing architecture, test coverage, and execution instructions for ROTATION IQ.

## 1. Test Architecture Overview

The automated test suite consists of **4 distinct test modules** totaling **51 test cases**:

```
tests/
├── test_analysis.py          # 9 Analytical Tests: Synthetic POWER/NDVI datasets, missing data handling, Mann-Kendall trends, MODIS quality masks
├── test_api.py               # 10 API Integration Tests: FastAPI endpoints, input validation, cache warming, production ASGI import via uvicorn
├── test_rotation.py          # 21 Unit Tests: 53 crops, 12 Fabaceae BNF, individual soil health formula components, dynamic wheat heat stress
└── test_e2e_integration.py   # 11 End-to-End Tests: Complete farmer journey, priority shifts, catalog filters, NASA/MODIS unavailability recovery
```

### Module Breakdown:
| Module | Tests | Test Scope & Nature |
| :--- | :---: | :--- |
| `tests/test_analysis.py` | 9 | **Synthetic Analytical Tests:** Evaluates Mann-Kendall trend tests, Sen's slopes, baseline departures, and MODIS sinusoidal pixel determinism using deterministic synthetic matrices. |
| `tests/test_api.py` | 10 | **API Integration Tests:** Verifies HTTP endpoints (`/api/health`, `/api/climate`, `/api/rotation/...`), coordinate/year bounds, and verifies production ASGI startup via `uvicorn.Config("backend.main:app")`. |
| `tests/test_rotation.py` | 21 | **Agronomic Unit Tests:** Verifies 53 crops catalog, 12 Fabaceae BNF, null non-legume BNF, sugarcane/perennial handling, all individual components of the soil health index, and dynamic wheat heat stress. |
| `tests/test_e2e_integration.py` | 11 | **Simulated Workflow & Failure Mode Tests:** Tests the complete multi-step farmer journey through mock HTTP requests, dynamic priority shifts, and server unavailability recovery (`available: False`). |

*Note: Automated tests execute using synthetic datasets and mock HTTP transports to ensure deterministic execution without live network flakiness.*

---

## 2. Running Automated Tests

### Backend Unit & Integration Tests (Python):
```bash
python -m unittest discover -s tests -v
```

### Expected Output:
```
Ran 51 tests in ~6.6s
OK
```

### Frontend TypeScript Verification & Production Build:
```bash
cd frontend
npm run build
```

### Expected Output:
```
vite v7.3.8 building client environment for production...
transforming...
✓ 452 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                            0.65 kB │ gzip:   0.33 kB
dist/assets/vendor-leaflet-CIGW-MKW.css   15.61 kB │ gzip:   6.46 kB
dist/assets/index-i3zvAIpk.css            27.67 kB │ gzip:   5.99 kB
dist/assets/vendor-leaflet-Bzw0dOc9.js   149.70 kB │ gzip:  43.36 kB
dist/assets/index-Bei3omWw.js            294.97 kB │ gzip:  84.07 kB
dist/assets/vendor-charts-DkEMDxJS.js    418.46 kB │ gzip: 114.94 kB
✓ built in 4.50s
```
