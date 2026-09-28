"""
Feature Store and State Manager for SIH26012 Feature Review Platform.
Maintains in-memory layer collections, handles human edits with immutable original_geometry,
dynamic re-calculation of topology warnings, and review-priority scoring.
"""
import copy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.services.data_loader import (
    load_lalpur_buildings,
    load_lalpur_roads,
    load_osm_roads,
    load_blank_parcel_template,
    PROVENANCE_DISCLAIMER
)
from backend.services.synthetic import get_synthetic_test_features, SYNTHETIC_LAYER_NAME, SYNTHETIC_LAYER_DISCLAIMER
from backend.services.topology import run_full_topology_validation
from backend.services.scoring import calculate_review_score
from backend.models.schemas import TopologyWarning, ReviewScoreBreakdown

class FeatureStore:
    """Central state manager for the local prototype."""
    
    def __init__(self):
        self.layers: Dict[str, List[Dict[str, Any]]] = {
            "buildings": [],
            "roads": [],
            "osm_roads": [],
            "parcels": [],
            "synthetic": [],
            "drafts": [],
            "ai_predictions": []
        }
        self.warnings: List[TopologyWarning] = []
        self.scores: Dict[str, ReviewScoreBreakdown] = {}
        self.is_initialized = False

    def initialize(self, force_reload: bool = False) -> None:
        """Loads all reference layers, synthetic test fixtures, runs initial topology checks and scoring."""
        if self.is_initialized and not force_reload:
            return

        # Load GeoJSON files
        bld_col = load_lalpur_buildings()
        self.layers["buildings"] = bld_col["features"]

        rd_col = load_lalpur_roads()
        self.layers["roads"] = rd_col["features"]

        osm_col = load_osm_roads()
        self.layers["osm_roads"] = osm_col["features"]

        parcel_col = load_blank_parcel_template()
        self.layers["parcels"] = parcel_col["features"]  # 0 features

        # Load synthetic test fixtures
        self.layers["synthetic"] = get_synthetic_test_features()

        self.revalidate_all()
        self.is_initialized = True

    def revalidate_all(self) -> None:
        """Runs topology validation and recalculates scores across all active features."""
        all_buildings = self.layers["buildings"] + self.layers["ai_predictions"]
        
        self.warnings = run_full_topology_validation(
            buildings=all_buildings,
            roads=self.layers["roads"],
            real_parcels=self.layers["parcels"],
            synthetic_features=self.layers["synthetic"]
        )

        # Build feature_id -> list of warning_ids mapping
        feat_warnings_map: Dict[str, List[str]] = {}
        for w in self.warnings:
            for fid in w.feature_ids:
                if fid not in feat_warnings_map:
                    feat_warnings_map[fid] = []
                feat_warnings_map[fid].append(w.warning_id)

        # Calculate scores for all features in layers
        self.scores.clear()
        for layer_name, feature_list in self.layers.items():
            for feat in feature_list:
                fid = feat["id"]
                w_ids = feat_warnings_map.get(fid, [])
                feat["properties"]["warning_ids"] = w_ids
                
                score_breakdown = calculate_review_score(feat, associated_warning_ids=w_ids)
                self.scores[fid] = score_breakdown
                feat["properties"]["review_score"] = score_breakdown.total_score

    def get_layer_collection(self, layer_name: str) -> Dict[str, Any]:
        """Returns GeoJSON FeatureCollection representation for the requested layer."""
        self.initialize()
        if layer_name not in self.layers:
            raise KeyError(f"Unknown layer: {layer_name}")

        features = self.layers[layer_name]
        
        metadata: Dict[str, Any] = {
            "total_features": len(features),
            "crs": "EPSG:4326 (WGS 84 / RFC 7946)"
        }

        if layer_name == "buildings":
            name = "sanitized_lalpur_buildings_4326"
            metadata["provenance"] = PROVENANCE_DISCLAIMER
            metadata["verification_status"] = "unverified"
        elif layer_name == "roads":
            name = "sanitized_lalpur_road_polygons_4326"
            metadata["provenance"] = PROVENANCE_DISCLAIMER
        elif layer_name == "osm_roads":
            name = "osm_roads_lalpur_4326"
            metadata["attribution"] = "© OpenStreetMap contributors"
            metadata["license"] = "ODbL 1.0"
        elif layer_name == "parcels":
            name = "blank_parcel_template_4326"
            metadata["disposition"] = "NO REAL PARCEL POLYGONS EXIST FOR THIS AOI"
            metadata["comment"] = "Zero features. Empty schema template."
        elif layer_name == "synthetic":
            name = SYNTHETIC_LAYER_NAME
            metadata["disclaimer"] = SYNTHETIC_LAYER_DISCLAIMER
            metadata["source"] = "synthetic_test"
        elif layer_name == "drafts":
            name = "user_review_drafts"
            metadata["source"] = "manual_visual_reference"
        elif layer_name == "ai_predictions":
            name = "ai_predicted_features"
            metadata["source"] = "ai_building_model"
        else:
            name = layer_name

        return {
            "type": "FeatureCollection",
            "name": name,
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "total_features": len(features),
            "metadata": metadata,
            "features": features
        }

    def find_feature(self, feature_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Finds a feature across all layers by ID. Returns (layer_name, feature_dict)."""
        self.initialize()
        for layer_name, feature_list in self.layers.items():
            for feat in feature_list:
                if feat.get("id") == feature_id:
                    return layer_name, feat
        return None

    def update_feature_status(
        self,
        feature_id: str,
        review_status: str,
        notes: Optional[str] = None,
        reviewer_label: str = "demo-reviewer"
    ) -> Dict[str, Any]:
        """Updates feature review status, notes, and reviewer audit fields."""
        found = self.find_feature(feature_id)
        if not found:
            raise KeyError(f"Feature not found: {feature_id}")

        layer_name, feat = found
        props = feat["properties"]
        props["review_status"] = review_status
        props["edited_by"] = reviewer_label
        props["edited_at"] = datetime.now(timezone.utc).isoformat()
        if notes is not None:
            props["notes"] = notes

        # Recompute score for this feature
        w_ids = props.get("warning_ids", [])
        score_bd = calculate_review_score(feat, associated_warning_ids=w_ids)
        self.scores[feature_id] = score_bd
        props["review_score"] = score_bd.total_score

        return feat

    def update_feature_geometry(
        self,
        feature_id: str,
        new_geometry: Dict[str, Any],
        reviewer_label: str = "demo-reviewer",
        edit_reason: str = "Boundary adjustment"
    ) -> Dict[str, Any]:
        """
        Updates geometry while preserving original_geometry immutable audit copy.
        Updates edited_by, edited_at, and edit_reason.
        """
        found = self.find_feature(feature_id)
        if not found:
            raise KeyError(f"Feature not found: {feature_id}")

        layer_name, feat = found
        # Retain original geometry if not already set
        if "original_geometry" not in feat or feat["original_geometry"] is None:
            feat["original_geometry"] = copy.deepcopy(feat["geometry"])

        feat["geometry"] = new_geometry
        props = feat["properties"]
        props["edited_by"] = reviewer_label
        props["edited_at"] = datetime.now(timezone.utc).isoformat()
        props["edit_reason"] = edit_reason

        # Re-run validation because geometry changed
        self.revalidate_all()
        return feat

    def revert_feature_geometry(self, feature_id: str) -> Dict[str, Any]:
        """Reverts feature geometry back to original_geometry snapshot."""
        found = self.find_feature(feature_id)
        if not found:
            raise KeyError(f"Feature not found: {feature_id}")

        layer_name, feat = found
        if "original_geometry" in feat and feat["original_geometry"] is not None:
            feat["geometry"] = copy.deepcopy(feat["original_geometry"])
            feat["properties"]["edit_reason"] = "Reverted to initial unedited geometry"
            feat["properties"]["edited_at"] = datetime.now(timezone.utc).isoformat()
            self.revalidate_all()

        return feat

    def add_draft_feature(
        self,
        geometry: Dict[str, Any],
        feature_type: str = "draft_polygon",
        notes: str = "Manual draft reference",
        reviewer_label: str = "demo-reviewer"
    ) -> Dict[str, Any]:
        """Creates a human-digitized review draft feature (tagged manual_visual_reference)."""
        self.initialize()
        draft_count = len(self.layers["drafts"]) + 1
        draft_id = f"DRAFT-{draft_count:03d}"

        new_feat = {
            "type": "Feature",
            "id": draft_id,
            "geometry": geometry,
            "properties": {
                "feature_id": draft_id,
                "feature_type": feature_type,
                "source": "manual_visual_reference",
                "source_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "verification_status": "unverified",
                "review_status": "under_review",
                "notes": notes,
                "edited_by": reviewer_label,
                "edited_at": datetime.now(timezone.utc).isoformat(),
                "locality": "Lalpur",
                "provenance_citation": "Manual human visual trace created in local reviewer UI."
            },
            "original_geometry": copy.deepcopy(geometry)
        }

        self.layers["drafts"].append(new_feat)
        self.revalidate_all()
        return new_feat

    def add_ai_predicted_features(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Appends features produced by AI Building Model inference adapter."""
        self.initialize()
        added = []
        for feat in features:
            f_copy = copy.deepcopy(feat)
            if "original_geometry" not in f_copy:
                f_copy["original_geometry"] = copy.deepcopy(f_copy.get("geometry"))
            self.layers["ai_predictions"].append(f_copy)
            added.append(f_copy)
            
        self.revalidate_all()
        return added

    def export_reviewed_bundle(self) -> Dict[str, Any]:
        """
        Exports all reviewed and active features into a single RFC 7946 GeoJSON bundle
        with audit trail, metadata, and transparent provenance citations.
        """
        self.initialize()
        all_features = []
        for layer_name in ["buildings", "roads", "osm_roads", "synthetic", "drafts", "ai_predictions"]:
            for feat in self.layers[layer_name]:
                f_export = copy.deepcopy(feat)
                f_export["properties"]["layer"] = layer_name
                all_features.append(f_export)

        now_iso = datetime.now(timezone.utc).isoformat()
        bundle = {
            "type": "FeatureCollection",
            "name": "SIH26012_Reviewed_Features_Export",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "export_metadata": {
                "exported_at": now_iso,
                "project_id": "SIH26012_INDIA_CANDIDATE_01_LALPUR",
                "locality": "Lalpur Village, Gujarat (LGD 511638)",
                "target_crs": "EPSG:4326 (WGS 84 / RFC 7946)",
                "native_analysis_crs": "EPSG:3857 (Web Mercator)",
                "provenance_disclaimer": PROVENANCE_DISCLAIMER,
                "total_features": len(all_features),
                "open_warnings_count": len(self.warnings),
                "cadastral_status": "PROTOTYPE ONLY. Zero real cadastral parcels exist. Not official parcel ground truth."
            },
            "features": all_features
        }
        return bundle

    def import_reviewed_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Imports and restores features from a previously exported GeoJSON bundle."""
        if not isinstance(bundle, dict) or bundle.get("type") != "FeatureCollection":
            raise ValueError("Import payload must be a valid GeoJSON FeatureCollection.")

        imported_features = bundle.get("features", [])
        if not isinstance(imported_features, list):
            raise ValueError("Malformed GeoJSON: missing features list.")

        # Group by layer
        layer_buckets: Dict[str, List[Dict[str, Any]]] = {
            "buildings": [],
            "roads": [],
            "osm_roads": [],
            "parcels": [],
            "synthetic": [],
            "drafts": [],
            "ai_predictions": []
        }

        for feat in imported_features:
            props = feat.get("properties", {})
            layer = props.get("layer", "buildings")
            if layer not in layer_buckets:
                layer = "buildings"
            layer_buckets[layer].append(feat)

        # Update layers
        for layer, feats in layer_buckets.items():
            if feats:
                self.layers[layer] = feats

        self.revalidate_all()
        return {
            "status": "success",
            "imported_count": len(imported_features),
            "layers_updated": [k for k, v in layer_buckets.items() if v]
        }

# Global singleton instance
store = FeatureStore()
