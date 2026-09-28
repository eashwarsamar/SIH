# SIH26012 — Full Implementation Plan
## AI-Assisted Cadastral Review Platform

*Derived from the Comprehensive Project Blueprint. This plan covers every layer of the system: data ingestion, AI models, GIS engine, backend services, frontend, integration, testing, and deployment.*

---

## Table of Contents

1. [Implementation Overview](#1-implementation-overview)
2. [Tech Stack & Tooling Decisions](#2-tech-stack--tooling-decisions)
3. [Phase 0 — Data Contract & Environment Setup](#3-phase-0--data-contract--environment-setup)
4. [Phase 1 — Input & Preprocessing Pipeline](#4-phase-1--input--preprocessing-pipeline)
5. [Phase 2 — AI Model Integration](#5-phase-2--ai-model-integration)
6. [Phase 3 — Deterministic GIS Engine](#6-phase-3--deterministic-gis-engine)
7. [Phase 4 — Backend API & Service Layer](#7-phase-4--backend-api--service-layer)
8. [Phase 5 — Frontend Web-GIS Interface](#8-phase-5--frontend-web-gis-interface)
9. [Phase 6 — Human-Review Feedback Loop](#9-phase-6--human-review-feedback-loop)
10. [Phase 7 — Export & Audit](#10-phase-7--export--audit)
11. [Phase 8 — Stretch Features](#11-phase-8--stretch-features)
12. [Phase 9 — Testing, Demo Fallback & Polish](#12-phase-9--testing-demo-fallback--polish)
13. [Day-by-Day Execution Schedule](#13-day-by-day-execution-schedule)
14. [Team Allocation](#14-team-allocation)
15. [Risk Registry & Mitigations](#15-risk-registry--mitigations)
16. [Definition of Done](#16-definition-of-done)

---

## 1. Implementation Overview

### 1.1 Guiding Principle

> "We do not use AI where deterministic GIS is more reliable. AI extracts uncertain visual features; the GIS engine validates their spatial relationships; the human reviewer approves the cadastral result."

### 1.2 System Layers

```text
┌─────────────────────────────────────────────────┐
│                  FRONTEND                       │
│  React/TS + MapLibre GL JS + GeoJSON layers     │
├─────────────────────────────────────────────────┤
│                BACKEND API                      │
│  FastAPI (Python) — REST endpoints              │
├─────────────────────────────────────────────────┤
│            PROCESSING PIPELINE                  │
│  Preprocessing → AI Models → GIS Engine         │
├─────────────────────────────────────────────────┤
│              DATA & STORAGE                     │
│  File system / SQLite+SpatiaLite / GeoJSON      │
└─────────────────────────────────────────────────┘
```

### 1.3 Three Output Categories (enforced everywhere)

| Category | Source | Example |
|---|---|---|
| **Observed/detected features** | AI models | Buildings, roads, land-use regions |
| **Reference features** | Existing data | Parcel boundaries, OSM roads |
| **AI suggestions & warnings** | GIS engine + rules | Conflicts, topology errors, priority scores |

---

## 2. Tech Stack & Tooling Decisions

### 2.1 Backend & Pipeline

| Concern | Tool | Justification |
|---|---|---|
| Web framework | **FastAPI** (Python) | Async-ready, auto-docs, Pydantic validation |
| Raster I/O | **rasterio** + **GDAL** | Industry-standard GeoTIFF reading, reprojection, tiling |
| Vector processing | **GeoPandas** + **Shapely** (GEOS) | Polygonization, spatial joins, topology checks |
| CRS transforms | **pyproj** | Coordinate reference system conversions |
| AI inference | **PyTorch** + **torchvision** | Model loading and forward pass |
| Optional model hub | **TorchGeo** | Pretrained geospatial models, dataset utilities |
| Array ops | **numpy** | Mask manipulation, thresholding |
| Image processing | **scikit-image** / **OpenCV** | Morphological ops, connected components |
| Task queue (optional) | **Celery** + **Redis** or simple `asyncio` worker | Background processing jobs |
| Database (optional) | **SQLite + SpatiaLite** or flat GeoJSON | Feature storage, spatial queries |

### 2.2 Frontend

| Concern | Tool | Justification |
|---|---|---|
| Framework | **React 18** + **TypeScript** | Component model, strong typing |
| Bundler | **Vite** | Fast HMR, simple config |
| Map engine | **MapLibre GL JS** | Free, vector-tile-ready, WebGL-accelerated |
| GeoJSON editing | **maplibre-gl-draw** or **Turf.js** + custom | Polygon vertex editing |
| Styling | **CSS Modules** or vanilla CSS | No heavy framework needed |
| HTTP client | **fetch** / **axios** | API communication |

### 2.3 Data Formats

| Data | Format |
|---|---|
| Input imagery | GeoTIFF (one tested file) |
| Vector layers | GeoJSON (internal), Shapefile/GeoPackage accepted on ingest |
| AI model output | Binary mask → GeoJSON after polygonization |
| Warnings | JSON array |
| Export | GeoJSON + metadata JSON |

---

## 3. Phase 0 — Data Contract & Environment Setup

> **Timeline: Day 1**

### 3.1 Tasks

- [ ] **Select and freeze the study area** — one small urban neighbourhood or campus
- [ ] **Acquire the orthomosaic** — one GeoTIFF with known CRS, resolution, and bounds
- [ ] **Acquire or create the reference parcel layer** — GeoJSON/Shapefile for the same area
- [ ] **Acquire reference road layer** — OSM extract or manual digitization
- [ ] **Verify alignment in QGIS** — overlay all layers, confirm CRS match
- [ ] **Freeze the JSON schemas** — adopt the shared master feature schema from the blueprint

### 3.2 Deliverables

```text
data/
  study_area/
    orthomosaic.tif          # The one tested GeoTIFF
    parcels_reference.geojson
    roads_reference.geojson
    metadata.json            # CRS, bounds, resolution, acquisition date
  source_tracking.csv        # Dataset/model/license provenance log
```

### 3.3 Source Tracking File Format

| Field | Example |
|---|---|
| Asset name | `orthomosaic.tif` |
| Source URL | `https://...` |
| License | `CC-BY-4.0` |
| Attribution | `Survey of India` |
| Download date | `2026-09-28` |
| Purpose | `Study area imagery` |

### 3.4 Environment Setup

```bash
# Backend
python -m venv venv
pip install fastapi uvicorn rasterio geopandas shapely pyproj numpy torch torchvision scikit-image

# Frontend
npx -y create-vite@latest ./ --template react-ts
npm install maplibre-gl @turf/turf axios
```

### 3.5 Acceptance Criteria

- [ ] All layers open in QGIS and align visually
- [ ] `source_tracking.csv` has an entry for every asset
- [ ] Dev environments run on all team machines

---

## 4. Phase 1 — Input & Preprocessing Pipeline

> **Timeline: Day 2–3 (backend portion)**

### 4.1 Module: `pipeline/validate.py`

**Purpose:** Accept or reject uploaded files with clear error messages.

**Implementation Steps:**

1. Read GeoTIFF metadata via `rasterio.open()`:
   - Extract: `width`, `height`, `count` (bands), `crs`, `transform`, `bounds`, `res`, `nodata`
2. Validate:
   - CRS is present and supported (reject if missing)
   - Resolution is within acceptable range (e.g., 0.05–1.0 m/px for drone imagery)
   - Band count matches expected (3 for RGB, 4 for RGBN)
   - File size is within demo limits
3. For vector layers:
   - Read with GeoPandas
   - Verify CRS matches or can be reprojected
   - Verify geometry types are Polygon/MultiPolygon (parcels) or LineString (roads)

**Output:**

```python
@dataclass
class ValidationResult:
    valid: bool
    crs: str
    bounds: tuple
    resolution: tuple
    band_count: int
    errors: list[str]
    warnings: list[str]
```

### 4.2 Module: `pipeline/preprocess.py`

**Purpose:** Reproject, align, tile, and normalize the raster.

**Implementation Steps:**

1. **CRS normalization:** Reproject all inputs to one internal projected CRS (e.g., UTM zone of the study area, `EPSG:32643` for India)
2. **Vector normalization:** Convert all vector layers to the internal CRS using `gdf.to_crs()`
3. **Tiling:** Split the orthomosaic into model-sized tiles:
   ```python
   TILE_SIZE = 512  # pixels
   OVERLAP = 64     # pixels — prevents edge artifacts
   ```
   - Use `rasterio.windows.Window` to read tiles
   - Store the affine transform for each tile (pixel → world coordinate mapping)
4. **Normalization:** Scale pixel values to [0, 1] or model-expected range
5. **DSM/DTM (if present):** Resample to match orthomosaic grid, compute nDSM = DSM − DTM

**Output:**

```text
project/
  tiles/
    tile_0000.npy   # or .tif — normalized image array
    tile_0001.npy
    ...
  tile_index.json   # tile_id → {row, col, transform, bounds}
  preprocessed_parcels.geojson
  preprocessed_roads.geojson
```

### 4.3 Acceptance Criteria

- [ ] Unsupported files produce clear rejection messages
- [ ] Tiles reconstruct back to the original image extent
- [ ] All vector layers share the same CRS after normalization

---

## 5. Phase 2 — AI Model Integration

> **Timeline: Day 3–4**

### 5.1 Module: `pipeline/buildings.py` — Building Footprint Extraction

**This is the single mandatory AI model.**

#### Step 1: Model Selection & Loading

```python
# Option A: Pretrained TorchGeo model
from torchgeo.models import ...

# Option B: Custom UNet++ with pretrained weights
model = UNetPlusPlus(encoder_name="resnet34", in_channels=3, classes=1)
model.load_state_dict(torch.load("models/building_model_v1/weights.pt"))
model.eval()
```

**Decision tree:**
1. Try a pretrained building model from TorchGeo or a published checkpoint
2. If it fails on the study area imagery → fine-tune on SpaceNet/Inria data
3. If fine-tuning is impractical by deadline → prepare a fallback GeoJSON manually

#### Step 2: Tile-Level Inference

```python
def predict_buildings(tile: np.ndarray, model, threshold: float = 0.55) -> np.ndarray:
    """Run building segmentation on one tile. Returns binary mask."""
    tensor = preprocess_tile(tile)  # normalize, to_tensor
    with torch.no_grad():
        logits = model(tensor.unsqueeze(0))
    prob = torch.sigmoid(logits).squeeze().numpy()
    return (prob > threshold).astype(np.uint8)
```

#### Step 3: Merge Tile Predictions

- Stitch tile masks back into a full-extent raster
- Handle overlap regions by averaging or max-pooling probabilities
- Store the merged mask as a GeoTIFF with the correct transform

#### Step 4: Post-Processing (Mask → Polygons)

```python
from skimage import measure, morphology
from shapely.geometry import shape
from rasterio.features import shapes

def postprocess_building_mask(mask: np.ndarray, transform) -> gpd.GeoDataFrame:
    # 1. Remove small objects (< 25 px)
    mask = morphology.remove_small_objects(mask.astype(bool), min_size=25)
    # 2. Fill small holes
    mask = morphology.remove_small_holes(mask, area_threshold=15)
    # 3. Polygonize
    features = []
    for geom, value in shapes(mask.astype(np.uint8), transform=transform):
        if value == 1:
            poly = shape(geom).simplify(0.5)  # simplify to reduce vertices
            if poly.area > min_building_area:
                features.append(poly)
    # 4. Assign IDs and metadata
    gdf = gpd.GeoDataFrame({
        'building_id': [f'B-{i:04d}' for i in range(len(features))],
        'geometry': features,
        'feature_type': 'building',
        'confidence': 0.0,  # populated from probability map
        'source': 'ai_building_model',
        'review_status': 'unverified'
    }, crs=PROJECT_CRS)
    return gdf
```

### 5.2 Module: `pipeline/roads.py` — Road & Pathway Layer

**MVP approach: Reference-first, model-optional**

#### Priority 1: Load OSM/Reference Roads

```python
def load_reference_roads(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    gdf = gdf.to_crs(PROJECT_CRS)
    gdf['road_id'] = [f'R-{i:04d}' for i in range(len(gdf))]
    gdf['source'] = 'reference_osm'
    gdf['confidence'] = None
    gdf['review_status'] = 'unverified'
    return gdf
```

#### Priority 2 (if time permits): Road Segmentation Model

- Same UNet++ architecture as buildings, trained on SpaceNet road labels
- Post-processing: threshold → skeletonize → vectorize → connect segments
- Output: LineString geometries with confidence scores

### 5.3 Module: `pipeline/landuse.py` — Land-Use Classification

**MVP approach: Rule-based derivation from existing masks**

```python
def derive_landuse(building_mask, road_mask, vegetation_index=None):
    """Rule-based land-use from already-computed masks."""
    landuse = np.zeros_like(building_mask, dtype=np.uint8)
    landuse[building_mask == 1] = 1   # built-up
    landuse[road_mask == 1] = 2       # road
    if vegetation_index is not None:
        landuse[(vegetation_index > 0.3) & (landuse == 0)] = 3  # vegetation
    # Remaining pixels = bare/open land
    landuse[landuse == 0] = 5
    return landuse
```

**Classes:**

| Code | Class |
|---:|---|
| 0 | No data |
| 1 | Building/built-up |
| 2 | Road/path |
| 3 | Vegetation |
| 4 | Water |
| 5 | Bare/open land |

### 5.4 Fallback Strategy

For every AI component, prepare a pre-computed fallback result:

```text
fallback/
  buildings_fallback.geojson   # Manually verified or pre-run model output
  roads_fallback.geojson
  landuse_fallback.geojson
```

If model inference fails at demo time → serve the fallback GeoJSON from the same API endpoint.

### 5.5 Acceptance Criteria

- [ ] Building model runs on all tiles without crashing
- [ ] Output polygons are geographically aligned with the orthomosaic
- [ ] Confidence values are populated per building
- [ ] Fallback GeoJSONs exist and render correctly on the map

---

## 6. Phase 3 — Deterministic GIS Engine

> **Timeline: Day 5**

### 6.1 Module: `pipeline/polygonize.py`

Already covered in §5.1 Step 4. This module generalizes the mask-to-vector conversion for all model outputs.

### 6.2 Module: `pipeline/topology.py` — Topology Validation Engine

**Purpose:** Identify geometry errors and spatial conflicts. **No AI involved.**

#### Implementation

```python
from shapely.validation import make_valid, explain_validity

def run_topology_checks(
    parcels: gpd.GeoDataFrame,
    buildings: gpd.GeoDataFrame,
    roads: gpd.GeoDataFrame
) -> list[dict]:
    warnings = []

    # --- Geometry validity ---
    for idx, row in parcels.iterrows():
        if not row.geometry.is_valid:
            warnings.append({
                'warning_id': f'W-{len(warnings):04d}',
                'warning_type': 'invalid_geometry',
                'severity': 'high',
                'feature_ids': [row['parcel_id']],
                'explanation': f'{row["parcel_id"]}: {explain_validity(row.geometry)}',
                'status': 'open'
            })

    # --- Parcel overlaps ---
    for i, p1 in parcels.iterrows():
        for j, p2 in parcels.iterrows():
            if i >= j:
                continue
            if p1.geometry.overlaps(p2.geometry):
                overlap_area = p1.geometry.intersection(p2.geometry).area
                warnings.append({
                    'warning_id': f'W-{len(warnings):04d}',
                    'warning_type': 'parcel_overlap',
                    'severity': 'high',
                    'feature_ids': [p1['parcel_id'], p2['parcel_id']],
                    'explanation': f'{p1["parcel_id"]} overlaps {p2["parcel_id"]} by {overlap_area:.1f} sq m',
                    'status': 'open'
                })

    # --- Building crosses parcel boundary ---
    for _, bldg in buildings.iterrows():
        intersecting = parcels[parcels.geometry.intersects(bldg.geometry)]
        if len(intersecting) > 1:
            warnings.append({
                'warning_id': f'W-{len(warnings):04d}',
                'warning_type': 'building_crosses_parcel',
                'severity': 'high',
                'feature_ids': [bldg['building_id']] + intersecting['parcel_id'].tolist(),
                'explanation': f'{bldg["building_id"]} intersects {len(intersecting)} parcels',
                'status': 'open'
            })
        elif len(intersecting) == 0:
            warnings.append({
                'warning_id': f'W-{len(warnings):04d}',
                'warning_type': 'building_outside_parcels',
                'severity': 'medium',
                'feature_ids': [bldg['building_id']],
                'explanation': f'{bldg["building_id"]} lies outside all parcel boundaries',
                'status': 'open'
            })

    # --- Road intersects parcel unexpectedly ---
    for _, road in roads.iterrows():
        intersecting = parcels[parcels.geometry.intersects(road.geometry)]
        for _, parcel in intersecting.iterrows():
            if not parcel.geometry.touches(road.geometry):
                warnings.append({
                    'warning_id': f'W-{len(warnings):04d}',
                    'warning_type': 'road_intersects_parcel',
                    'severity': 'medium',
                    'feature_ids': [road['road_id'], parcel['parcel_id']],
                    'explanation': f'Road {road["road_id"]} cuts through {parcel["parcel_id"]}',
                    'status': 'open'
                })

    return warnings
```

### 6.3 Module: `pipeline/change_detection.py` — Deterministic Change Comparator

**Purpose:** Compare current building polygons with a prior-date layer (if available).

```python
def detect_changes(
    current_buildings: gpd.GeoDataFrame,
    prior_buildings: gpd.GeoDataFrame,
    area_change_threshold: float = 0.15
) -> list[dict]:
    changes = []

    # New buildings (in current but not in prior)
    for _, curr in current_buildings.iterrows():
        matches = prior_buildings[prior_buildings.geometry.intersects(curr.geometry)]
        best_iou = max(
            (curr.geometry.intersection(m.geometry).area /
             curr.geometry.union(m.geometry).area
             for _, m in matches.iterrows()),
            default=0
        )
        if best_iou < 0.3:
            changes.append({
                'type': 'new_construction',
                'feature_id': curr['building_id'],
                'geometry': curr.geometry
            })
        elif best_iou < 0.7:
            changes.append({
                'type': 'geometry_change',
                'feature_id': curr['building_id'],
                'geometry': curr.geometry
            })

    # Removed buildings (in prior but not in current)
    for _, prior in prior_buildings.iterrows():
        matches = current_buildings[current_buildings.geometry.intersects(prior.geometry)]
        best_iou = max(
            (prior.geometry.intersection(m.geometry).area /
             prior.geometry.union(m.geometry).area
             for _, m in matches.iterrows()),
            default=0
        )
        if best_iou < 0.3:
            changes.append({
                'type': 'possible_removal',
                'feature_id': prior.get('building_id', 'unknown'),
                'geometry': prior.geometry
            })

    return changes
```

### 6.4 Module: `pipeline/scoring.py` — Review-Priority Scoring

```python
def compute_review_scores(
    parcels: gpd.GeoDataFrame,
    warnings: list[dict],
    buildings: gpd.GeoDataFrame,
    change_indicators: list[dict] = None
) -> list[dict]:
    scores = []
    for _, parcel in parcels.iterrows():
        pid = parcel['parcel_id']
        score = 0
        reasons = []

        # Factor 1: Building-boundary conflict (30 pts)
        bldg_warnings = [w for w in warnings
                         if w['warning_type'] == 'building_crosses_parcel'
                         and pid in w['feature_ids']]
        if bldg_warnings:
            score += 30
            reasons.extend([w['explanation'] for w in bldg_warnings])

        # Factor 2: Geometry invalidity (20 pts)
        invalid_warnings = [w for w in warnings
                            if w['warning_type'] == 'invalid_geometry'
                            and pid in w['feature_ids']]
        if invalid_warnings:
            score += 20
            reasons.extend([w['explanation'] for w in invalid_warnings])

        # Factor 3: Parcel overlap or gap (15 pts)
        overlap_warnings = [w for w in warnings
                            if w['warning_type'] in ('parcel_overlap', 'parcel_gap')
                            and pid in w['feature_ids']]
        if overlap_warnings:
            score += 15
            reasons.extend([w['explanation'] for w in overlap_warnings])

        # Factor 4: Road intersection (10 pts)
        road_warnings = [w for w in warnings
                         if w['warning_type'] == 'road_intersects_parcel'
                         and pid in w['feature_ids']]
        if road_warnings:
            score += 10
            reasons.extend([w['explanation'] for w in road_warnings])

        # Factor 5: Low confidence detections (10 pts)
        parcel_buildings = buildings[buildings.geometry.intersects(parcel.geometry)]
        low_conf = parcel_buildings[parcel_buildings['confidence'] < 0.6]
        if len(low_conf) > 0:
            score += 10
            reasons.append(f'{len(low_conf)} building(s) with low confidence')

        # Factor 6: Recent building change (15 pts)
        if change_indicators:
            parcel_changes = [c for c in change_indicators
                              if parcel.geometry.intersects(c['geometry'])]
            if parcel_changes:
                score += 15
                reasons.append(f'{len(parcel_changes)} change(s) detected since prior survey')

        # Priority banding
        if score >= 60:
            priority = 'high'
        elif score >= 30:
            priority = 'medium'
        else:
            priority = 'low'

        scores.append({
            'parcel_id': pid,
            'review_score': score,
            'priority': priority,
            'reasons': reasons
        })

    return scores
```

### 6.5 Acceptance Criteria

- [ ] Deliberately injected test errors produce the correct warnings
- [ ] Scoring formula is transparent — every point can be traced to a reason
- [ ] Change comparator correctly flags added/removed buildings

---

## 7. Phase 4 — Backend API & Service Layer

> **Timeline: Day 3–4 (parallel with model work)**

### 7.1 Directory Structure

```text
backend/
  api/
    __init__.py
    projects.py       # Project CRUD, file upload
    processing.py     # Trigger and poll pipeline jobs
    features.py       # Query buildings/roads/parcels/warnings
    exports.py        # GeoJSON export
  pipeline/
    validate.py
    preprocess.py
    buildings.py
    roads.py
    landuse.py
    polygonize.py
    change_detection.py
    topology.py
    scoring.py
    orchestrator.py   # Runs the full pipeline end-to-end
  models/
    building_model_v1/
      weights.pt
      config.json
  main.py             # FastAPI app entry point
  config.py            # Project-wide constants
```

### 7.2 API Endpoints

#### Project Management

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/projects` | Create a new project (upload orthomosaic + reference layers) |
| `GET` | `/api/projects/{id}` | Get project metadata and status |
| `GET` | `/api/projects/{id}/status` | Poll processing status |

#### Processing

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/projects/{id}/process` | Trigger full pipeline processing |
| `POST` | `/api/projects/{id}/process/buildings` | Run building extraction only |
| `GET` | `/api/projects/{id}/process/status` | Get processing job status |

#### Features & Layers

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/projects/{id}/layers/buildings` | Building GeoJSON |
| `GET` | `/api/projects/{id}/layers/roads` | Road GeoJSON |
| `GET` | `/api/projects/{id}/layers/parcels` | Parcel GeoJSON |
| `GET` | `/api/projects/{id}/layers/landuse` | Land-use GeoJSON or raster tile URL |
| `GET` | `/api/projects/{id}/warnings` | Warnings JSON array |
| `GET` | `/api/projects/{id}/scores` | Review-priority scores |
| `GET` | `/api/projects/{id}/changes` | Change detection results |

#### Review & Edit

| Method | Endpoint | Purpose |
|---|---|---|
| `PUT` | `/api/projects/{id}/features/{feature_id}` | Update feature geometry/status |
| `POST` | `/api/projects/{id}/features/{feature_id}/approve` | Approve a feature |
| `POST` | `/api/projects/{id}/features/{feature_id}/reject` | Reject a feature |
| `POST` | `/api/projects/{id}/revalidate` | Re-run topology after edits |

#### Export

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/projects/{id}/export` | Export reviewed GeoJSON + metadata |

### 7.3 Pipeline Orchestrator

```python
# pipeline/orchestrator.py

async def run_full_pipeline(project_id: str, config: dict):
    """Execute the complete processing pipeline."""
    update_status(project_id, 'preprocessing')
    tiles, tile_index = preprocess(config['image_path'], config['tile_size'])

    update_status(project_id, 'extracting_buildings')
    building_mask = run_building_model(tiles, config['model_name'])
    buildings = postprocess_building_mask(building_mask, tile_index)
    save_geojson(buildings, f'projects/{project_id}/buildings.geojson')

    update_status(project_id, 'loading_roads')
    roads = load_reference_roads(config.get('roads_path'))
    save_geojson(roads, f'projects/{project_id}/roads.geojson')

    update_status(project_id, 'classifying_landuse')
    landuse = derive_landuse(building_mask, road_mask=None)
    save_landuse(landuse, f'projects/{project_id}/landuse.geojson')

    update_status(project_id, 'loading_parcels')
    parcels = load_and_normalize_parcels(config['parcels_path'])
    save_geojson(parcels, f'projects/{project_id}/parcels.geojson')

    update_status(project_id, 'detecting_changes')
    changes = []
    if config.get('prior_buildings_path'):
        prior = gpd.read_file(config['prior_buildings_path'])
        changes = detect_changes(buildings, prior)

    update_status(project_id, 'validating_topology')
    warnings = run_topology_checks(parcels, buildings, roads)
    save_json(warnings, f'projects/{project_id}/warnings.json')

    update_status(project_id, 'scoring')
    scores = compute_review_scores(parcels, warnings, buildings, changes)
    save_json(scores, f'projects/{project_id}/scores.json')

    update_status(project_id, 'complete')
```

### 7.4 Processing Status Flow

```text
queued → preprocessing → extracting_buildings → loading_roads →
classifying_landuse → loading_parcels → detecting_changes →
validating_topology → scoring → complete
```

### 7.5 Acceptance Criteria

- [ ] All endpoints return correct HTTP status codes
- [ ] The pipeline runs end-to-end without manual intervention
- [ ] Processing status updates are visible to the frontend
- [ ] Fallback GeoJSONs are served if model inference fails

---

## 8. Phase 5 — Frontend Web-GIS Interface

> **Timeline: Day 2–4 (skeleton + layers), Day 6 (editing)**

### 8.1 Layout

```text
┌──────────────┬──────────────────────────────┬──────────────┐
│  LEFT PANEL  │          MAIN MAP            │ RIGHT PANEL  │
│              │                              │              │
│ Project info │  Orthomosaic base layer       │ Feature      │
│ Layer toggles│  Parcel polygons             │ attributes   │
│ Feature count│  Building polygons           │ Confidence   │
│ Warning count│  Road lines                  │ Warnings     │
│ Warning list │  Warning highlights          │ Approve /    │
│ Export button│  Editing controls            │ Reject /     │
│              │                              │ Edit actions │
└──────────────┴──────────────────────────────┴──────────────┘
```

### 8.2 Component Tree

```text
<App>
  <Header />                    # Project name, status badge
  <MainLayout>
    <LeftPanel>
      <ProjectStatus />         # Processing stage indicator
      <LayerToggles />          # Checkboxes per layer
      <FeatureSummary />        # Building count, road count, parcel count
      <WarningList />           # Clickable warnings → zoom to feature
      <ExportButton />          # Download GeoJSON
    </LeftPanel>
    <MapView>
      <MapLibreMap />           # Core map with all layers
      <EditingToolbar />        # Draw, edit vertex, delete
    </MapView>
    <RightPanel>
      <FeatureInspector />      # Selected feature details
      <ConfidenceBadge />       # AI confidence visualization
      <WarningDetails />        # Relevant warnings for selection
      <ReviewActions />         # Approve, Reject, Save Correction
    </RightPanel>
  </MainLayout>
</App>
```

### 8.3 Map Layers

| Layer | Style | Interactivity |
|---|---|---|
| Orthomosaic | Raster tile layer | Pan/zoom |
| Parcels | Polygon fill with stroke; color by review score | Click to select, edit vertices |
| Buildings | Blue/orange polygon fill | Click to inspect |
| Roads | Line with dashed/solid style | Click to inspect |
| Warnings | Red highlight on affected features | Click to zoom + show detail |
| Land-use | Semi-transparent colored regions | Toggle on/off |
| NDVI/LST (optional) | Heatmap overlay | Toggle on/off |

### 8.4 Key Interactions

1. **Layer toggle** — show/hide any layer
2. **Click feature** — populate right panel with attributes
3. **Click warning** — zoom map to affected feature, highlight it
4. **Edit parcel** — drag vertices to correct geometry
5. **Approve/Reject** — update `review_status` via API
6. **Export** — download all reviewed features as GeoJSON

### 8.5 Acceptance Criteria

- [ ] Map loads with orthomosaic and at least 3 vector layers
- [ ] Clicking a building shows its ID, confidence, source, and review status
- [ ] Clicking a warning in the list zooms to the correct location
- [ ] Parcel editing works (move a vertex, save)
- [ ] Export produces a valid GeoJSON file

---

## 9. Phase 6 — Human-Review Feedback Loop

> **Timeline: Day 6**

### 9.1 Review Workflow

```text
User clicks feature
  → Right panel shows: AI geometry, confidence, source, warnings
  → User chooses: Approve | Edit | Reject | Needs Field Visit
  → If Edit: user modifies polygon vertices on map → Save
  → Backend stores: original geometry + corrected geometry + user + timestamp + reason
  → Backend re-runs topology checks on the edited feature
  → Warnings and scores update
  → Map re-renders with updated styling
```

### 9.2 Audit Trail Schema

```json
{
  "edit_id": "E-001",
  "feature_id": "P-014",
  "action": "geometry_edit",
  "original_geometry": { "type": "Polygon", "coordinates": [] },
  "corrected_geometry": { "type": "Polygon", "coordinates": [] },
  "edited_by": "reviewer_1",
  "edited_at": "2026-09-30T14:22:00Z",
  "reason": "Building footprint extends beyond parcel edge — corrected boundary",
  "verification_status": "reviewed"
}
```

### 9.3 Re-Validation After Edit

After any geometry edit:
1. Re-run `topology.py` checks on the affected parcel and its neighbors
2. Re-compute the review score for the affected parcel
3. Update warnings list
4. Push updated data to frontend

### 9.4 Acceptance Criteria

- [ ] Edit a parcel → save → re-run topology → warnings update
- [ ] Approve a feature → status changes to "approved"
- [ ] Original geometry is preserved alongside the correction
- [ ] Audit trail captures who edited what and when

---

## 10. Phase 7 — Export & Audit

> **Timeline: Day 6**

### 10.1 GeoJSON Export

```python
def export_project(project_id: str) -> dict:
    parcels = load_geojson(f'projects/{project_id}/parcels.geojson')
    buildings = load_geojson(f'projects/{project_id}/buildings.geojson')
    roads = load_geojson(f'projects/{project_id}/roads.geojson')
    warnings = load_json(f'projects/{project_id}/warnings.json')
    scores = load_json(f'projects/{project_id}/scores.json')

    metadata = {
        'project_id': project_id,
        'crs': 'EPSG:32643',
        'study_area': 'Demo neighbourhood',
        'processing_date': datetime.now().isoformat(),
        'disclaimer': 'Preliminary AI-assisted output. All parcel boundaries require surveyor verification.',
        'feature_counts': {
            'parcels': len(parcels['features']),
            'buildings': len(buildings['features']),
            'roads': len(roads['features']),
            'warnings': len(warnings)
        }
    }

    return {
        'parcels': parcels,
        'buildings': buildings,
        'roads': roads,
        'warnings': warnings,
        'metadata': metadata
    }
```

### 10.2 Acceptance Criteria

- [ ] Exported GeoJSON opens correctly in QGIS
- [ ] Metadata includes CRS, date, disclaimer, and feature counts
- [ ] Exported features include review status and edit history

---

## 11. Phase 8 — Stretch Features

> **Timeline: Day 7 — only if core is stable**

### 11.1 Conflict-Based Review Prioritization (UI)

- Color-code parcels on the map: **Red** (≥60), **Amber** (30–59), **Green** (<30)
- Add a "Review Queue" panel sorted by descending score
- Click an item in the queue → zoom to parcel + show reasons

### 11.2 Deterministic Change Comparator (Visualization)

- If a prior building layer is provided, show change indicators on the map:
  - 🟢 New construction
  - 🔴 Possible removal
  - 🟡 Geometry changed
- Feed change indicators into the review score

### 11.3 NDVI/LST Climate Layer (Optional)

- Compute NDVI from NIR and Red bands (or a proxy from RGB):
  ```
  NDVI = (NIR - Red) / (NIR + Red)
  ```
- Render as a toggleable heatmap overlay
- Label clearly: **"Optional urban-planning layer — not part of the cadastral review"**
- **Never** feed into topology warnings or review scores

### 11.4 Acceptance Criteria

- [ ] Stretch features do NOT break the core workflow
- [ ] Each stretch feature has its own toggle and can be disabled

---

## 12. Phase 9 — Testing, Demo Fallback & Polish

> **Timeline: Day 8 + post-exam days**

### 12.1 Feature Freeze (Day 8)

- No new features after this date
- Focus entirely on reliability, visual polish, and fallback preparation

### 12.2 Demo Fallback Preparation

```text
fallback/
  buildings_fallback.geojson
  roads_fallback.geojson
  landuse_fallback.geojson
  parcels_preloaded.geojson
  warnings_fallback.json
  scores_fallback.json
  screenshots/
  demo_recording.mp4
```

### 12.3 Testing Checklist

- [ ] Full pipeline runs from clean start on a new machine
- [ ] Fallback mode works when model fails
- [ ] Export produces valid GeoJSON
- [ ] All layers align geographically
- [ ] UI works on the presentation machine's browser
- [ ] Known limitations are documented

### 12.4 Contingency Plans

| Failure | Fallback |
|---|---|
| Model inference crashes | Serve pre-computed GeoJSON |
| Internet unavailable | All data and tiles served locally |
| Slow upload | Pre-loaded project, skip upload step |
| Browser rendering issues | Recorded demo video |
| Map tiles missing | Local tile server or static image |

### 12.5 Post-Exam Polish (Days 9–12)

- Fix defects found during recorded demo
- Improve labels, colors, and visual hierarchy
- Test on the presentation machine
- Recheck exports and map alignment
- Prepare the judging narrative

### 12.6 Rehearsal Day

- Run the full presentation 3 times
- Time the demo
- Prepare responses for likely judge questions

---

## 13. Day-by-Day Execution Schedule

| Day | Focus | Key Deliverable |
|---:|---|---|
| **1** | Data contract + environment | Study area frozen, all layers aligned in QGIS, dev envs ready |
| **2** | Frontend skeleton + backend scaffold | Map displays orthomosaic + reference layers, FastAPI running |
| **3** | Upload flow + preprocessing pipeline | File validation, tiling, CRS normalization working |
| **4** | AI model integration | Building model runs on tiles, output rendered on map |
| **5** | Topology engine + warnings | Conflict detection working, warnings displayed in UI |
| **6** | Editing + approval + export | Polygon editing, approve/reject, GeoJSON export |
| **7** | Stretch features | Review scoring UI, change detection, NDVI layer (if stable) |
| **8** | Feature freeze + fallback | Recorded demo, precomputed fallbacks, backup of everything |
| **9–12** | Post-exam polish | Defect fixes, visual polish, presentation machine testing |
| **13** | Rehearsal + contingency | 3 full run-throughs, fallback plans tested |
| **14** | Submission | Packaging only — no coding |

---

## 14. Team Allocation

| Member | Primary | Secondary |
|---|---|---|
| **Member 1** | Frontend: map, layers, editing, UI components | Demo design, presentation flow |
| **Member 2** | AI: model selection, inference, preprocessing, output generation | Model fallback, evaluation on study area |
| **Member 3** | Backend: API, topology engine, scoring, persistence, export | Data preparation, integration testing |

### Integration Points (daily sync required)

```text
Member 2 (AI output) → GeoJSON → Member 3 (backend ingests)
Member 3 (API endpoints) → JSON/GeoJSON → Member 1 (frontend consumes)
Member 1 (edit actions) → API calls → Member 3 (backend stores/revalidates)
```

---

## 15. Risk Registry & Mitigations

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| 1 | Pretrained model performs poorly on study area | High | Medium | Pre-compute fallback output; fine-tune on small dataset |
| 2 | CRS mismatch between layers | High | Medium | Validate in QGIS on Day 1; reject mismatched inputs |
| 3 | Model inference too slow for live demo | Medium | Medium | Pre-compute results; show cached output |
| 4 | Frontend editing library integration issues | Medium | Medium | Start simple (vertex drag only); test early |
| 5 | Internet unavailable at presentation | Medium | Low | All data/tiles served locally |
| 6 | Team member unavailable during exam period | High | Medium | Feature freeze on Day 8; no new work during exams |
| 7 | GeoJSON export misaligned | High | Low | End-to-end test: export → reopen in QGIS |
| 8 | Judge asks about apartment unit mapping | Low | High | Prepared response: "Top-down imagery cannot expose internal boundaries" |

---

## 16. Definition of Done

A clean demo run must demonstrate **all** of the following:

- [ ] 1. User selects or uploads the prepared orthomosaic
- [ ] 2. System confirms the image and reference layer are aligned
- [ ] 3. Map displays imagery, parcels, buildings, and roads
- [ ] 4. System shows feature counts and confidence values
- [ ] 5. At least one topology/cadastral conflict is deliberately demonstrated
- [ ] 6. User clicks a warning → map zooms to affected location
- [ ] 7. User edits or approves a parcel feature
- [ ] 8. System marks the feature as reviewed
- [ ] 9. User exports the reviewed layer as GeoJSON
- [ ] 10. UI clearly states boundaries are preliminary and require surveyor verification

> **Final framing for the presentation:**
> *"We do not use AI where deterministic GIS is more reliable. AI extracts uncertain visual features; the GIS engine validates their spatial relationships; the human reviewer approves the cadastral result."*
