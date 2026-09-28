"""
FastAPI Application and REST API for SIH26012 Feature Review Platform.
Provides endpoints for layers, inspection, human edits, topology warnings,
transparent scoring, model inference stub, benchmark status, and GeoJSON export/import.
"""
import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, status, Query, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from backend.services.feature_store import store
from backend.services.data_loader import PROVENANCE_DISCLAIMER
from backend.services.raster_service import raster_tile_service
from backend.services.model_adapter import MockBuildingModel, BenchmarkDatasetAdapter, ModelInferenceError
from backend.services.scoring import aggregate_parcel_scores
from backend.models.schemas import (
    GeometryEditRequest,
    FeatureStatusUpdateRequest,
    DraftFeatureCreateRequest,
    ModelPredictRequest
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.initialize()
    yield

app = FastAPI(
    title="SIH26012 Feature Review Platform API",
    description="Geospatial feature-review and topology inspection platform for Lalpur study area.",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/health")
def get_health():
    """Health check and active layer status."""
    store.initialize()
    return {
        "status": "online",
        "study_area": "Lalpur Village, Gujarat (LGD 511638)",
        "layers_loaded": {k: len(v) for k, v in store.layers.items()},
        "total_warnings": len(store.warnings)
    }

@app.get("/api/metadata")
def get_metadata():
    """System metadata, study area bounds, CRS, and provenance notices."""
    return {
        "aoi_id": "SIH26012_INDIA_CANDIDATE_01_LALPUR",
        "locality": "Lalpur Village, Gujarat, India (LGD Code: 511638)",
        "bounds_epsg_4326": {
            "lon_min": 72.754522,
            "lat_min": 23.037534,
            "lon_max": 72.760638,
            "lat_max": 23.043371,
            "centroid": [72.757580, 23.040453]
        },
        "coordinate_systems": {
            "web_map_input": "EPSG:4326 (WGS 84 / RFC 7946)",
            "native_raster_crs": "EPSG:3857 (Web Mercator)"
        },
        "raster_orthomosaic_status": {
            "filename": "lalpur_orthomosaic.tif",
            "format": "GeoTIFF (4 bands, uint8, EPSG:3857, 20,137 x 20,886 px, 3.38 cm GSD)",
            "bounds_epsg_3857": [8098996.3782, 2636558.4073, 8099677.1552, 2637264.506],
            "file_size_bytes": 1682493007,
            "browser_service_status": "AVAILABLE_LOCAL_XYZ_TILES" if raster_tile_service.is_available else "UNAVAILABLE",
            "tile_url": "/api/raster/tiles/{z}/{x}/{y}.png",
            "min_zoom": 14,
            "max_zoom": 21,
            "details": raster_tile_service.metadata
        },
        "provenance_disclaimer": PROVENANCE_DISCLAIMER,
        "cadastral_notice": (
            "This application is a feature-review prototype and is NOT an official cadastral system. "
            "Building footprints are unverified physical envelopes, not cadastral parcels. "
            "No official parcel ground truth exists for this AOI (parcel template has 0 features)."
        ),
        "osm_attribution": "© OpenStreetMap contributors (ODbL 1.0)"
    }

@app.get("/api/raster/status")
def get_raster_status():
    """Returns technical metadata and availability of the local GeoTIFF orthomosaic."""
    return {
        "status": "ready" if raster_tile_service.is_available else "unavailable",
        "metadata": raster_tile_service.metadata,
        "tile_template": "/api/raster/tiles/{z}/{x}/{y}.png"
    }

@app.get("/api/raster/tiles/{z}/{x}/{y}.png")
def get_raster_tile(z: int, x: int, y: int):
    """Dynamically serves 256x256 Web Mercator PNG tile extracted from local GeoTIFF."""
    tile_bytes = raster_tile_service.get_tile_png(z, x, y)
    return Response(
        content=tile_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"}
    )

@app.get("/api/layers/{layer_name}")
def get_layer(layer_name: str):
    """Returns GeoJSON FeatureCollection for specified layer."""
    try:
        return store.get_layer_collection(layer_name)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer '{layer_name}' not found. Available layers: {list(store.layers.keys())}"
        )

@app.get("/api/warnings")
def get_warnings():
    """Returns list of all active topology warnings."""
    store.initialize()
    return {
        "total_warnings": len(store.warnings),
        "synthetic_warning_count": sum(1 for w in store.warnings if "synthetic" in w.source),
        "real_warning_count": sum(1 for w in store.warnings if "synthetic" not in w.source),
        "warnings": store.warnings
    }

@app.get("/api/scores")
def get_scores():
    """Returns review-priority scores for all loaded features."""
    store.initialize()
    return {
        "total_scored_features": len(store.scores),
        "heuristic_disclaimer": "prototype heuristic—not a validated survey-priority model",
        "scores": store.scores
    }

@app.get("/api/features/{feature_id}")
def get_feature_details(feature_id: str):
    """Retrieves full details, audit trail, warnings, and score breakdown for a single feature."""
    found = store.find_feature(feature_id)
    if not found:
        raise HTTPException(status_code=404, detail=f"Feature with ID '{feature_id}' not found.")

    layer_name, feat = found
    score_bd = store.scores.get(feature_id)
    w_ids = feat.get("properties", {}).get("warning_ids", [])
    relevant_warnings = [w for w in store.warnings if w.warning_id in w_ids]

    has_geometry_edits = False
    if feat.get("original_geometry") and feat.get("original_geometry") != feat.get("geometry"):
        has_geometry_edits = True

    return {
        "feature": feat,
        "layer": layer_name,
        "score_breakdown": score_bd,
        "associated_warnings": relevant_warnings,
        "has_geometry_edits": has_geometry_edits
    }

@app.put("/api/features/{feature_id}")
def update_feature(feature_id: str, req: FeatureStatusUpdateRequest):
    """Updates review status (under_review, approved, rejected) and inspector notes."""
    try:
        updated = store.update_feature_status(
            feature_id=feature_id,
            review_status=req.review_status,
            notes=req.notes,
            reviewer_label=req.reviewer_label
        )
        return {
            "status": "success",
            "feature": updated,
            "score": store.scores.get(feature_id)
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/features/{feature_id}/edit-geometry")
def edit_geometry(feature_id: str, req: GeometryEditRequest):
    """Saves human geometry edits while preserving original_geometry audit snapshot."""
    try:
        updated = store.update_feature_geometry(
            feature_id=feature_id,
            new_geometry=req.geometry.model_dump(),
            reviewer_label=req.reviewer_label,
            edit_reason=req.edit_reason
        )
        return {
            "status": "success",
            "message": "Geometry updated; original geometry preserved in audit snapshot.",
            "feature": updated
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/features/{feature_id}/revert")
def revert_geometry(feature_id: str):
    """Reverts a feature's geometry back to its original unedited geometry."""
    try:
        reverted = store.revert_feature_geometry(feature_id)
        return {
            "status": "success",
            "message": "Geometry reverted to original baseline.",
            "feature": reverted
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/features/draft")
def create_draft(req: DraftFeatureCreateRequest):
    """Adds a newly drawn draft feature (tagged manual_visual_reference)."""
    draft = store.add_draft_feature(
        geometry=req.geometry.model_dump(),
        feature_type=req.feature_type,
        notes=req.notes,
        reviewer_label=req.reviewer_label
    )
    return {"status": "success", "feature": draft}

@app.post("/api/models/predict")
def predict_building_model(req: ModelPredictRequest):
    """Triggers building model inference mock provider."""
    model = MockBuildingModel(model_name=req.model_name, model_version=req.model_version)
    try:
        result = model.predict(
            confidence_threshold=req.confidence_threshold,
            simulate_failure=req.simulate_failure
        )
        # Add generated features to active store
        added_features = store.add_ai_predicted_features(result["features"])
        return {
            "status": "success",
            "detected_count": len(added_features),
            "features": added_features,
            "metadata": result.get("model_metadata")
        }
    except ModelInferenceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/models/benchmarks")
def get_benchmarks():
    """Returns official benchmark datasets manifest and evaluation status."""
    return BenchmarkDatasetAdapter.get_dataset_manifest()

@app.get("/api/export")
def export_bundle():
    """Exports all reviewed features into a single RFC 7946 GeoJSON bundle."""
    bundle = store.export_reviewed_bundle()
    return JSONResponse(
        content=bundle,
        headers={"Content-Disposition": "attachment; filename=SIH26012_Lalpur_Reviewed_Features.geojson"}
    )

@app.post("/api/import")
def import_bundle(bundle: Dict[str, Any] = Body(...)):
    """Imports and validates an exported GeoJSON bundle."""
    try:
        res = store.import_reviewed_bundle(bundle)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/parcels/rag")
def get_parcel_rag():
    """
    Returns Red/Amber/Green parcel aggregation status.
    When real parcel layer is empty (0 features), reports 'not_evaluated'.
    When synthetic parcels present, aggregates with 'synthetic' badge.
    """
    store.initialize()
    real_parcels = store.layers["parcels"]
    synthetic_feats = store.layers["synthetic"]
    synth_parcels = [f for f in synthetic_feats if f.get("properties", {}).get("feature_type") == "synthetic_parcel"]

    if len(real_parcels) == 0:
        real_parcel_status = {
            "status": "not_evaluated",
            "reason": "No real parcel polygons loaded for this AOI. "
                      "Official cadastral parcel data is not available for Lalpur (LGD 511638). "
                      "Use QGIS to digitize a manual_visual_reference layer and import it to enable parcel evaluation.",
            "real_parcel_count": 0,
            "disclaimer": "This status is NOT equivalent to 'zero conflicts'. "
                          "It means evaluation was not performed due to absent reference data."
        }
    else:
        real_parcel_status = {"status": "real_parcels_present", "real_parcel_count": len(real_parcels)}

    # Synthetic RAG for demo
    synth_rag_results = []
    for parcel in synth_parcels:
        pid = parcel.get("id") or parcel.get("properties", {}).get("feature_id")
        parcel_warnings = [w.warning_id for w in store.warnings if pid in w.feature_ids]
        intersecting_blds = [f for f in synthetic_feats if f.get("properties", {}).get("feature_type") == "synthetic_building"]
        rag = aggregate_parcel_scores(parcel, intersecting_blds, [], parcel_warnings)
        synth_rag_results.append(rag)

    return {
        "real_parcel_evaluation": real_parcel_status,
        "synthetic_parcel_rag": {
            "disclaimer": "Synthetic test data — not real parcels. Demo only.",
            "parcel_count": len(synth_rag_results),
            "results": synth_rag_results
        },
        "heuristic_disclaimer": "prototype heuristic—not a validated survey-priority model"
    }


@app.get("/api/models/discrepancy")
def get_model_reference_discrepancy():
    """
    Model vs Reference Discrepancy Comparator.
    Compares AI-predicted building footprints against the 317 Vaayu reference footprints
    using spatial IoU matching within the same area. NOT temporal change detection.
    The reference footprints are not an 'old' layer — they are same-area annotations.
    """
    store.initialize()
    ai_preds = store.layers["ai_predictions"]
    reference = store.layers["buildings"]

    if not ai_preds:
        return {
            "status": "no_predictions",
            "message": "No AI model predictions loaded. Run model inference first via POST /api/models/predict.",
            "disclaimer": "This comparator shows same-area AI-vs-reference disagreement. "
                          "It is NOT temporal change detection. Reference features are unverified annotations."
        }

    import shapely.geometry
    from backend.services.model_adapter import BenchmarkDatasetAdapter

    def parse_shape(feat):
        geom = feat.get("geometry")
        if not geom:
            return None
        try:
            s = shapely.geometry.shape(geom)
            return s if s.is_valid else None
        except Exception:
            return None

    ref_shapes = [(f["id"], parse_shape(f)) for f in reference]
    ref_shapes = [(fid, s) for fid, s in ref_shapes if s]
    pred_shapes = [(f["id"], parse_shape(f)) for f in ai_preds]
    pred_shapes = [(fid, s) for fid, s in pred_shapes if s]

    iou_threshold = 0.35
    matched_ref = set()
    matched_pred = set()
    matched_pairs = []

    for pid, ps in pred_shapes:
        best_iou = 0.0
        best_rid = None
        for rid, rs in ref_shapes:
            if rid in matched_ref:
                continue
            iou = BenchmarkDatasetAdapter.compute_polygon_iou(rs, ps)
            if iou > best_iou:
                best_iou = iou
                best_rid = rid
        if best_iou >= iou_threshold and best_rid:
            matched_ref.add(best_rid)
            matched_pred.add(pid)
            matched_pairs.append({"ai_id": pid, "ref_id": best_rid, "iou": round(best_iou, 4)})

    model_only = [pid for pid, _ in pred_shapes if pid not in matched_pred]
    ref_only = [rid for rid, _ in ref_shapes if rid not in matched_ref]

    tp = len(matched_pred)
    fp = len(model_only)
    fn = len(ref_only)
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round((2 * precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    return {
        "status": "discrepancies_computed",
        "comparator_nature": "Same-area spatial disagreement check (NOT temporal change detection)",
        "disclaimer": "Model vs Reference Discrepancy: same-area AI-vs-annotation disagreement check. "
                      "NOT temporal change detection. 317 reference footprints are unverified visual annotations "
                      "(Project Vaayu sample, not ground truth). This is a prototype heuristic.",
        "iou_matching_threshold": iou_threshold,
        "metrics": {
            "matched_pairs_count": len(matched_pairs),
            "model_only_detections": len(model_only),
            "reference_only_footprints": len(ref_only),
            "precision": precision,
            "recall": recall,
            "f1_score": f1
        },
        "total_reference_features": len(ref_shapes),
        "total_ai_predictions": len(pred_shapes),
        "matched_pairs": matched_pairs[:20],
        "model_only_features": model_only[:20],
        "reference_only_features": ref_only[:20],
        "interpretation": {
            "matched": "AI and reference overlap at IoU >= threshold — spatial agreement",
            "model_only": "AI detected footprint not found in reference — possible false positive or unmapped building",
            "ref_only": "Reference footprint not found in AI predictions — possible missed detection"
        }
    }


# Mount static frontend files if folder exists
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
