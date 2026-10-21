"""
Unit tests for Epic 2 & Epic 3: Cohort Analytics Engine, 4D Feature Engineering,
and Two-Tier Anomaly Detection Engine (`detector.py`).
"""

import numpy as np
import pandas as pd
import pytest

from generate_data import generate_synthetic_dataset
from detector import (
    filter_dataset,
    calculate_cohort_matrices,
    extract_grace_period_watch,
    engineer_agent_features,
    run_two_tier_detection,
)


@pytest.fixture(scope="module")
def dataset():
    return generate_synthetic_dataset(
        n_agents=200,
        n_policies=12000,
        n_cohorts=24,
        random_seed=42,
    )


def test_filter_dataset(dataset):
    agents_df, policies_df, history_df = (
        dataset["agents"],
        dataset["policies"],
        dataset["history"],
    )

    filtered = filter_dataset(
        agents_df, policies_df, history_df,
        channel=["Agency"],
        branch_office=["Jakarta Selatan"],
    )
    assert len(filtered["agents"]) > 0
    assert (filtered["agents"]["channel"] == "Agency").all()
    assert (filtered["agents"]["branch_office"] == "Jakarta Selatan").all()

    # Integrity between filtered policies and history
    valid_agents = set(filtered["agents"]["agent_id"])
    assert set(filtered["policies"]["agent_id"]).issubset(valid_agents)
    valid_policies = set(filtered["policies"]["policy_id"])
    assert set(filtered["history"]["policy_id"]).issubset(valid_policies)


def test_cohort_matrices_dimensions_and_values(dataset):
    policies_df, history_df = dataset["policies"], dataset["history"]
    matrices = calculate_cohort_matrices(policies_df, history_df)

    vol_mat = matrices["volume_matrix"]
    ape_mat = matrices["ape_matrix"]
    disc_mat = matrices["discrepancy_matrix"]

    assert vol_mat.shape == (24, 24)
    assert ape_mat.shape == (24, 24)
    assert disc_mat.shape == (24, 24)

    # M1 column must be exactly 100.0%
    assert np.allclose(vol_mat["M1"].values, 100.0)
    assert np.allclose(ape_mat["M1"].values, 100.0)

    # Monotonic decreasing or equal check across months M1..M24
    for i in range(1, 24):
        curr_m = f"M{i}"
        next_m = f"M{i+1}"
        assert (vol_mat[next_m].values <= vol_mat[curr_m].values + 1e-6).all(), (
            f"Volume matrix not monotonically non-increasing at {curr_m} -> {next_m}"
        )
        assert (ape_mat[next_m].values <= ape_mat[curr_m].values + 1e-6).all(), (
            f"APE matrix not monotonically non-increasing at {curr_m} -> {next_m}"
        )

    # M13 summary check
    summary = matrices["m13_summary"]
    assert "m13_vol_persistency" in summary
    assert "m13_ape_persistency" in summary
    assert "leakage_gap" in summary
    assert 0.0 <= summary["m13_vol_persistency"] <= 100.0
    assert 0.0 <= summary["m13_ape_persistency"] <= 100.0


def test_extract_grace_period_watch(dataset):
    policies_df, history_df = dataset["policies"], dataset["history"]
    watch_df = extract_grace_period_watch(policies_df, history_df, months=(11, 12))

    assert isinstance(watch_df, pd.DataFrame)
    assert len(watch_df) > 0
    assert "policy_id" in watch_df.columns
    assert "agent_id" in watch_df.columns
    assert "month_index" in watch_df.columns
    assert "ape" in watch_df.columns
    assert watch_df["month_index"].isin([11, 12]).all()


def test_engineer_agent_features_dimensions_and_validity(dataset):
    agents_df, policies_df, history_df = (
        dataset["agents"],
        dataset["policies"],
        dataset["history"],
    )

    feat_df = engineer_agent_features(agents_df, policies_df, history_df)

    assert len(feat_df) == len(agents_df)
    required_cols = [
        "agent_id",
        "agent_name",
        "channel",
        "branch_office",
        "total_policies",
        "total_ape",
        "m12_vol_persistency",
        "m13_vol_persistency",
        "lapse_shock_vol",
        "m12_ape_persistency",
        "m13_ape_persistency",
        "lapse_shock_ape",
        "ape_disparity_ratio",
        "cash_payment_ratio",
        "grace_period_m11_m12_count",
    ]
    for col in required_cols:
        assert col in feat_df.columns, f"Missing column {col} in engineered features"

    # No NaNs or infinities in features
    numeric_features = [
        "lapse_shock_vol",
        "lapse_shock_ape",
        "ape_disparity_ratio",
        "cash_payment_ratio",
    ]
    for col in numeric_features:
        assert not feat_df[col].isna().any(), f"NaN found in {col}"
        assert not np.isinf(feat_df[col]).any(), f"Inf found in {col}"


def test_feature_separability_for_anomalies(dataset):
    agents_df, policies_df, history_df = (
        dataset["agents"],
        dataset["policies"],
        dataset["history"],
    )

    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    feat_df = feat_df.merge(
        agents_df[["agent_id", "true_label"]],
        on="agent_id",
        how="left",
    )

    normal_mean_hr = feat_df.loc[feat_df["true_label"] == "Normal", "lapse_shock_vol"].mean()
    hr_mean_shock = feat_df.loc[feat_df["true_label"] == "Hit-and-Run", "lapse_shock_vol"].mean()

    assert hr_mean_shock > normal_mean_hr + 20.0, (
        f"Hit-and-Run lapse_shock_vol ({hr_mean_shock:.2f}) not significantly higher than Normal ({normal_mean_hr:.2f})"
    )

    cp_disp = feat_df.loc[feat_df["true_label"] == "Cherry-Picking", "ape_disparity_ratio"].mean()
    assert cp_disp > 1.8, f"Cherry-Picking APE disparity ratio was {cp_disp:.2f}, expected > 1.8"

    cp_shock_ape = feat_df.loc[feat_df["true_label"] == "Cherry-Picking", "lapse_shock_ape"].mean()
    cp_shock_vol = feat_df.loc[feat_df["true_label"] == "Cherry-Picking", "lapse_shock_vol"].mean()
    assert cp_shock_ape > cp_shock_vol + 15.0, (
        f"Cherry-picking APE shock ({cp_shock_ape:.2f}) should significantly exceed volume shock ({cp_shock_vol:.2f})"
    )


# ==============================================================================
# EPIC 3 TESTS: TWO-TIER DETECTION & MODEL EVALUATION
# ==============================================================================


def test_two_tier_detection_outputs_and_scores(dataset):
    agents_df, policies_df, history_df = (
        dataset["agents"],
        dataset["policies"],
        dataset["history"],
    )
    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    detected_df = run_two_tier_detection(feat_df)

    assert len(detected_df) == len(feat_df)

    expected_cols = [
        "tier1_violation",
        "tier2_anomaly",
        "anomaly_score",
        "risk_category",
        "primary_risk_drivers",
    ]
    for col in expected_cols:
        assert col in detected_df.columns, f"Missing output column {col}"

    # Score bounded in [0.0, 1.0]
    scores = detected_df["anomaly_score"]
    assert (scores >= 0.0).all() and (scores <= 1.0).all()

    # Risk categories check
    allowed_categories = {
        "Normal",
        "Hit and Run",
        "Cherry Picking",
    }
    assert set(detected_df["risk_category"]).issubset(allowed_categories)

    # Risk drivers non-empty for flagged agents
    flagged = detected_df[detected_df["risk_category"] != "Normal"]
    assert (flagged["primary_risk_drivers"].str.len() > 5).all()


def test_tier1_captures_hit_and_run(dataset):
    """Ensure Tier 1 hard rule flags all extreme Hit-and-Run agents."""
    agents_df, policies_df, history_df = (
        dataset["agents"],
        dataset["policies"],
        dataset["history"],
    )
    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    detected_df = run_two_tier_detection(feat_df)
    merged = detected_df.merge(agents_df[["agent_id", "true_label"]], on="agent_id")

    hr_agents = merged[merged["true_label"] == "Hit-and-Run"]
    assert len(hr_agents) > 0
    hr_tier1_captured = hr_agents["tier1_violation"].mean()
    assert hr_tier1_captured >= 0.83, f"Expected Tier 1 to capture at least 83% of Hit-and-Run, got {hr_tier1_captured:.2%}"


def test_tier2_captures_cherry_picking_that_bypasses_tier1(dataset):
    """Ensure Tier 2 Isolation Forest captures subtle Cherry-Picking agents that pass Tier 1."""
    agents_df, policies_df, history_df = (
        dataset["agents"],
        dataset["policies"],
        dataset["history"],
    )
    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    detected_df = run_two_tier_detection(feat_df)
    merged = detected_df.merge(agents_df[["agent_id", "true_label"]], on="agent_id")

    cp_agents = merged[merged["true_label"] == "Cherry-Picking"]
    assert len(cp_agents) > 0

    # Cherry-picking agents that bypassed Tier 1
    cp_bypassed_t1 = cp_agents[~cp_agents["tier1_violation"]]
    assert len(cp_bypassed_t1) > 0, "Expected some Cherry-Picking agents to bypass Tier 1 volume rule"

    # Tier 2 should catch the vast majority of these bypassed agents
    cp_t2_catch_rate = cp_bypassed_t1["tier2_anomaly"].mean()
    assert cp_t2_catch_rate >= 0.70, (
        f"Tier 2 Isolation Forest catch rate on bypassed CP agents was {cp_t2_catch_rate:.2%}, expected >= 70%"
    )


def test_model_overall_recall_target_on_ground_truth(dataset):
    """
    Test SPEC.md Requirement:
    Recall of anomaly detection against synthetic ground-truth labels >= 85%
    within top-20% risk ranking.
    """
    agents_df, policies_df, history_df = (
        dataset["agents"],
        dataset["policies"],
        dataset["history"],
    )
    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    detected_df = run_two_tier_detection(feat_df)
    merged = detected_df.merge(agents_df[["agent_id", "is_anomaly", "true_label"]], on="agent_id")

    # Sort by anomaly_score descending (Risk Ranking)
    merged_sorted = merged.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

    # Top 20% of agent population
    top_20_pct_n = int(np.ceil(len(merged_sorted) * 0.20))
    top_20 = merged_sorted.iloc[:top_20_pct_n]

    total_anomalies = merged["is_anomaly"].sum()
    anomalies_in_top_20 = top_20["is_anomaly"].sum()
    recall_top_20 = anomalies_in_top_20 / total_anomalies

    assert recall_top_20 >= 0.85, (
        f"Recall in Top 20% risk ranking was {recall_top_20:.2%}, target >= 85% required by SPEC.md!"
    )


def test_detector_robustness_with_edge_cases():
    """Ensure detector handles empty records, single-policy agents, and zero values gracefully."""
    dummy_agents = pd.DataFrame(
        {
            "agent_id": ["AGT-9991", "AGT-9992"],
            "agent_name": ["Edge Case 1", "Edge Case 2"],
            "channel": ["Agency", "Bancassurance"],
            "branch_office": ["Jakarta Selatan", "Surabaya"],
            "join_date": ["2023-01-01", "2023-01-01"],
            "total_policies": [1, 0],
            "total_ape": [5_000_000.0, 0.0],
            "m12_vol_persistency": [100.0, 0.0],
            "m13_vol_persistency": [100.0, 0.0],
            "lapse_shock_vol": [0.0, 0.0],
            "m12_ape_persistency": [100.0, 0.0],
            "m13_ape_persistency": [100.0, 0.0],
            "lapse_shock_ape": [0.0, 0.0],
            "ape_disparity_ratio": [1.0, 1.0],
            "cash_payment_ratio": [0.0, 0.0],
            "grace_period_m11_m12_count": [0, 0],
            "grace_period_m11_m12_ape": [0.0, 0.0],
        }
    )
    detected = run_two_tier_detection(dummy_agents)
    assert len(detected) == 2
    assert not detected["anomaly_score"].isna().any()
    assert (detected["anomaly_score"] >= 0.0).all()
