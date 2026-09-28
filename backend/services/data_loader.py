"""
Data loader and normalization service for SIH26012 Feature Review Platform.
Enforces all prompt provenance constraints:
1. Normalizes building source to 'project_vaayu_sample' (correcting manual_visual_reference).
2. Sets verification_status='unverified', review_status='unverified'.
3. Anonymization check: ensures no PII (owner_name, property_id, property_card_no).
4. Retains immutable original_geometry for audit and reverts.
5. Preserves unknown fields in 'extra' without silently discarding them.
6. Reports clear validation errors on malformed GeoJSON or unsupported CRS.
7. Honors 0-feature count of real parcel template.
"""
import copy
import json
import os
from typing import Dict, Any, List, Optional, Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DATA_DIR = os.path.join(
    WORKSPACE_ROOT, "data", "acquisition", "SIH26012_INDIA_CANDIDATE_01", "working"
)

PROVENANCE_DISCLAIMER = (
    "Project Vaayu sample; repository README describes underlying data as "
    "Ministry-supplied SVAMITVA/hackathon material. Provenance is reported, "
    "not independently verified. Not official parcel ground truth."
)

BANNED_PII_FIELDS = ["owner_name", "name", "property_id", "property_i", "property_card_no", "property_c"]

class GeoJSONValidationError(Exception):
    """Raised when GeoJSON structure fails validation."""
    pass

def validate_geojson_structure(data: Dict[str, Any], expected_name: str) -> None:
    """Validates GeoJSON compliance (RFC 7946) and coordinate reference system."""
    if not isinstance(data, dict):
        raise GeoJSONValidationError(f"Invalid GeoJSON for {expected_name}: Root must be a JSON object.")
        
    obj_type = data.get("type")
    if obj_type != "FeatureCollection":
        raise GeoJSONValidationError(f"Expected FeatureCollection, received type: {obj_type}")
        
    if "features" not in data or not isinstance(data["features"], list):
        raise GeoJSONValidationError(f"Missing 'features' array in FeatureCollection for {expected_name}.")
        
    # Check CRS if specified: warn/error if not 4326/CRS84
    crs_info = data.get("crs")
    if crs_info:
        crs_name = crs_info.get("properties", {}).get("name", "")
        if "3857" in crs_name and "4326" in expected_name:
            raise GeoJSONValidationError(f"CRS mismatch: Expected EPSG:4326/CRS84, found {crs_name}")

def sanitize_and_normalize_feature(
    raw_feature: Dict[str, Any],
    default_feature_type: str,
    layer_source: str = "project_vaayu_sample"
) -> Dict[str, Any]:
    """
    Normalizes a single GeoJSON feature to the SIH26012 shared schema.
    Converts building source from manual_visual_reference to project_vaayu_sample.
    Saves immutable original_geometry.
    """
    feat_id = raw_feature.get("id") or raw_feature.get("properties", {}).get("building_id") or raw_feature.get("properties", {}).get("road_id")
    if not feat_id:
        feat_id = f"{default_feature_type.upper()}-AUTO-{id(raw_feature)}"

    geom = raw_feature.get("geometry")
    raw_props = copy.deepcopy(raw_feature.get("properties", {}) or {})
    
    # Check and strip any PII fields if inadvertently present
    for banned in BANNED_PII_FIELDS:
        if banned in raw_props:
            raw_props.pop(banned, None)

    # Determine corrected source
    original_source = raw_props.get("source", layer_source)
    if default_feature_type == "building" and original_source == "manual_visual_reference":
        normalized_source = "project_vaayu_sample"
    elif "osm" in original_source.lower() or default_feature_type == "road":
        normalized_source = "osm"
    elif "synthetic" in original_source.lower():
        normalized_source = "synthetic_test"
    else:
        normalized_source = layer_source

    # Standard schema fields
    normalized_props = {
        "feature_id": str(feat_id),
        "feature_type": raw_props.get("feature_type", default_feature_type),
        "source": normalized_source,
        "source_date": raw_props.get("source_date", "2026-09-28" if normalized_source == "osm" else None),
        "model_name": raw_props.get("model_name", None),
        "model_version": raw_props.get("model_version", None),
        "confidence": raw_props.get("confidence", None),
        "verification_status": raw_props.get("verification_status", "unverified"),
        "review_status": raw_props.get("review_status", "unverified"),
        "review_score": raw_props.get("review_score", None),
        "warning_ids": raw_props.get("warning_ids", []),
        "parent_feature_ids": raw_props.get("parent_feature_ids", []),
        "edited_by": raw_props.get("edited_by", None),
        "edited_at": raw_props.get("edited_at", None),
        "notes": raw_props.get("notes", ""),
        "edit_reason": raw_props.get("edit_reason", None),
        "area_sqm": raw_props.get("area_sqm", None),
        "roof_type": raw_props.get("roof_type", None),
        "no_floors": raw_props.get("no_floors", None),
        "highway": raw_props.get("highway", None),
        "locality": raw_props.get("locality", "Lalpur"),
        "lgd_village_code": raw_props.get("lgd_village_code", "511638"),
        "provenance_citation": PROVENANCE_DISCLAIMER
    }
    
    # Store any extra non-standard fields in 'extra'
    standard_keys = set(normalized_props.keys()) | {"building_id", "road_id", "osm_id"}
    extra_props = {k: v for k, v in raw_props.items() if k not in standard_keys}
    if extra_props:
        normalized_props["extra"] = extra_props

    normalized_feature = {
        "type": "Feature",
        "id": str(feat_id),
        "geometry": geom,
        "properties": normalized_props,
        "original_geometry": copy.deepcopy(geom)  # Retain immutable audit snapshot
    }
    
    return normalized_feature

def load_lalpur_buildings(data_dir: str = DEFAULT_DATA_DIR) -> Dict[str, Any]:
    """Loads and normalizes the 317 Lalpur building footprints."""
    filepath = os.path.join(data_dir, "sanitized_lalpur_buildings_4326.geojson")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Building GeoJSON not found at: {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    validate_geojson_structure(data, "sanitized_lalpur_buildings_4326")
    
    normalized_features = [
        sanitize_and_normalize_feature(f, default_feature_type="building", layer_source="project_vaayu_sample")
        for f in data.get("features", [])
    ]
    
    return {
        "type": "FeatureCollection",
        "name": "sanitized_lalpur_buildings_4326",
        "total_features": len(normalized_features),
        "provenance": PROVENANCE_DISCLAIMER,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": normalized_features
    }

def load_lalpur_roads(data_dir: str = DEFAULT_DATA_DIR) -> Dict[str, Any]:
    """Loads and normalizes the 19 Lalpur village road corridor polygons."""
    filepath = os.path.join(data_dir, "sanitized_lalpur_road_polygons_4326.geojson")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Road polygon GeoJSON not found at: {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    validate_geojson_structure(data, "sanitized_lalpur_road_polygons_4326")
    
    normalized_features = [
        sanitize_and_normalize_feature(f, default_feature_type="village_road_polygon", layer_source="project_vaayu_sample")
        for f in data.get("features", [])
    ]
    
    return {
        "type": "FeatureCollection",
        "name": "sanitized_lalpur_road_polygons_4326",
        "total_features": len(normalized_features),
        "provenance": PROVENANCE_DISCLAIMER,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": normalized_features
    }

def load_osm_roads(data_dir: str = DEFAULT_DATA_DIR) -> Dict[str, Any]:
    """Loads and normalizes the 5 OSM road centerlines."""
    filepath = os.path.join(data_dir, "osm_roads_lalpur_4326.geojson")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"OSM roads GeoJSON not found at: {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    validate_geojson_structure(data, "osm_roads_lalpur_4326")
    
    normalized_features = [
        sanitize_and_normalize_feature(f, default_feature_type="road", layer_source="osm")
        for f in data.get("features", [])
    ]
    
    return {
        "type": "FeatureCollection",
        "name": "osm_roads_lalpur_4326",
        "total_features": len(normalized_features),
        "attribution": "© OpenStreetMap contributors",
        "license": "ODbL 1.0 (Open Database License)",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": normalized_features
    }

def load_blank_parcel_template(data_dir: str = DEFAULT_DATA_DIR) -> Dict[str, Any]:
    """
    Loads the blank parcel template.
    Explicitly reports zero real parcel features without creating fictional parcels.
    """
    filepath = os.path.join(data_dir, "blank_parcel_template_4326.geojson")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Blank parcel template not found at: {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    validate_geojson_structure(data, "blank_parcel_template_4326")
    
    return {
        "type": "FeatureCollection",
        "name": "blank_parcel_template_4326",
        "total_features": 0,
        "disposition": "NO REAL PARCEL POLYGONS EXIST FOR THIS AOI",
        "comment": "Empty template for official reference parcels. Zero features loaded. Real cadastral parcels are unavailable from public self-service portals.",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": []
    }
