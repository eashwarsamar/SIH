"""
Comprehensive Test Suite for SIH26012 Geospatial Feature Review Platform.
Tests all prompt-mandated finish criteria:
1. GeoJSON parsing and required schema fields.
2. Stable source/status serialization and provenance correction (project_vaayu_sample, unverified).
3. Status transitions and note persistence with reviewer attribution.
4. Edit saves while preserving immutable original_geometry and revert capability.
5. GeoJSON export and re-import round trip integrity.
6. Synthetic topology fixtures produce expected warnings (overlap, bowtie, empty, road overlap, parcel crossing).
7. Transparent review score calculation and heuristic explanation.
8. OSM attribution presence.
9. Empty real parcel layer never triggers real parcel-conflict claims.
10. Model adapter prediction success, confidence filtering, and simulated failure states.
11. Benchmark dataset manifest and evaluation harness (IoU, precision, recall, F1).
12. FastAPI HTTP endpoints end-to-end integration.
"""
import copy
import pytest
from fastapi.testclient import TestClient
import shapely.geometry

from backend.api import app
from backend.services.data_loader import (
    load_lalpur_buildings,
    load_lalpur_roads,
    load_osm_roads,
    load_blank_parcel_template,
    sanitize_and_normalize_feature,
    PROVENANCE_DISCLAIMER
)
from backend.services.feature_store import FeatureStore, store
from backend.services.topology import (
    run_full_topology_validation,
    validate_feature_geometries,
    check_polygon_overlaps,
    check_building_road_intersections,
    check_synthetic_parcel_crossings
)
from backend.services.synthetic import get_synthetic_test_features, SYNTHETIC_LAYER_DISCLAIMER
from backend.services.scoring import calculate_review_score, load_scoring_config
from backend.services.model_adapter import (
    MockBuildingModel,
    BenchmarkDatasetAdapter,
    ModelInferenceError
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def clean_store():
    """Provides an isolated, freshly initialized FeatureStore instance."""
    s = FeatureStore()
    s.initialize(force_reload=True)
    return s


@pytest.fixture
def client():
    """FastAPI TestClient instance."""
    return TestClient(app)


# ==============================================================================
# 1. GeoJSON Parsing and Required Schema Fields
# ==============================================================================

class TestGeoJSONSchemaAndDataLoading:
    def test_load_lalpur_buildings_schema(self):
        fc = load_lalpur_buildings()
        assert fc["type"] == "FeatureCollection"
        assert fc["total_features"] == 317
        assert len(fc["features"]) == 317

        for feat in fc["features"]:
            assert feat["type"] == "Feature"
            assert "id" in feat
            assert "geometry" in feat
            assert "original_geometry" in feat
            props = feat["properties"]

            # Required schema fields
            assert "feature_id" in props
            assert "feature_type" in props
            assert "source" in props
            assert "verification_status" in props
            assert "review_status" in props
            assert "warning_ids" in props
            assert "notes" in props
            assert "edited_by" in props
            assert "edited_at" in props

    def test_load_lalpur_roads(self):
        fc = load_lalpur_roads()
        assert fc["type"] == "FeatureCollection"
        assert fc["total_features"] == 19
        assert len(fc["features"]) == 19

    def test_load_osm_roads_attribution(self):
        fc = load_osm_roads()
        assert fc["type"] == "FeatureCollection"
        assert fc["total_features"] == 5
        assert "OpenStreetMap" in fc.get("attribution", "")

    def test_load_blank_parcel_template_is_zero(self):
        fc = load_blank_parcel_template()
        assert fc["type"] == "FeatureCollection"
        assert fc["total_features"] == 0
        assert len(fc["features"]) == 0
        assert "NO REAL PARCEL" in fc["disposition"]


# ==============================================================================
# 2. Stable Source and Status Serialization & Provenance Correction
# ==============================================================================

class TestProvenanceAndSanitization:
    def test_provenance_correction_project_vaayu(self):
        # Raw feature incorrectly tagged manual_visual_reference must be normalized
        raw_feat = {
            "type": "Feature",
            "id": "RAW-BLD-01",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "source": "manual_visual_reference",
                "feature_type": "building"
            }
        }
        normalized = sanitize_and_normalize_feature(raw_feat, default_feature_type="building")
        # Must be corrected to project_vaayu_sample and unverified
        assert normalized["properties"]["source"] == "project_vaayu_sample"
        assert normalized["properties"]["verification_status"] == "unverified"
        assert normalized["properties"]["review_status"] == "unverified"
        assert "Project Vaayu sample" in normalized["properties"]["provenance_citation"]

    def test_pii_sanitization_strips_sensitive_fields(self):
        raw_feat = {
            "type": "Feature",
            "id": "PII-TEST-01",
            "geometry": {"type": "Point", "coordinates": [72.75, 23.04]},
            "properties": {
                "owner_name": "Ramesh Patel",
                "property_card_no": "PC-511638-0099",
                "property_id": "PROP-1234",
                "valid_field": "keep_this"
            }
        }
        normalized = sanitize_and_normalize_feature(raw_feat, default_feature_type="building")
        props = normalized["properties"]
        assert "owner_name" not in props
        assert "property_card_no" not in props
        assert "property_id" not in props
        # Non-standard extra field preserved safely in 'extra'
        assert props.get("extra", {}).get("valid_field") == "keep_this"


# ==============================================================================
# 3. Status Transitions and Notes Persistence
# ==============================================================================

class TestFeatureStatusUpdates:
    def test_status_transitions_and_note_update(self, clean_store):
        first_bld_id = clean_store.layers["buildings"][0]["id"]

        # Initial state
        assert clean_store.layers["buildings"][0]["properties"]["review_status"] == "unverified"

        # Update to under_review
        clean_store.update_feature_status(
            feature_id=first_bld_id,
            review_status="under_review",
            notes="Initial visual check required",
            reviewer_label="reviewer-alice"
        )
        layer_name, feat = clean_store.find_feature(first_bld_id)
        assert feat["properties"]["review_status"] == "under_review"
        assert feat["properties"]["notes"] == "Initial visual check required"
        assert feat["properties"]["edited_by"] == "reviewer-alice"
        assert feat["properties"]["edited_at"] is not None

        # Update to approved
        clean_store.update_feature_status(
            feature_id=first_bld_id,
            review_status="approved",
            notes="Boundary verified against imagery",
            reviewer_label="reviewer-alice"
        )
        _, feat = clean_store.find_feature(first_bld_id)
        assert feat["properties"]["review_status"] == "approved"
        assert feat["properties"]["notes"] == "Boundary verified against imagery"

        # Update to rejected
        clean_store.update_feature_status(
            feature_id=first_bld_id,
            review_status="rejected",
            notes="False positive detection",
            reviewer_label="reviewer-bob"
        )
        _, feat = clean_store.find_feature(first_bld_id)
        assert feat["properties"]["review_status"] == "rejected"
        assert feat["properties"]["edited_by"] == "reviewer-bob"


# ==============================================================================
# 4. Geometry Edits Preserving Immutable Original Geometry & Revert
# ==============================================================================

class TestGeometryEditingAndRevert:
    def test_save_edit_preserves_original_geometry(self, clean_store):
        bld = clean_store.layers["buildings"][0]
        bld_id = bld["id"]
        original_coords = copy.deepcopy(bld["geometry"]["coordinates"])

        # Create modified coordinates
        modified_coords = [
            [[c[0] + 0.0001, c[1] + 0.0001] for c in original_coords[0]]
        ]
        new_geom = {"type": "Polygon", "coordinates": modified_coords}

        clean_store.update_feature_geometry(
            feature_id=bld_id,
            new_geometry=new_geom,
            reviewer_label="reviewer-carol",
            edit_reason="Adjusted south-east vertex"
        )

        _, updated = clean_store.find_feature(bld_id)
        assert updated["geometry"]["coordinates"] == modified_coords
        assert updated["original_geometry"]["coordinates"] == original_coords
        assert updated["properties"]["edited_by"] == "reviewer-carol"
        assert updated["properties"]["edit_reason"] == "Adjusted south-east vertex"

        # Revert geometry back to original
        clean_store.revert_feature_geometry(bld_id)
        _, reverted = clean_store.find_feature(bld_id)
        assert reverted["geometry"]["coordinates"] == original_coords
        assert "Reverted" in reverted["properties"]["edit_reason"]


# ==============================================================================
# 5. Export and Re-Import Round Trip
# ==============================================================================

class TestExportImportRoundTrip:
    def test_export_and_import_integrity(self, clean_store):
        bundle = clean_store.export_reviewed_bundle()
        assert bundle["type"] == "FeatureCollection"
        assert "export_metadata" in bundle
        assert bundle["export_metadata"]["target_crs"] == "EPSG:4326 (WGS 84 / RFC 7946)"
        assert len(bundle["features"]) == 349  # 317 bld + 19 rd + 5 osm + 8 synth

        # Fresh store instance imports the bundle
        new_store = FeatureStore()
        result = new_store.import_reviewed_bundle(bundle)
        assert result["status"] == "success"
        assert result["imported_count"] == 349
        assert len(new_store.layers["buildings"]) == 317
        assert len(new_store.layers["roads"]) == 19
        assert len(new_store.layers["synthetic"]) == 8


# ==============================================================================
# 6. Synthetic Topology Fixtures and Expected Warnings
# ==============================================================================

class TestTopologyWarnings:
    def test_synthetic_fixtures_produce_all_expected_warnings(self, clean_store):
        synth_warnings = [w for w in clean_store.warnings if "synthetic" in w.source]
        types_found = {w.warning_type for w in synth_warnings}

        # 1. Overlapping polygons
        assert "overlapping_polygons" in types_found
        overlap_warn = next(w for w in synth_warnings if w.warning_type == "overlapping_polygons")
        assert "SYN-BLD-OVERLAP-1" in overlap_warn.feature_ids
        assert "SYN-BLD-OVERLAP-2" in overlap_warn.feature_ids

        # 2. Invalid geometry (bowtie / self-intersecting)
        assert "invalid_geometry" in types_found
        inv_warn = next(w for w in synth_warnings if w.warning_type == "invalid_geometry")
        assert "SYN-INVALID-GEOM-1" in inv_warn.feature_ids
        assert "Self-intersection" in inv_warn.explanation

        # 2b. Empty geometry
        assert "empty_geometry" in types_found
        empty_warn = next(w for w in synth_warnings if w.warning_type == "empty_geometry")
        assert "SYN-EMPTY-GEOM-1" in empty_warn.feature_ids

        # 3. Synthetic building intersecting synthetic road corridor
        assert "building_road_spatial_overlap" in types_found
        road_warn = next(w for w in synth_warnings if w.warning_type == "building_road_spatial_overlap")
        assert "SYN-BLD-ROAD-INT-1" in road_warn.feature_ids
        assert "SYN-ROAD-CORRIDOR-1" in road_warn.feature_ids

        # 4. Synthetic building crossing synthetic parcel
        assert "building_crosses_synthetic_parcel" in types_found
        parcel_warn = next(w for w in synth_warnings if w.warning_type == "building_crosses_synthetic_parcel")
        assert "SYN-BLD-PARCEL-CROSS-1" in parcel_warn.feature_ids
        assert "SYN-PARCEL-DEMO-1" in parcel_warn.feature_ids

    def test_empty_real_parcel_layer_never_produces_real_parcel_warnings(self, clean_store):
        real_parcel_warnings = [
            w for w in clean_store.warnings
            if "parcel" in w.warning_type and "synthetic" not in w.warning_type
        ]
        assert len(real_parcel_warnings) == 0, (
            "Violated rule: real parcel conflict warning produced when real parcels are empty!"
        )


# ==============================================================================
# 7. Review Score Calculation and Breakdown
# ==============================================================================

class TestScoringEngine:
    def test_score_calculation_breakdown_and_disclaimer(self):
        sample_feat = {
            "type": "Feature",
            "id": "TEST-SCORE-01",
            "properties": {
                "feature_id": "TEST-SCORE-01",
                "feature_type": "building",
                "source": "project_vaayu_sample",
                "review_status": "unverified",
                "area_sqm": 850.0  # triggers extreme dimensions rule (> 600m)
            }
        }
        breakdown = calculate_review_score(
            sample_feat,
            associated_warning_ids=["W-OVERLAP-01"]
        )

        assert breakdown.feature_id == "TEST-SCORE-01"
        assert 0 <= breakdown.total_score <= 100
        assert "prototype heuristic—not a validated survey-priority model" in breakdown.heuristic_disclaimer

        triggered_rule_ids = {r.rule_id for r in breakdown.rules_triggered}
        assert "R_UNVERIFIED_SOURCE" in triggered_rule_ids
        assert "R_SPATIAL_OVERLAP_WARNING" in triggered_rule_ids
        assert "R_EXTREME_DIMENSIONS" in triggered_rule_ids
        assert breakdown.priority in ["medium", "high"]

    def test_approved_feature_score_reduction(self):
        sample_feat = {
            "type": "Feature",
            "id": "TEST-SCORE-APPROVED",
            "properties": {
                "feature_id": "TEST-SCORE-APPROVED",
                "feature_type": "building",
                "source": "project_vaayu_sample",
                "review_status": "approved",
                "area_sqm": 120.0
            }
        }
        breakdown = calculate_review_score(sample_feat, associated_warning_ids=[])
        triggered_rule_ids = {r.rule_id for r in breakdown.rules_triggered}
        assert "R_HUMAN_APPROVED" in triggered_rule_ids
        assert breakdown.total_score == 0  # 10 base + 20 unverified - 30 approved = 0


# ==============================================================================
# 8. Building Model Interface and Benchmark Evaluation Harness
# ==============================================================================

class TestBuildingModelAndBenchmarkHarness:
    def test_mock_building_model_prediction_success(self):
        model = MockBuildingModel()
        result = model.predict(confidence_threshold=0.70, simulate_failure=False)
        assert result["type"] == "FeatureCollection"
        assert result["model_metadata"]["inference_status"] == "success"
        # Only features with confidence >= 0.70
        for feat in result["features"]:
            assert feat["properties"]["source"] == "ai_building_model"
            assert feat["properties"]["confidence"] >= 0.70

    def test_mock_building_model_failure_simulation(self):
        model = MockBuildingModel()
        with pytest.raises(ModelInferenceError) as exc_info:
            model.predict(simulate_failure=True)
        assert "Simulated Model Failure" in str(exc_info.value)

    def test_benchmark_manifest_status_pending(self):
        manifest = BenchmarkDatasetAdapter.get_dataset_manifest()
        datasets = manifest["registered_datasets"]
        assert "inria_aerial_image_labeling" in datasets
        assert "spacenet_2_buildings" in datasets
        assert datasets["inria_aerial_image_labeling"]["status"] == "PENDING_ACQUISITION"
        assert "PENDING_ACQUISITION" in manifest["disclaimer"]

    def test_polygon_evaluation_metrics_iou_and_f1(self):
        # Two identical squares: IoU = 1.0
        p1 = shapely.geometry.box(0, 0, 10, 10)
        p2 = shapely.geometry.box(0, 0, 10, 10)
        iou = BenchmarkDatasetAdapter.compute_polygon_iou(p1, p2)
        assert iou == 1.0

        # Disjoint squares: IoU = 0.0
        p3 = shapely.geometry.box(20, 20, 30, 30)
        assert BenchmarkDatasetAdapter.compute_polygon_iou(p1, p3) == 0.0

        # Evaluation harness metric calculation
        gt = [p1, p3]
        pred = [p2]  # p2 matches p1, p3 missed (1 TP, 0 FP, 1 FN)
        metrics = BenchmarkDatasetAdapter.evaluate_detections(gt, pred, iou_threshold=0.5)
        assert metrics["true_positives"] == 1
        assert metrics["false_positives"] == 0
        assert metrics["false_negatives"] == 1
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 0.5
        assert round(metrics["f1_score"], 4) == 0.6667


# ==============================================================================
# 9. FastAPI API Endpoints Integration
# ==============================================================================

class TestApiEndpoints:
    def test_api_health(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "online"
        assert data["layers_loaded"]["buildings"] == 317

    def test_api_metadata_osm_and_disclaimer(self, client):
        res = client.get("/api/metadata")
        assert res.status_code == 200
        data = res.json()
        assert "OpenStreetMap" in data["osm_attribution"]
        assert "Project Vaayu sample" in data["provenance_disclaimer"]
        assert "UNAVAILABLE_DIRECT_ECW" in data["raster_orthomosaic_status"]["browser_service_status"]

    def test_api_get_layers(self, client):
        for layer_name in ["buildings", "roads", "osm_roads", "parcels", "synthetic"]:
            res = client.get(f"/api/layers/{layer_name}")
            assert res.status_code == 200
            data = res.json()
            assert data["type"] == "FeatureCollection"

    def test_api_update_feature_status(self, client):
        # Pick first building
        res_list = client.get("/api/layers/buildings")
        bld_id = res_list.json()["features"][0]["id"]

        update_payload = {
            "review_status": "under_review",
            "notes": "FastAPI integration test note",
            "reviewer_label": "api-tester"
        }
        res = client.put(f"/api/features/{bld_id}", json=update_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["feature"]["properties"]["review_status"] == "under_review"
        assert data["feature"]["properties"]["notes"] == "FastAPI integration test note"

    def test_api_model_predict_endpoint(self, client):
        req = {
            "model_name": "Vaayu-UnetPP-Lite",
            "model_version": "0.1.0-mock",
            "confidence_threshold": 0.6,
            "simulate_failure": False
        }
        res = client.post("/api/models/predict", json=req)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["detected_count"] > 0

    def test_api_model_predict_failure_simulation(self, client):
        req = {
            "model_name": "Vaayu-UnetPP-Lite",
            "model_version": "0.1.0-mock",
            "simulate_failure": True
        }
        res = client.post("/api/models/predict", json=req)
        assert res.status_code == 500
        assert "Simulated Model Failure" in res.json()["detail"]

    def test_api_export_and_import(self, client):
        # Export
        exp_res = client.get("/api/export")
        assert exp_res.status_code == 200
        bundle = exp_res.json()
        assert bundle["type"] == "FeatureCollection"

        # Import
        imp_res = client.post("/api/import", json=bundle)
        assert imp_res.status_code == 200
        imp_data = imp_res.json()
        assert imp_data["status"] == "success"
        assert imp_data["imported_count"] == len(bundle["features"])
