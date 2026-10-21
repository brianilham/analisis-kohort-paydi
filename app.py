"""
Dashboard Analisis Kohort Persistensi Polis dan Deteksi Churn Agen (PAYDI).
PT MNC Life Assurance.
Mengacu pada panduan desain mnclife.com-design.md dengan kontras tinggi (High Legibility).
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

# CSS berpedoman pada DESIGN.md dengan penegasan kontras tinggi (Anti-Nyaru)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Global Typography & Background */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #FFFFFF !important;
        color: #192C4D !important;
    }

    /* Memastikan semua teks markdown, paragraf, list, span memiliki warna gelap solid */
    .stApp p, .stApp span, .stApp label, .stApp li, .stMarkdown p, .stMarkdown span, .stMarkdown div, .stText {
        color: #192C4D !important;
        font-weight: 450;
    }

    /* Heading tebal dan kontras */
    h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #192C4D !important;
        font-weight: 700 !important;
    }

    /* Container utama serba putih dengan jarak napas lega di atas */
    .main .block-container {
        background-color: #FFFFFF !important;
        padding-top: 3.5rem !important;
        padding-bottom: 2.8rem !important;
        max-width: 1350px !important;
    }

    /* Header bar atas Streamlit: selaraskan ke putih bersih agar tidak ada bar hitam */
    header[data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        border-bottom: 1.5px solid #D9E5F2 !important;
    }
    header[data-testid="stHeader"] * {
        color: #192C4D !important;
        stroke: #192C4D !important;
        fill: #192C4D !important;
    }

    /* Tombol ikon pembuka sidebar saat sidebar sedang ditutup/collapsed */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        visibility: visible !important;
        z-index: 1000001 !important;
        top: 0.75rem !important;
        left: 1rem !important;
    }
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button {
        background-color: #192C4D !important;
        color: #FFFFFF !important;
        border: 1.5px solid #192C4D !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        box-shadow: 0 2px 8px rgba(25, 44, 77, 0.28) !important;
        cursor: pointer !important;
    }
    [data-testid="collapsedControl"] button:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover {
        background-color: #0E1B31 !important;
        border-color: #C89B2C !important;
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="collapsedControl"] svg *,
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="stSidebarCollapsedControl"] svg * {
        stroke: #FFFFFF !important;
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }

    /* Tombol penutup sidebar saat sidebar sedang terbuka */
    section[data-testid="stSidebar"] button[data-testid="stSidebarCollapseButton"],
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button {
        background-color: #FFFFFF !important;
        border: 1.5px solid #D9E5F2 !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] button[data-testid="stSidebarCollapseButton"] svg,
    section[data-testid="stSidebar"] button[data-testid="stSidebarCollapseButton"] svg *,
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button svg,
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button svg * {
        stroke: #192C4D !important;
        color: #192C4D !important;
        fill: #192C4D !important;
    }

    /* Hilangkan ikon zoom/fullscreen bawaan pada logo */
    button[title="View fullscreen"], div[data-testid="StyledFullScreenButton"] {
        display: none !important;
    }

    /* Header atas utama */
    .mnc-main-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 16px;
        margin-bottom: 20px;
        border-bottom: 1.5px solid #D9E5F2;
        background-color: #FFFFFF;
        gap: 20px;
        flex-wrap: wrap;
    }
    .mnc-header-titles {
        display: flex;
        flex-direction: column;
    }
    .mnc-title-text {
        font-size: 1.65rem;
        font-weight: 800;
        color: #192C4D !important;
        margin: 0;
        line-height: 1.25;
    }
    .mnc-subtitle-text {
        font-size: 0.95rem;
        font-weight: 500;
        color: #334155 !important;
        margin-top: 4px;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .mnc-badge-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-right: 8px;
    }
    .badge-tertiary {
        background-color: #C89B2C;
        color: #FFFFFF !important;
    }
    .badge-subtle {
        background-color: #EBF2FA;
        color: #0E203C !important;
        border: 1px solid #BACFE8;
    }
    .badge-dummy {
        background-color: #F8FAFC;
        color: #475569 !important;
        border: 1px dashed #94A3B8;
    }

    /* Kartu metrik dengan kontras tajam */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1.5px solid #D9E5F2 !important;
        border-radius: 8px !important;
        padding: 14px 16px !important;
        box-shadow: none !important;
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
        color: #334155 !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] div {
        color: #192C4D !important;
        font-size: 1.6rem !important;
        font-weight: 800 !important;
    }

    /* Caption agar tidak abu-abu pudar */
    .stCaption, [data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] {
        color: #334155 !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
    }

    /* Radio buttons & text kontras */
    div[data-testid="stRadio"] label, div[data-testid="stRadio"] div[role="radiogroup"] label p {
        color: #192C4D !important;
        font-weight: 600 !important;
    }

    /* Form inputs, Multiselect, Selectbox labels */
    div[data-testid="stSelectbox"] label p, div[data-testid="stMultiSelect"] label p, div[data-testid="stTextInput"] label p {
        color: #192C4D !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }

    /* Kotak input Selectbox & Multiselect kondisi tertutup */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1.5px solid #D9E5F2 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input {
        color: #192C4D !important;
    }

    /* Multiselect tag badges (pilihan yang aktif di dalam kotak) */
    span[data-baseweb="tag"] {
        background-color: #EBF2FA !important;
        border: 1px solid #BACFE8 !important;
        border-radius: 6px !important;
    }
    span[data-baseweb="tag"] span {
        color: #192C4D !important;
        font-weight: 600 !important;
    }
    span[data-baseweb="tag"] svg {
        fill: #192C4D !important;
        color: #192C4D !important;
    }

    /* Popover Menu Dropdown (Selectbox & Multiselect saat diklik/dibuka) */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] ul,
    ul[data-baseweb="menu"] {
        background-color: #192C4D !important;
        border: 1.5px solid #334E78 !important;
        border-radius: 8px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35) !important;
    }

    /* Opsi daftar pilihan di dalam menu dropdown popover */
    li[data-baseweb="menu-item"],
    li[role="option"],
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] [role="option"],
    div[data-baseweb="popover"] ul li {
        background-color: #192C4D !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 8px 14px !important;
    }

    /* Teks seluruh elemen di dalam opsi dropdown (teks putih terang) */
    li[data-baseweb="menu-item"] *,
    li[role="option"] *,
    div[data-baseweb="popover"] li *,
    div[data-baseweb="popover"] [role="option"] *,
    div[data-baseweb="popover"] ul li * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }

    /* Efek hover ketika kursor menyorot opsi */
    li[data-baseweb="menu-item"]:hover,
    li[role="option"]:hover,
    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="popover"] [role="option"]:hover {
        background-color: #274370 !important;
    }

    li[data-baseweb="menu-item"]:hover *,
    li[role="option"]:hover *,
    div[data-baseweb="popover"] li:hover *,
    div[data-baseweb="popover"] [role="option"]:hover * {
        color: #FFFFFF !important;
    }

    /* Status opsi yang sedang terpilih */
    li[data-baseweb="menu-item"][aria-selected="true"],
    li[role="option"][aria-selected="true"],
    div[data-baseweb="popover"] [aria-selected="true"] {
        background-color: #243B61 !important;
    }

    li[data-baseweb="menu-item"][aria-selected="true"] *,
    li[role="option"][aria-selected="true"] *,
    div[data-baseweb="popover"] [aria-selected="true"] * {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Tab navigasi */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 2px solid #D9E5F2;
        background-color: #FFFFFF;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-weight: 600;
        font-size: 0.95rem;
        color: #334155 !important;
        background-color: #FFFFFF !important;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [aria-selected="true"] {
        color: #192C4D !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #C89B2C !important;
        background-color: #F5F8FC !important;
    }
    .stTabs [data-baseweb="tab"] p {
        color: inherit !important;
    }

    /* Sidebar bersih dan terbaca (surface #F5F8FC) */
    section[data-testid="stSidebar"] {
        background-color: #F5F8FC !important;
        border-right: 1.5px solid #D9E5F2 !important;
    }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #192C4D !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        margin-bottom: 14px !important;
    }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label {
        color: #192C4D !important;
    }

    /* Kotak Alert (st.info, st.warning, st.success) teks solid */
    div[data-testid="stAlert"] {
        border-radius: 8px !important;
    }
    div[data-testid="stAlert"] p, div[data-testid="stAlert"] div {
        color: #0F172A !important;
        font-weight: 500 !important;
    }

    /* Penyelarasan tabel dataframe agar menyatu rapi dengan background putih */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D9E5F2 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stDataFrame"] > div {
        background-color: #FFFFFF !important;
    }

    /* Tombol primer berpedoman DESIGN.md */
    div.stButton > button, div.stDownloadButton > button {
        background-color: #192C4D !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #192C4D !important;
        font-weight: 700 !important;
        padding: 10px 18px !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #0E1B31 !important;
        color: #FFFFFF !important;
    }
    div.stButton > button p, div.stDownloadButton > button p {
        color: #FFFFFF !important;
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
# SIDEBAR: FILTER PORTOFOLIO
# ==============================================================================

with st.sidebar:
    st.subheader("Filter Portofolio")

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

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.caption("🔒 **Kerahasiaan Data:** Seluruh data yang ditampilkan adalah data sintetis (dummy) portofolio.")


# Pemfilteran data
filtered_data = filter_dataset(
    raw_data["agents"],
    raw_data["policies"],
    raw_data["history"],
    channel=selected_channels,
    branch_office=selected_branches,
)

if len(filtered_data["agents"]) == 0 or len(filtered_data["policies"]) == 0:
    st.warning("Data tidak ditemukan untuk pilihan filter yang sedang aktif.")
    st.stop()


# ==============================================================================
# PERHITUNGAN ANALITIK KOHORT & DETEKSI DUA TIER
# ==============================================================================

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
# HEADER DASHBOARD UTAMA
# ==============================================================================

col_logo, col_title = st.columns([1, 4])
with col_logo:
    logo_path = Path("mnc_life_logo.svg")
    if logo_path.exists():
        st.image(str(logo_path), width=185)
    else:
        st.markdown("<h3 style='color:#192C4D; margin:0;'>MNC Life</h3>", unsafe_allow_html=True)

with col_title:
    st.markdown(
        """
        <div class="mnc-header-titles" style="padding-top: 2px;">
            <h1 class="mnc-title-text">Dashboard Persistensi Polis PAYDI & Deteksi Churn Agen</h1>
            <div style="margin-top: 8px;">
                <span class="mnc-badge-pill badge-tertiary">SEOJK No. 5/SEOJK.05/2022</span>
                <span class="mnc-badge-pill badge-subtle">Standar AAJI M13: 80% - 85%</span>
                <span class="mnc-badge-pill badge-dummy">🔒 Data Portofolio: Dummy / Confidential</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div style="background-color:#F5F8FC; border:1px solid #D9E5F2; border-left:4px solid #192C4D; border-radius:6px; padding:8px 14px; margin-top:10px; margin-bottom:12px; font-size:0.84rem; color:#334155;">
        <strong>Catatan Kerahasiaan Data:</strong> Seluruh data pada dashboard ini merupakan data sintetis (dummy) untuk keperluan portofolio teknis dan menjaga kerahasiaan data perusahaan (<em>corporate data confidentiality</em>). Pola aktuaria dan skenario anomali disimulasikan sesuai karakteristik riil produk PAYDI.
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# RINGKASAN METRIK KUNCI
# ==============================================================================

c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

with c_kpi1:
    m13_v = kpis["m13_vol"]
    delta_ojk = m13_v - 80.0
    st.metric(
        label="Persistensi Volume M13",
        value=f"{m13_v:.1f}%",
        delta=f"{delta_ojk:+.1f}% vs Standar AAJI (80%)",
        delta_color="normal" if delta_ojk >= 0 else "inverse",
    )

with c_kpi2:
    m13_a = kpis["m13_ape"]
    gap = kpis["leakage_gap"]
    st.metric(
        label="Persistensi Premi (APE) M13",
        value=f"{m13_a:.1f}%",
        delta=f"-{gap:.1f}% Selisih Kebocoran" if gap > 0 else "0.0%",
        delta_color="inverse" if gap > 5.0 else "off",
    )

with c_kpi3:
    st.metric(
        label="Agen Terindikasi Risiko",
        value=f"{kpis['total_flagged']} Agen",
        delta=f"Hit and Run: {kpis['tier1_count']} | Cherry Picking: {kpis['tier2_count']}",
        delta_color="inverse" if kpis["total_flagged"] > 0 else "off",
    )

with c_kpi4:
    grace_ape_m = kpis["grace_total_ape"] / 1_000_000_000.0
    st.metric(
        label="Grace Period M11-M12",
        value=f"{kpis['grace_policy_count']:,} Polis",
        delta=f"Rp {grace_ape_m:.2f} Miliar Berisiko",
        delta_color="inverse" if kpis["grace_policy_count"] > 0 else "off",
    )

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# TAB ANALISIS & INVESTIGASI
# ==============================================================================

tab_cohort, tab_scatter, tab_grace, tab_audit = st.tabs(
    [
        "Matriks Kohort (Volume vs APE)",
        "Peta Sebaran Anomali Agen",
        "Early Warning Grace Period (M11-M12)",
        "Daftar Pengawasan Agen Berisiko",
    ]
)

# ------------------------------------------------------------------------------
# TAB 1: MATRIKS KOHORT (VOLUME VS APE)
# ------------------------------------------------------------------------------
with tab_cohort:
    st.subheader("Matriks Kohort: Volume Polis vs Nilai Premi (APE)")
    st.write(
        "Perbandingan retensi dari bulan pertama (M1) sampai bulan ke-24 (M24). "
        "Garis putus-putus merah menandai batas bulan ke-13 setelah pencairan komisi tahun pertama."
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
                    colorscale="Blues",
                ),
                use_container_width=True,
            )
        with heat_col2:
            st.plotly_chart(
                create_cohort_heatmap(
                    matrices["ape_matrix"],
                    title="Retensi Premi APE (% Aktif)",
                    colorscale="Blues",
                ),
                use_container_width=True,
            )
    else:
        st.plotly_chart(
            create_discrepancy_heatmap(matrices["discrepancy_matrix"]),
            use_container_width=True,
        )
        st.caption(
            "Warna oranye atau merah pekat menunjukkan persentase volume terlihat aman tetapi nilai premi riil turun drastis (indikasi cherry-picking)."
        )

# ------------------------------------------------------------------------------
# TAB 2: PETA SEBARAN ANOMALI
# ------------------------------------------------------------------------------
with tab_scatter:
    st.subheader("Peta Sebaran Perilaku Agen")
    st.write(
        "Sumbu X menunjukkan penurunan volume pada M12 ke M13. Sumbu Y menunjukkan penurunan premi APE pada M12 ke M13. "
        "Ukuran lingkaran mewakili rasio perbedaan premi polis yang lapse dibanding polis aktif."
    )

    st.plotly_chart(
        create_anomaly_scatter_plot(detected_agents),
        use_container_width=True,
    )

    c_norm, c_t1, c_t2 = st.columns(3)
    with c_norm:
        st.markdown(
            """
            <div style="background-color:#F5F8FC; border:1px solid #D9E5F2; border-radius:8px; padding:14px;">
                <strong style="color:#10573F; font-size:0.95rem;">Agen Normal</strong>
                <p style="font-size:0.88rem; color:#192C4D; font-weight:500; margin:6px 0 0 0; line-height:1.5;">
                    Penurunan wajar dan tetap memenuhi ambang batas persistensi AAJI (80% - 85%).
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_t1:
        st.markdown(
            """
            <div style="background-color:#F5F8FC; border:1px solid #D9E5F2; border-radius:8px; padding:14px;">
                <strong style="color:#D94B4B; font-size:0.95rem;">Hit and Run</strong>
                <p style="font-size:0.88rem; color:#192C4D; font-weight:500; margin:6px 0 0 0; line-height:1.5;">
                    Persistensi M1-M12 tinggi, lalu anjlok serempak lebih dari 25% di bulan ke-13.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_t2:
        st.markdown(
            """
            <div style="background-color:#F5F8FC; border:1px solid #D9E5F2; border-radius:8px; padding:14px;">
                <strong style="color:#8C6615; font-size:0.95rem;">Cherry Picking</strong>
                <p style="font-size:0.88rem; color:#192C4D; font-weight:500; margin:6px 0 0 0; line-height:1.5;">
                    Volume M13 dipertahankan aman, tetapi polis berpremi besar sengaja dimatikan.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ------------------------------------------------------------------------------
# TAB 3: EARLY WARNING GRACE PERIOD
# ------------------------------------------------------------------------------
with tab_grace:
    st.subheader("Daftar Polis Grace Period (M11 dan M12)")
    st.write(
        "Daftar polis yang sedang memasuki masa tenggang sebelum jatuh tempo M13. "
        "Data ini berguna untuk tindak lanjut retensi sebelum polis resmi lapse."
    )

    if len(grace_df) > 0:
        g1, g2 = st.columns([1, 2])
        with g1:
            st.metric("Total Polis Rawan", f"{len(grace_df):,} Polis")
            st.metric("Total Premi Berisiko", f"Rp {grace_df['ape'].sum() / 1_000_000:,.0f} Juta")

            pm_dist = grace_df["payment_method"].value_counts(normalize=True) * 100.0
            st.write("**Metode Pembayaran:**")
            st.markdown(
                f"""
                <div style="background-color:#FFFFFF; border:1px solid #D9E5F2; border-radius:8px; padding:14px 16px; margin-top:6px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span style="color:#192C4D; font-weight:600; font-size:0.9rem;">Auto-Debit:</span>
                        <span style="color:#192C4D; font-weight:700; font-size:0.92rem;">{pm_dist.get('Auto-Debit', 0.0):.1f}%</span>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#192C4D; font-weight:600; font-size:0.9rem;">Manual / Tunai:</span>
                        <span style="color:#D94B4B; font-weight:700; font-size:0.92rem;">{pm_dist.get('Manual/Cash', 0.0):.1f}%</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with g2:
            cols = ["policy_id", "agent_id", "cohort_month", "month_index", "ape", "payment_method"]
            grace_display = grace_df[cols].copy().rename(
                columns={
                    "policy_id": "Nomor Polis",
                    "agent_id": "Kode Agen",
                    "cohort_month": "Bulan Kohort",
                    "month_index": "Bulan Polis",
                    "ape": "Nilai APE",
                    "payment_method": "Metode Pembayaran",
                }
            )
            grace_display["Nilai APE"] = grace_display["Nilai APE"].map(lambda x: f"Rp {x:,.0f}")

            st.dataframe(
                grace_display,
                use_container_width=True,
                height=320,
                hide_index=True,
            )
    else:
        st.info("Tidak ada polis pada masa tenggang di bulan M11 atau M12.")

# ------------------------------------------------------------------------------
# TAB 4: DAFTAR PENGAWASAN AGEN & DETAIL BUKTI
# ------------------------------------------------------------------------------
with tab_audit:
    st.subheader("Daftar Pengawasan Agen Berisiko")
    st.write("Daftar agen yang terindikasi anomali pada saringan aturan maupun model deteksi.")

    w1, w2, w3 = st.columns([1, 1, 2])
    with w1:
        tier_filter = st.selectbox(
            "Filter Status:",
            options=["Semua Status", "Hanya Terindikasi Anomali", "Hit and Run", "Cherry Picking", "Normal"],
        )
    with w2:
        min_score = st.slider("Skor Anomali Minimal:", min_value=0.0, max_value=1.0, value=0.0, step=0.05)
    with w3:
        search_query = st.text_input("Cari Agen (ID atau Nama):", "")

    watchlist = detected_agents[detected_agents["anomaly_score"] >= min_score].copy()

    if tier_filter == "Hanya Terindikasi Anomali":
        watchlist = watchlist[watchlist["risk_category"] != "Normal"]
    elif tier_filter == "Hit and Run":
        watchlist = watchlist[watchlist["risk_category"].str.contains("Hit and Run|Hit-and-Run")]
    elif tier_filter == "Cherry Picking":
        watchlist = watchlist[watchlist["risk_category"].str.contains("Cherry Picking|Cherry-Picking")]
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

    watch_display = watchlist[display_cols].copy().rename(
        columns={
            "agent_id": "Kode Agen",
            "agent_name": "Nama Agen",
            "channel": "Kanal",
            "branch_office": "Cabang",
            "risk_category": "Status Risiko",
            "anomaly_score": "Skor Anomali",
            "m13_vol_persistency": "Vol M13",
            "m13_ape_persistency": "APE M13",
            "lapse_shock_vol": "Δ Vol",
            "lapse_shock_ape": "Δ APE",
            "ape_disparity_ratio": "Disparitas",
            "cash_payment_ratio": "% Tunai",
            "primary_risk_drivers": "Faktor Risiko Kuantitatif",
        }
    )
    watch_display["Skor Anomali"] = watch_display["Skor Anomali"].map(lambda x: f"{x:.2f}")
    watch_display["Vol M13"] = watch_display["Vol M13"].map(lambda x: f"{x:.1f}%")
    watch_display["APE M13"] = watch_display["APE M13"].map(lambda x: f"{x:.1f}%")
    watch_display["Δ Vol"] = watch_display["Δ Vol"].map(lambda x: f"{x:.1f}%")
    watch_display["Δ APE"] = watch_display["Δ APE"].map(lambda x: f"{x:.1f}%")
    watch_display["Disparitas"] = watch_display["Disparitas"].map(lambda x: f"{x:.2f}x")
    watch_display["% Tunai"] = watch_display["% Tunai"].map(lambda x: f"{x:.1f}%")

    st.dataframe(
        watch_display,
        use_container_width=True,
        height=320,
        hide_index=True,
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
