"""
Script to generate an interactive PyGWalker visualization mockup.
Saves a standalone interactive HTML file `pygwalker_mockup.html`.
"""

from pathlib import Path
import pandas as pd
import pygwalker as pyg

from generate_data import generate_synthetic_dataset
from detector import engineer_agent_features, run_two_tier_detection


def create_mockup():
    data_dir = Path("data")
    if (data_dir / "agents.csv").exists() and (data_dir / "policies.csv").exists():
        print("Loading existing dataset from data/ ...")
        agents_df = pd.read_csv(data_dir / "agents.csv")
        policies_df = pd.read_csv(data_dir / "policies.csv")
        history_df = pd.read_csv(data_dir / "policy_monthly_status.csv")
    else:
        print("Generating fresh synthetic dataset...")
        dataset = generate_synthetic_dataset()
        agents_df, policies_df, history_df = (
            dataset["agents"],
            dataset["policies"],
            dataset["history"],
        )

    print("Engineering 4D agent features & running Two-Tier anomaly detection...")
    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    detected_df = run_two_tier_detection(feat_df)

    # Enrich with ground-truth for comparison in PyGWalker exploration
    if "true_label" in agents_df.columns:
        detected_df = detected_df.merge(
            agents_df[["agent_id", "true_label"]],
            on="agent_id",
            how="left",
        )

    # Format APE into millions (IDR) for cleaner visualization axis
    detected_df["total_ape_millions"] = (detected_df["total_ape"] / 1_000_000).round(2)
    detected_df["grace_period_m11_m12_ape_millions"] = (
        detected_df["grace_period_m11_m12_ape"] / 1_000_000
    ).round(2)

    print("Generating PyGWalker HTML mockup...")
    html_content = pyg.to_html(
        detected_df,
        spec="",
        theme_key="vega",
        default_tab="data",
    )

    output_path = Path("pygwalker_mockup.html")
    output_path.write_text(html_content, encoding="utf-8")
    print(f"Mockup generated successfully at: {output_path.resolve()}")
    return output_path


if __name__ == "__main__":
    create_mockup()
