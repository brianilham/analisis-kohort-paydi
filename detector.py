"""
PAYDI Cohort Analytics Engine, Feature Engineering & Two-Tier Anomaly Detector.

Implements:
1. Multi-dimensional filtering (channel, branch, agent).
2. 2D Cohort Persistence Matrices (Volume vs APE M1-M24) and discrepancy tracking.
3. Early Warning Grace Period extraction (M11-M12).
4. 4D Multivariate Agent Feature Engineering (Lapse Shock Vol, Lapse Shock APE,
   APE Disparity Ratio, Payment Method Risk Concentration).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


def filter_dataset(
    agents_df: pd.DataFrame,
    policies_df: pd.DataFrame,
    history_df: pd.DataFrame,
    channel: Optional[Union[str, List[str]]] = None,
    branch_office: Optional[Union[str, List[str]]] = None,
    agent_ids: Optional[Union[str, List[str]]] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Filter agents, policies, and history by channel, branch, and/or agent ID,
    preserving full referential integrity.
    """
    filtered_agents = agents_df.copy()

    if channel:
        channels = [channel] if isinstance(channel, str) else channel
        filtered_agents = filtered_agents[filtered_agents["channel"].isin(channels)]

    if branch_office:
        branches = [branch_office] if isinstance(branch_office, str) else branch_office
        filtered_agents = filtered_agents[filtered_agents["branch_office"].isin(branches)]

    if agent_ids:
        ids = [agent_ids] if isinstance(agent_ids, str) else agent_ids
        filtered_agents = filtered_agents[filtered_agents["agent_id"].isin(ids)]

    active_agent_ids = set(filtered_agents["agent_id"])
    filtered_policies = policies_df[policies_df["agent_id"].isin(active_agent_ids)].copy()

    active_policy_ids = set(filtered_policies["policy_id"])
    filtered_history = history_df[history_df["policy_id"].isin(active_policy_ids)].copy()

    return {
        "agents": filtered_agents,
        "policies": filtered_policies,
        "history": filtered_history,
    }


def calculate_cohort_matrices(
    policies_df: pd.DataFrame,
    history_df: pd.DataFrame,
    active_statuses: Tuple[str, ...] = ("Active", "Grace Period"),
) -> Dict[str, Union[pd.DataFrame, Dict[str, float]]]:
    """
    Calculate 2D Cohort Retention Matrices (Volume & APE) from M1 to M24.

    Formulas:
    - Persistency_Vol(Mt) = (Active Policies at Mt / Initial Cohort Policies M1) * 100%
    - Persistency_APE(Mt) = (Active APE at Mt / Initial Cohort APE M1) * 100%
    - Discrepancy Matrix = Persistency_Vol - Persistency_APE
    """
    if len(policies_df) == 0 or len(history_df) == 0:
        empty_df = pd.DataFrame()
        return {
            "volume_matrix": empty_df,
            "ape_matrix": empty_df,
            "discrepancy_matrix": empty_df,
            "m13_summary": {
                "m13_vol_persistency": 0.0,
                "m13_ape_persistency": 0.0,
                "leakage_gap": 0.0,
            },
        }

    # Join history with policies for cohort month and APE
    merged = history_df.merge(
        policies_df[["policy_id", "cohort_month", "ape"]],
        on="policy_id",
        how="inner",
    )

    cohorts = sorted(policies_df["cohort_month"].unique())
    months = [f"M{m}" for m in range(1, 25)]

    # Initial cohort denominators (M1 totals)
    init_vol = policies_df.groupby("cohort_month")["policy_id"].nunique()
    init_ape = policies_df.groupby("cohort_month")["ape"].sum()

    # Active status indicator
    merged["is_active"] = merged["status"].isin(active_statuses)
    merged["active_ape"] = np.where(merged["is_active"], merged["ape"], 0.0)

    # Aggregate by cohort_month and month_index
    agg = merged.groupby(["cohort_month", "month_index"]).agg(
        active_policies=("is_active", "sum"),
        active_ape=("active_ape", "sum"),
    ).reset_index()

    # Pivot into matrices
    vol_pivot = agg.pivot(index="cohort_month", columns="month_index", values="active_policies")
    ape_pivot = agg.pivot(index="cohort_month", columns="month_index", values="active_ape")

    # Reindex to ensure all 24 cohorts and months exist
    vol_pivot = vol_pivot.reindex(index=cohorts, columns=range(1, 25)).fillna(0)
    ape_pivot = ape_pivot.reindex(index=cohorts, columns=range(1, 25)).fillna(0)

    # Normalize by initial cohort totals
    vol_matrix_pct = (vol_pivot.div(init_vol, axis=0) * 100.0).round(2)
    ape_matrix_pct = (ape_pivot.div(init_ape, axis=0) * 100.0).round(2)

    vol_matrix_pct.columns = months
    ape_matrix_pct.columns = months

    # Discrepancy Matrix (Volume % - APE %) -> positive indicates premium leakage
    discrepancy_matrix = (vol_matrix_pct - ape_matrix_pct).round(2)

    # Summary metrics at M13
    m13_vol = float(vol_matrix_pct["M13"].mean()) if "M13" in vol_matrix_pct else 0.0
    m13_ape = float(ape_matrix_pct["M13"].mean()) if "M13" in ape_matrix_pct else 0.0
    leakage_gap = round(m13_vol - m13_ape, 2)

    return {
        "volume_matrix": vol_matrix_pct,
        "ape_matrix": ape_matrix_pct,
        "discrepancy_matrix": discrepancy_matrix,
        "m13_summary": {
            "m13_vol_persistency": round(m13_vol, 2),
            "m13_ape_persistency": round(m13_ape, 2),
            "leakage_gap": leakage_gap,
        },
    }


def extract_grace_period_watch(
    policies_df: pd.DataFrame,
    history_df: pd.DataFrame,
    months: Tuple[int, ...] = (11, 12),
) -> pd.DataFrame:
    """
    Extract policies currently or historically in Grace Period at critical M11-M12 window.
    Enables proactive retention initiatives before M13 lapse.
    """
    grace_hist = history_df[
        (history_df["month_index"].isin(months)) & (history_df["status"] == "Grace Period")
    ]

    watch_df = grace_hist.merge(
        policies_df[["policy_id", "agent_id", "cohort_month", "ape", "payment_method"]],
        on="policy_id",
        how="inner",
    )
    return watch_df.sort_values(["month_index", "ape"], ascending=[True, False]).reset_index(drop=True)


def engineer_agent_features(
    agents_df: pd.DataFrame,
    policies_df: pd.DataFrame,
    history_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Engineers agent-level multivariate feature vector across 4 core risk dimensions:
    1. lapse_shock_vol: Delta Persistency Volume (M12 - M13)
    2. lapse_shock_ape: Delta Persistency APE (M12 - M13)
    3. ape_disparity_ratio: Mean APE of lapsed policies / Mean APE of active policies at M13
    4. cash_payment_ratio: Proportion of Manual/Cash payment method
    """
    # Merge policies with status at month 12 and month 13
    m12_status = history_df[history_df["month_index"] == 12][["policy_id", "status"]].rename(
        columns={"status": "status_m12"}
    )
    m13_status = history_df[history_df["month_index"] == 13][["policy_id", "status"]].rename(
        columns={"status": "status_m13"}
    )

    p_joined = policies_df.merge(m12_status, on="policy_id", how="left")
    p_joined = p_joined.merge(m13_status, on="policy_id", how="left")

    active_statuses = {"Active", "Grace Period"}
    p_joined["is_active_m12"] = p_joined["status_m12"].isin(active_statuses)
    p_joined["is_active_m13"] = p_joined["status_m13"].isin(active_statuses)

    p_joined["active_ape_m12"] = np.where(p_joined["is_active_m12"], p_joined["ape"], 0.0)
    p_joined["active_ape_m13"] = np.where(p_joined["is_active_m13"], p_joined["ape"], 0.0)

    # Grace period in M11 or M12
    gp_hist = history_df[
        (history_df["month_index"].isin([11, 12])) & (history_df["status"] == "Grace Period")
    ]
    gp_per_policy = gp_hist.groupby("policy_id")["month_index"].count().rename("gp_count")
    p_joined = p_joined.merge(gp_per_policy, on="policy_id", how="left")
    p_joined["gp_count"] = p_joined["gp_count"].fillna(0)

    # Group by agent
    records = []
    grouped = p_joined.groupby("agent_id")

    for agent_id, group in grouped:
        n_pols = len(group)
        total_ape = float(group["ape"].sum())

        # Volume persistency at M12 & M13
        n_active_m12 = group["is_active_m12"].sum()
        n_active_m13 = group["is_active_m13"].sum()
        vol_p_m12 = (n_active_m12 / n_pols * 100.0) if n_pols > 0 else 0.0
        vol_p_m13 = (n_active_m13 / n_pols * 100.0) if n_pols > 0 else 0.0
        lapse_shock_vol = max(0.0, vol_p_m12 - vol_p_m13)

        # APE persistency at M12 & M13
        ape_active_m12 = float(group["active_ape_m12"].sum())
        ape_active_m13 = float(group["active_ape_m13"].sum())
        ape_p_m12 = (ape_active_m12 / total_ape * 100.0) if total_ape > 0 else 0.0
        ape_p_m13 = (ape_active_m13 / total_ape * 100.0) if total_ape > 0 else 0.0
        lapse_shock_ape = max(0.0, ape_p_m12 - ape_p_m13)

        # APE Disparity Ratio at M13: Mean APE of lapsed / Mean APE of active
        lapsed_m13 = group[~group["is_active_m13"]]
        active_m13 = group[group["is_active_m13"]]

        mean_lapsed_ape = float(lapsed_m13["ape"].mean()) if len(lapsed_m13) > 0 else 0.0
        mean_active_ape = float(active_m13["ape"].mean()) if len(active_m13) > 0 else 0.0

        if mean_active_ape > 0 and mean_lapsed_ape > 0:
            disparity_ratio = mean_lapsed_ape / mean_active_ape
        elif mean_lapsed_ape > 0:
            disparity_ratio = 2.5
        else:
            disparity_ratio = 1.0

        # Cash / Manual payment concentration
        n_cash = (group["payment_method"] == "Manual/Cash").sum()
        cash_ratio = (n_cash / n_pols * 100.0) if n_pols > 0 else 0.0

        # Grace period counts and APE
        gp_count = int(group["gp_count"].sum())
        gp_ape = float(group.loc[group["gp_count"] > 0, "ape"].sum())

        records.append(
            {
                "agent_id": agent_id,
                "total_policies": n_pols,
                "total_ape": total_ape,
                "m12_vol_persistency": round(vol_p_m12, 2),
                "m13_vol_persistency": round(vol_p_m13, 2),
                "lapse_shock_vol": round(lapse_shock_vol, 2),
                "m12_ape_persistency": round(ape_p_m12, 2),
                "m13_ape_persistency": round(ape_p_m13, 2),
                "lapse_shock_ape": round(lapse_shock_ape, 2),
                "ape_disparity_ratio": round(disparity_ratio, 2),
                "cash_payment_ratio": round(cash_ratio, 2),
                "grace_period_m11_m12_count": gp_count,
                "grace_period_m11_m12_ape": gp_ape,
            }
        )

    features_df = pd.DataFrame(records)

    # Merge with master agent attributes
    merged_features = agents_df[
        ["agent_id", "agent_name", "channel", "branch_office", "join_date"]
    ].merge(features_df, on="agent_id", how="left")

    # Safety fill for agents without policies (if any)
    fill_defaults = {
        "total_policies": 0,
        "total_ape": 0.0,
        "m12_vol_persistency": 0.0,
        "m13_vol_persistency": 0.0,
        "lapse_shock_vol": 0.0,
        "m12_ape_persistency": 0.0,
        "m13_ape_persistency": 0.0,
        "lapse_shock_ape": 0.0,
        "ape_disparity_ratio": 1.0,
        "cash_payment_ratio": 0.0,
        "grace_period_m11_m12_count": 0,
        "grace_period_m11_m12_ape": 0.0,
    }
    merged_features = merged_features.fillna(value=fill_defaults)

    return merged_features
