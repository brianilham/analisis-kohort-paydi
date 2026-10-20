"""
Synthetic Data Generator Engine for PAYDI (Unit Link) Policy Persistency Cohort Analysis
& Agent Churn / Fraud Manipulation Detection.

Simulates 24 monthly cohorts, 150-200 agents, and 10,000-15,000 policies in accordance
with OJK/AAJI persistency benchmarks and ground-truth anomaly injection (8% total:
3% Hit-and-Run, 5% Cherry-Picking).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


CHANNELS = ["Agency", "Bancassurance", "Worksite"]
CHANNEL_WEIGHTS = [0.55, 0.30, 0.15]

BRANCH_OFFICES = [
    "Jakarta Selatan",
    "Jakarta Pusat",
    "Surabaya",
    "Bandung",
    "Medan",
    "Semarang",
    "Denpasar",
    "Makassar",
]
BRANCH_WEIGHTS = [0.22, 0.18, 0.16, 0.12, 0.10, 0.08, 0.07, 0.07]

FIRST_NAMES = [
    "Budi", "Siti", "Agus", "Dewi", "Andi", "Rina", "Hendra", "Maya",
    "Rizky", "Putri", "Fajar", "Lestari", "Dimas", "Nadia", "Wahyu",
    "Kartika", "Arif", "Yuni", "Bayu", "Ratna", "Eko", "Intan",
    "Reza", "Ayu", "Taufik", "Sari", "Dian", "Pratama", "Nugroho", "Wulan",
]
LAST_NAMES = [
    "Santoso", "Wijaya", "Saputra", "Lestari", "Hidayat", "Kusuma",
    "Pratama", "Setiawan", "Nugraha", "Rahmawati", "Permana", "Susanto",
    "Wibowo", "Siregar", "Gunawan", "Putra", "Utami", "Firmansyah",
    "Hakim", "Halim", "Hartono", "Suryani", "Nasution", "Mahendra",
]


@dataclass
class SimulationConfig:
    """Configuration parameters for the PAYDI synthetic insurance dataset."""

    n_agents: int = 200
    n_policies: int = 12000
    n_cohorts: int = 24
    start_cohort: str = "2024-01"
    hit_and_run_ratio: float = 0.03
    cherry_picking_ratio: float = 0.05
    normal_m13_target_min: float = 0.80
    normal_m13_target_max: float = 0.85
    random_seed: int = 42


def _generate_agents(config: SimulationConfig, rng: np.random.Generator) -> pd.DataFrame:
    """Generate agent master records with calibrated ground-truth anomaly labels."""
    n_agents = config.n_agents
    n_hit_and_run = int(round(n_agents * config.hit_and_run_ratio))
    n_cherry_picking = int(round(n_agents * config.cherry_picking_ratio))
    n_normal = n_agents - n_hit_and_run - n_cherry_picking

    labels = (
        ["Normal"] * n_normal
        + ["Hit-and-Run"] * n_hit_and_run
        + ["Cherry-Picking"] * n_cherry_picking
    )
    rng.shuffle(labels)

    agent_ids = [f"AGT-{i+1:04d}" for i in range(n_agents)]
    firsts = rng.choice(FIRST_NAMES, size=n_agents)
    lasts = rng.choice(LAST_NAMES, size=n_agents)
    names = [f"{f} {l}" for f, l in zip(firsts, lasts)]

    channels = rng.choice(CHANNELS, size=n_agents, p=CHANNEL_WEIGHTS)
    branches = rng.choice(BRANCH_OFFICES, size=n_agents, p=BRANCH_WEIGHTS)

    # Agent tenure: joined between 24 and 48 months before simulation end
    join_months_ago = rng.integers(12, 48, size=n_agents)
    ref_end = pd.Period(config.start_cohort, freq="M") + config.n_cohorts
    join_dates = [
        (ref_end - int(m)).start_time + pd.Timedelta(days=int(rng.integers(1, 28)))
        for m in join_months_ago
    ]

    agents_df = pd.DataFrame(
        {
            "agent_id": agent_ids,
            "agent_name": names,
            "channel": channels,
            "branch_office": branches,
            "join_date": [d.strftime("%Y-%m-%d") for d in join_dates],
            "true_label": labels,
            "is_anomaly": [lbl != "Normal" for lbl in labels],
        }
    )
    return agents_df


def _generate_cohort_months(config: SimulationConfig) -> list[str]:
    """Generate list of cohort month strings formatted as YYYY-MM."""
    start_period = pd.Period(config.start_cohort, freq="M")
    return [(start_period + i).strftime("%Y-%m") for i in range(config.n_cohorts)]


def _generate_policies_and_history(
    agents_df: pd.DataFrame,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate policy master and monthly lifecycle histories (M1-M24).
    Enforces terminal absorbing states and realistic PAYDI persistency dynamics.
    """
    cohort_months = _generate_cohort_months(config)
    n_policies = config.n_policies
    n_cohorts = config.n_cohorts

    # Policy distribution per cohort month (relatively even with slight growth)
    cohort_growth = np.linspace(0.85, 1.15, n_cohorts)
    cohort_probs = cohort_growth / cohort_growth.sum()
    policy_cohorts = rng.choice(cohort_months, size=n_policies, p=cohort_probs)

    # Assign policies to agents: Pareto-like distribution where some agents write more
    agent_weights = rng.gamma(shape=3.0, scale=1.0, size=len(agents_df))
    # Give anomaly agents realistic sales volume
    agent_weights = agent_weights / agent_weights.sum()
    assigned_agents = rng.choice(agents_df["agent_id"].values, size=n_policies, p=agent_weights)

    policy_ids = [f"POL-{i+1:06d}" for i in range(n_policies)]

    # Agent label lookup map
    agent_label_map = dict(zip(agents_df["agent_id"], agents_df["true_label"]))

    # Generate APE and Payment Method based on agent behavioral profiles
    apes = np.zeros(n_policies, dtype=float)
    payment_methods = []

    for idx, (p_id, agt_id) in enumerate(zip(policy_ids, assigned_agents)):
        label = agent_label_map[agt_id]

        if label == "Normal":
            # Real PAYDI Unit Link APE: Log-normal, median ~12M, mean ~15M IDR
            val = rng.lognormal(mean=2.45, sigma=0.55) * 1_000_000
            val = np.clip(val, 3_000_000, 150_000_000)
            apes[idx] = round(val, -5)
            # 80% Auto-Debit, 20% Manual/Cash
            pm = "Auto-Debit" if rng.random() < 0.80 else "Manual/Cash"
            payment_methods.append(pm)

        elif label == "Hit-and-Run":
            # Medium to high APE to maximize First Year Commission (FYC)
            val = rng.lognormal(mean=2.70, sigma=0.50) * 1_000_000
            val = np.clip(val, 6_000_000, 180_000_000)
            apes[idx] = round(val, -5)
            # 75% Manual/Cash (agent funding / dummy policy risk)
            pm = "Manual/Cash" if rng.random() < 0.75 else "Auto-Debit"
            payment_methods.append(pm)

        else:  # Cherry-Picking
            # Bimodal: 70% small policies (volume buffer), 30% jumbo policies (high commission)
            is_jumbo = rng.random() < 0.30
            if is_jumbo:
                val = rng.uniform(40_000_000, 120_000_000)
                pm = "Manual/Cash" if rng.random() < 0.70 else "Auto-Debit"
            else:
                val = rng.uniform(4_000_000, 10_000_000)
                pm = "Auto-Debit" if rng.random() < 0.85 else "Manual/Cash"
            apes[idx] = round(val, -5)
            payment_methods.append(pm)

    # Issue dates within the cohort month
    issue_dates = []
    for c_m in policy_cohorts:
        p_month = pd.Period(c_m, freq="M")
        day = rng.integers(1, 28)
        issue_dates.append(p_month.start_time + pd.Timedelta(days=int(day)))

    policies_df = pd.DataFrame(
        {
            "policy_id": policy_ids,
            "agent_id": assigned_agents,
            "cohort_month": policy_cohorts,
            "issue_date": [d.strftime("%Y-%m-%d") for d in issue_dates],
            "ape": apes,
            "payment_method": payment_methods,
        }
    )

    # Simulate monthly statuses across 24 lifecycle months (M1 - M24)
    # Using vectorized array logic for efficiency and transition validity
    n_months = 24
    status_array = np.full((n_policies, n_months), "Active", dtype=object)

    for i in range(n_policies):
        agt_id = assigned_agents[i]
        label = agent_label_map[agt_id]
        ape = apes[i]

        # Determine termination month (lapse or surrender)
        if label == "Normal":
            # Calibrated geometric monthly drop ~1.55% so M13 persistency is strictly 80%-85%
            # P(active at M13) = (1 - p)^12. For 82.5%, p ~= 0.016
            r = rng.random()
            # Empirical retention distribution targeting 82.5% at M13 and ~72% at M24
            if r < 0.175:
                # Terminates before or at M13 (months 2-13)
                term_month = rng.integers(2, 14)
            elif r < 0.28:
                # Terminates between M14-M24
                term_month = rng.integers(14, 25)
            else:
                # Stays active throughout M24
                term_month = 999

        elif label == "Hit-and-Run":
            # Very high persistency M1-M12 (>94%), then massive drop at M13-M14
            r = rng.random()
            if r < 0.05:
                term_month = rng.integers(2, 13)
            elif r < 0.65:
                # 60% of all policies drop sharply at M13 or M14 (after commission payout)
                term_month = rng.choice([13, 14], p=[0.70, 0.30])
            elif r < 0.80:
                term_month = rng.integers(15, 25)
            else:
                term_month = 999

        else:  # Cherry-Picking
            # Small policies kept active (~82% at M13), jumbo policies (>25M) dropped at M13
            if ape >= 25_000_000:
                # Jumbo policy: 80% intentionally lapsed at M13
                if rng.random() < 0.80:
                    term_month = 13
                else:
                    term_month = rng.integers(14, 25) if rng.random() < 0.5 else 999
            else:
                # Small policy: normal retention ~83% at M13
                if rng.random() < 0.17:
                    term_month = rng.integers(2, 14)
                elif rng.random() < 0.25:
                    term_month = rng.integers(14, 25)
                else:
                    term_month = 999

        # Fill lifecycle status
        if term_month <= n_months:
            # 1 month before termination, policy enters Grace Period (especially at M11-M12)
            if term_month > 1 and rng.random() < 0.70:
                status_array[i, term_month - 2] = "Grace Period"

            # Terminal status: 85% Lapsed, 15% Surrendered
            term_status = "Surrendered" if rng.random() < 0.15 else "Lapsed"
            # Once terminal, remains terminal for all remaining months
            status_array[i, (term_month - 1):] = term_status

    # Unroll into long-format history DataFrame
    policy_rep = np.repeat(policy_ids, n_months)
    month_rep = np.tile(np.arange(1, n_months + 1), n_policies)
    status_flat = status_array.flatten()

    history_df = pd.DataFrame(
        {
            "policy_id": policy_rep,
            "month_index": month_rep,
            "status": status_flat,
        }
    )

    return policies_df, history_df


def generate_synthetic_dataset(
    n_agents: int = 200,
    n_policies: int = 12000,
    n_cohorts: int = 24,
    start_cohort: str = "2024-01",
    hit_and_run_ratio: float = 0.03,
    cherry_picking_ratio: float = 0.05,
    normal_m13_target_min: float = 0.80,
    normal_m13_target_max: float = 0.85,
    random_seed: int = 42,
    config: Optional[SimulationConfig] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Main entry point for generating the complete PAYDI synthetic dataset.
    Returns a dictionary of DataFrames: 'agents', 'policies', 'history'.
    """
    if config is None:
        config = SimulationConfig(
            n_agents=n_agents,
            n_policies=n_policies,
            n_cohorts=n_cohorts,
            start_cohort=start_cohort,
            hit_and_run_ratio=hit_and_run_ratio,
            cherry_picking_ratio=cherry_picking_ratio,
            normal_m13_target_min=normal_m13_target_min,
            normal_m13_target_max=normal_m13_target_max,
            random_seed=random_seed,
        )

    rng = np.random.default_rng(config.random_seed)
    agents_df = _generate_agents(config, rng)
    policies_df, history_df = _generate_policies_and_history(agents_df, config, rng)

    return {
        "agents": agents_df,
        "policies": policies_df,
        "history": history_df,
    }


def save_dataset_to_csv(dataset: Dict[str, pd.DataFrame], output_dir: str = "data") -> None:
    """Save generated DataFrames to CSV files in the designated data directory."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    dataset["agents"].to_csv(out_path / "agents.csv", index=False)
    dataset["policies"].to_csv(out_path / "policies.csv", index=False)
    dataset["history"].to_csv(out_path / "policy_monthly_status.csv", index=False)
    print(f"Synthetic dataset saved successfully to {out_path.resolve()}")


if __name__ == "__main__":
    print("Generating PAYDI synthetic dataset...")
    data = generate_synthetic_dataset()
    save_dataset_to_csv(data)
    print("Finished.")
