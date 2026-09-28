"""
Transparent Prototype Review-Priority Scoring Engine.
Calculates explainable 0-100 scores based on documented rules in config/scoring_rules.json.
Provides full breakdown of contributing rules and explicit prototype heuristic disclaimer.
"""
import json
import os
from typing import Dict, Any, List, Optional
from backend.models.schemas import ReviewScoreBreakdown, ScoreRuleContribution

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "scoring_rules.json")

def load_scoring_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def calculate_review_score(
    feature: Dict[str, Any],
    associated_warning_ids: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None
) -> ReviewScoreBreakdown:
    """
    Computes explainable review score and returns structured breakdown.
    Marked with disclaimer: prototype heuristic—not a validated survey-priority model.
    """
    if config is None:
        config = load_scoring_config()
        
    feat_id = feature.get("id") or feature.get("properties", {}).get("feature_id", "UNKNOWN")
    props = feature.get("properties", {})
    feat_type = props.get("feature_type", "building")
    source = props.get("source", "project_vaayu_sample")
    review_status = props.get("review_status", "unverified")
    confidence = props.get("confidence")
    area_sqm = props.get("area_sqm") or 0.0
    
    current_score = config.get("base_score", 10)
    triggered_rules: List[ScoreRuleContribution] = []
    
    # 1. Unverified source rule
    if source == "project_vaayu_sample" or source == "synthetic_test":
        rule = next((r for r in config["rules"] if r["rule_id"] == "R_UNVERIFIED_SOURCE"), None)
        if rule:
            current_score += rule["points"]
            triggered_rules.append(ScoreRuleContribution(
                rule_id=rule["rule_id"],
                rule_name=rule["rule_name"],
                description=rule["description"],
                points=rule["points"]
            ))
            
    # 2. Spatial overlap or topology warning rule
    if associated_warning_ids and len(associated_warning_ids) > 0:
        rule = next((r for r in config["rules"] if r["rule_id"] == "R_SPATIAL_OVERLAP_WARNING"), None)
        if rule:
            current_score += rule["points"]
            triggered_rules.append(ScoreRuleContribution(
                rule_id=rule["rule_id"],
                rule_name=rule["rule_name"],
                description=f"{rule['description']} ({len(associated_warning_ids)} warnings active: {', '.join(associated_warning_ids[:3])})",
                points=rule["points"]
            ))
            
    # 3. Low model confidence (for AI building model)
    if source == "ai_building_model" and confidence is not None and confidence < 0.70:
        rule = next((r for r in config["rules"] if r["rule_id"] == "R_LOW_AI_CONFIDENCE"), None)
        if rule:
            current_score += rule["points"]
            triggered_rules.append(ScoreRuleContribution(
                rule_id=rule["rule_id"],
                rule_name=rule["rule_name"],
                description=f"Model confidence ({confidence:.2f}) is below 0.70 threshold.",
                points=rule["points"]
            ))
            
    # 4. Extreme footprint dimensions (tiny or massive)
    if feat_type in ["building", "synthetic_building"] and area_sqm > 0 and (area_sqm < 10.0 or area_sqm > 600.0):
        rule = next((r for r in config["rules"] if r["rule_id"] == "R_EXTREME_DIMENSIONS"), None)
        if rule:
            current_score += rule["points"]
            triggered_rules.append(ScoreRuleContribution(
                rule_id=rule["rule_id"],
                rule_name=rule["rule_name"],
                description=f"Footprint area ({area_sqm:.1f} m²) is outside typical residential building envelope (10-600 m²).",
                points=rule["points"]
            ))
            
    # 5. Human review status rules
    if review_status == "approved":
        rule = next((r for r in config["rules"] if r["rule_id"] == "R_HUMAN_APPROVED"), None)
        if rule:
            current_score += rule["points"]
            triggered_rules.append(ScoreRuleContribution(
                rule_id=rule["rule_id"],
                rule_name=rule["rule_name"],
                description=rule["description"],
                points=rule["points"]
            ))
    elif review_status == "rejected":
        rule = next((r for r in config["rules"] if r["rule_id"] == "R_HUMAN_REJECTED"), None)
        if rule:
            current_score += rule["points"]
            triggered_rules.append(ScoreRuleContribution(
                rule_id=rule["rule_id"],
                rule_name=rule["rule_name"],
                description=rule["description"],
                points=rule["points"]
            ))
            
    # Clamp score to [0, 100]
    final_score = max(0, min(100, current_score))
    
    # Determine priority tier
    if final_score >= 70:
        priority = "high"
    elif final_score >= 40:
        priority = "medium"
    else:
        priority = "low"
        
    return ReviewScoreBreakdown(
        feature_id=feat_id,
        feature_type=feat_type,
        total_score=final_score,
        priority=priority,
        heuristic_disclaimer=config.get("disclaimer", "prototype heuristic—not a validated survey-priority model"),
        rules_triggered=triggered_rules
    )
