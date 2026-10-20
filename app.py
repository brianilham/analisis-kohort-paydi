"""
Dashboard Analisis Kohort Persistensi Polis dan Deteksi Churn Agen (PAYDI).
PT MNC Life Assurance.
"""

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import streamlit as st

from generate_data import generate_synthetic_dataset
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
    page_title="MNC Life - Persistensi Polis PAYDI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS: white background throughout, clean corporate typography
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #FFFFFF !important;
        color: #1E293B;
    }

    /* Main container background */
    .main .block-container {
        background-color: #FFFFFF;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    /* Top Brand Header */
    .main-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 18px;
        margin-bottom: 20px;
        border-bottom: 1px solid #E2E8F0;
        background-color: #FFFFFF;
        gap: 24px;
        flex-wrap: wrap;
    }
    .main-header-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #002554;
        margin: 0;
    }
    .main-header-sub {
        font-size: 0.9rem;
        color: #64748B;
        margin-top: 4px;
        margin-bottom: 8px;
    }
    .badge-rule {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        color: #002554;
        background-color: #EEF4FF;
        border: 1px solid #D0E1FD;
        padding: 3px 8px;
        border-radius: 4px;
        margin-right: 6px;
    }

    /* Cards */
    .metric-card-clean {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #E2E8F0;
        background-color: #FFFFFF;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-weight: 600;
        color: #475569;
        background-color: #FFFFFF;
    }
    .stTabs [aria-selected="true"] {
        color: #002554 !important;
        border-bottom: 3px solid #002554 !important;
        background-color: #FFFFFF !important;
    }

    /* Clean Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FAFAFA;
        border-right: 1px solid #EAEAEA;
    }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #002554;
        font-size: 1.05rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_dataset() -> Dict[str, pd.DataFrame]:
    data_dir = Path("data")
    agents_file = data_dir / "agents.csv"
    policies_file = data_dir / "policies.csv"
    history_file = data_dir / "policy_monthly_status.csv"

    if agents_file.exists() and policies_file.exists() and history_file.exists():
        agents_df = pd.read_csv(agents_file)
        policies_df = pd.read_csv(policies_file)
        history_df = pd.read_csv(history_file)
        return {"agents": agents_df, "policies": policies_df, "history": history_df}

    return generate_synthetic_dataset(random_seed=42)


raw_data = load_dataset()

# ==============================================================================
# SIDEBAR: HANYA FILTER DATA PENTING
# ==============================================================================

with st.sidebar:
    st.subheader("Filter Data")

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


# Filter data
filtered_data = filter_dataset(
    raw_data["agents"],
    raw_data["policies"],
    raw_data["history"],
    channel=selected_channels,
    branch_office=selected_branches,
)

if len(filtered_data["agents"]) == 0 or len(filtered_data["policies"]) == 0:
    st.warning("Data tidak ditemukan untuk kombinasi filter yang dipilih.")
    st.stop()


# ==============================================================================
# PROSES ANALISIS & DETEKSI DENGAN AMBANG BATAS STANDAR
# ==============================================================================

# Ambang batas standar regulasi OJK & AAJI
DEFAULT_VOL_SHOCK_THRESH = 25.0
DEFAULT_M13_MIN_PERSISTENCY = 75.0
DEFAULT_CONTAMINATION = 0.08

matrices = calculate_cohort_matrices(filtered_data["policies"], filtered_data["history"])
grace_df = extract_grace_period_watch(filtered_data["policies"], filtered_data["history"])

agent_features = engineer_agent_features(
    filtered_data["agents"],
    filtered_data["policies"],
    filtered_data["history"],
)

detected_agents = run_two_tier_detection(
    agent_features,
    rule_lapse_vol_thresh=DEFAULT_VOL_SHOCK_THRESH,
    rule_m13_vol_min=DEFAULT_M13_MIN_PERSISTENCY,
    contamination=DEFAULT_CONTAMINATION,
)

if "true_label" in filtered_data["agents"].columns:
    detected_agents = detected_agents.merge(
        filtered_data["agents"][["agent_id", "true_label"]],
        on="agent_id",
        how="left",
    )

kpis = calculate_dashboard_kpis(matrices, detected_agents, grace_df)


# ==============================================================================
# HEADER UTAMA: LOGO MNC LIFE & IDENTITAS
# ==============================================================================

col_h1, col_h2 = st.columns([1, 4])
with col_h1:
    logo_path = Path("mnc_life_logo.svg")
    if logo_path.exists():
        st.image(str(logo_path), width=190)
    else:
        st.markdown("### MNC Life")

with col_h2:
    st.markdown(
        """
        <div>
            <h2 style='color:#002554; margin:0; font-size:1.35rem; font-weight:700;'>
                PT MNC Life Assurance
            </h2>
            <div style='color:#64748B; font-size:0.92rem; margin-top:2px; margin-bottom:8px;'>
                Monitoring Persistensi Polis PAYDI dan Deteksi Churn Agen
            </div>
            <div>
                <span class='badge-rule'>SEOJK No. 5/SEOJK.05/2022</span>
                <span class='badge-rule'>Standar AAJI M13 (80%-85%)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin-top:10px; margin-bottom:20px; border:0; border-top:1px solid #E2E8F0;'>", unsafe_allow_html=True)


# ==============================================================================
# RINGKASAN METRIK UTAMA
# ==============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    m13_v = kpis["m13_vol"]
    delta_ojk = m13_v - 80.0
    st.metric(
        label="Persistensi Volume M13",
        value=f"{m13_v:.1f}%",
        delta=f"{delta_ojk:+.1f}% vs Standar AAJI (80%)",
        delta_color="normal" if delta_ojk >= 0 else "inverse",
    )

with col2:
    m13_a = kpis["m13_ape"]
    gap = kpis["leakage_gap"]
    st.metric(
        label="Persistensi Premi (APE) M13",
        value=f"{m13_a:.1f}%",
        delta=f"-{gap:.1f}% Selisih Kebocoran" if gap > 0 else "0.0%",
        delta_color="inverse" if gap > 5.0 else "off",
    )

with col3:
    st.metric(
        label="Agen Berisiko Terindikasi",
        value=f"{kpis['total_flagged']} Agen",
        delta=f"Tier 1: {kpis['tier1_count']} | Tier 2: {kpis['tier2_count']}",
        delta_color="inverse" if kpis["total_flagged"] > 0 else "off",
    )

with col4:
    grace_ape_m = kpis["grace_total_ape"] / 1_000_000_000.0
    st.metric(
        label="Grace Period M11-M12",
        value=f"{kpis['grace_policy_count']:,} Polis",
        delta=f"Rp {grace_ape_m:.2f} Miliar",
        delta_color="inverse" if kpis["grace_policy_count"] > 0 else "off",
    )

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# TAB ANALISIS
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Matriks Kohort (Volume vs APE)",
        "Peta Sebaran Anomali Agen",
        "Early Warning Grace Period (M11-M12)",
        "Daftar Pengawasan Agen Berisiko",
    ]
)

# ------------------------------------------------------------------------------
# TAB 1: MATRIKS KOHORT DUA DIMENSI
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("Matriks Kohort: Volume Polis vs Nilai Premi (APE)")
    st.write(
        "Perbandingan retensi dari bulan pertama (M1) sampai bulan ke-24 (M24). "
        "Garis putus-putus menandai batas bulan ke-13 setelah pencairan komisi tahun pertama."
    )

    view_mode = st.radio(
        "Pilihan Tampilan:",
        options=["Berdampingan (Volume vs APE)", "Selisih Kebocoran Premi (Volume % - APE %)"],
        horizontal=True,
    )

    if view_mode == "Berdampingan (Volume vs APE)":
        heat_col1, heat_col2 = st.columns(2)
        with heat_col1:
            st.plotly_chart(
                create_cohort_heatmap(
                    matrices["volume_matrix"],
                    title="Retensi Volume Polis (% Aktif)",
                    colorscale="Tealrose",
                ),
                use_container_width=True,
            )
        with heat_col2:
            st.plotly_chart(
                create_cohort_heatmap(
                    matrices["ape_matrix"],
                    title="Retensi Premi APE (% Aktif)",
                    colorscale="Tealrose",
                ),
                use_container_width=True,
            )
    else:
        st.plotly_chart(
            create_discrepancy_heatmap(matrices["discrepancy_matrix"]),
            use_container_width=True,
        )
        st.caption(
            "Warna merah pekat menunjukkan persentase volume terlihat aman tetapi nilai premi riil turun drastis (indikasi cherry-picking)."
        )

# ------------------------------------------------------------------------------
# TAB 2: PETA SEBARAN ANOMALI
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("Peta Sebaran Perilaku Agen")
    st.write(
        "Sumbu X menunjukkan penurunan volume pada M12 ke M13. Sumbu Y menunjukkan penurunan premi APE pada M12 ke M13. "
        "Ukuran lingkaran mewakili rasio perbedaan premi polis yang lapse dibanding polis aktif."
    )

    st.plotly_chart(
        create_anomaly_scatter_plot(detected_agents),
        use_container_width=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**Agen Normal**\n\nPenurunan wajar dan tetap memenuhi ambang batas persistensi.")
    with c2:
        st.write("**Tier 1: Hit-and-Run**\n\nPersistensi M1-M12 tinggi, lalu anjlok serempak lebih dari 25% di M13.")
    with c3:
        st.write("**Tier 2: Cherry-Picking**\n\nVolume M13 dipertahankan di batas aman, tetapi polis bernilai premi besar dibiarkan mati.")

# ------------------------------------------------------------------------------
# TAB 3: EARLY WARNING GRACE PERIOD
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("Daftar Polis Grace Period (M11 dan M12)")
    st.write(
        "Daftar polis yang sedang memasuki masa tenggang sebelum jatuh tempo M13. "
        "Bagian ini dapat digunakan untuk tindak lanjut retensi sebelum polis resmi lapse."
    )

    if len(grace_df) > 0:
        g1, g2 = st.columns([1, 2])
        with g1:
            st.metric("Total Polis Rawan", f"{len(grace_df):,} Polis")
            st.metric("Total Premi Berisiko", f"Rp {grace_df['ape'].sum() / 1_000_000:,.0f} Juta")

            pm_dist = grace_df["payment_method"].value_counts(normalize=True) * 100.0
            st.write("**Metode Pembayaran:**")
            st.dataframe(pm_dist.round(1).rename("Persentase (%)"))

        with g2:
            cols = ["policy_id", "agent_id", "cohort_month", "month_index", "ape", "payment_method"]
            st.dataframe(
                grace_df[cols].rename(
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
                height=320,
            )
    else:
        st.info("Tidak ada polis pada masa tenggang di bulan M11 atau M12.")

# ------------------------------------------------------------------------------
# TAB 4: DAFTAR PENGAWASAN AGEN & DETAIL BUKTI
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("Daftar Pengawasan Agen Berisiko")
    st.write("Daftar agen yang terindikasi anomali pada saringan aturan maupun model deteksi.")

    w1, w2, w3 = st.columns([1, 1, 2])
    with w1:
        tier_filter = st.selectbox(
            "Filter Status:",
            options=["Semua Status", "Hanya Terindikasi Anomali", "Tier 1: Hit-and-Run", "Tier 2: Cherry-Picking", "Normal"],
        )
    with w2:
        min_score = st.slider("Skor Anomali Minimal:", min_value=0.0, max_value=1.0, value=0.0, step=0.05)
    with w3:
        search_query = st.text_input("Cari Agen (ID atau Nama):", "")

    watchlist = detected_agents[detected_agents["anomaly_score"] >= min_score].copy()

    if tier_filter == "Hanya Terindikasi Anomali":
        watchlist = watchlist[watchlist["risk_category"] != "Normal"]
    elif tier_filter == "Tier 1: Hit-and-Run":
        watchlist = watchlist[watchlist["risk_category"].str.contains("Tier 1")]
    elif tier_filter == "Tier 2: Cherry-Picking":
        watchlist = watchlist[watchlist["risk_category"].str.contains("Tier 2")]
    elif tier_filter == "Normal":
        watchlist = watchlist[watchlist["risk_category"] == "Normal"]

    if search_query:
        q = search_query.lower()
        watchlist = watchlist[
            watchlist["agent_id"].str.lower().str.contains(q)
            | watchlist["agent_name"].str.lower().str.contains(q)
        ]

    watchlist = watchlist.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

    csv_data = watchlist.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Unduh Daftar Pengawasan (CSV)",
        data=csv_data,
        file_name="Daftar_Pengawasan_Agen_PAYDI.csv",
        mime="text/csv",
        use_container_width=True,
    )

    display_cols = [
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

    st.dataframe(
        watchlist[display_cols],
        use_container_width=True,
        height=300,
    )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    st.subheader("Pemeriksaan Detail Agen")

    if len(watchlist) > 0:
        agent_options = [
            f"{row['agent_id']} - {row['agent_name']} ({row['risk_category']})"
            for _, row in watchlist.iterrows()
        ]
        selected_str = st.selectbox("Pilih Agen:", options=agent_options)
        selected_id = selected_str.split(" - ")[0]

        agent_row = watchlist[watchlist["agent_id"] == selected_id].iloc[0]

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.metric("Total Polis & Premi", f"{agent_row['total_policies']} Polis", f"Rp {agent_row['total_ape']/1_000_000:.0f} Juta")
        with d2:
            st.metric("Penurunan Volume M12-M13", f"{agent_row['lapse_shock_vol']:.1f}%")
        with d3:
            st.metric("Penurunan Premi APE M12-M13", f"{agent_row['lapse_shock_ape']:.1f}%")
        with d4:
            st.metric("Rasio Disparitas Premi", f"{agent_row['ape_disparity_ratio']:.2f}x")

        st.caption(f"Faktor Risiko: {agent_row['primary_risk_drivers']}")

        st.plotly_chart(
            create_agent_drilldown_curves(
                filtered_data["policies"],
                filtered_data["history"],
                agent_id=selected_id,
            ),
            use_container_width=True,
        )
    else:
        st.write("Tidak ada data agen yang sesuai kriteria.")
