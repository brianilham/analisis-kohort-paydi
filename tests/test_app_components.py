"""
Unit tests for Epic 4: Dashboard Visualization Helpers and Components (`visuals.py`).
"""

import pandas as pd
import pytest
import plotly.graph_objects as go

from generate_data import generate_synthetic_dataset
from detector import (
    calculate_cohort_matrices,
    engineer_agent_features,
    run_two_tier_detection,
    extract_grace_period_watch,
)
from visuals import (
    create_cohort_heatmap,
    create_discrepancy_heatmap,
    create_anomaly_scatter_plot,
    create_agent_drilldown_curves,
    calculate_dashboard_kpis,
)


@pytest.fixture(scope="module")
def processed_data():
    dataset = generate_synthetic_dataset(
        n_agents=150,
        n_policies=10000,
        n_cohorts=24,
        random_seed=42,
    )
    agents_df, policies_df, history_df = (
        dataset["agents"],
        dataset["policies"],
        dataset["history"],
    )
    matrices = calculate_cohort_matrices(policies_df, history_df)
    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    detected_df = run_two_tier_detection(feat_df)
    grace_df = extract_grace_period_watch(policies_df, history_df)
    return {
        "agents": agents_df,
        "policies": policies_df,
        "history": history_df,
        "matrices": matrices,
        "detected": detected_df,
        "grace": grace_df,
    }


def test_calculate_dashboard_kpis(processed_data):
    matrices = processed_data["matrices"]
    detected_df = processed_data["detected"]
    grace_df = processed_data["grace"]

    kpis = calculate_dashboard_kpis(matrices, detected_df, grace_df)

    assert "m13_vol" in kpis
    assert "m13_ape" in kpis
    assert "leakage_gap" in kpis
    assert "tier1_count" in kpis
    assert "tier2_count" in kpis
    assert "total_flagged" in kpis
    assert "grace_policy_count" in kpis
    assert "grace_total_ape" in kpis

    assert 0.0 <= kpis["m13_vol"] <= 100.0
    assert 0.0 <= kpis["m13_ape"] <= 100.0
    assert kpis["total_flagged"] == kpis["tier1_count"] + kpis["tier2_count"]


def test_create_cohort_heatmap(processed_data):
    vol_mat = processed_data["matrices"]["volume_matrix"]
    fig = create_cohort_heatmap(vol_mat, title="Volume Retention Matrix (%)")

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.data[0].type == "heatmap"


def test_create_discrepancy_heatmap(processed_data):
    disc_mat = processed_data["matrices"]["discrepancy_matrix"]
    fig = create_discrepancy_heatmap(disc_mat)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.data[0].type == "heatmap"


def test_create_anomaly_scatter_plot(processed_data):
    detected_df = processed_data["detected"]
    fig = create_anomaly_scatter_plot(detected_df)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    # Check that scatter markers exist
    types = [d.type for d in fig.data]
    assert "scatter" in types


def test_create_agent_drilldown_curves(processed_data):
    policies_df = processed_data["policies"]
    history_df = processed_data["history"]
    agent_id = processed_data["detected"]["agent_id"].iloc[0]

    fig = create_agent_drilldown_curves(policies_df, history_df, agent_id=agent_id)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 2  # At least Volume curve and APE curve
