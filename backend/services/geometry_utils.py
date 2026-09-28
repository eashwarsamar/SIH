"""
CRS-Aware Geometry Utilities for Metric Calculations.
Transforms geometries between WGS 84 (EPSG:4326) and local projected UTM Zone 43N (EPSG:32643)
for accurate metric area (m²), distance (m), buffer (m), and spatial intersection calculations.
Safely repairs invalid geometries (e.g. self-intersections) using make_valid while logging repairs.
"""
from typing import Tuple, Dict, Any, Optional, Union
import pyproj
import shapely.geometry
from shapely.ops import transform
from shapely.validation import make_valid

# Standard target UTM zone for Lalpur, Gujarat (approx 72.75°E, 23.04°N)
LOCAL_METRIC_CRS = "EPSG:32643"
WGS84_CRS = "EPSG:4326"

# Reusable PyProj transformers
_to_metric_transformer = pyproj.Transformer.from_crs(WGS84_CRS, LOCAL_METRIC_CRS, always_xy=True)
_to_wgs84_transformer = pyproj.Transformer.from_crs(LOCAL_METRIC_CRS, WGS84_CRS, always_xy=True)


def project_to_metric(geom: shapely.geometry.base.BaseGeometry) -> shapely.geometry.base.BaseGeometry:
    """Projects a Shapely geometry from EPSG:4326 to EPSG:32643 (UTM Zone 43N, meters)."""
    return transform(_to_metric_transformer.transform, geom)


def project_to_wgs84(geom: shapely.geometry.base.BaseGeometry) -> shapely.geometry.base.BaseGeometry:
    """Projects a Shapely geometry from EPSG:32643 to EPSG:4326 (WGS 84 degrees)."""
    return transform(_to_wgs84_transformer.transform, geom)


def safe_repair_geometry(
    geom: shapely.geometry.base.BaseGeometry
) -> Tuple[shapely.geometry.base.BaseGeometry, bool, str]:
    """
    Validates and safely repairs an invalid geometry using make_valid.
    Returns (repaired_geometry, was_repaired, explanation).
    Does NOT silently mutate; explicitly signals if a repair occurred.
    """
    if geom.is_valid:
        return geom, False, "Geometry is valid."
    try:
        repaired = make_valid(geom)
        return repaired, True, "Geometry self-intersection or boundary anomaly repaired via OGC make_valid."
    except Exception as e:
        return geom, False, f"Geometry repair failed: {str(e)}"


def calculate_metric_area_sqm(geom: shapely.geometry.base.BaseGeometry) -> float:
    """
    Calculates exact ground area in square meters (m²) by projecting EPSG:4326 geometry to EPSG:32643.
    Guaranteed NOT to use degrees or degree² * constant approximation.
    """
    if geom.is_empty:
        return 0.0
    metric_geom = project_to_metric(geom)
    return float(metric_geom.area)


def calculate_metric_distance_meters(
    geom1: shapely.geometry.base.BaseGeometry,
    geom2: shapely.geometry.base.BaseGeometry
) -> float:
    """
    Calculates minimum metric Euclidean distance in meters between two EPSG:4326 geometries
    by projecting both to EPSG:32643.
    """
    if geom1.is_empty or geom2.is_empty:
        return 0.0
    m_geom1 = project_to_metric(geom1)
    m_geom2 = project_to_metric(geom2)
    return float(m_geom1.distance(m_geom2))


def calculate_metric_intersection(
    geom1: shapely.geometry.base.BaseGeometry,
    geom2: shapely.geometry.base.BaseGeometry
) -> Tuple[Optional[shapely.geometry.base.BaseGeometry], float]:
    """
    Calculates the spatial intersection in EPSG:4326 and returns (intersection_wgs84, metric_area_sqm).
    """
    if not geom1.intersects(geom2):
        return None, 0.0
    inter = geom1.intersection(geom2)
    if inter.is_empty:
        return None, 0.0
    area_sqm = calculate_metric_area_sqm(inter)
    return inter, area_sqm
