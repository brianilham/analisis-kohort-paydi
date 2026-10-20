"""
Streamlit PyGWalker Mockup Application.

Run with:
    streamlit run mockup_app.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
from pygwalker.api.streamlit import StreamlitRenderer

from generate_data import generate_synthetic_dataset
from detector import engineer_agent_features, run_two_tier_detection


st.set_page_config(
    page_title="PAYDI Agent Risk Mockup (PyGWalker)",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Mockup Visualisasi Interaktif PyGWalker: Analisis Persistensi & Anomali Agen (PAYDI)")
st.markdown(
    """
    Mockup visualisasi ini menggunakan library **PyGWalker** (Graphic Walker) untuk memberikan kemampuan 
    eksplorasi data ala *Tableau/Power BI* secara langsung di browser:
    - **Drag & drop** variabel (dimensi & metrik) ke *Rows*, *Columns*, *Color*, atau *Size*.
    - Visualisasikan hubungan antar fitur: `lapse_shock_vol`, `lapse_shock_ape`, `ape_disparity_ratio`, `cash_payment_ratio`, dan `anomaly_score`.
    - Bandingkan hasil deteksi `risk_category` Two-Tier terhadap label aktual `true_label`.
    """
)


@st.cache_data
def load_and_process_data():
    data_dir = Path("data")
    if (data_dir / "agents.csv").exists() and (data_dir / "policies.csv").exists():
        agents_df = pd.read_csv(data_dir / "agents.csv")
        policies_df = pd.read_csv(data_dir / "policies.csv")
        history_df = pd.read_csv(data_dir / "policy_monthly_status.csv")
    else:
        dataset = generate_synthetic_dataset()
        agents_df, policies_df, history_df = (
            dataset["agents"],
            dataset["policies"],
            dataset["history"],
        )

    feat_df = engineer_agent_features(agents_df, policies_df, history_df)
    detected_df = run_two_tier_detection(feat_df)

    if "true_label" in agents_df.columns:
        detected_df = detected_df.merge(
            agents_df[["agent_id", "true_label"]],
            on="agent_id",
            how="left",
        )

    detected_df["total_ape_juta"] = (detected_df["total_ape"] / 1_000_000).round(2)
    detected_df["grace_m11_m12_ape_juta"] = (detected_df["grace_period_m11_m12_ape"] / 1_000_000).round(2)
    return detected_df


df = load_and_process_data()

st.sidebar.header("Data Overview")
st.sidebar.metric("Total Agen", len(df))
st.sidebar.metric("Tier 1 Violations", int(df["tier1_violation"].sum()))
st.sidebar.metric("Tier 2 ML Anomalies", int(df["tier2_anomaly"].sum()))

renderer = StreamlitRenderer(df, spec="", spec_type="json")
renderer.render_explore()
