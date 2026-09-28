"""
Deterministic Topology Validation Engine using Shapely.
Detects:
1. Invalid / empty / self-intersecting geometry (safe handling)
2. Overlapping polygons within a layer
3. Building-road spatial intersections (neutral wording)
4. Synthetic building crossing synthetic parcel polygon
5. Enforces strictly: NO real parcel conflict warnings when real parcel layer has 0 features.
"""
from typing import Dict, Any, List, Optional
import shapely.geometry
from shapely.validation import explain_validity
from backend.models.schemas import TopologyWarning

NEUTRAL_ROAD_OVERLAP_EXPLANATION = (
    "Spatial overlap detected between building {bld_id} and road corridor {road_id}—review visually. "
    "Road corridors and centerlines are spatial references, not legal rights-of-way."
)

SYNTHETIC_ROAD_OVERLAP_EXPLANATION = (
    "Demonstration Warning: Spatial overlap detected between synthetic building {bld_id} "
    "and synthetic road corridor {road_id}—review visually."
)

SYNTHETIC_PARCEL_CROSSING_EXPLANATION = (
    "Demonstration Warning: Synthetic building footprint {bld_id} crosses boundary of synthetic parcel {parcel_id}. "
    "This is a demonstration fixture; real Lalpur parcel dataset is 0 features."
)

SYNTHETIC_OVERLAP_EXPLANATION = (
    "Demonstration Warning: Synthetic polygons {id1} and {id2} overlap spatially by approximately {area:.1f} m². "
    "Requires human vertex reconciliation."
)

REAL_OVERLAP_EXPLANATION = (
    "Spatial overlap detected between polygon {id1} and polygon {id2} (approx {area:.1f} m²). "
    "Review boundaries visually."
)

def safe_parse_geometry(geom_dict: Optional[Dict[str, Any]]) -> Optional[shapely.geometry.base.BaseGeometry]:
    """Safely converts GeoJSON geometry dict to Shapely shape without throwing unhandled exceptions."""
    if not geom_dict:
        return None
    coords = geom_dict.get("coordinates")
    if coords is None or len(coords) == 0:
        return None
    try:
        shape = shapely.geometry.shape(geom_dict)
        return shape
    except Exception:
        return None

def validate_feature_geometries(features: List[Dict[str, Any]], layer_source: str = "project_vaayu_sample") -> List[TopologyWarning]:
    """Checks individual features for empty, null, or invalid geometry."""
    warnings: List[TopologyWarning] = []
    
    for feat in features:
        feat_id = feat.get("id") or feat.get("properties", {}).get("feature_id", "UNKNOWN")
        geom = feat.get("geometry")
        source = feat.get("properties", {}).get("source", layer_source)
        
        # Check empty or None geometry
        if not geom or not geom.get("coordinates") or len(geom.get("coordinates")) == 0:
            warnings.append(TopologyWarning(
                warning_id=f"W-EMPTY-{feat_id}",
                warning_type="empty_geometry",
                severity="high",
                feature_ids=[feat_id],
                explanation=f"Feature {feat_id} contains an empty or null coordinate array.",
                plain_language_rule="Features must contain valid polygon or line coordinates.",
                source=source,
                status="open"
            ))
            continue
            
        try:
            shape = shapely.geometry.shape(geom)
            if not shape.is_valid:
                validity_reason = explain_validity(shape)
                warnings.append(TopologyWarning(
                    warning_id=f"W-INVALID-{feat_id}",
                    warning_type="invalid_geometry",
                    severity="critical" if "synthetic" not in source else "high",
                    feature_ids=[feat_id],
                    explanation=f"Geometry for {feat_id} violates OGC standards: {validity_reason}.",
                    plain_language_rule="Non-simple or self-intersecting polygon boundary detected. Ring must not cross itself.",
                    source=source,
                    status="open",
                    affected_coordinates=[shape.centroid.x, shape.centroid.y] if not shape.is_empty else None
                ))
        except Exception as e:
            warnings.append(TopologyWarning(
                warning_id=f"W-CORRUPT-{feat_id}",
                warning_type="invalid_geometry",
                severity="critical",
                feature_ids=[feat_id],
                explanation=f"Geometry parsing error for {feat_id}: {str(e)}",
                plain_language_rule="Malformed GeoJSON geometry structure.",
                source=source,
                status="open"
            ))
            
    return warnings

def check_polygon_overlaps(features: List[Dict[str, Any]], layer_source: str = "project_vaayu_sample") -> List[TopologyWarning]:
    """Detects mutual overlaps among polygon features in the same layer."""
    warnings: List[TopologyWarning] = []
    parsed_shapes = []
    
    for feat in features:
        feat_id = feat.get("id") or feat.get("properties", {}).get("feature_id", "UNKNOWN")
        source = feat.get("properties", {}).get("source", layer_source)
        shape = safe_parse_geometry(feat.get("geometry"))
        if shape and shape.is_valid and shape.geom_type in ["Polygon", "MultiPolygon"]:
            parsed_shapes.append((feat_id, source, shape))
            
    n = len(parsed_shapes)
    for i in range(n):
        id1, src1, s1 = parsed_shapes[i]
        for j in range(i + 1, n):
            id2, src2, s2 = parsed_shapes[j]
            try:
                if s1.intersects(s2):
                    inter = s1.intersection(s2)
                    # Convert degree area roughly to m² (1 deg ≈ 111,000m at equator; 1 deg² ≈ 1.2e10 m², scale at lat 23 is ~1e10)
                    area_m2 = inter.area * 1e10
                    if area_m2 > 1.0: # Filter out microscopic numerical touching edges
                        is_synth = "synthetic" in src1 or "synthetic" in src2
                        explanation = (
                            SYNTHETIC_OVERLAP_EXPLANATION.format(id1=id1, id2=id2, area=area_m2)
                            if is_synth else
                            REAL_OVERLAP_EXPLANATION.format(id1=id1, id2=id2, area=area_m2)
                        )
                        warnings.append(TopologyWarning(
                            warning_id=f"W-OVERLAP-{id1}-{id2}",
                            warning_type="overlapping_polygons",
                            severity="medium",
                            feature_ids=[id1, id2],
                            explanation=explanation,
                            plain_language_rule="Building footprints or parcels should not overlap without a multi-level partition.",
                            source=src1 if is_synth else "project_vaayu_sample",
                            status="open",
                            affected_coordinates=[inter.centroid.x, inter.centroid.y] if not inter.is_empty else None
                        ))
            except Exception:
                continue
                
    return warnings

def check_building_road_intersections(
    building_features: List[Dict[str, Any]],
    road_features: List[Dict[str, Any]]
) -> List[TopologyWarning]:
    """
    Checks spatial overlaps between building polygons and road corridor polygons.
    Uses strictly NEUTRAL wording: 'spatial overlap—review visually'.
    """
    warnings: List[TopologyWarning] = []
    
    buildings = []
    for b in building_features:
        bid = b.get("id") or b.get("properties", {}).get("feature_id")
        src = b.get("properties", {}).get("source", "project_vaayu_sample")
        s = safe_parse_geometry(b.get("geometry"))
        if s and s.is_valid:
            buildings.append((bid, src, s))
            
    roads = []
    for r in road_features:
        rid = r.get("id") or r.get("properties", {}).get("feature_id") or r.get("properties", {}).get("road_id")
        src = r.get("properties", {}).get("source", "project_vaayu_sample")
        s = safe_parse_geometry(r.get("geometry"))
        if s and s.is_valid:
            roads.append((rid, src, s))
            
    for bid, b_src, b_shape in buildings:
        for rid, r_src, r_shape in roads:
            try:
                if b_shape.intersects(r_shape):
                    inter = b_shape.intersection(r_shape)
                    inter_area_m2 = inter.area * 1e10 if inter.geom_type in ["Polygon", "MultiPolygon"] else 0.0
                    
                    is_synth = "synthetic" in b_src or "synthetic" in r_src
                    explanation = (
                        SYNTHETIC_ROAD_OVERLAP_EXPLANATION.format(bld_id=bid, road_id=rid)
                        if is_synth else
                        NEUTRAL_ROAD_OVERLAP_EXPLANATION.format(bld_id=bid, road_id=rid)
                    )
                    warnings.append(TopologyWarning(
                        warning_id=f"W-RD-OVERLAP-{bid}-{rid}",
                        warning_type="building_road_spatial_overlap",
                        severity="medium",
                        feature_ids=[bid, rid],
                        explanation=explanation,
                        plain_language_rule="Building footprint spatially intersects road corridor. Review imagery visually to confirm setback or alignment.",
                        source=b_src if is_synth else "project_vaayu_sample",
                        status="open",
                        affected_coordinates=[inter.centroid.x, inter.centroid.y] if not inter.is_empty else None
                    ))
            except Exception:
                continue
                
    return warnings

def check_synthetic_parcel_crossings(synthetic_features: List[Dict[str, Any]]) -> List[TopologyWarning]:
    """
    Checks if synthetic building crosses synthetic parcel polygon boundary.
    Exclusively run on synthetic demonstration features.
    """
    warnings: List[TopologyWarning] = []
    
    synth_buildings = [
        f for f in synthetic_features 
        if f.get("properties", {}).get("feature_type") == "synthetic_building"
    ]
    synth_parcels = [
        f for f in synthetic_features 
        if f.get("properties", {}).get("feature_type") == "synthetic_parcel"
    ]
    
    for b in synth_buildings:
        bid = b.get("id") or b.get("properties", {}).get("feature_id")
        b_shape = safe_parse_geometry(b.get("geometry"))
        if not b_shape or not b_shape.is_valid:
            continue
            
        for p in synth_parcels:
            pid = p.get("id") or p.get("properties", {}).get("feature_id")
            p_shape = safe_parse_geometry(p.get("geometry"))
            if not p_shape or not p_shape.is_valid:
                continue
                
            try:
                # Straddling check: intersects parcel, but is NOT completely contained within it
                if b_shape.intersects(p_shape) and not p_shape.contains(b_shape):
                    inter = b_shape.intersection(p_shape)
                    warnings.append(TopologyWarning(
                        warning_id=f"W-SYN-PARCEL-{bid}-{pid}",
                        warning_type="building_crosses_synthetic_parcel",
                        severity="high",
                        feature_ids=[bid, pid],
                        explanation=SYNTHETIC_PARCEL_CROSSING_EXPLANATION.format(bld_id=bid, parcel_id=pid),
                        plain_language_rule="Demonstration Rule: Building footprint should be wholly inside parcel boundary without crossing parcel edge.",
                        source="synthetic_test",
                        status="open",
                        affected_coordinates=[inter.centroid.x, inter.centroid.y] if not inter.is_empty else None
                    ))
            except Exception:
                continue
                
    return warnings

def run_full_topology_validation(
    buildings: List[Dict[str, Any]],
    roads: List[Dict[str, Any]],
    real_parcels: List[Dict[str, Any]],
    synthetic_features: List[Dict[str, Any]]
) -> List[TopologyWarning]:
    """
    Executes all topology checks across loaded layers.
    GUARANTEE: If real_parcels has 0 features, zero real parcel conflict warnings are produced.
    """
    all_warnings: List[TopologyWarning] = []
    
    # 1. Individual geometry validity checks
    all_warnings.extend(validate_feature_geometries(buildings, "project_vaayu_sample"))
    all_warnings.extend(validate_feature_geometries(roads, "project_vaayu_sample"))
    all_warnings.extend(validate_feature_geometries(synthetic_features, "synthetic_test"))
    
    # 2. Polygon overlaps (within building footprint layer)
    all_warnings.extend(check_polygon_overlaps(buildings, "project_vaayu_sample"))
    all_warnings.extend(check_polygon_overlaps(synthetic_features, "synthetic_test"))
    
    # 3. Building-road spatial intersections
    all_warnings.extend(check_building_road_intersections(buildings, roads))
    
    # Synthetic road corridors & buildings
    synth_buildings = [f for f in synthetic_features if f.get("properties", {}).get("feature_type") == "synthetic_building"]
    synth_roads = [f for f in synthetic_features if f.get("properties", {}).get("feature_type") == "synthetic_road_corridor"]
    if synth_buildings and synth_roads:
        all_warnings.extend(check_building_road_intersections(synth_buildings, synth_roads))
        
    # 4. Synthetic parcel crossings
    all_warnings.extend(check_synthetic_parcel_crossings(synthetic_features))
    
    # 5. Real parcel crossings: ONLY IF real parcels exist!
    if real_parcels and len(real_parcels) > 0:
        # We know real parcels are empty in Lalpur, but handle safely if a real parcel is ever provided
        pass
        
    return all_warnings
