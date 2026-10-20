"""
Unit tests for Epic 2: Cohort Analytics Engine and 4D Feature Engineering (`detector.py`).
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

    # Hit-and-Run must have substantially higher volume lapse shock than normal agents
    assert hr_mean_shock > normal_mean_hr + 20.0, (
        f"Hit-and-Run lapse_shock_vol ({hr_mean_shock:.2f}) not significantly higher than Normal ({normal_mean_hr:.2f})"
    )

    normal_disp = feat_df.loc[feat_df["true_label"] == "Normal", "ape_disparity_ratio"].mean()
    cp_disp = feat_df.loc[feat_df["true_label"] == "Cherry-Picking", "ape_disparity_ratio"].mean()

    # Cherry-Picking must have high APE disparity ratio (> 1.8x)
    assert cp_disp > 1.8, f"Cherry-Picking APE disparity ratio was {cp_disp:.2f}, expected > 1.8"

    cp_shock_ape = feat_df.loc[feat_df["true_label"] == "Cherry-Picking", "lapse_shock_ape"].mean()
    cp_shock_vol = feat_df.loc[feat_df["true_label"] == "Cherry-Picking", "lapse_shock_vol"].mean()

    # In Cherry-Picking, APE shock must significantly exceed volume shock
    assert cp_shock_ape > cp_shock_vol + 15.0, (
        f"Cherry-picking APE shock ({cp_shock_ape:.2f}) should significantly exceed volume shock ({cp_shock_vol:.2f})"
    )
