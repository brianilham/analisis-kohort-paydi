"""
Unit tests for TICKET-01 & TICKET-02: Calibrated Two-Tier Detection,
4-Pillar Explainability, and Power BI ETL Exporter.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from generate_data import SimulationConfig, generate_synthetic_dataset
from detector import (
    filter_dataset,
    calculate_cohort_matrices,
    engineer_agent_features,
    run_two_tier_detection,
)
from export_powerbi_data import compute_risk_pillars, run_export_pipeline


@pytest.fixture(scope="module")
def calibrated_data():
    config = SimulationConfig(
        n_agents=200,
        n_policies=12000,
        n_cohorts=24,
        start_cohort="2022-01",
        random_seed=42,
    )
    dataset = generate_synthetic_dataset(config=config)
    feat_df = engineer_agent_features(dataset["agents"], dataset["policies"], dataset["history"])
    detected_df = run_two_tier_detection(feat_df)
    detected_df = detected_df.merge(
        dataset["agents"][["agent_id", "true_label", "is_anomaly"]],
        on="agent_id",
        how="left",
    )
    enriched_df, pillars_df = compute_risk_pillars(detected_df)
    return {
        "dataset": dataset,
        "features": feat_df,
        "detected": detected_df,
        "enriched": enriched_df,
        "pillars": pillars_df,
    }


def test_fully_seasoned_cohort_range(calibrated_data):
    """Verify cohorts span 24 months from 2022-01 to 2023-12."""
    policies = calibrated_data["dataset"]["policies"]
    cohorts = sorted(policies["cohort_month"].unique())
    assert len(cohorts) == 24
    assert cohorts[0] == "2022-01"
    assert cohorts[-1] == "2023-12"


def test_cluster_separation_and_zero_false_positives_in_normal_shock(calibrated_data):
    """Verify cluster separation: no normal agents with low shock are tagged as Hit and Run."""
    detected = calibrated_data["detected"]
    
    # 1. Normal agents with low lapse shock (< 10%) must not be Hit and Run
    norm_low_shock = detected[(detected["true_label"] == "Normal") & (detected["lapse_shock_vol"] < 10.0)]
    assert (norm_low_shock["risk_category"] != "Hit and Run").all()

    # 2. Hit-and-Run capture rate in Tier 1 >= 83% (5/6 or 6/6)
    hr_agents = detected[detected["true_label"] == "Hit-and-Run"]
    assert len(hr_agents) == 6
    hr_t1_rate = (hr_agents["risk_category"] == "Hit and Run").mean()
    assert hr_t1_rate >= 0.83

    # 3. Cherry-Picking capture rate >= 70% in Cherry Picking
    cp_agents = detected[detected["true_label"] == "Cherry-Picking"]
    assert len(cp_agents) == 10
    cp_catch_rate = (cp_agents["risk_category"] == "Cherry Picking").mean()
    assert cp_catch_rate >= 0.70

    # 4. Top-20% recall >= 85%
    sorted_df = detected.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
    top_40 = sorted_df.iloc[:40]
    recall_top20 = top_40["is_anomaly"].sum() / detected["is_anomaly"].sum()
    assert recall_top20 >= 0.85


def test_explainable_4_pillars_structure_and_bounds(calibrated_data):
    """Verify 4 normalized risk pillars (0-100) and contribution percentages."""
    enriched = calibrated_data["enriched"]
    pillars = calibrated_data["pillars"]

    # Enriched DataFrame columns
    pillar_cols = [
        "score_vol_shock",
        "score_ape_shock",
        "score_ape_disparity",
        "score_cash_ratio",
        "share_vol_shock_pct",
        "share_ape_shock_pct",
        "share_ape_disparity_pct",
        "share_cash_ratio_pct",
        "dominant_risk_pillar",
        "risk_rank",
        "is_top20_risk_rank",
    ]
    for col in pillar_cols:
        assert col in enriched.columns, f"Missing {col} in enriched agents"

    # Scores within [0, 100]
    for s_col in ["score_vol_shock", "score_ape_shock", "score_ape_disparity", "score_cash_ratio"]:
        assert (enriched[s_col] >= 0.0).all() and (enriched[s_col] <= 100.0).all()

    # Contributions sum to ~100%
    contrib_sum = (
        enriched["share_vol_shock_pct"]
        + enriched["share_ape_shock_pct"]
        + enriched["share_ape_disparity_pct"]
        + enriched["share_cash_ratio_pct"]
    )
    assert np.allclose(contrib_sum.values, 100.0, atol=0.5)

    # Pillars unpivoted DataFrame: 800 rows (200 * 4)
    assert len(pillars) == 800
    expected_pillar_names = {
        "Volume Shock M12-M13",
        "APE Leakage Shock M12-M13",
        "APE Ticket Disparity",
        "Manual/Cash Concentration",
    }
    assert set(pillars["pillar_name"].unique()) == expected_pillar_names
    assert (pillars["pillar_score_100"] >= 0.0).all() and (pillars["pillar_score_100"] <= 100.0).all()


def test_exported_files_exist_and_match_row_counts():
    """Verify exported CSV files and PNG logo exist in the filesystem."""
    data_dir = Path("data")
    assert (data_dir / "agents.csv").exists()
    assert (data_dir / "policies.csv").exists()
    assert (data_dir / "policy_monthly_status.csv").exists()
    assert (data_dir / "agent_risk_scores.csv").exists()
    assert (data_dir / "agent_risk_pillars.csv").exists()
    assert Path("powerbi/assets/mnc_life_logo.png").exists()

    df_scores = pd.read_csv(data_dir / "agent_risk_scores.csv")
    df_pillars = pd.read_csv(data_dir / "agent_risk_pillars.csv")
    assert len(df_scores) == 200
    assert len(df_pillars) == 800
    assert df_scores["is_top20_risk_rank"].sum() == 40
