"""
Building Model Interface and Benchmark Dataset Adapter.
Provides:
1. BuildingModel abstract interface
2. MockBuildingModel stub provider with success and failure simulation
3. BenchmarkDatasetAdapter for SpaceNet 2 and Inria Aerial Image Labeling Dataset
   (with terms, download route, attribution, and pending evaluation harness)
4. Deterministic polygon evaluation metrics (IoU, Precision, Recall, F1)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union
import shapely.geometry

class ModelInferenceError(Exception):
    """Raised when model inference fails."""
    pass

class BuildingModel(ABC):
    """Abstract interface for AI building footprint extraction models."""
    
    @abstractmethod
    def predict(
        self,
        image_or_tile: Optional[Union[str, bytes]] = None,
        bounds: Optional[Tuple[float, float, float, float]] = None,
        confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Executes inference and returns a GeoJSON FeatureCollection of building footprints.
        Features must include: source='ai_building_model', model_name, model_version, confidence.
        """
        pass

class MockBuildingModel(BuildingModel):
    """
    Mock building model provider for UI testing and developer verification.
    Generates realistic building footprint predictions in the Lalpur AOI.
    """
    def __init__(self, model_name: str = "Vaayu-UnetPP-Lite", model_version: str = "0.1.0-mock"):
        self.model_name = model_name
        self.model_version = model_version

    def predict(
        self,
        image_or_tile: Optional[Union[str, bytes]] = None,
        bounds: Optional[Tuple[float, float, float, float]] = None,
        confidence_threshold: float = 0.5,
        simulate_failure: bool = False
    ) -> Dict[str, Any]:
        if simulate_failure:
            raise ModelInferenceError(
                f"Simulated Model Failure: {self.model_name} v{self.model_version} "
                "GPU memory allocation failed or tile preprocessing timeout."
            )
            
        # Sample simulated inference footprints within Lalpur abadi
        simulated_footprints = [
            {
                "type": "Feature",
                "id": "AI-BLD-001",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [72.75685, 23.04105],
                            [72.75705, 23.04105],
                            [72.75705, 23.04122],
                            [72.75685, 23.04122],
                            [72.75685, 23.04105]
                        ]
                    ]
                },
                "properties": {
                    "feature_id": "AI-BLD-001",
                    "feature_type": "building",
                    "source": "ai_building_model",
                    "model_name": self.model_name,
                    "model_version": self.model_version,
                    "confidence": 0.92,
                    "verification_status": "unverified",
                    "review_status": "unverified",
                    "area_sqm": 41.5,
                    "notes": "Automated inference candidate via Unet++"
                }
            },
            {
                "type": "Feature",
                "id": "AI-BLD-002",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [72.75715, 23.04130],
                            [72.75738, 23.04130],
                            [72.75738, 23.04148],
                            [72.75715, 23.04148],
                            [72.75715, 23.04130]
                        ]
                    ]
                },
                "properties": {
                    "feature_id": "AI-BLD-002",
                    "feature_type": "building",
                    "source": "ai_building_model",
                    "model_name": self.model_name,
                    "model_version": self.model_version,
                    "confidence": 0.86,
                    "verification_status": "unverified",
                    "review_status": "unverified",
                    "area_sqm": 53.2,
                    "notes": "Automated inference candidate via Unet++"
                }
            },
            {
                "type": "Feature",
                "id": "AI-BLD-003",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [72.75745, 23.04080],
                            [72.75765, 23.04080],
                            [72.75765, 23.04096],
                            [72.75745, 23.04096],
                            [72.75745, 23.04080]
                        ]
                    ]
                },
                "properties": {
                    "feature_id": "AI-BLD-003",
                    "feature_type": "building",
                    "source": "ai_building_model",
                    "model_name": self.model_name,
                    "model_version": self.model_version,
                    "confidence": 0.64,  # Below 0.70 threshold to test score penalty
                    "verification_status": "unverified",
                    "review_status": "unverified",
                    "area_sqm": 35.8,
                    "notes": "Low-confidence extraction candidate"
                }
            }
        ]
        
        # Filter by confidence
        filtered = [f for f in simulated_footprints if f["properties"]["confidence"] >= confidence_threshold]
        
        return {
            "type": "FeatureCollection",
            "name": "ai_predicted_buildings",
            "model_metadata": {
                "model_name": self.model_name,
                "model_version": self.model_version,
                "inference_status": "success",
                "confidence_threshold": confidence_threshold,
                "detected_count": len(filtered)
            },
            "features": filtered
        }


class WHUBuildingModel(BuildingModel):
    """
    Live inference provider wrapping WHU Building Detection U-Net++ EfficientNet-B4.
    Executes real sliding-window inference over local Lalpur orthomosaic.
    """
    def __init__(
        self,
        model_name: str = "giswqs/whu-building-unetplusplus-efficientnet-b4",
        model_version: str = "09df9efd323bbd3d56b98b4857129eb9b5baa2d3"
    ):
        self.model_name = model_name
        self.model_version = model_version

    def predict(
        self,
        image_or_tile: Optional[Union[str, bytes]] = None,
        bounds: Optional[Tuple[float, float, float, float]] = None,
        confidence_threshold: float = 0.5,
        simulate_failure: bool = False
    ) -> Dict[str, Any]:
        if simulate_failure:
            raise ModelInferenceError(
                f"Model Failure ({self.model_name}): Simulated live model failure request."
            )

        try:
            from backend.services.whu_model import run_whu_live_inference
            res = run_whu_live_inference(confidence_threshold=confidence_threshold)
            return {
                "type": "FeatureCollection",
                "name": res.get("name", "whu_predicted_buildings"),
                "model_metadata": res.get("model_metadata", {}),
                "features": res.get("features", [])
            }
        except Exception as e:
            raise ModelInferenceError(f"Live Model Inference Error: {e}")



# ==============================================================================
# Benchmark Dataset Adapters & Evaluation Harness
# ==============================================================================

class BenchmarkDatasetAdapter:
    """
    Official benchmark dataset specifications, legal reuse terms, and evaluation harness.
    Implements honest, reproducible evaluation without fabricating benchmark passes.
    """
    SUPPORTED_DATASETS = {
        "inria_aerial_image_labeling": {
            "name": "Inria Aerial Image Labeling Dataset",
            "url": "https://project.inria.fr/aerialimagelabeling/",
            "license": "Inria Non-Commercial Research License / CC BY-NC-ND",
            "resolution": "0.3 m GSD",
            "coverage": "810 km² (Austin, Chicago, Kitsap County, Tyrol, Vienna)",
            "download_method": "Manual registration and multi-GB tarball download (~21 GB total)",
            "status": "PENDING_ACQUISITION",
            "status_details": "Large multi-GB research corpus requiring manual user registration. Adapter ready."
        },
        "spacenet_2_buildings": {
            "name": "SpaceNet 2: Building Detection Dataset",
            "url": "https://spacenet.ai/spacenet-buildings-dataset-v2/",
            "license": "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)",
            "resolution": "0.3 m WorldView-3 imagery",
            "coverage": "Las Vegas, Paris, Shanghai, Khartoum (>300,000 building footprints)",
            "download_method": "AWS S3 CLI (aws s3 sync s3://spacenet-dataset/spacenet/SN2_buildings/ ...)",
            "status": "PENDING_ACQUISITION",
            "status_details": "Requires configured AWS S3 credentials with Requester Pays. Adapter ready."
        }
    }

    @classmethod
    def get_dataset_manifest(cls) -> Dict[str, Any]:
        """Returns the registered benchmark datasets, terms, and current acquisition status."""
        return {
            "registered_datasets": cls.SUPPORTED_DATASETS,
            "disclaimer": "Benchmark evaluation execution is marked PENDING_ACQUISITION. "
                          "No benchmark pass or accuracy metrics are fabricated."
        }

    @staticmethod
    def compute_polygon_iou(poly1: shapely.geometry.Polygon, poly2: shapely.geometry.Polygon) -> float:
        """Computes geometric Intersection-over-Union (Jaccard Index) between two polygons."""
        if not poly1.is_valid:
            poly1 = poly1.buffer(0)
        if not poly2.is_valid:
            poly2 = poly2.buffer(0)
        if poly1.is_empty or poly2.is_empty:
            return 0.0
            
        inter_area = poly1.intersection(poly2).area
        union_area = poly1.union(poly2).area
        if union_area <= 0:
            return 0.0
        return inter_area / union_area

    @classmethod
    def evaluate_detections(
        cls,
        ground_truth_polygons: List[shapely.geometry.Polygon],
        predicted_polygons: List[shapely.geometry.Polygon],
        iou_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Deterministic benchmark evaluation computing True Positives, False Positives,
        False Negatives, Precision, Recall, and F1 Score at the specified IoU threshold.
        """
        if not ground_truth_polygons:
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "true_positives": 0,
                "false_positives": len(predicted_polygons),
                "false_negatives": 0,
                "iou_threshold": iou_threshold
            }

        matched_gt = set()
        matched_pred = set()

        for p_idx, pred in enumerate(predicted_polygons):
            best_iou = 0.0
            best_gt_idx = -1
            for g_idx, gt in enumerate(ground_truth_polygons):
                if g_idx in matched_gt:
                    continue
                iou = cls.compute_polygon_iou(gt, pred)
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = g_idx
                    
            if best_iou >= iou_threshold and best_gt_idx >= 0:
                matched_gt.add(best_gt_idx)
                matched_pred.add(p_idx)

        tp = len(matched_pred)
        fp = len(predicted_polygons) - tp
        fn = len(ground_truth_polygons) - len(matched_gt)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "total_ground_truth": len(ground_truth_polygons),
            "total_predictions": len(predicted_polygons),
            "iou_threshold": iou_threshold
        }
