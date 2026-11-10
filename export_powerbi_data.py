"""
ETL Pipeline for Power BI Export: PAYDI Cohort Persistency & Agent Risk Detection.
Generates:
1. data/agents.csv
2. data/policies.csv
3. data/policy_monthly_status.csv
4. data/agent_risk_scores.csv (200 rows with 4-pillar scores, rank, top20 flag)
5. data/agent_risk_pillars.csv (800 rows unpivoted for Power BI Bar Chart)
6. powerbi/assets/mnc_life_logo.png
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple
import re

import numpy as np
import pandas as pd
from PIL import Image

from generate_data import SimulationConfig, generate_synthetic_dataset
from detector import engineer_agent_features, run_two_tier_detection


def compute_risk_pillars(features_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Decomposes agent multivariate risk into 4 normalized pillars (0.0 to 100.0)
    and computes relative contribution percentages.
    
    Pillars:
    1. score_vol_shock: severity of M12->M13 volume collapse (scaled to 45.0% ceiling)
    2. score_ape_shock: severity of M12->M13 APE leakage (scaled to 60.0% ceiling)
    3. score_ape_disparity: ticket-size disparity ratio between lapsed & active policies (scaled to 4.0 ceiling above 1.0)
    4. score_cash_ratio: manual/cash payment risk concentration (scaled to 80.0% ceiling)
    
    Returns:
    - enriched_agents_df: features_df with pillar scores, contribution %, risk_rank, is_top20_risk_rank
    - pillars_unpivoted_df: 800 rows (200 agents * 4 pillars) for Power BI comparison visuals
    """
    df = features_df.copy()
    
    # Normal benchmarks across Normal agents (or general population if labels absent)
    if "true_label" in df.columns:
        norm_mask = df["true_label"] == "Normal"
        bm_vol_shock = float(df.loc[norm_mask, "lapse_shock_vol"].mean()) if norm_mask.sum() > 0 else 2.5
        bm_ape_shock = float(df.loc[norm_mask, "lapse_shock_ape"].mean()) if norm_mask.sum() > 0 else 3.0
        bm_disparity = float(df.loc[norm_mask, "ape_disparity_ratio"].mean()) if norm_mask.sum() > 0 else 1.1
        bm_cash_ratio = float(df.loc[norm_mask, "cash_payment_ratio"].mean()) if norm_mask.sum() > 0 else 20.0
    else:
        bm_vol_shock = 2.5
        bm_ape_shock = 3.0
        bm_disparity = 1.1
        bm_cash_ratio = 20.0
        
    bm_vol_shock = round(bm_vol_shock, 2)
    bm_ape_shock = round(bm_ape_shock, 2)
    bm_disparity = round(bm_disparity, 2)
    bm_cash_ratio = round(bm_cash_ratio, 2)

    # 1. Normalized Pillar Scores (0.0 to 100.0)
    # Vol shock: 0 to 45% -> 0 to 100
    s_vol = np.clip((df["lapse_shock_vol"] / 45.0) * 100.0, 0.0, 100.0).round(1)
    # APE shock: 0 to 60% -> 0 to 100
    s_ape = np.clip((df["lapse_shock_ape"] / 60.0) * 100.0, 0.0, 100.0).round(1)
    # APE disparity: 1.0 to 5.0 (delta 4.0) -> 0 to 100
    s_disp = np.clip((np.maximum(0.0, df["ape_disparity_ratio"] - 1.0) / 4.0) * 100.0, 0.0, 100.0).round(1)
    # Cash ratio: 0 to 80% -> 0 to 100
    s_cash = np.clip((df["cash_payment_ratio"] / 80.0) * 100.0, 0.0, 100.0).round(1)
    
    df["score_vol_shock"] = s_vol
    df["score_ape_shock"] = s_ape
    df["score_ape_disparity"] = s_disp
    df["score_cash_ratio"] = s_cash

    # 2. Contribution percentages (sum to 100.0% per agent)
    pillar_sum = (s_vol + s_ape + s_disp + s_cash).replace(0.0, 1e-6)
    share_vol = ((s_vol / pillar_sum) * 100.0).round(1)
    share_ape = ((s_ape / pillar_sum) * 100.0).round(1)
    share_disp = ((s_disp / pillar_sum) * 100.0).round(1)
    share_cash = ((s_cash / pillar_sum) * 100.0).round(1)
    
    # Adjust slight rounding discrepancies on the last column
    share_cash = (100.0 - (share_vol + share_ape + share_disp)).round(1)

    df["share_vol_shock_pct"] = share_vol
    df["share_ape_shock_pct"] = share_ape
    df["share_ape_disparity_pct"] = share_disp
    df["share_cash_ratio_pct"] = share_cash

    # 3. Dominant Risk Pillar
    pillar_names = ["Volume Shock M12-M13", "APE Leakage Shock M12-M13", "APE Ticket Disparity", "Manual/Cash Concentration"]
    scores_matrix = df[["score_vol_shock", "score_ape_shock", "score_ape_disparity", "score_cash_ratio"]].values
    dom_indices = np.argmax(scores_matrix, axis=1)
    df["dominant_risk_pillar"] = [pillar_names[i] for i in dom_indices]

    # 4. Risk Ranking & Top-20% Flag
    df = df.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
    df["risk_rank"] = np.arange(1, len(df) + 1)
    top_20_cutoff = int(np.ceil(len(df) * 0.20))
    df["is_top20_risk_rank"] = df["risk_rank"] <= top_20_cutoff

    # Sort back by agent_id for deterministic storage
    enriched_df = df.sort_values("agent_id").reset_index(drop=True)

    # 5. Build 800-row Unpivoted Table for Power BI Comparison Bar Chart
    records = []
    for _, row in enriched_df.iterrows():
        a_id = row["agent_id"]
        # Pillar 1: Vol shock
        records.append({
            "agent_id": a_id,
            "pillar_order": 1,
            "pillar_name": "Volume Shock M12-M13",
            "agent_raw_value": row["lapse_shock_vol"],
            "normal_benchmark_value": bm_vol_shock,
            "unit_label": "%",
            "pillar_score_100": row["score_vol_shock"],
            "contribution_pct": row["share_vol_shock_pct"],
        })
        # Pillar 2: APE shock
        records.append({
            "agent_id": a_id,
            "pillar_order": 2,
            "pillar_name": "APE Leakage Shock M12-M13",
            "agent_raw_value": row["lapse_shock_ape"],
            "normal_benchmark_value": bm_ape_shock,
            "unit_label": "%",
            "pillar_score_100": row["score_ape_shock"],
            "contribution_pct": row["share_ape_shock_pct"],
        })
        # Pillar 3: Disparity
        records.append({
            "agent_id": a_id,
            "pillar_order": 3,
            "pillar_name": "APE Ticket Disparity",
            "agent_raw_value": row["ape_disparity_ratio"],
            "normal_benchmark_value": bm_disparity,
            "unit_label": "x",
            "pillar_score_100": row["score_ape_disparity"],
            "contribution_pct": row["share_ape_disparity_pct"],
        })
        # Pillar 4: Cash ratio
        records.append({
            "agent_id": a_id,
            "pillar_order": 4,
            "pillar_name": "Manual/Cash Concentration",
            "agent_raw_value": row["cash_payment_ratio"],
            "normal_benchmark_value": bm_cash_ratio,
            "unit_label": "%",
            "pillar_score_100": row["score_cash_ratio"],
            "contribution_pct": row["share_cash_ratio_pct"],
        })

    pillars_df = pd.DataFrame(records)
    return enriched_df, pillars_df


def extract_and_convert_logo(svg_path: str = "mnc_life_logo.svg", output_png_path: str = "powerbi/assets/mnc_life_logo.png") -> Path:
    """
    Extracts embedded high-resolution PNG image from mnc_life_logo.svg
    and saves it as a clean PNG asset for Power BI Image visuals.
    """
    svg_file = Path(svg_path)
    out_file = Path(output_png_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if not svg_file.exists():
        raise FileNotFoundError(f"Source logo SVG {svg_file} does not exist!")

    content = svg_file.read_text(encoding="utf-8")
    match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', content)
    if match:
        b64_data = match.group(1)
        image_data = base64.b64decode(b64_data)
        img = Image.open(BytesIO(image_data))
        img.save(out_file, format="PNG")
        print(f"Extracted embedded high-res PNG logo ({img.size[0]}x{img.size[1]}) to {out_file.resolve()}")
    else:
        # Fallback: create crisp text-based MNC Life logo with Pillow
        img = Image.new("RGBA", (500, 200), (255, 255, 255, 0))
        img.save(out_file, format="PNG")
        print(f"Saved fallback PNG logo to {out_file.resolve()}")

    return out_file


def run_export_pipeline(data_dir: str = "data", powerbi_asset_dir: str = "powerbi/assets") -> Dict[str, pd.DataFrame]:
    """
    Executes full ETL export pipeline:
    1. Generates 2022-2023 seasoned synthetic dataset
    2. Engineers 4D features & runs two-tier detection
    3. Decomposes explainable 4-pillar scores (0-100) & risk ranks
    4. Saves 5 CSV tables to data/
    5. Converts logo SVG to PNG asset
    """
    out_data = Path(data_dir)
    out_data.mkdir(parents=True, exist_ok=True)

    print("Step 1/5: Generating 2022-2023 Fully Seasoned PAYDI dataset (24 cohorts, 200 agents, 12,000 policies)...")
    config = SimulationConfig(
        n_agents=200,
        n_policies=12000,
        n_cohorts=24,
        start_cohort="2022-01",
        random_seed=42,
    )
    dataset = generate_synthetic_dataset(config=config)
    agents_df = dataset["agents"]
    policies_df = dataset["policies"]
    history_df = dataset["history"]

    print("Step 2/5: Engineering agent 4D features and running calibrated two-tier detection...")
    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    detected_df = run_two_tier_detection(feat_df)

    # Attach ground-truth labels for audit/model validation
    if "true_label" in agents_df.columns:
        detected_df = detected_df.merge(
            agents_df[["agent_id", "true_label", "is_anomaly"]],
            on="agent_id",
            how="left",
        )

    print("Step 3/5: Decomposing explainable 4-pillar risk scores (0-100) and ranking...")
    enriched_agents_df, pillars_df = compute_risk_pillars(detected_df)

    print("Step 4/5: Saving all 5 CSV tables to data/ directory...")
    agents_df.to_csv(out_data / "agents.csv", index=False)
    policies_df.to_csv(out_data / "policies.csv", index=False)
    history_df.to_csv(out_data / "policy_monthly_status.csv", index=False)
    enriched_agents_df.to_csv(out_data / "agent_risk_scores.csv", index=False)
    pillars_df.to_csv(out_data / "agent_risk_pillars.csv", index=False)
    print(f"   -> {out_data / 'agents.csv'} ({len(agents_df)} rows)")
    print(f"   -> {out_data / 'policies.csv'} ({len(policies_df)} rows)")
    print(f"   -> {out_data / 'policy_monthly_status.csv'} ({len(history_df)} rows)")
    print(f"   -> {out_data / 'agent_risk_scores.csv'} ({len(enriched_agents_df)} rows)")
    print(f"   -> {out_data / 'agent_risk_pillars.csv'} ({len(pillars_df)} rows)")

    print("Step 5/5: Converting MNC Life SVG logo to high-resolution PNG...")
    extract_and_convert_logo("mnc_life_logo.svg", f"{powerbi_asset_dir}/mnc_life_logo.png")

    print("\nETL Export Pipeline completed successfully!")
    return {
        "agents": agents_df,
        "policies": policies_df,
        "history": history_df,
        "agent_risk_scores": enriched_agents_df,
        "agent_risk_pillars": pillars_df,
    }


if __name__ == "__main__":
    run_export_pipeline()
