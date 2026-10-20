"""
Invariant & Integrity Tests for Synthetic PAYDI Data Generator (`generate_data.py`).
"""

import pytest
from generate_data import SimulationConfig, generate_synthetic_dataset


@pytest.fixture(scope="module")
def dataset():
    return generate_synthetic_dataset(
        n_agents=200,
        n_policies=12000,
        n_cohorts=24,
        random_seed=42,
    )


def test_scale_and_cohort_dimensions(dataset):
    agents_df = dataset["agents"]
    policies_df = dataset["policies"]
    history_df = dataset["history"]

    assert 150 <= len(agents_df) <= 200
    assert 10000 <= len(policies_df) <= 15000
    assert policies_df["cohort_month"].nunique() == 24
    assert history_df["month_index"].min() == 1
    assert history_df["month_index"].max() == 24


def test_unique_policies_in_history_do_not_exceed_master(dataset):
    policies_df = dataset["policies"]
    history_df = dataset["history"]

    master_ids = set(policies_df["policy_id"].unique())
    history_ids = set(history_df["policy_id"].unique())

    assert len(history_ids) <= len(master_ids)
    assert history_ids.issubset(master_ids)


def test_ground_truth_anomaly_proportions(dataset):
    agents_df = dataset["agents"]
    total = len(agents_df)
    counts = agents_df["true_label"].value_counts()

    hr_ratio = counts.get("Hit-and-Run", 0) / total
    cp_ratio = counts.get("Cherry-Picking", 0) / total
    anomaly_ratio = agents_df["is_anomaly"].mean()

    assert pytest.approx(hr_ratio, abs=0.005) == 0.03
    assert pytest.approx(cp_ratio, abs=0.005) == 0.05
    assert pytest.approx(anomaly_ratio, abs=0.005) == 0.08


def test_valid_status_transitions_no_resurrection_after_lapsed(dataset):
    """Ensure Lapsed or Surrendered policies never transition back to Active or Grace Period."""
    history_df = dataset["history"].sort_values(["policy_id", "month_index"])

    same_policy = history_df["policy_id"] == history_df["policy_id"].shift(1)
    prev_status = history_df["status"].shift(1)
    curr_status = history_df["status"]

    terminal_prev = prev_status.isin(["Lapsed", "Surrendered"])
    active_or_grace_curr = curr_status.isin(["Active", "Grace Period"])

    violations = (same_policy & terminal_prev & active_or_grace_curr).sum()
    assert violations == 0, f"Found {violations} illegal resurrecting transitions!"


def test_normal_population_m13_persistency_within_ojk_benchmark(dataset):
    """Ensure normal agents achieve OJK/AAJI 80%-85% benchmark at M13."""
    agents_df = dataset["agents"]
    policies_df = dataset["policies"]
    history_df = dataset["history"]

    normal_agents = set(agents_df.loc[agents_df["true_label"] == "Normal", "agent_id"])
    normal_policies = set(policies_df.loc[policies_df["agent_id"].isin(normal_agents), "policy_id"])

    norm_hist = history_df[history_df["policy_id"].isin(normal_policies)]
    m1_active = norm_hist[(norm_hist["month_index"] == 1) & (norm_hist["status"].isin(["Active", "Grace Period"]))]["policy_id"].nunique()
    m13_active = norm_hist[(norm_hist["month_index"] == 13) & (norm_hist["status"].isin(["Active", "Grace Period"]))]["policy_id"].nunique()

    persistency_m13 = m13_active / m1_active
    assert 0.80 <= persistency_m13 <= 0.85, f"Normal M13 persistency was {persistency_m13:.4f}, expected 0.80-0.85"


def test_grace_period_present_at_m11_m12(dataset):
    """Ensure policies enter Grace Period at M11-M12 for early warning."""
    history_df = dataset["history"]
    grace_m11_12 = history_df[(history_df["month_index"].isin([11, 12])) & (history_df["status"] == "Grace Period")]
    assert len(grace_m11_12) > 0, "Expected Grace Period policies at M11-M12 for early warning"
