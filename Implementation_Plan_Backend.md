# SIH26012 — Backend & Pipeline Implementation Plan
## Everything Except the Frontend

*This plan covers: data ingestion, preprocessing, AI model integration, deterministic GIS engine, backend API, change detection, topology validation, review-priority scoring, export, and deployment. Frontend is excluded.*

---

## Table of Contents

1. [Scope & Architecture](#1-scope--architecture)
2. [Tech Stack](#2-tech-stack)
3. [Phase 0 — Data Contract & Environment](#3-phase-0--data-contract--environment)
4. [Phase 1 — Input Validation & Preprocessing](#4-phase-1--input-validation--preprocessing)
5. [Phase 2 — AI Model Integration](#5-phase-2--ai-model-integration)
6. [Phase 3 — Raster-to-Vector Polygonization](#6-phase-3--raster-to-vector-polygonization)
7. [Phase 4 — Deterministic GIS Engine](#7-phase-4--deterministic-gis-engine)
8. [Phase 5 — Change Detection (Deterministic)](#8-phase-5--change-detection-deterministic)
9. [Phase 6 — Review-Priority Scoring Engine](#9-phase-6--review-priority-scoring-engine)
10. [Phase 7 — Backend API Layer (FastAPI)](#10-phase-7--backend-api-layer-fastapi)
11. [Phase 8 — Pipeline Orchestrator](#11-phase-8--pipeline-orchestrator)
12. [Phase 9 — Export & Audit Trail](#12-phase-9--export--audit-trail)
13. [Phase 10 — Stretch: NDVI/LST Climate Layer](#13-phase-10--stretch-ndvilst-climate-layer)
14. [Phase 11 — Testing & Fallback](#14-phase-11--testing--fallback)
15. [Directory Structure](#15-directory-structure)
16. [API Contract Reference](#16-api-contract-reference)
17. [Data Flow Diagram](#17-data-flow-diagram)
18. [Day-by-Day Backend Schedule](#18-day-by-day-backend-schedule)
19. [Acceptance Criteria](#19-acceptance-criteria)

---

## 1. Scope & Architecture

### 1.1 What This Plan Covers

```text
✅ Data validation and metadata inspection
✅ CRS normalization and reprojection
✅ Raster tiling and normalization
✅ Building footprint extraction (AI model)
✅ Road layer loading (reference-first, model-optional)
✅ Land-use classification (rule-based)
✅ Mask-to-vector polygonization and post-processing
✅ Topology validation engine (Shapely/GEOS)
✅ Deterministic change detection (vector comparison)
✅ Review-priority scoring (weighted rules)
✅ FastAPI REST endpoints
✅ Pipeline orchestration and job status
✅ GeoJSON export with metadata
✅ Audit trail for human edits
✅ NDVI/LST computation (stretch)
✅ Fallback/precomputed outputs
```

### 1.2 What This Plan Does NOT Cover

```text
❌ React/TypeScript application
❌ MapLibre GL JS map rendering
❌ UI components (panels, toggles, buttons)
❌ Frontend polygon editing interactions
❌ Browser-side state management
❌ CSS/styling
```

### 1.3 Architecture Diagram

```text
┌────────────────────────────────────────────────────────┐
│                    BACKEND API (FastAPI)                │
│  /api/projects  /api/process  /api/layers  /api/export │
├────────────────────────────────────────────────────────┤
│               PIPELINE ORCHESTRATOR                    │
│  validate → preprocess → models → polygonize →         │
│  topology → change_detect → score → export             │
├────────────────────────────────────────────────────────┤
│            PROCESSING MODULES                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ validate │ │preprocess│ │ buildings│ │  roads   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ landuse  │ │polygonize│ │ topology │ │ scoring  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────────┐ ┌──────────┐                        │
│  │change_detect │ │  export  │                        │
│  └──────────────┘ └──────────┘                        │
├────────────────────────────────────────────────────────┤
│                   DATA LAYER                           │
│  File system: GeoTIFF, GeoJSON, JSON, .npy tiles      │
└────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

| Concern | Library/Tool | Version | Purpose |
|---|---|---|---|
| Web framework | FastAPI | latest | REST API, auto-docs, Pydantic models |
| ASGI server | uvicorn | latest | Run FastAPI |
| Raster I/O | rasterio | 1.3+ | GeoTIFF read/write, tiling, windowed reads |
| GDAL | GDAL | 3.x | Reprojection, raster format conversion |
| Vector processing | GeoPandas | 0.14+ | GeoDataFrame ops, spatial joins |
| Geometry engine | Shapely | 2.0+ | Topology checks, spatial predicates |
| CRS transforms | pyproj | 3.x | Coordinate system conversions |
| AI framework | PyTorch | 2.x | Model loading and inference |
| Image processing | scikit-image | latest | Morphological ops, connected components |
| Array ops | numpy | latest | Mask manipulation |
| Serialization | json / geojson | stdlib | GeoJSON read/write |
| Optional DB | SQLite + SpatiaLite | — | Spatial feature storage |

### Installation

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install \
    fastapi uvicorn[standard] \
    rasterio GDAL \
    geopandas shapely pyproj fiona \
    numpy scikit-image opencv-python-headless \
    torch torchvision \
    pydantic python-multipart \
    aiofiles
```

---

## 3. Phase 0 — Data Contract & Environment

> **Timeline: Day 1**

### 3.1 Study Area Requirements

| Requirement | Specification |
|---|---|
| Orthomosaic | One GeoTIFF, RGB (3 bands), georeferenced with CRS |
| Resolution | 0.05–1.0 m/pixel (drone or high-res satellite) |
| Reference parcels | GeoJSON or Shapefile, Polygon/MultiPolygon |
| Reference roads | GeoJSON or OSM extract, LineString |
| CRS | All layers must share or be convertible to a common projected CRS |
| Size | Small enough for demo processing (<100 MB orthomosaic) |

### 3.2 Internal CRS Convention

Choose one projected CRS in metres for all internal processing:

```python
# config.py
PROJECT_CRS = "EPSG:32643"  # UTM Zone 43N — covers most of India
```

All input layers are reprojected to this CRS on ingest. All output GeoJSON uses this CRS.

### 3.3 Source Tracking

Create `data/source_tracking.csv`:

```csv
asset_name,source_url,license,attribution,download_date,purpose
orthomosaic.tif,https://...,CC-BY-4.0,Survey of India,2026-09-28,Study area imagery
parcels_reference.geojson,...,,...,...,Reference parcel boundaries
roads_reference.geojson,...,ODbL,OpenStreetMap contributors,...,Reference road network
building_model_weights.pt,...,MIT,...,...,Building segmentation model
```

### 3.4 Shared JSON Schemas

Freeze these on Day 1 — they are the contract between backend modules and frontend:

**Building Feature:**
```json
{
  "building_id": "B-0103",
  "geometry": { "type": "Polygon", "coordinates": [] },
  "feature_type": "building",
  "confidence": 0.87,
  "source": "ai_building_model",
  "model_name": "building_model_v1",
  "review_status": "unverified"
}
```

**Parcel Feature:**
```json
{
  "parcel_id": "P-014",
  "geometry": { "type": "Polygon", "coordinates": [] },
  "feature_type": "parcel",
  "source": "reference",
  "source_date": "2025-04-12",
  "verification_status": "unverified",
  "confidence": null,
  "review_score": null,
  "warning_ids": []
}
```

**Warning Object:**
```json
{
  "warning_id": "W-0011",
  "warning_type": "building_crosses_parcel",
  "severity": "high",
  "feature_ids": ["B-0103", "P-014", "P-015"],
  "explanation": "Building B-0103 intersects two parcel polygons.",
  "status": "open"
}
```

**Review Score:**
```json
{
  "parcel_id": "P-014",
  "review_score": 82,
  "priority": "high",
  "reasons": [
    "Building B-0103 crosses western boundary",
    "Parcel overlaps P-015 by 3.2 sq m"
  ]
}
```

---

## 4. Phase 1 — Input Validation & Preprocessing

> **Timeline: Day 2–3**

### 4.1 Module: `pipeline/validate.py`

#### Raster Validation

```python
import rasterio
from dataclasses import dataclass, field

@dataclass
class RasterValidation:
    valid: bool
    width: int = 0
    height: int = 0
    band_count: int = 0
    crs: str = ""
    bounds: tuple = ()
    resolution: tuple = ()
    nodata: float = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

def validate_raster(path: str) -> RasterValidation:
    result = RasterValidation(valid=True)
    try:
        with rasterio.open(path) as src:
            result.width = src.width
            result.height = src.height
            result.band_count = src.count
            result.crs = str(src.crs) if src.crs else ""
            result.bounds = src.bounds
            result.resolution = src.res
            result.nodata = src.nodata

            # Critical checks
            if not src.crs:
                result.errors.append("Missing CRS — cannot georeference")
                result.valid = False

            if src.count < 3:
                result.errors.append(f"Expected ≥3 bands (RGB), got {src.count}")
                result.valid = False

            # Advisory checks
            if src.res[0] > 1.0:
                result.warnings.append(f"Resolution {src.res[0]:.2f} m/px is coarse for building detection")

            if src.width * src.height > 100_000_000:
                result.warnings.append("Very large raster — processing may be slow")

    except Exception as e:
        result.valid = False
        result.errors.append(f"Cannot open file: {str(e)}")

    return result
```

#### Vector Validation

```python
import geopandas as gpd

def validate_vector(path: str, expected_geom_type: str = "Polygon") -> dict:
    """Validate a vector layer (parcels, roads, etc.)."""
    try:
        gdf = gpd.read_file(path)
    except Exception as e:
        return {"valid": False, "errors": [f"Cannot read file: {e}"]}

    errors = []
    warnings = []

    if gdf.crs is None:
        errors.append("Missing CRS")

    invalid_geoms = gdf[~gdf.geometry.is_valid]
    if len(invalid_geoms) > 0:
        warnings.append(f"{len(invalid_geoms)} geometries are invalid (will be auto-repaired)")

    empty_geoms = gdf[gdf.geometry.is_empty]
    if len(empty_geoms) > 0:
        warnings.append(f"{len(empty_geoms)} empty geometries found")

    return {
        "valid": len(errors) == 0,
        "feature_count": len(gdf),
        "geometry_types": gdf.geometry.geom_type.unique().tolist(),
        "crs": str(gdf.crs),
        "errors": errors,
        "warnings": warnings
    }
```

### 4.2 Module: `pipeline/preprocess.py`

#### Raster Tiling

```python
import numpy as np
import rasterio
from rasterio.windows import Window
import json

def tile_raster(
    path: str,
    tile_size: int = 512,
    overlap: int = 64,
    output_dir: str = "tiles"
) -> dict:
    """Split a GeoTIFF into tiles for model inference."""
    os.makedirs(output_dir, exist_ok=True)
    tile_index = {}

    with rasterio.open(path) as src:
        step = tile_size - overlap
        tile_id = 0

        for row_off in range(0, src.height, step):
            for col_off in range(0, src.width, step):
                # Clamp to image boundaries
                win_height = min(tile_size, src.height - row_off)
                win_width = min(tile_size, src.width - col_off)
                window = Window(col_off, row_off, win_width, win_height)

                # Read tile data (bands × height × width)
                tile_data = src.read(window=window)

                # Pad if smaller than tile_size
                if win_height < tile_size or win_width < tile_size:
                    padded = np.zeros((src.count, tile_size, tile_size), dtype=tile_data.dtype)
                    padded[:, :win_height, :win_width] = tile_data
                    tile_data = padded

                # Save tile
                tile_name = f"tile_{tile_id:04d}"
                np.save(os.path.join(output_dir, f"{tile_name}.npy"), tile_data)

                # Record tile metadata
                tile_transform = rasterio.windows.transform(window, src.transform)
                tile_index[tile_name] = {
                    "row_off": row_off,
                    "col_off": col_off,
                    "width": win_width,
                    "height": win_height,
                    "transform": list(tile_transform)[:6],
                    "bounds": list(rasterio.windows.bounds(window, src.transform))
                }
                tile_id += 1

    # Save tile index
    with open(os.path.join(output_dir, "tile_index.json"), "w") as f:
        json.dump(tile_index, f, indent=2)

    return tile_index
```

#### Vector CRS Normalization

```python
def normalize_vectors(path: str, target_crs: str) -> gpd.GeoDataFrame:
    """Load a vector file, reproject to the project CRS, repair invalid geoms."""
    gdf = gpd.read_file(path)

    # Reproject
    if str(gdf.crs) != target_crs:
        gdf = gdf.to_crs(target_crs)

    # Repair invalid geometries
    gdf['geometry'] = gdf.geometry.apply(
        lambda g: make_valid(g) if not g.is_valid else g
    )

    # Remove empty geometries
    gdf = gdf[~gdf.geometry.is_empty]

    return gdf
```

---

## 5. Phase 2 — AI Model Integration

> **Timeline: Day 3–4**

### 5.1 Module: `pipeline/buildings.py` — Building Footprint Extraction

#### Model Loading

```python
import torch

class BuildingExtractor:
    def __init__(self, model_dir: str, device: str = "cpu"):
        self.device = torch.device(device)
        config_path = os.path.join(model_dir, "config.json")
        weights_path = os.path.join(model_dir, "weights.pt")

        with open(config_path) as f:
            self.config = json.load(f)

        # Load the model architecture (UNet++ recommended)
        self.model = self._build_model()
        self.model.load_state_dict(torch.load(weights_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def _build_model(self):
        """Build the segmentation model from config."""
        # Example: segmentation_models_pytorch UNet++
        import segmentation_models_pytorch as smp
        return smp.UnetPlusPlus(
            encoder_name=self.config.get("encoder", "resnet34"),
            encoder_weights=None,  # weights loaded from .pt
            in_channels=self.config.get("in_channels", 3),
            classes=1
        )

    def predict_tile(self, tile: np.ndarray, threshold: float = 0.55) -> np.ndarray:
        """Run inference on a single tile. Returns binary mask."""
        # tile shape: (C, H, W), values in [0, 255]
        tensor = torch.from_numpy(tile.astype(np.float32) / 255.0)
        tensor = tensor.unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)

        prob = torch.sigmoid(logits).squeeze().cpu().numpy()
        return (prob > threshold).astype(np.uint8), prob

    def predict_all_tiles(
        self,
        tile_dir: str,
        tile_index: dict,
        threshold: float = 0.55
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run inference on all tiles and stitch into a full mask."""
        # Determine full raster dimensions from tile_index
        max_row = max(t['row_off'] + t['height'] for t in tile_index.values())
        max_col = max(t['col_off'] + t['width'] for t in tile_index.values())

        full_mask = np.zeros((max_row, max_col), dtype=np.uint8)
        full_prob = np.zeros((max_row, max_col), dtype=np.float32)
        count_map = np.zeros((max_row, max_col), dtype=np.float32)

        for tile_name, meta in tile_index.items():
            tile_data = np.load(os.path.join(tile_dir, f"{tile_name}.npy"))
            mask, prob = self.predict_tile(tile_data, threshold)

            h, w = meta['height'], meta['width']
            r, c = meta['row_off'], meta['col_off']

            # Accumulate probabilities for overlap averaging
            full_prob[r:r+h, c:c+w] += prob[:h, :w]
            count_map[r:r+h, c:c+w] += 1.0

        # Average overlapping regions
        count_map[count_map == 0] = 1
        full_prob /= count_map
        full_mask = (full_prob > threshold).astype(np.uint8)

        return full_mask, full_prob
```

#### Model Config File

```json
{
  "model_name": "building_model_v1",
  "architecture": "UNetPlusPlus",
  "encoder": "resnet34",
  "in_channels": 3,
  "classes": 1,
  "tile_size": 512,
  "default_threshold": 0.55,
  "trained_on": "SpaceNet + Inria",
  "resolution_m": 0.3,
  "notes": "Pretrained, tested on study area"
}
```

### 5.2 Module: `pipeline/roads.py`

#### Priority 1: Reference Roads

```python
def load_reference_roads(path: str, target_crs: str) -> gpd.GeoDataFrame:
    """Load and normalize a reference road layer."""
    gdf = gpd.read_file(path)
    gdf = gdf.to_crs(target_crs)
    gdf = gdf[~gdf.geometry.is_empty]

    # Assign IDs
    gdf = gdf.reset_index(drop=True)
    gdf['road_id'] = [f'R-{i:04d}' for i in range(len(gdf))]
    gdf['feature_type'] = 'road'
    gdf['source'] = 'reference_osm'
    gdf['confidence'] = None
    gdf['review_status'] = 'unverified'

    return gdf
```

#### Priority 2: Model-Based Roads (stretch)

```python
def extract_roads_from_model(
    tile_dir: str,
    tile_index: dict,
    model_dir: str,
    threshold: float = 0.5
) -> gpd.GeoDataFrame:
    """Run road segmentation model and vectorize."""
    # Similar to BuildingExtractor but with road-specific post-processing:
    # 1. Threshold the probability mask
    # 2. Morphological thinning/skeletonization
    # 3. Vectorize skeleton to LineString geometries
    # 4. Connect nearby endpoints (distance tolerance)
    # 5. Assign road IDs and metadata
    pass  # Implement only if time permits
```

### 5.3 Module: `pipeline/landuse.py`

```python
def derive_landuse_from_masks(
    building_mask: np.ndarray,
    road_mask: np.ndarray = None,
    ndvi: np.ndarray = None,
    transform=None,
    crs: str = None
) -> gpd.GeoDataFrame:
    """Rule-based land-use classification from existing masks."""
    landuse = np.zeros_like(building_mask, dtype=np.uint8)

    # Class assignment priority (higher priority overwrites lower)
    if road_mask is not None:
        landuse[road_mask == 1] = 2       # Road
    landuse[building_mask == 1] = 1       # Built-up (overwrites road if overlap)

    if ndvi is not None:
        vegetation = (ndvi > 0.3) & (landuse == 0)
        landuse[vegetation] = 3           # Vegetation

    # Everything else = bare/open
    landuse[landuse == 0] = 5

    # Polygonize each class
    class_names = {1: 'built_up', 2: 'road', 3: 'vegetation', 4: 'water', 5: 'bare_open'}
    features = []
    for class_val, class_name in class_names.items():
        class_mask = (landuse == class_val).astype(np.uint8)
        for geom, val in shapes(class_mask, transform=transform):
            if val == 1:
                features.append({
                    'geometry': shape(geom),
                    'class': class_name,
                    'class_code': class_val,
                    'source': 'rule_based'
                })

    return gpd.GeoDataFrame(features, crs=crs)
```

### 5.4 Fallback Data

For every model output, maintain a pre-computed fallback:

```python
# pipeline/fallback.py

FALLBACK_DIR = "data/fallback"

def get_buildings(project_id: str, use_fallback: bool = False) -> gpd.GeoDataFrame:
    if use_fallback:
        return gpd.read_file(os.path.join(FALLBACK_DIR, "buildings_fallback.geojson"))
    return gpd.read_file(f"projects/{project_id}/buildings.geojson")
```

---

## 6. Phase 3 — Raster-to-Vector Polygonization

> **Timeline: Day 4 (part of model post-processing)**

### 6.1 Module: `pipeline/polygonize.py`

```python
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.validation import make_valid
from skimage import morphology
import geopandas as gpd

def mask_to_polygons(
    mask: np.ndarray,
    probability_map: np.ndarray,
    transform,
    crs: str,
    feature_type: str = "building",
    id_prefix: str = "B",
    min_area_px: int = 25,
    simplify_tolerance: float = 0.5,
    min_area_m2: float = 10.0
) -> gpd.GeoDataFrame:
    """Convert a binary mask to a GeoDataFrame of polygons."""

    # 1. Morphological cleaning
    cleaned = morphology.remove_small_objects(mask.astype(bool), min_size=min_area_px)
    cleaned = morphology.remove_small_holes(cleaned, area_threshold=15)
    cleaned = cleaned.astype(np.uint8)

    # 2. Polygonize
    features = []
    for geom_dict, value in shapes(cleaned, transform=transform):
        if value != 1:
            continue

        poly = shape(geom_dict)

        # Repair if needed
        if not poly.is_valid:
            poly = make_valid(poly)

        # Simplify to reduce vertex count
        poly = poly.simplify(simplify_tolerance)

        # Filter by minimum area
        if poly.area < min_area_m2:
            continue

        # Compute mean confidence from probability map
        # (simplified: use centroid pixel)
        confidence = float(np.mean(probability_map[cleaned == 1])) if probability_map is not None else 0.0

        features.append({
            'geometry': poly,
            'feature_type': feature_type,
            'confidence': round(confidence, 3),
            'source': f'ai_{feature_type}_model',
            'review_status': 'unverified'
        })

    # 3. Build GeoDataFrame with IDs
    gdf = gpd.GeoDataFrame(features, crs=crs)
    gdf.insert(0, f'{feature_type}_id', [f'{id_prefix}-{i:04d}' for i in range(len(gdf))])

    return gdf
```

---

## 7. Phase 4 — Deterministic GIS Engine

> **Timeline: Day 5**

### 7.1 Module: `pipeline/topology.py`

This is the **highest-value non-AI component** — it converts raw model output into actionable cadastral information.

```python
from shapely.validation import explain_validity
from shapely.ops import unary_union
import geopandas as gpd

class TopologyEngine:
    """Deterministic topology and conflict checker. No AI involved."""

    def __init__(self, gap_tolerance_m2: float = 1.0, overlap_tolerance_m2: float = 0.5):
        self.gap_tolerance = gap_tolerance_m2
        self.overlap_tolerance = overlap_tolerance_m2
        self.warnings: list[dict] = []
        self._warning_counter = 0

    def _add_warning(self, warning_type: str, severity: str,
                     feature_ids: list, explanation: str):
        self._warning_counter += 1
        self.warnings.append({
            'warning_id': f'W-{self._warning_counter:04d}',
            'warning_type': warning_type,
            'severity': severity,
            'feature_ids': feature_ids,
            'explanation': explanation,
            'status': 'open',
            'geometry': None  # optionally store the conflict geometry
        })

    def check_geometry_validity(self, gdf: gpd.GeoDataFrame, id_col: str):
        """Check all geometries for validity."""
        for _, row in gdf.iterrows():
            geom = row.geometry
            fid = row[id_col]

            if geom.is_empty:
                self._add_warning('empty_geometry', 'high', [fid],
                                  f'{fid} has an empty geometry')
            elif not geom.is_valid:
                reason = explain_validity(geom)
                self._add_warning('invalid_geometry', 'high', [fid],
                                  f'{fid} is invalid: {reason}')

    def check_parcel_overlaps(self, parcels: gpd.GeoDataFrame):
        """Detect pairwise parcel overlaps."""
        sindex = parcels.sindex
        checked = set()

        for i, p1 in parcels.iterrows():
            candidates = list(sindex.intersection(p1.geometry.bounds))
            for j in candidates:
                if j <= i or (i, j) in checked:
                    continue
                checked.add((i, j))

                p2 = parcels.iloc[j]
                if p1.geometry.overlaps(p2.geometry):
                    overlap = p1.geometry.intersection(p2.geometry)
                    if overlap.area > self.overlap_tolerance:
                        self._add_warning(
                            'parcel_overlap', 'high',
                            [p1['parcel_id'], p2['parcel_id']],
                            f'{p1["parcel_id"]} overlaps {p2["parcel_id"]} '
                            f'by {overlap.area:.1f} sq m'
                        )

    def check_parcel_gaps(self, parcels: gpd.GeoDataFrame):
        """Detect gaps between adjacent parcels."""
        all_union = unary_union(parcels.geometry)
        convex_hull = all_union.convex_hull
        gap = convex_hull.difference(all_union)

        if not gap.is_empty and gap.area > self.gap_tolerance:
            # Decompose multi-polygon gaps
            if gap.geom_type == 'MultiPolygon':
                for g in gap.geoms:
                    if g.area > self.gap_tolerance:
                        self._add_warning(
                            'parcel_gap', 'medium', [],
                            f'Possible gap ({g.area:.1f} sq m) detected between adjacent parcels'
                        )
            else:
                self._add_warning(
                    'parcel_gap', 'medium', [],
                    f'Possible gap ({gap.area:.1f} sq m) detected between adjacent parcels'
                )

    def check_building_parcel_conflicts(self, buildings: gpd.GeoDataFrame,
                                          parcels: gpd.GeoDataFrame):
        """Detect buildings crossing parcel boundaries or outside all parcels."""
        parcels_sindex = parcels.sindex

        for _, bldg in buildings.iterrows():
            candidate_idxs = list(parcels_sindex.intersection(bldg.geometry.bounds))
            intersecting = parcels.iloc[candidate_idxs]
            intersecting = intersecting[intersecting.geometry.intersects(bldg.geometry)]

            if len(intersecting) > 1:
                self._add_warning(
                    'building_crosses_parcel', 'high',
                    [bldg['building_id']] + intersecting['parcel_id'].tolist(),
                    f'{bldg["building_id"]} intersects {len(intersecting)} parcels: '
                    f'{", ".join(intersecting["parcel_id"].tolist())}'
                )
            elif len(intersecting) == 0:
                self._add_warning(
                    'building_outside_parcels', 'medium',
                    [bldg['building_id']],
                    f'{bldg["building_id"]} lies outside all parcel boundaries'
                )

    def check_road_parcel_conflicts(self, roads: gpd.GeoDataFrame,
                                      parcels: gpd.GeoDataFrame):
        """Detect roads cutting through parcels."""
        parcels_sindex = parcels.sindex

        for _, road in roads.iterrows():
            candidate_idxs = list(parcels_sindex.intersection(road.geometry.bounds))
            for idx in candidate_idxs:
                parcel = parcels.iloc[idx]
                if road.geometry.intersects(parcel.geometry):
                    if not road.geometry.touches(parcel.geometry):
                        # Road actually cuts through (not just touching boundary)
                        self._add_warning(
                            'road_intersects_parcel', 'medium',
                            [road['road_id'], parcel['parcel_id']],
                            f'Road {road["road_id"]} cuts through {parcel["parcel_id"]}'
                        )

    def check_low_confidence(self, features: gpd.GeoDataFrame,
                              id_col: str, threshold: float = 0.6):
        """Flag features with low AI confidence."""
        low = features[features['confidence'] < threshold]
        for _, feat in low.iterrows():
            self._add_warning(
                'low_confidence', 'low',
                [feat[id_col]],
                f'{feat[id_col]} has low model confidence ({feat["confidence"]:.2f})'
            )

    def run_all_checks(self, parcels, buildings, roads) -> list[dict]:
        """Run the complete topology validation suite."""
        self.warnings = []
        self._warning_counter = 0

        self.check_geometry_validity(parcels, 'parcel_id')
        self.check_geometry_validity(buildings, 'building_id')
        self.check_parcel_overlaps(parcels)
        self.check_parcel_gaps(parcels)
        self.check_building_parcel_conflicts(buildings, parcels)
        self.check_road_parcel_conflicts(roads, parcels)
        self.check_low_confidence(buildings, 'building_id')

        return self.warnings
```

#### Key Design Decision: Spatial Indexing

Use `gdf.sindex` (R-tree) for all spatial queries to avoid O(n²) full scans when parcels/buildings scale up.

---

## 8. Phase 5 — Change Detection (Deterministic)

> **Timeline: Day 7 (stretch)**

### 8.1 Module: `pipeline/change_detection.py`

```python
def detect_building_changes(
    current: gpd.GeoDataFrame,
    prior: gpd.GeoDataFrame,
    iou_new_threshold: float = 0.3,
    iou_change_threshold: float = 0.7
) -> list[dict]:
    """
    Compare current building polygons against a prior-date layer.
    Uses IoU (Intersection over Union) to match buildings.
    """
    changes = []
    prior_sindex = prior.sindex

    # --- New or changed buildings ---
    for _, curr_bldg in current.iterrows():
        candidate_idxs = list(prior_sindex.intersection(curr_bldg.geometry.bounds))
        candidates = prior.iloc[candidate_idxs]
        candidates = candidates[candidates.geometry.intersects(curr_bldg.geometry)]

        if len(candidates) == 0:
            changes.append({
                'change_type': 'new_construction',
                'feature_id': curr_bldg['building_id'],
                'confidence': curr_bldg.get('confidence', None),
                'area_m2': curr_bldg.geometry.area,
                'geometry': curr_bldg.geometry.__geo_interface__
            })
            continue

        # Find best IoU match
        best_iou = 0
        for _, prior_bldg in candidates.iterrows():
            intersection = curr_bldg.geometry.intersection(prior_bldg.geometry).area
            union = curr_bldg.geometry.union(prior_bldg.geometry).area
            iou = intersection / union if union > 0 else 0
            best_iou = max(best_iou, iou)

        if best_iou < iou_new_threshold:
            changes.append({
                'change_type': 'new_construction',
                'feature_id': curr_bldg['building_id'],
                'area_m2': curr_bldg.geometry.area,
                'geometry': curr_bldg.geometry.__geo_interface__
            })
        elif best_iou < iou_change_threshold:
            changes.append({
                'change_type': 'geometry_change',
                'feature_id': curr_bldg['building_id'],
                'iou_with_prior': round(best_iou, 3),
                'area_m2': curr_bldg.geometry.area,
                'geometry': curr_bldg.geometry.__geo_interface__
            })

    # --- Removed buildings ---
    current_sindex = current.sindex
    for _, prior_bldg in prior.iterrows():
        candidate_idxs = list(current_sindex.intersection(prior_bldg.geometry.bounds))
        candidates = current.iloc[candidate_idxs]
        candidates = candidates[candidates.geometry.intersects(prior_bldg.geometry)]

        if len(candidates) == 0:
            changes.append({
                'change_type': 'possible_removal',
                'feature_id': prior_bldg.get('building_id', 'unknown'),
                'area_m2': prior_bldg.geometry.area,
                'geometry': prior_bldg.geometry.__geo_interface__
            })

    return changes
```

---

## 9. Phase 6 — Review-Priority Scoring Engine

> **Timeline: Day 5–7**

### 9.1 Module: `pipeline/scoring.py`

```python
SCORING_WEIGHTS = {
    'building_crosses_parcel': 30,
    'invalid_geometry': 20,
    'parcel_overlap': 15,
    'parcel_gap': 15,
    'road_intersects_parcel': 10,
    'low_confidence': 10,
    'building_outside_parcels': 5,
    'recent_change': 15,
}

PRIORITY_BANDS = {
    'high': 60,    # score >= 60 → Red
    'medium': 30,  # score 30–59 → Amber
    'low': 0,      # score < 30 → Green
}

def compute_review_scores(
    parcels: gpd.GeoDataFrame,
    warnings: list[dict],
    buildings: gpd.GeoDataFrame,
    change_indicators: list[dict] = None
) -> list[dict]:
    """Compute a transparent, rule-based review priority score per parcel."""
    scores = []

    for _, parcel in parcels.iterrows():
        pid = parcel['parcel_id']
        score = 0
        reasons = []
        contributing_warnings = []

        # Score from topology warnings
        for w in warnings:
            if pid not in w.get('feature_ids', []):
                continue
            wtype = w['warning_type']
            weight = SCORING_WEIGHTS.get(wtype, 0)
            if weight > 0:
                score += weight
                reasons.append(w['explanation'])
                contributing_warnings.append(w['warning_id'])

        # Score from low-confidence buildings within this parcel
        parcel_buildings = buildings[buildings.geometry.intersects(parcel.geometry)]
        low_conf = parcel_buildings[parcel_buildings['confidence'] < 0.6]
        if len(low_conf) > 0 and 'low_confidence' not in [w['warning_type'] for w in warnings if pid in w.get('feature_ids', [])]:
            score += SCORING_WEIGHTS['low_confidence']
            reasons.append(f'{len(low_conf)} building(s) with low confidence')

        # Score from change indicators
        if change_indicators:
            parcel_changes = [
                c for c in change_indicators
                if parcel.geometry.intersects(shape(c['geometry']))
            ]
            if parcel_changes:
                score += SCORING_WEIGHTS['recent_change']
                change_types = set(c['change_type'] for c in parcel_changes)
                reasons.append(
                    f'{len(parcel_changes)} change(s) detected: {", ".join(change_types)}'
                )

        # Priority banding
        priority = 'low'
        for band, threshold in sorted(PRIORITY_BANDS.items(),
                                       key=lambda x: x[1], reverse=True):
            if score >= threshold:
                priority = band
                break

        scores.append({
            'parcel_id': pid,
            'review_score': min(score, 100),
            'priority': priority,
            'reasons': reasons,
            'contributing_warnings': contributing_warnings
        })

    return sorted(scores, key=lambda s: s['review_score'], reverse=True)
```

---

## 10. Phase 7 — Backend API Layer (FastAPI)

> **Timeline: Day 3–4 (parallel with model work)**

### 10.1 Application Setup

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import projects, processing, features, exports

app = FastAPI(
    title="SIH26012 Cadastral Review API",
    description="AI-Assisted Cadastral Review Platform Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(processing.router, prefix="/api/projects", tags=["Processing"])
app.include_router(features.router, prefix="/api/projects", tags=["Features"])
app.include_router(exports.router, prefix="/api/projects", tags=["Export"])
```

### 10.2 Pydantic Models

```python
# schemas.py
from pydantic import BaseModel
from enum import Enum
from typing import Optional

class ProcessingStatus(str, Enum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    EXTRACTING_BUILDINGS = "extracting_buildings"
    LOADING_ROADS = "loading_roads"
    CLASSIFYING_LANDUSE = "classifying_landuse"
    LOADING_PARCELS = "loading_parcels"
    DETECTING_CHANGES = "detecting_changes"
    VALIDATING_TOPOLOGY = "validating_topology"
    SCORING = "scoring"
    COMPLETE = "complete"
    ERROR = "error"

class ProjectCreate(BaseModel):
    name: str
    study_area: str
    crs: str = "EPSG:32643"

class ProcessingConfig(BaseModel):
    model_name: str = "building_model_v1"
    tile_size: int = 512
    confidence_threshold: float = 0.55
    use_fallback: bool = False

class FeatureUpdate(BaseModel):
    geometry: Optional[dict] = None
    review_status: Optional[str] = None
    notes: Optional[str] = None

class ReviewAction(BaseModel):
    action: str  # "approve", "reject", "needs_field_visit"
    reason: Optional[str] = None
```

### 10.3 Key Route Implementations

```python
# api/processing.py
from fastapi import APIRouter, BackgroundTasks

router = APIRouter()

@router.post("/{project_id}/process")
async def start_processing(
    project_id: str,
    config: ProcessingConfig,
    background_tasks: BackgroundTasks
):
    """Trigger the full processing pipeline as a background task."""
    update_project_status(project_id, ProcessingStatus.QUEUED)
    background_tasks.add_task(run_full_pipeline, project_id, config.dict())
    return {"project_id": project_id, "status": "queued"}

@router.get("/{project_id}/process/status")
async def get_processing_status(project_id: str):
    """Poll the current processing status."""
    status = get_project_status(project_id)
    return {"project_id": project_id, "status": status}
```

```python
# api/features.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/{project_id}/layers/{layer_name}")
async def get_layer(project_id: str, layer_name: str):
    """Return a GeoJSON layer (buildings, roads, parcels, landuse)."""
    valid_layers = ['buildings', 'roads', 'parcels', 'landuse']
    if layer_name not in valid_layers:
        return JSONResponse(status_code=404, content={"error": f"Unknown layer: {layer_name}"})

    path = f"projects/{project_id}/{layer_name}.geojson"
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "Layer not yet generated"})

    with open(path) as f:
        return json.load(f)

@router.get("/{project_id}/warnings")
async def get_warnings(project_id: str):
    path = f"projects/{project_id}/warnings.json"
    with open(path) as f:
        return json.load(f)

@router.get("/{project_id}/scores")
async def get_scores(project_id: str):
    path = f"projects/{project_id}/scores.json"
    with open(path) as f:
        return json.load(f)

@router.put("/{project_id}/features/{feature_id}")
async def update_feature(project_id: str, feature_id: str, update: FeatureUpdate):
    """Update a feature's geometry or review status."""
    # Load the appropriate layer, find the feature, update it
    # Store both original and updated geometry for audit trail
    # Return the updated feature
    pass

@router.post("/{project_id}/features/{feature_id}/approve")
async def approve_feature(project_id: str, feature_id: str, action: ReviewAction):
    """Mark a feature as approved."""
    pass

@router.post("/{project_id}/revalidate")
async def revalidate(project_id: str):
    """Re-run topology checks after edits."""
    pass
```

---

## 11. Phase 8 — Pipeline Orchestrator

> **Timeline: Day 4–5**

### 11.1 Module: `pipeline/orchestrator.py`

```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, project_id: str, config: dict):
        self.project_id = project_id
        self.config = config
        self.project_dir = f"projects/{project_id}"
        os.makedirs(self.project_dir, exist_ok=True)

    def update_status(self, status: str, detail: str = ""):
        """Update the processing status (read by the status endpoint)."""
        status_file = os.path.join(self.project_dir, "status.json")
        with open(status_file, "w") as f:
            json.dump({
                "status": status,
                "detail": detail,
                "updated_at": datetime.now().isoformat()
            }, f)
        logger.info(f"[{self.project_id}] Status: {status} — {detail}")

    async def run(self):
        """Execute the full pipeline end-to-end."""
        try:
            # Step 1: Validate
            self.update_status("preprocessing", "Validating input files")
            raster_result = validate_raster(self.config['image_path'])
            if not raster_result.valid:
                self.update_status("error", f"Validation failed: {raster_result.errors}")
                return

            # Step 2: Tile
            self.update_status("preprocessing", "Tiling orthomosaic")
            tile_dir = os.path.join(self.project_dir, "tiles")
            tile_index = tile_raster(
                self.config['image_path'],
                tile_size=self.config.get('tile_size', 512),
                output_dir=tile_dir
            )

            # Step 3: Building model
            self.update_status("extracting_buildings", "Running building segmentation")
            try:
                extractor = BuildingExtractor(
                    model_dir=f"models/{self.config['model_name']}"
                )
                mask, prob = extractor.predict_all_tiles(tile_dir, tile_index)
                # Get the transform from the original raster
                with rasterio.open(self.config['image_path']) as src:
                    transform = src.transform
                buildings = mask_to_polygons(mask, prob, transform, PROJECT_CRS, "building", "B")
            except Exception as e:
                logger.warning(f"Model failed: {e}. Using fallback.")
                buildings = gpd.read_file("data/fallback/buildings_fallback.geojson")

            buildings.to_file(os.path.join(self.project_dir, "buildings.geojson"), driver="GeoJSON")

            # Step 4: Roads
            self.update_status("loading_roads", "Loading reference roads")
            roads = load_reference_roads(self.config['roads_path'], PROJECT_CRS)
            roads.to_file(os.path.join(self.project_dir, "roads.geojson"), driver="GeoJSON")

            # Step 5: Land-use
            self.update_status("classifying_landuse", "Deriving land-use classes")
            landuse = derive_landuse_from_masks(mask, road_mask=None, transform=transform, crs=PROJECT_CRS)
            landuse.to_file(os.path.join(self.project_dir, "landuse.geojson"), driver="GeoJSON")

            # Step 6: Parcels
            self.update_status("loading_parcels", "Normalizing parcel layer")
            parcels = normalize_vectors(self.config['parcels_path'], PROJECT_CRS)
            if 'parcel_id' not in parcels.columns:
                parcels['parcel_id'] = [f'P-{i:04d}' for i in range(len(parcels))]
            parcels.to_file(os.path.join(self.project_dir, "parcels.geojson"), driver="GeoJSON")

            # Step 7: Change detection (if prior data exists)
            changes = []
            if self.config.get('prior_buildings_path'):
                self.update_status("detecting_changes", "Comparing with prior survey")
                prior = gpd.read_file(self.config['prior_buildings_path'])
                prior = prior.to_crs(PROJECT_CRS)
                changes = detect_building_changes(buildings, prior)

            # Step 8: Topology
            self.update_status("validating_topology", "Running topology checks")
            engine = TopologyEngine()
            warnings = engine.run_all_checks(parcels, buildings, roads)
            with open(os.path.join(self.project_dir, "warnings.json"), "w") as f:
                json.dump(warnings, f, indent=2)

            # Step 9: Scoring
            self.update_status("scoring", "Computing review priorities")
            scores = compute_review_scores(parcels, warnings, buildings, changes)
            with open(os.path.join(self.project_dir, "scores.json"), "w") as f:
                json.dump(scores, f, indent=2)

            # Step 10: Save changes
            if changes:
                with open(os.path.join(self.project_dir, "changes.json"), "w") as f:
                    json.dump(changes, f, indent=2, default=str)

            self.update_status("complete", f"Processed {len(buildings)} buildings, "
                             f"{len(parcels)} parcels, {len(warnings)} warnings")

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            self.update_status("error", str(e))
```

---

## 12. Phase 9 — Export & Audit Trail

> **Timeline: Day 6**

### 12.1 Module: `api/exports.py`

```python
from fastapi import APIRouter
from fastapi.responses import FileResponse
import zipfile

router = APIRouter()

@router.get("/{project_id}/export")
async def export_project(project_id: str):
    """Export all layers, warnings, scores, and metadata as a ZIP."""
    project_dir = f"projects/{project_id}"
    export_dir = os.path.join(project_dir, "export")
    os.makedirs(export_dir, exist_ok=True)

    # Generate metadata
    metadata = {
        "project_id": project_id,
        "crs": PROJECT_CRS,
        "processing_date": datetime.now().isoformat(),
        "disclaimer": (
            "PRELIMINARY AI-ASSISTED OUTPUT. "
            "All parcel boundaries are suggestions and require "
            "field verification by an authorized surveyor."
        ),
        "layers": []
    }

    # Copy each layer and count features
    for layer_name in ['buildings', 'roads', 'parcels', 'landuse']:
        src = os.path.join(project_dir, f"{layer_name}.geojson")
        if os.path.exists(src):
            shutil.copy(src, os.path.join(export_dir, f"{layer_name}.geojson"))
            with open(src) as f:
                data = json.load(f)
                count = len(data.get('features', []))
            metadata['layers'].append({"name": layer_name, "feature_count": count})

    # Copy warnings and scores
    for extra in ['warnings.json', 'scores.json', 'changes.json']:
        src = os.path.join(project_dir, extra)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(export_dir, extra))

    # Write metadata
    with open(os.path.join(export_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    # Create ZIP
    zip_path = os.path.join(project_dir, f"{project_id}_export.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(export_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, export_dir)
                zf.write(filepath, arcname)

    return FileResponse(zip_path, filename=f"{project_id}_export.zip")
```

### 12.2 Audit Trail

```python
# pipeline/audit.py

def record_edit(project_id: str, edit: dict):
    """Append an edit record to the audit trail."""
    audit_path = f"projects/{project_id}/audit_trail.json"

    if os.path.exists(audit_path):
        with open(audit_path) as f:
            trail = json.load(f)
    else:
        trail = []

    edit['edit_id'] = f"E-{len(trail)+1:04d}"
    edit['timestamp'] = datetime.now().isoformat()
    trail.append(edit)

    with open(audit_path, "w") as f:
        json.dump(trail, f, indent=2)

    return edit
```

---

## 13. Phase 10 — Stretch: NDVI/LST Climate Layer

> **Timeline: Day 7 (only if core is stable)**

### 13.1 Module: `pipeline/climate.py`

```python
def compute_ndvi(nir_band: np.ndarray, red_band: np.ndarray) -> np.ndarray:
    """Compute NDVI from NIR and Red bands."""
    nir = nir_band.astype(np.float32)
    red = red_band.astype(np.float32)
    denominator = nir + red
    denominator[denominator == 0] = 1  # avoid division by zero
    ndvi = (nir - red) / denominator
    return np.clip(ndvi, -1.0, 1.0)

def compute_rgb_vegetation_proxy(image: np.ndarray) -> np.ndarray:
    """When only RGB is available, compute a simple vegetation proxy."""
    # Excess Green Index: 2*G - R - B
    r, g, b = image[0].astype(float), image[1].astype(float), image[2].astype(float)
    total = r + g + b
    total[total == 0] = 1
    egi = (2 * g - r - b) / total
    return np.clip(egi, -1.0, 1.0)

def compute_heat_vulnerability(
    building_density: np.ndarray,
    vegetation_index: np.ndarray
) -> np.ndarray:
    """
    Simple heat-vulnerability proxy when no thermal data is available.
    High built-up density + low vegetation = higher vulnerability.
    """
    # Normalize inputs to [0, 1]
    bd = building_density / max(building_density.max(), 1)
    vi = (vegetation_index + 1) / 2  # NDVI range [-1,1] → [0,1]

    vulnerability = bd * (1 - vi)
    return vulnerability
```

> **Important:** This layer is **isolated from cadastral logic**. It never feeds into topology checks, review scores, or parcel warnings. Label it clearly in the API response as `"category": "planning_overlay"`.

---

## 14. Phase 11 — Testing & Fallback

> **Timeline: Day 8 onwards**

### 14.1 Unit Tests

```python
# tests/test_topology.py

def test_building_crosses_parcel():
    """A building overlapping two parcels should produce a warning."""
    parcels = create_test_parcels([
        ("P-001", box(0, 0, 10, 10)),
        ("P-002", box(10, 0, 20, 10)),
    ])
    buildings = create_test_buildings([
        ("B-001", box(8, 3, 12, 7)),  # crosses P-001 and P-002
    ])
    roads = gpd.GeoDataFrame()

    engine = TopologyEngine()
    warnings = engine.run_all_checks(parcels, buildings, roads)

    crossing_warnings = [w for w in warnings if w['warning_type'] == 'building_crosses_parcel']
    assert len(crossing_warnings) == 1
    assert 'B-001' in crossing_warnings[0]['feature_ids']
    assert 'P-001' in crossing_warnings[0]['feature_ids']
    assert 'P-002' in crossing_warnings[0]['feature_ids']

def test_parcel_overlap():
    """Overlapping parcels should produce a warning."""
    parcels = create_test_parcels([
        ("P-001", box(0, 0, 11, 10)),  # extends past boundary
        ("P-002", box(10, 0, 20, 10)), # overlaps P-001 by 1×10
    ])

    engine = TopologyEngine()
    engine.check_parcel_overlaps(parcels)
    assert any(w['warning_type'] == 'parcel_overlap' for w in engine.warnings)

def test_review_score_high_priority():
    """A parcel with building conflict + overlap should score high."""
    # ... test that score >= 60 → priority = "high"
    pass
```

### 14.2 Integration Test

```python
# tests/test_pipeline.py

def test_full_pipeline():
    """Run the full pipeline on test data and verify outputs."""
    orchestrator = PipelineOrchestrator("test_project", {
        'image_path': 'data/test/small_ortho.tif',
        'parcels_path': 'data/test/parcels.geojson',
        'roads_path': 'data/test/roads.geojson',
        'model_name': 'building_model_v1',
    })

    import asyncio
    asyncio.run(orchestrator.run())

    # Verify outputs exist
    assert os.path.exists("projects/test_project/buildings.geojson")
    assert os.path.exists("projects/test_project/warnings.json")
    assert os.path.exists("projects/test_project/scores.json")

    # Verify GeoJSON is valid
    buildings = gpd.read_file("projects/test_project/buildings.geojson")
    assert len(buildings) > 0
    assert all(buildings.geometry.is_valid)
```

### 14.3 Fallback Files

```text
data/fallback/
  buildings_fallback.geojson     # Pre-run model output, manually checked
  roads_fallback.geojson         # OSM extract
  landuse_fallback.geojson       # Pre-computed rule-based output
  parcels_preloaded.geojson      # Reference layer
  warnings_fallback.json         # Pre-computed topology warnings
  scores_fallback.json           # Pre-computed review scores
```

---

## 15. Directory Structure

```text
backend/
├── main.py                    # FastAPI app entry point
├── config.py                  # Constants (CRS, paths, thresholds)
├── schemas.py                 # Pydantic models
│
├── api/
│   ├── __init__.py
│   ├── projects.py            # Project CRUD, file upload
│   ├── processing.py          # Trigger/poll pipeline
│   ├── features.py            # Query layers, update features
│   └── exports.py             # GeoJSON/ZIP export
│
├── pipeline/
│   ├── __init__.py
│   ├── validate.py            # Input file validation
│   ├── preprocess.py          # CRS normalization, tiling
│   ├── buildings.py           # Building extraction model
│   ├── roads.py               # Road loading/extraction
│   ├── landuse.py             # Land-use classification
│   ├── polygonize.py          # Mask → vector conversion
│   ├── topology.py            # Topology validation engine
│   ├── change_detection.py    # Deterministic change comparator
│   ├── scoring.py             # Review-priority scoring
│   ├── climate.py             # NDVI/LST (stretch)
│   ├── audit.py               # Edit audit trail
│   ├── fallback.py            # Fallback data loading
│   └── orchestrator.py        # Full pipeline controller
│
├── models/
│   └── building_model_v1/
│       ├── weights.pt
│       └── config.json
│
├── data/
│   ├── study_area/
│   │   ├── orthomosaic.tif
│   │   ├── parcels_reference.geojson
│   │   ├── roads_reference.geojson
│   │   └── metadata.json
│   ├── fallback/
│   │   ├── buildings_fallback.geojson
│   │   ├── roads_fallback.geojson
│   │   └── ...
│   └── source_tracking.csv
│
├── projects/                  # Runtime project outputs
│   └── {project_id}/
│       ├── tiles/
│       ├── buildings.geojson
│       ├── roads.geojson
│       ├── parcels.geojson
│       ├── landuse.geojson
│       ├── warnings.json
│       ├── scores.json
│       ├── changes.json
│       ├── audit_trail.json
│       ├── status.json
│       └── export/
│
├── tests/
│   ├── test_validate.py
│   ├── test_topology.py
│   ├── test_scoring.py
│   ├── test_change_detection.py
│   └── test_pipeline.py
│
└── requirements.txt
```

---

## 16. API Contract Reference

This is the complete API that the frontend team consumes. No endpoint runs model inference in the browser.

### Projects

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| `POST` | `/api/projects` | `{ name, study_area, crs }` | `{ project_id, status }` |
| `GET` | `/api/projects/{id}` | — | `{ project_id, name, status, created_at }` |

### Processing

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| `POST` | `/api/projects/{id}/process` | `ProcessingConfig` | `{ project_id, status: "queued" }` |
| `GET` | `/api/projects/{id}/process/status` | — | `{ status, detail, updated_at }` |

### Layers

| Method | Endpoint | Response |
|---|---|---|
| `GET` | `/api/projects/{id}/layers/buildings` | GeoJSON FeatureCollection |
| `GET` | `/api/projects/{id}/layers/roads` | GeoJSON FeatureCollection |
| `GET` | `/api/projects/{id}/layers/parcels` | GeoJSON FeatureCollection |
| `GET` | `/api/projects/{id}/layers/landuse` | GeoJSON FeatureCollection |

### Analysis

| Method | Endpoint | Response |
|---|---|---|
| `GET` | `/api/projects/{id}/warnings` | `[{ warning_id, warning_type, severity, ... }]` |
| `GET` | `/api/projects/{id}/scores` | `[{ parcel_id, review_score, priority, reasons }]` |
| `GET` | `/api/projects/{id}/changes` | `[{ change_type, feature_id, geometry }]` |

### Review

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| `PUT` | `/api/projects/{id}/features/{fid}` | `FeatureUpdate` | Updated feature |
| `POST` | `/api/projects/{id}/features/{fid}/approve` | `ReviewAction` | `{ status: "approved" }` |
| `POST` | `/api/projects/{id}/features/{fid}/reject` | `ReviewAction` | `{ status: "rejected" }` |
| `POST` | `/api/projects/{id}/revalidate` | — | Updated warnings + scores |

### Export

| Method | Endpoint | Response |
|---|---|---|
| `GET` | `/api/projects/{id}/export` | ZIP file download |

---

## 17. Data Flow Diagram

```text
orthomosaic.tif ──→ validate.py ──→ preprocess.py ──→ tiles/
                                                        │
                                    ┌───────────────────┤
                                    ↓                   ↓
                            buildings.py          (road model — stretch)
                                    │
                                    ↓
                            polygonize.py ──→ buildings.geojson
                                                     │
parcels_reference.geojson ──→ preprocess.py ──→ parcels.geojson
                                                     │
roads_reference.geojson ──→ roads.py ──→ roads.geojson
                                                     │
                    ┌────────────────────────────────┤
                    ↓                                ↓
            topology.py                    change_detection.py
                    │                                │
                    ↓                                ↓
            warnings.json                    changes.json
                    │                                │
                    └──────────┬─────────────────────┘
                               ↓
                          scoring.py
                               │
                               ↓
                         scores.json
                               │
                               ↓
                     FastAPI serves all JSON/GeoJSON
                               │
                               ↓
                     Frontend consumes via HTTP
```

---

## 18. Day-by-Day Backend Schedule

| Day | Backend Tasks |
|---:|---|
| **1** | Freeze study area, acquire data, validate in QGIS, set up Python env, create `source_tracking.csv` |
| **2** | Implement `validate.py`, `preprocess.py` (tiling, CRS normalization), basic FastAPI scaffold |
| **3** | Implement `buildings.py` (model loading, tile inference, stitching), test on study area |
| **4** | Implement `polygonize.py`, `roads.py`, `landuse.py`, wire up API endpoints for layers |
| **5** | Implement `topology.py` (all checks), `scoring.py`, wire up warnings/scores endpoints |
| **6** | Implement edit/approve/reject endpoints, `audit.py`, `exports.py`, re-validation flow |
| **7** | Stretch: `change_detection.py`, `climate.py` (NDVI), integration testing |
| **8** | Feature freeze, generate fallback data, end-to-end pipeline test, backup |

---

## 19. Acceptance Criteria

### Per-Module

| Module | Acceptance |
|---|---|
| `validate.py` | Rejects files with missing CRS; accepts valid GeoTIFF |
| `preprocess.py` | Tiles reconstruct to original extent; CRS is correct |
| `buildings.py` | Output polygons align with orthomosaic; confidence values present |
| `roads.py` | Reference roads load with correct CRS and IDs |
| `landuse.py` | All pixels classified into one of the 5 classes |
| `topology.py` | Test cases with injected errors produce correct warnings |
| `change_detection.py` | IoU-based matching flags new/changed/removed buildings |
| `scoring.py` | Score is traceable — every point maps to a reason |
| `orchestrator.py` | Full pipeline runs end-to-end without crashing |
| `exports.py` | Exported GeoJSON opens in QGIS; metadata includes disclaimer |

### End-to-End

- [ ] Pipeline completes from raw GeoTIFF to scored parcels in under 5 minutes
- [ ] Fallback mode works when model inference fails
- [ ] All API endpoints return correct data
- [ ] Exported GeoJSON is valid and georeferenced
- [ ] Audit trail records all edits
