"""
Streamlit Application: Analisis Kohort Persistensi Polis & Deteksi Churn Agen (PAYDI).
Interactive Actuarial Cohort Analysis, Early Warning & Two-Tier Fraud Detection System.
"""

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import streamlit as st

from generate_data import generate_synthetic_dataset, save_dataset_to_csv
from detector import (
    filter_dataset,
    calculate_cohort_matrices,
    extract_grace_period_watch,
    engineer_agent_features,
    run_two_tier_detection,
)
from visuals import (
    calculate_dashboard_kpis,
    create_cohort_heatmap,
    create_discrepancy_heatmap,
    create_anomaly_scatter_plot,
    create_agent_drilldown_curves,
)


st.set_page_config(
    page_title="PAYDI Cohort Persistency & Agent Churn Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished financial & actuarial UI
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-ojk-pass {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-ojk-warn {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_or_generate_dataset(seed: int = 42) -> Dict[str, pd.DataFrame]:
    """Load dataset from disk or generate with specified deterministic seed."""
    data_dir = Path("data")
    agents_file = data_dir / "agents.csv"
    policies_file = data_dir / "policies.csv"
    history_file = data_dir / "policy_monthly_status.csv"

    if seed == 42 and agents_file.exists() and policies_file.exists() and history_file.exists():
        agents_df = pd.read_csv(agents_file)
        policies_df = pd.read_csv(policies_file)
        history_df = pd.read_csv(history_file)
        return {"agents": agents_df, "policies": policies_df, "history": history_df}

    dataset = generate_synthetic_dataset(random_seed=seed)
    return dataset


# ==============================================================================
# SIDEBAR: FILTERS & DETECTION CONTROLS
# ==============================================================================

with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/shield.png",
        width=56,
    )
    st.title("PAYDI Analytics")
    st.caption("Monitoring Persistensi Polis & Integritas Agen")

    st.markdown("---")
    st.subheader("⚙️ Pengaturan Data")
    sim_seed = st.number_input("Random Seed Simulasi", min_value=1, max_value=9999, value=42, step=1)
    if st.button("🔄 Muat / Reset Dataset", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    raw_data = load_or_generate_dataset(seed=int(sim_seed))

    st.markdown("---")
    st.subheader("🔍 Filter Dimensi")
    all_channels = sorted(raw_data["agents"]["channel"].unique())
    selected_channels = st.multiselect(
        "Kanal Distribusi",
        options=all_channels,
        default=all_channels,
    )

    all_branches = sorted(raw_data["agents"]["branch_office"].unique())
    selected_branches = st.multiselect(
        "Kantor Cabang",
        options=all_branches,
        default=all_branches,
    )

    st.markdown("---")
    st.subheader("🚨 Parameter Deteksi Two-Tier")
    t1_vol_shock_threshold = st.slider(
        "Tier 1: Max Δ Vol Shock M12→M13 (%)",
        min_value=10.0,
        max_value=50.0,
        value=25.0,
        step=5.0,
        help="Ambang batas toleransi penurunan jumlah polis di bulan ke-13.",
    )
    t1_m13_min_persistency = st.slider(
        "Tier 1: Min Persistensi M13 (%)",
        min_value=60.0,
        max_value=90.0,
        value=75.0,
        step=5.0,
        help="Batas toleransi kepatuhan regulasi OJK/AAJI.",
    )
    t2_contamination = st.slider(
        "Tier 2: Proporsi Kontaminasi ML (%)",
        min_value=3.0,
        max_value=15.0,
        value=8.0,
        step=1.0,
        help="Perkiraan rasio anomali multivariat untuk model Isolation Forest.",
    ) / 100.0


# Filter raw dataset based on sidebar inputs
filtered_data = filter_dataset(
    raw_data["agents"],
    raw_data["policies"],
    raw_data["history"],
    channel=selected_channels,
    branch_office=selected_branches,
)

if len(filtered_data["agents"]) == 0 or len(filtered_data["policies"]) == 0:
    st.warning("⚠️ Tidak ada data yang cocok dengan kriteria filter terpilih. Silakan sesuaikan filter sidebar.")
    st.stop()


# ==============================================================================
# PIPELINE COMPUTATION (CACHED VIA SCRIPT LOGIC)
# ==============================================================================

matrices = calculate_cohort_matrices(filtered_data["policies"], filtered_data["history"])
grace_df = extract_grace_period_watch(filtered_data["policies"], filtered_data["history"])

agent_features = engineer_agent_features(
    filtered_data["agents"],
    filtered_data["policies"],
    filtered_data["history"],
)

detected_agents = run_two_tier_detection(
    agent_features,
    rule_lapse_vol_thresh=t1_vol_shock_threshold,
    rule_m13_vol_min=t1_m13_min_persistency,
    contamination=t2_contamination,
)

# Merge true labels if available for transparency during demo/audit
if "true_label" in filtered_data["agents"].columns:
    detected_agents = detected_agents.merge(
        filtered_data["agents"][["agent_id", "true_label"]],
        on="agent_id",
        how="left",
    )

kpis = calculate_dashboard_kpis(matrices, detected_agents, grace_df)


# ==============================================================================
# MAIN PAGE: HEADER & EXECUTIVE KPI BANNER
# ==============================================================================

st.title("🛡️ Deteksi Anomali Persistensi Polis & Churn Agen (PAYDI)")
st.markdown(
    "Platform analitik kohort dua dimensi (*Volume vs APE*) dan sistem deteksi kecurangan agen "
    "(*Hit-and-Run* & *Cherry-Picking*) sesuai kepatuhan **SEOJK PAYDI & Standar Persistensi AAJI**."
)

st.markdown("---")

# KPI Summary Cards (4 Columns)
col1, col2, col3, col4 = st.columns(4)

with col1:
    m13_v = kpis["m13_vol"]
    delta_ojk = m13_v - 80.0
    st.metric(
        label="M13 Volume Persistency",
        value=f"{m13_v:.1f}%",
        delta=f"{delta_ojk:+.1f}% vs OJK Benchmark (80%)",
        delta_color="normal" if delta_ojk >= 0 else "inverse",
    )
    if m13_v >= 80.0:
        st.markdown("<span class='badge-ojk-pass'>Memenuhi Standar AAJI</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-ojk-warn'>Di Bawah Standar AAJI</span>", unsafe_allow_html=True)

with col2:
    m13_a = kpis["m13_ape"]
    gap = kpis["leakage_gap"]
    st.metric(
        label="M13 APE Persistency",
        value=f"{m13_a:.1f}%",
        delta=f"-{gap:.1f}% Kebocoran Premi (Gap)",
        delta_color="inverse" if gap > 5.0 else "off",
    )
    st.caption(f"Volume: {m13_v:.1f}% | Premi (APE): {m13_a:.1f}%")

with col3:
    st.metric(
        label="Agen Berisiko Tinggi Terdeteksi",
        value=f"{kpis['total_flagged']} Agen",
        delta=f"Tier 1: {kpis['tier1_count']} | Tier 2: {kpis['tier2_count']}",
        delta_color="inverse" if kpis["total_flagged"] > 0 else "off",
    )
    st.caption("Penyaringan Deterministik & Isolation Forest")

with col4:
    grace_ape_m = kpis["grace_total_ape"] / 1_000_000_000.0
    st.metric(
        label="Early Warning: Grace Period (M11-M12)",
        value=f"{kpis['grace_policy_count']:,} Polis",
        delta=f"Rp {grace_ape_m:.2f} Miliar Berisiko Lapse",
        delta_color="inverse" if kpis["grace_policy_count"] > 0 else "off",
    )
    st.caption("Target intervensi tim retensi sebelum M13")

st.markdown("---")


# ==============================================================================
# MAIN TABS ARCHITECTURE
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📊 Dual-Cohort Retention Matrix",
        "🎯 Multivariate Anomaly Scatter Map",
        "⏳ Early Warning: Grace Period (M11-M12)",
        "📋 Agent Risk Watchlist & Audit Drill-down",
    ]
)

# ------------------------------------------------------------------------------
# TAB 1: DUAL-COHORT RETENTION MATRIX (VOLUME VS APE)
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("Matriks Kohort Dua Dimensi: Volume Polis vs Nilai Premi (APE)")
    st.markdown(
        "Membandingkan retensi kohort berdasarkan jumlah polis (*Volume*) dengan retensi nilai premi tahunan (*APE*). "
        "Garis putus-putus merah menandai **batas kritis M13** pasca pencairan komisi tahun pertama (*FYC*)."
    )

    view_mode = st.radio(
        "Mode Tampilan Matriks:",
        options=["Berdampingan (Volume Matrix vs APE Matrix)", "Matriks Kebocoran Premi (Volume % − APE %)"],
        horizontal=True,
    )

    if view_mode == "Berdampingan (Volume Matrix vs APE Matrix)":
        heat_col1, heat_col2 = st.columns(2)
        with heat_col1:
            st.plotly_chart(
                create_cohort_heatmap(
                    matrices["volume_matrix"],
                    title="Matriks Retensi Volume Polis (% Aktif)",
                    colorscale="Tealrose",
                ),
                use_container_width=True,
            )
        with heat_col2:
            st.plotly_chart(
                create_cohort_heatmap(
                    matrices["ape_matrix"],
                    title="Matriks Retensi Premi / APE (% Aktif)",
                    colorscale="Tealrose",
                ),
                use_container_width=True,
            )
    else:
        st.plotly_chart(
            create_discrepancy_heatmap(matrices["discrepancy_matrix"]),
            use_container_width=True,
        )
        st.info(
            "💡 **Interpretasi Kebocoran Premi**: Sel berwarna merah gelap menunjukkan kohort di mana rasio volume "
            "tampak sehat, namun nilai premi riil yang aktif mengalami anjlok tajam (sinyal kuat manipulasi *Cherry-Picking*)."
        )

# ------------------------------------------------------------------------------
# TAB 2: MULTIVARIATE ANOMALY SCATTER MAP
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("Peta Klaster Anomali Agen: Volume Shock vs APE Shock")
    st.markdown(
        "Plot ini memetakan profil perilaku agen berdasarkan **Lapse Shock Volume** (Sumbu X) dan "
        "**Lapse Shock APE** (Sumbu Y). Ukuran gelembung merefleksikan **APE Disparity Ratio**."
    )

    st.plotly_chart(
        create_anomaly_scatter_plot(detected_agents),
        use_container_width=True,
    )

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.success(
            "**🟢 Agen Normal (Patuh)**\n\n"
            "- Persistensi volume dan APE terjaga konsisten di M13.\n"
            "- Laju penurunan alami sejalan dengan benchmark OJK 80%–85%."
        )
    with col_info2:
        st.error(
            "**🔴 Tier 1: Hit-and-Run**\n\n"
            "- Persistensi tinggi di M1–M12, anjlok serentak >25% di M13.\n"
            "- Konsentrasi pembayaran tunai tinggi (indikasi talangan premi komisi)."
        )
    with col_info3:
        st.warning(
            "**🟣 Tier 2: Cherry-Picking**\n\n"
            "- Volume M13 dipertahankan aman (~80%), namun APE anjlok drastis.\n"
            "- Polis nominal besar sengaja dibiarkan mati demi bonus persistensi volume."
        )

# ------------------------------------------------------------------------------
# TAB 3: EARLY WARNING GRACE PERIOD MONITOR (M11-M12)
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("Early Warning Monitor: Polis Dalam Grace Period (M11 & M12)")
    st.markdown(
        "Daftar polis yang saat ini berada dalam masa tenggang (*Grace Period* 30–45 hari) sebelum mencapai bulan ke-13. "
        "Gunakan daftar ini untuk program *proactive retention outreach* sebelum polis resmi mengalami *lapse*."
    )

    if len(grace_df) > 0:
        col_g1, col_g2 = st.columns([1, 2])
        with col_g1:
            st.metric("Total Polis Rawan Lapse", f"{len(grace_df):,} Polis")
            st.metric("Total APE Terancam", f"Rp {grace_df['ape'].sum() / 1_000_000:,.0f} Juta")

            pm_dist = grace_df["payment_method"].value_counts(normalize=True) * 100.0
            st.write("**Distribusi Metode Pembayaran Polis Grace Period:**")
            st.dataframe(pm_dist.round(1).rename("Persentase (%)"))

        with col_g2:
            # Display sorted grace policies table
            display_cols = ["policy_id", "agent_id", "cohort_month", "month_index", "ape", "payment_method"]
            st.dataframe(
                grace_df[display_cols].rename(
                    columns={
                        "policy_id": "Nomor Polis",
                        "agent_id": "Kode Agen",
                        "cohort_month": "Bulan Kohort",
                        "month_index": "Bulan Polis",
                        "ape": "Nilai APE (IDR)",
                        "payment_method": "Metode Pembayaran",
                    }
                ),
                use_container_width=True,
                height=350,
            )
    else:
        st.info("Tidak ada polis yang berada pada Grace Period di bulan M11 atau M12.")

# ------------------------------------------------------------------------------
# TAB 4: AGENT RISK WATCHLIST & AUDIT DRILL-DOWN
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("Prioritized Agent Risk Watchlist & Bukti Audit")
    st.markdown(
        "Daftar agen yang terindikasi anomali berdasarkan saringan kepatuhan Tier 1 atau model *Isolation Forest* Tier 2. "
        "Data dapat diekspor langsung ke format CSV untuk kebutuhan pelaporan audit kepatuhan internal."
    )

    watch_f1, watch_f2, watch_f3 = st.columns([1, 1, 2])
    with watch_f1:
        tier_filter = st.selectbox(
            "Filter Status Risiko:",
            options=["Semua Status", "Hanya Terindikasi Anomali (Tier 1 & Tier 2)", "Tier 1: Hit-and-Run", "Tier 2: Cherry-Picking", "Normal"],
        )
    with watch_f2:
        min_score = st.slider("Min Anomaly Score:", min_value=0.0, max_value=1.0, value=0.0, step=0.05)
    with watch_f3:
        search_query = st.text_input("Cari Agen (ID atau Nama):", "")

    # Apply table filters
    filtered_watchlist = detected_agents[detected_agents["anomaly_score"] >= min_score].copy()

    if tier_filter == "Hanya Terindikasi Anomali (Tier 1 & Tier 2)":
        filtered_watchlist = filtered_watchlist[filtered_watchlist["risk_category"] != "Normal"]
    elif tier_filter == "Tier 1: Hit-and-Run":
        filtered_watchlist = filtered_watchlist[filtered_watchlist["risk_category"].str.contains("Tier 1")]
    elif tier_filter == "Tier 2: Cherry-Picking":
        filtered_watchlist = filtered_watchlist[filtered_watchlist["risk_category"].str.contains("Tier 2")]
    elif tier_filter == "Normal":
        filtered_watchlist = filtered_watchlist[filtered_watchlist["risk_category"] == "Normal"]

    if search_query:
        query = search_query.lower()
        filtered_watchlist = filtered_watchlist[
            filtered_watchlist["agent_id"].str.lower().str.contains(query)
            | filtered_watchlist["agent_name"].str.lower().str.contains(query)
        ]

    # Sort by anomaly score descending
    filtered_watchlist = filtered_watchlist.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

    # Export Button (US-12)
    csv_bytes = filtered_watchlist.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Unduh Agent Risk Watchlist (CSV)",
        data=csv_bytes,
        file_name="Agent_Risk_Watchlist_Audit_PAYDI.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Interactive Table Display
    display_watch = filtered_watchlist[
        [
            "agent_id",
            "agent_name",
            "channel",
            "branch_office",
            "risk_category",
            "anomaly_score",
            "m13_vol_persistency",
            "m13_ape_persistency",
            "lapse_shock_vol",
            "lapse_shock_ape",
            "ape_disparity_ratio",
            "cash_payment_ratio",
            "primary_risk_drivers",
        ]
    ]

    st.dataframe(
        display_watch,
        use_container_width=True,
        height=320,
    )

    st.markdown("---")
    st.subheader("🔍 Bukti Audit & Investigasi Individual Agen (Drill-Down)")

    if len(filtered_watchlist) > 0:
        agent_options = [
            f"{row['agent_id']} - {row['agent_name']} ({row['risk_category']})"
            for _, row in filtered_watchlist.iterrows()
        ]
        selected_agent_str = st.selectbox("Pilih Agen untuk Investigasi Mendalam:", options=agent_options)
        selected_agent_id = selected_agent_str.split(" - ")[0]

        agent_row = filtered_watchlist[filtered_watchlist["agent_id"] == selected_agent_id].iloc[0]

        # Individual Agent Evidence Details
        e_col1, e_col2, e_col3, e_col4 = st.columns(4)
        with e_col1:
            st.metric("Total Polis & APE", f"{agent_row['total_policies']} Polis", f"Rp {agent_row['total_ape']/1_000_000:.0f} Jt")
        with e_col2:
            st.metric("Lapse Shock Volume (M12-M13)", f"{agent_row['lapse_shock_vol']:.1f}%")
        with e_col3:
            st.metric("Lapse Shock APE (M12-M13)", f"{agent_row['lapse_shock_ape']:.1f}%")
        with e_col4:
            st.metric("APE Disparity Ratio", f"{agent_row['ape_disparity_ratio']:.2f}x")

        st.info(f"**Pemicu Risiko Kuantitatif (Bukti Sidang Audit):**\n\n{agent_row['primary_risk_drivers']}")

        # Individual Agent M1-M24 Lifecycle Retention Curve
        st.plotly_chart(
            create_agent_drilldown_curves(
                filtered_data["policies"],
                filtered_data["history"],
                agent_id=selected_agent_id,
            ),
            use_container_width=True,
        )
    else:
        st.write("Tidak ada agen yang sesuai dengan kriteria pencarian.")
