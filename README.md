# SIH26012 Geospatial Feature Review Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900.svg)](https://leafletjs.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

A lightweight, local-first Web-GIS review platform designed for automated topology validation, AI footprint discrepancy checking, and interactive human-in-the-loop review of village settlement geospatial datasets (Study AOI: Lalpur Village, Gujarat, LGD Code 511638).

---

## ⚠️ Important Scope & Provenance Declarations

1. **Building Footprints vs Cadastral Parcels**:
   The 317 vector footprints in this dataset represent **physical rooftop outlines**, not legal cadastral parcel boundaries.
2. **Zero Real Parcel Data**:
   The real parcel layer (`blank_parcel_template_4326.geojson`) contains **0 features**. No official cadastral parcel boundaries exist in this dataset. Parcel boundaries have **not** been inferred from rooflines or fabricated.
3. **Data Provenance**:
   The reference building footprints and road polygons originate from the Project Vaayu repository sample. The repository README describes the underlying data as Ministry-supplied SVAMITVA/hackathon material; this origin is reported from the repository README and is **not independently verified**. It is not official cadastral truth.
4. **AI vs Reference Discrepancy Checking**:
   Comparing model inference outputs against the 317 reference footprint layer is a **same-area spatial disagreement check** (IoU matching), **not temporal change detection**. There is no historical imagery or temporal baseline in this dataset.
5. **Road Centerlines & Corridors**:
   OpenStreetMap lines and road corridor polygons are map spatial references, not surveyed legal rights-of-way. Overlaps are flagged neutrally as *"spatial overlap—review visually"*, never as illegal encroachment.
6. **Synthetic Demo Fixtures**:
   Synthetic parcel and building polygons are included exclusively for automated tests and UI demonstration. They are explicitly badged as `Synthetic test data — not real parcels`.
7. **Scoring Model**:
   Review priority scores are calculated transparently via `backend/config/scoring_rules.json` and are explicitly labeled *"prototype heuristic—not a validated cadastral or survey-priority score"*.

---

## 🛰️ Architecture & Stack

- **Backend**: Python 3.10+ with FastAPI, Uvicorn, Pydantic v2.
- **Geospatial Processing**:
  - `shapely` (2.x): Topology analysis, OGC validation, polygon intersection.
  - `pyproj` (3.x): CRS projection between WGS 84 (`EPSG:4326`) and UTM Zone 43N (`EPSG:32643`) for metric calculations (m² / meters).
  - `rasterio` (1.5.x) & `PIL`: Dynamic local XYZ tile pyramid rendering from GeoTIFF orthomosaics.
- **Frontend**: Responsive 3-panel Web-GIS interface in Vanilla HTML5, CSS3 (Glassmorphism Dark Theme), and Leaflet.js 1.9.4. Zero heavyweight npm build dependencies.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14.
- Git.

### 2. Installation
Clone the repository and install dependencies in your virtual environment:

```bash
git clone https://github.com/vismayvikram/SIH.git
cd SIH

# Create virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Running Automated Tests
Run the comprehensive 48-test test suite:

```bash
python -m pytest tests/test_platform.py -v
```

### 4. Starting the Local Application Server
Launch the server (default port `8000`, customizable via the `PORT` environment variable):

```bash
python run_server.py
```

Then open your browser at:
👉 **`http://127.0.0.1:8000/`**

---

## 🗺️ GeoTIFF Orthomosaic Raster Serving

The platform includes a local tiled raster service (`backend/services/raster_service.py`) that reads the georeferenced orthomosaic and dynamically serves XYZ map tiles at `GET /api/tiles/{z}/{x}/{y}.png`:

- **Path**: `data/acquisition/SIH26012_INDIA_CANDIDATE_01/working/lalpur_orthomosaic.tif`
- **File Size**: ~1.57 GB (1,682,493,007 bytes)
- **CRS**: Projected `EPSG:3857` (WGS 84 / Pseudo-Mercator)
- **Dimensions**: 20,137 × 20,886 pixels (4 bands: RGBA, uint8)
- **Spatial Resolution**: ~3.38 cm GSD (Ground Sample Distance)
- **Bounds (EPSG:3857)**:
  - Left: `8098996.38`
  - Bottom: `2636558.41`
  - Right: `8099677.16`
  - Top: `2637264.51`
- **Map Integration**: Dynamic Leaflet `L.tileLayer('/api/tiles/{z}/{x}/{y}.png', { minZoom: 14, maxZoom: 21 })` with scale-aware rendering and graceful fallback to OpenStreetMap / Dark Neutral canvas if the GeoTIFF is not present.

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status |
| `GET` | `/api/metadata` | Study area metadata, raster status, and provenance disclaimer |
| `GET` | `/api/layers/{layer_name}` | GeoJSON layers (`buildings`, `roads`, `osm_roads`, `parcels`, `synthetic`, `drafts`, `ai_predictions`) |
| `GET` | `/api/tiles/{z}/{x}/{y}.png` | Dynamic 256×256 XYZ PNG tiles from GeoTIFF |
| `GET` | `/api/warnings` | Real-time topology warnings (metric overlaps, invalid geometry, corridor intersections) |
| `GET` | `/api/scores` | Heuristic review-priority scores (0–100) with rule breakdowns |
| `GET` | `/api/parcels/rag` | Red/Amber/Green parcel aggregation status (gated on non-empty parcels) |
| `GET` | `/api/models/discrepancy` | Model vs Reference Discrepancy Comparator (IoU spatial matching, TP/FP/FN counts) |
| `POST`| `/api/models/predict` | AI footprint inference mock provider with failure simulation |
| `GET` | `/api/models/benchmarks` | SpaceNet 2 and Inria benchmark datasets manifest (`PENDING_ACQUISITION`) |
| `GET` | `/api/export` | RFC 7946 WGS 84 GeoJSON bundle export with audit trail |
| `POST`| `/api/import` | GeoJSON bundle import and validation |

---

## 🛡️ Security & Git Tracking Guidelines

- All local raster GeoTIFF files (`*.tif`, `*.tiff`), raw ECW files (`*.ecw`), QGIS project files (`*.qgs`, `*.qgz`), model weights (`*.pt`, `*.onnx`), and working GeoJSON data are ignored in `.gitignore`.
- Removing tracked files from Git index does **not** erase them from past Git commit history. If this repository was previously public or pushed to a remote, past commits must be purged using tools like `git-filter-repo` or BFG Repo-Cleaner before making the repository public.
