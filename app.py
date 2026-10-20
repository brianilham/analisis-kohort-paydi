"""
Streamlit Application: Analisis Kohort Persistensi Polis & Deteksi Churn Agen (PAYDI).
Embedded with MNC Life Assurance Corporate Design System & Brand Identity.
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
    page_title="MNC Life - Analisis Kohort Persistensi Polis & Deteksi Churn Agen (PAYDI)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# MNC LIFE ASSURANCE CORPORATE DESIGN SYSTEM & CSS INJECTION
# ==============================================================================

st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* MNC Corporate Header Banner */
    .mnc-header-container {
        background: linear-gradient(135deg, #002554 0%, #001738 60%, #003875 100%);
        border-radius: 12px;
        padding: 24px 32px;
        color: #FFFFFF;
        box-shadow: 0 10px 25px -5px rgba(0, 37, 84, 0.25);
        margin-bottom: 24px;
        border-bottom: 4px solid #F7941D;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    .mnc-header-left {
        max-width: 820px;
    }
    .mnc-brand-title {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        color: #FFFFFF;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .mnc-brand-gold {
        color: #F7941D;
    }
    .mnc-sub-title {
        font-size: 0.95rem;
        color: #CBD5E1;
        margin-top: 6px;
        margin-bottom: 12px;
        line-height: 1.5;
    }
    .mnc-badge-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    .badge-ojk {
        background-color: rgba(247, 148, 29, 0.2);
        color: #FBBF24;
        border: 1px solid rgba(247, 148, 29, 0.5);
    }
    .badge-iso {
        background-color: rgba(255, 255, 255, 0.15);
        color: #E2E8F0;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* MNC Metric Cards */
    .metric-card-mnc {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 18px 20px;
        border: 1px solid #E2E8F0;
        border-top: 4px solid #002554;
        box-shadow: 0 4px 12px rgba(0, 37, 84, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card-mnc:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 18px rgba(0, 37, 84, 0.1);
    }

    /* Status Badges */
    .badge-pass {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-warn {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.8rem;
    }

    /* Styled Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        font-weight: 600;
        font-size: 0.95rem;
        color: #475569;
        border-radius: 6px 6px 0 0;
    }
    .stTabs [aria-selected="true"] {
        color: #002554 !important;
        border-bottom: 3px solid #F7941D !important;
        background-color: rgba(0, 37, 84, 0.04);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #002554;
        font-weight: 700;
    }

    /* Footer styling */
    .mnc-footer {
        margin-top: 48px;
        padding: 20px 0;
        border-top: 1px solid #E2E8F0;
        text-align: center;
        font-size: 0.82rem;
        color: #64748B;
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
# SIDEBAR: MNC BRANDING, FILTERS & DETECTION CONTROLS
# ==============================================================================

with st.sidebar:
    logo_path = Path("mnc_life_logo.svg")
    if logo_path.exists():
        st.image(str(logo_path), use_column_width=True)
    else:
        st.markdown("### 🏢 **MNC LIFE ASSURANCE**")

    st.caption("🛡️ **Internal Risk & Actuarial Governance Portal**")
    st.markdown(
        """
        <div style='background-color:#EBF5FF; padding:8px 12px; border-radius:6px; font-size:0.8rem; color:#002554; margin-bottom:12px;'>
            <strong>MNC Financial Services</strong><br>Solusi Proteksi dan Investasi Terpercaya
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("⚙️ Parameter Data")
    sim_seed = st.number_input("Random Seed Simulasi", min_value=1, max_value=9999, value=42, step=1)
    if st.button("🔄 Muat / Reset Dataset", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    raw_data = load_or_generate_dataset(seed=int(sim_seed))

    st.markdown("---")
    st.subheader("🔍 Filter Dimensi Portofolio")
    all_channels = sorted(raw_data["agents"]["channel"].unique())
    selected_channels = st.multiselect(
        "Kanal Distribusi",
        options=all_channels,
        default=all_channels,
    )

    all_branches = sorted(raw_data["agents"]["branch_office"].unique())
    selected_branches = st.multiselect(
        "Kantor Cabang MNC Life",
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

    st.markdown("---")
    st.link_button(
        "🌐 Buka Website Resmi mnclife.com ↗",
        "https://www.mnclife.com/",
        use_container_width=True,
    )


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
# PIPELINE COMPUTATION
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

if "true_label" in filtered_data["agents"].columns:
    detected_agents = detected_agents.merge(
        filtered_data["agents"][["agent_id", "true_label"]],
        on="agent_id",
        how="left",
    )

kpis = calculate_dashboard_kpis(matrices, detected_agents, grace_df)


# ==============================================================================
# MNC LIFE HEADER BANNER
# ==============================================================================

st.markdown(
    """
    <div class="mnc-header-container">
        <div class="mnc-header-left">
            <h1 class="mnc-brand-title">
                PT MNC LIFE ASSURANCE <span class="mnc-brand-gold">| ACTUARIAL & RISK PORTAL</span>
            </h1>
            <div class="mnc-sub-title">
                Sistem Analitik Kohort Persistensi Polis 2D (Volume vs APE) & Deteksi Anomali Manipulasi Churn Agen 
                pada Portofolio Produk PAYDI (Unit Link).
            </div>
            <div>
                <span class="mnc-badge-pill badge-ojk">✓ Berizin & Diawasi Otoritas Jasa Keuangan (OJK)</span>
                <span class="mnc-badge-pill badge-iso">✓ SEOJK No. 5/SEOJK.05/2022 (PAYDI)</span>
                <span class="mnc-badge-pill badge-iso">✓ Standar Persistensi AAJI (80%–85%)</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# EXECUTIVE SUMMARY KPI CARDS (MNC STYLING)
# ==============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    m13_v = kpis["m13_vol"]
    delta_ojk = m13_v - 80.0
    st.metric(
        label="M13 Volume Persistency",
        value=f"{m13_v:.1f}%",
        delta=f"{delta_ojk:+.1f}% vs Target AAJI (80%)",
        delta_color="normal" if delta_ojk >= 0 else "inverse",
    )
    if m13_v >= 80.0:
        st.markdown("<span class='badge-pass'>Memenuhi Standar AAJI</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-warn'>Di Bawah Standar AAJI</span>", unsafe_allow_html=True)

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
        label="Agen Berisiko Terdeteksi",
        value=f"{kpis['total_flagged']} Agen",
        delta=f"Tier 1: {kpis['tier1_count']} | Tier 2: {kpis['tier2_count']}",
        delta_color="inverse" if kpis["total_flagged"] > 0 else "off",
    )
    st.caption("Penyaringan Deterministik & Isolation Forest")

with col4:
    grace_ape_m = kpis["grace_total_ape"] / 1_000_000_000.0
    st.metric(
        label="Early Warning: Grace Period M11-M12",
        value=f"{kpis['grace_policy_count']:,} Polis",
        delta=f"Rp {grace_ape_m:.2f} Miliar Berisiko Lapse",
        delta_color="inverse" if kpis["grace_policy_count"] > 0 else "off",
    )
    st.caption("Fokus intervensi tim retensi MNC Life")

st.markdown("---")


# ==============================================================================
# MAIN TABS ARCHITECTURE
# ==============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Dual-Cohort Retention Matrix",
        "🎯 Multivariate Anomaly Scatter Map",
        "⏳ Early Warning: Grace Period (M11-M12)",
        "📋 Agent Risk Watchlist & Audit Drill-down",
        "🏢 Profil MNC Life & Tata Kelola PAYDI",
    ]
)

# ------------------------------------------------------------------------------
# TAB 1: DUAL-COHORT RETENTION MATRIX (VOLUME VS APE)
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("Matriks Kohort Dua Dimensi: Volume Polis vs Nilai Premi (APE)")
    st.markdown(
        "Pemantauan kohort bulanan produk PAYDI (Unit Link) MNC Life dari **M1 hingga M24**. "
        "Garis putus-putus merah menandai **batas kritis M13** pasca pencairan First Year Commission (FYC) & bonus persistensi."
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
                    title="MNC Life: Matriks Retensi Volume Polis (% Aktif)",
                    colorscale="Tealrose",
                ),
                use_container_width=True,
            )
        with heat_col2:
            st.plotly_chart(
                create_cohort_heatmap(
                    matrices["ape_matrix"],
                    title="MNC Life: Matriks Retensi Nilai Premi APE (% Aktif)",
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
            "💡 **Indikasi Kebocoran Premi (Premium Leakage Gap)**: Sel merah pekat menandakan selisih tinggi di mana rasio volume "
            "terlihat memenuhi batas regulasi, tetapi nilai premi riil yang aktif mengalami penurunan drastis "
            "(indikasi manipulasi *Cherry-Picking* oleh agen)."
        )

# ------------------------------------------------------------------------------
# TAB 2: MULTIVARIATE ANOMALY SCATTER MAP
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("Peta Kuadran Anomali Agen: Volume Shock vs APE Shock")
    st.markdown(
        "Visualisasi multivariat memetakan agen berdasarkan **Lapse Shock Volume** (Sumbu X) dan "
        "**Lapse Shock APE** (Sumbu Y). Ukuran gelembung merefleksikan **APE Disparity Ratio**."
    )

    st.plotly_chart(
        create_anomaly_scatter_plot(detected_agents),
        use_container_width=True,
    )

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.success(
            "**🟢 Agen Normal (Patuh Kepatuhan MNC Life)**\n\n"
            "- Persistensi terjaga di M13 sesuai koridor AAJI (80%–85%).\n"
            "- Penurunan polis bersifat alami dan terdistribusi merata."
        )
    with col_info2:
        st.error(
            "**🔴 Tier 1: Hit-and-Run Violation**\n\n"
            "- Persistensi M1–M12 sangat tinggi, lalu anjlok serentak >25% di M13.\n"
            "- Terkonsentrasi pada pembayaran tunai (indikasi talangan premi komisi)."
        )
    with col_info3:
        st.warning(
            "**🟣 Tier 2: ML Anomaly (Cherry-Picking)**\n\n"
            "- Persistensi volume M13 lolos aturan kaku (~80%), namun APE anjlok tajam.\n"
            "- Polis nominal besar dibiarkan mati demi bonus persistensi volume."
        )

# ------------------------------------------------------------------------------
# TAB 3: EARLY WARNING GRACE PERIOD MONITOR (M11-M12)
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("Early Warning System: Polis Dalam Grace Period (M11 & M12)")
    st.markdown(
        "Daftar polis nasabah PAYDI MNC Life yang sedang berada dalam masa tenggang (*Grace Period* 30–45 hari) "
        "sebelum mencapai bulan ke-13. Digunakan oleh tim *Retention & Customer Care* untuk intervensi preventif."
    )

    if len(grace_df) > 0:
        col_g1, col_g2 = st.columns([1, 2])
        with col_g1:
            st.metric("Total Polis Rawan Lapse", f"{len(grace_df):,} Polis")
            st.metric("Total APE Terancam", f"Rp {grace_df['ape'].sum() / 1_000_000:,.0f} Juta")

            pm_dist = grace_df["payment_method"].value_counts(normalize=True) * 100.0
            st.write("**Distribusi Metode Pembayaran:**")
            st.dataframe(pm_dist.round(1).rename("Persentase (%)"))

        with col_g2:
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
        st.info("Tidak ada polis yang berada pada status Grace Period di bulan M11 atau M12.")

# ------------------------------------------------------------------------------
# TAB 4: AGENT RISK WATCHLIST & AUDIT DRILL-DOWN
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("MNC Life Prioritized Agent Risk Watchlist & Bukti Audit")
    st.markdown(
        "Daftar agen terindikasi risiko tinggi berdasarkan saringan kepatuhan Tier 1 atau model *Isolation Forest* Tier 2. "
        "Data dapat diekspor langsung dalam format CSV untuk diintegrasikan ke sistem manajemen audit internal MNC Life."
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

    filtered_watchlist = filtered_watchlist.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

    csv_bytes = filtered_watchlist.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Unduh Agent Risk Watchlist MNC Life (CSV)",
        data=csv_bytes,
        file_name="MNC_Life_Agent_Risk_Watchlist_Audit.csv",
        mime="text/csv",
        use_container_width=True,
    )

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
        selected_agent_str = st.selectbox("Pilih Agen untuk Pemeriksaan Bukti Audit:", options=agent_options)
        selected_agent_id = selected_agent_str.split(" - ")[0]

        agent_row = filtered_watchlist[filtered_watchlist["agent_id"] == selected_agent_id].iloc[0]

        e_col1, e_col2, e_col3, e_col4 = st.columns(4)
        with e_col1:
            st.metric("Total Polis & APE Agen", f"{agent_row['total_policies']} Polis", f"Rp {agent_row['total_ape']/1_000_000:.0f} Juta")
        with e_col2:
            st.metric("Lapse Shock Volume (M12-M13)", f"{agent_row['lapse_shock_vol']:.1f}%")
        with e_col3:
            st.metric("Lapse Shock APE (M12-M13)", f"{agent_row['lapse_shock_ape']:.1f}%")
        with e_col4:
            st.metric("APE Disparity Ratio", f"{agent_row['ape_disparity_ratio']:.2f}x")

        st.info(f"**Pemicu Risiko Kuantitatif (Bukti Sidang Komite Kepatuhan):**\n\n{agent_row['primary_risk_drivers']}")

        st.plotly_chart(
            create_agent_drilldown_curves(
                filtered_data["policies"],
                filtered_data["history"],
                agent_id=selected_agent_id,
            ),
            use_container_width=True,
        )
    else:
        st.write("Tidak ada agen yang sesuai dengan kriteria filter.")

# ------------------------------------------------------------------------------
# TAB 5: ABOUT MNC LIFE & PAYDI GOVERNANCE
# ------------------------------------------------------------------------------
with tab5:
    st.subheader("🏢 Profil PT MNC Life Assurance & Tata Kelola PAYDI")
    
    col_about1, col_about2 = st.columns([2, 1])
    with col_about1:
        st.markdown(
            """
            **PT MNC Life Assurance (MNC Life)** adalah perusahaan asuransi jiwa terkemuka di Indonesia yang bernaung di bawah **MNC Financial Services (MNC Group)**. 
            MNC Life menyediakan rangkaian produk perlindungan jiwa, asuransi kesehatan, serta produk asuransi yang dikaitkan dengan investasi (**PAYDI / Unit Link**).

            ### Kerangka Kepatuhan & Regulasi Terkait:
            1. **Surat Edaran Otoritas Jasa Keuangan (SEOJK No. 5/SEOJK.05/2022)**:
               - Mengatur transparansi pengelolaan, *waiting period*, alokasi premi investasi, dan kesesuaian profil risiko nasabah PAYDI.
            2. **Standar Persistensi AAJI**:
               - Target persistensi polis bulan ke-13 (M13) berada di rentang **80%–85%** sebagai indikator kesehatan retensi portofolio dan kualitas penjualan agen.
            3. **Mitigasi Anti-Fraud Komisi**:
               - Mencegah praktik *churning*, *hit-and-run* (pembiaran polis mati serentak pasca komisi FYC), dan *cherry-picking* (menjaga kuota volume dengan mematikan polis berpremi besar).
            """
        )
    with col_about2:
        st.markdown(
            """
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-top: 4px solid #F7941D; border-radius: 8px; padding: 18px;">
                <h4 style="color:#002554; margin-top:0;">Informasi Perusahaan</h4>
                <p style="font-size:0.85rem; color:#475569; line-height:1.6;">
                    <strong>Kantor Pusat:</strong><br>
                    MNC Financial Center, Lt. 6-8<br>
                    Jl. Kebon Sirih No. 21-27, Jakarta Pusat 10340<br><br>
                    <strong>Layanan Nasabah:</strong><br>
                    📞 1500-899 (Call Center)<br>
                    ✉️ customer.service@mnclife.com<br>
                    🌐 <a href="https://www.mnclife.com" target="_blank" style="color:#002554; font-weight:600;">www.mnclife.com</a>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button(
            "Kunjungi Website Resmi MNC Life ↗",
            "https://www.mnclife.com/",
            use_container_width=True,
        )

# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown(
    """
    <div class="mnc-footer">
        <strong>PT MNC Life Assurance</strong> — Berizin dan diawasi oleh <strong>Otoritas Jasa Keuangan (OJK)</strong>.<br>
        Portal Internal Aktuaria & Deteksi Dini Churn Agen PAYDI | Hak Cipta © 2026 PT MNC Life Assurance. Seluruh hak cipta dilindungi undang-undang.
    </div>
    """,
    unsafe_allow_html=True,
)
