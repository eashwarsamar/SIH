"""
Synthetic test fixtures for SIH26012 Feature Review Platform.
Provides dedicated demonstration fixtures satisfying all prompt requirements:
1. Two overlapping polygons
2. Feature with invalid geometry (bowtie/self-intersecting) and empty geometry
3. Synthetic building intersecting synthetic road corridor
4. Synthetic building crossing an explicitly synthetic parcel polygon

Every feature carries source="synthetic_test".
Notice: Real Lalpur layers NEVER trigger synthetic parcel warnings.
"""
from typing import Dict, Any, List

SYNTHETIC_LAYER_NAME = "Synthetic test data — not real parcels"
SYNTHETIC_LAYER_DISCLAIMER = (
    "Fabricated test geometry for automated topology validation and review demonstration. "
    "Do NOT treat as real Lalpur parcels or survey boundaries. Real parcel layer has 0 features."
)

def get_synthetic_test_features() -> List[Dict[str, Any]]:
    """
    Returns the collection of deliberate synthetic test features in EPSG:4326.
    Located in a dedicated test zone within the study area perimeter.
    """
    features = [
        # 1. Overlapping polygon pair: SYN-BLD-OVERLAP-1 and SYN-BLD-OVERLAP-2
        {
            "type": "Feature",
            "id": "SYN-BLD-OVERLAP-1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.75880, 23.03880],
                        [72.75910, 23.03880],
                        [72.75910, 23.03905],
                        [72.75880, 23.03905],
                        [72.75880, 23.03880]
                    ]
                ]
            },
            "properties": {
                "feature_id": "SYN-BLD-OVERLAP-1",
                "feature_type": "synthetic_building",
                "name": "Synthetic Overlap Feature A",
                "source": "synthetic_test",
                "verification_status": "unverified",
                "review_status": "unverified",
                "confidence": None,
                "area_sqm": 725.0,
                "notes": "Deliberate synthetic test case 1: overlaps SYN-BLD-OVERLAP-2 by ~180 sqm."
            }
        },
        {
            "type": "Feature",
            "id": "SYN-BLD-OVERLAP-2",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.75900, 23.03890],
                        [72.75930, 23.03890],
                        [72.75930, 23.03915],
                        [72.75900, 23.03915],
                        [72.75900, 23.03890]
                    ]
                ]
            },
            "properties": {
                "feature_id": "SYN-BLD-OVERLAP-2",
                "feature_type": "synthetic_building",
                "name": "Synthetic Overlap Feature B",
                "source": "synthetic_test",
                "verification_status": "unverified",
                "review_status": "unverified",
                "confidence": None,
                "area_sqm": 725.0,
                "notes": "Deliberate synthetic test case 1: overlaps SYN-BLD-OVERLAP-1."
            }
        },

        # 2. Invalid Geometry: SYN-INVALID-GEOM-1 (Self-intersecting / Bowtie)
        {
            "type": "Feature",
            "id": "SYN-INVALID-GEOM-1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.75820, 23.03880],
                        [72.75850, 23.03905],
                        [72.75850, 23.03880],
                        [72.75820, 23.03905],
                        [72.75820, 23.03880]
                    ]
                ]
            },
            "properties": {
                "feature_id": "SYN-INVALID-GEOM-1",
                "feature_type": "synthetic_building",
                "name": "Synthetic Invalid Polygon (Bowtie / Self-Intersection)",
                "source": "synthetic_test",
                "verification_status": "unverified",
                "review_status": "unverified",
                "confidence": None,
                "area_sqm": 0.0,
                "notes": "Deliberate synthetic test case 2: self-intersecting bowtie polygon violating OGC validity rules."
            }
        },

        # 2b. Empty Geometry feature: SYN-EMPTY-GEOM-1 (Safe handling test)
        {
            "type": "Feature",
            "id": "SYN-EMPTY-GEOM-1",
            "geometry": {
                "type": "Polygon",
                "coordinates": []
            },
            "properties": {
                "feature_id": "SYN-EMPTY-GEOM-1",
                "feature_type": "synthetic_building",
                "name": "Synthetic Empty Geometry Feature",
                "source": "synthetic_test",
                "verification_status": "unverified",
                "review_status": "unverified",
                "confidence": None,
                "area_sqm": 0.0,
                "notes": "Deliberate synthetic test case 2b: polygon with empty coordinate array."
            }
        },

        # 3. Synthetic Building Intersecting Synthetic Road Corridor
        {
            "type": "Feature",
            "id": "SYN-BLD-ROAD-INT-1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.75780, 23.03920],
                        [72.75805, 23.03920],
                        [72.75805, 23.03940],
                        [72.75780, 23.03940],
                        [72.75780, 23.03920]
                    ]
                ]
            },
            "properties": {
                "feature_id": "SYN-BLD-ROAD-INT-1",
                "feature_type": "synthetic_building",
                "name": "Synthetic Building across Road Corridor",
                "source": "synthetic_test",
                "verification_status": "unverified",
                "review_status": "unverified",
                "confidence": None,
                "area_sqm": 530.0,
                "notes": "Deliberate synthetic test case 3: encroaches into SYN-ROAD-CORRIDOR-1 right-of-way."
            }
        },
        {
            "type": "Feature",
            "id": "SYN-ROAD-CORRIDOR-1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.75760, 23.03930],
                        [72.75830, 23.03930],
                        [72.75830, 23.03938],
                        [72.75760, 23.03938],
                        [72.75760, 23.03930]
                    ]
                ]
            },
            "properties": {
                "feature_id": "SYN-ROAD-CORRIDOR-1",
                "feature_type": "synthetic_road_corridor",
                "name": "Synthetic Road Corridor",
                "source": "synthetic_test",
                "verification_status": "unverified",
                "review_status": "unverified",
                "confidence": None,
                "width": 8.0,
                "notes": "Deliberate synthetic test case 3: 8m road corridor intersected by SYN-BLD-ROAD-INT-1."
            }
        },

        # 4. Synthetic Building Crossing Explicitly Synthetic Parcel Polygon
        {
            "type": "Feature",
            "id": "SYN-BLD-PARCEL-CROSS-1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.75850, 23.03955],
                        [72.75880, 23.03955],
                        [72.75880, 23.03980],
                        [72.75850, 23.03980],
                        [72.75850, 23.03955]
                    ]
                ]
            },
            "properties": {
                "feature_id": "SYN-BLD-PARCEL-CROSS-1",
                "feature_type": "synthetic_building",
                "name": "Synthetic Building Straddling Parcel Edge",
                "source": "synthetic_test",
                "verification_status": "unverified",
                "review_status": "unverified",
                "confidence": None,
                "area_sqm": 680.0,
                "notes": "Deliberate synthetic test case 4: straddles boundary of SYN-PARCEL-DEMO-1."
            }
        },
        {
            "type": "Feature",
            "id": "SYN-PARCEL-DEMO-1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.75865, 23.03950],
                        [72.75920, 23.03950],
                        [72.75920, 23.04000],
                        [72.75865, 23.04000],
                        [72.75865, 23.03950]
                    ]
                ]
            },
            "properties": {
                "feature_id": "SYN-PARCEL-DEMO-1",
                "feature_type": "synthetic_parcel",
                "name": "Synthetic Parcel (Demonstration Only - Not Real)",
                "source": "synthetic_test",
                "verification_status": "unverified",
                "review_status": "unverified",
                "confidence": None,
                "notes": "Explicitly synthetic parcel fixture. Real parcel dataset is 0 features."
            }
        }
    ]
    return features

def get_synthetic_feature_collection() -> Dict[str, Any]:
    """Returns synthetic features wrapped in GeoJSON FeatureCollection."""
    features = get_synthetic_test_features()
    return {
        "type": "FeatureCollection",
        "name": SYNTHETIC_LAYER_NAME,
        "disclaimer": SYNTHETIC_LAYER_DISCLAIMER,
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "total_features": len(features),
        "features": features
    }
