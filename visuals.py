"""
Plotly Visualizations & Dashboard Analytics Components for PAYDI Persistency App.
Themed with MNC Life Design System (DESIGN.md) and High-Contrast Typography.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# MNC Life Design Tokens
MNC_PRIMARY = "#192C4D"       # Deep Navy (Utama)
MNC_SECONDARY = "#475569"     # Dark Slate Neutral (Teks Keterangan Terbaca)
MNC_TERTIARY = "#C89B2C"      # Warm Gold
MNC_TERTIARY_TEXT = "#8C6615" # Darker Gold for high text contrast on white
MNC_NEUTRAL = "#FFFFFF"       # Clean White
MNC_SURFACE = "#F5F8FC"       # Pale Blue-White
MNC_ERROR = "#D94B4B"         # Clear Red Alert
MNC_BORDER = "#D9E5F2"        # Crisp Light Border
MNC_FONT_FAMILY = "Plus Jakarta Sans, sans-serif"


def calculate_dashboard_kpis(
    matrices: Dict[str, Any],
    detected_df: pd.DataFrame,
    grace_df: pd.DataFrame,
) -> Dict[str, float]:
    """Calculate executive KPI summary metrics."""
    m13_summary = matrices.get("m13_summary", {})
    m13_vol = float(m13_summary.get("m13_vol_persistency", 0.0))
    m13_ape = float(m13_summary.get("m13_ape_persistency", 0.0))
    leakage_gap = float(m13_summary.get("leakage_gap", 0.0))

    tier1_count = int(detected_df["tier1_violation"].sum())
    tier2_count = int(
        (detected_df["tier2_anomaly"] & ~detected_df["tier1_violation"]).sum()
    )
    total_flagged = tier1_count + tier2_count

    grace_policy_count = len(grace_df["policy_id"].unique()) if len(grace_df) > 0 else 0
    grace_total_ape = float(grace_df["ape"].sum()) if len(grace_df) > 0 else 0.0

    return {
        "m13_vol": m13_vol,
        "m13_ape": m13_ape,
        "leakage_gap": leakage_gap,
        "tier1_count": tier1_count,
        "tier2_count": tier2_count,
        "total_flagged": total_flagged,
        "grace_policy_count": grace_policy_count,
        "grace_total_ape": grace_total_ape,
    }


def create_cohort_heatmap(
    matrix_df: pd.DataFrame,
    title: str = "Cohort Retention Matrix (%)",
    colorscale: str = "Blues",
    zmin: float = 40.0,
    zmax: float = 100.0,
) -> go.Figure:
    """Generate interactive 2D cohort retention heatmap with high-contrast text and crisp cell borders."""
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix_df.values,
            x=list(matrix_df.columns),
            y=list(matrix_df.index),
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
            xgap=1.5,
            ygap=1.5,
            colorbar=dict(
                title=dict(text="Retensi %", font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY)),
                tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
                ticksuffix="%",
            ),
            hoverongaps=False,
            hovertemplate=(
                "<b>Kohort:</b> %{y}<br>"
                "<b>Bulan Polis:</b> %{x}<br>"
                "<b>Tingkat Retensi:</b> %{z:.1f}%<extra></extra>"
            ),
        )
    )

    if "M13" in matrix_df.columns:
        fig.add_shape(
            type="line",
            x0="M13",
            x1="M13",
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color=MNC_ERROR, width=2.5, dash="dash"),
        )
        fig.add_annotation(
            x="M13",
            y=1.04,
            yref="paper",
            text="Batas M13",
            showarrow=False,
            font=dict(size=12, color=MNC_ERROR, family=MNC_FONT_FAMILY),
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=MNC_PRIMARY, family=MNC_FONT_FAMILY)),
        font=dict(family=MNC_FONT_FAMILY, color=MNC_PRIMARY),
        plot_bgcolor="#CAD7E6",
        paper_bgcolor=MNC_NEUTRAL,
        xaxis=dict(
            title=dict(text="Bulan Polis (M1 - M24)", font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY)),
            tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            tickangle=-45,
            gridcolor=MNC_BORDER,
        ),
        yaxis=dict(
            title=dict(text="Bulan Kohort (Issue Date)", font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY)),
            tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            autorange="reversed",
            gridcolor=MNC_BORDER,
        ),
        margin=dict(l=40, r=40, t=55, b=40),
        height=480,
    )
    return fig


def create_discrepancy_heatmap(
    discrepancy_df: pd.DataFrame,
    title: str = "Selisih Kebocoran Premi: Volume % − APE %",
) -> go.Figure:
    """
    Generate heatmap highlighting premium leakage.
    Uses custom MNC Life theme gradient with clearly visible non-white base for M1-M12
    (Pale Slate Blue -> Light Sky Blue -> Warm Gold -> Rich Amber -> Red Alert).
    """
    mnc_leakage_palette = [
        [0.0, "#E6EFF9"],    # Selisih <= 0% (Seimbang / Tidak ada kebocoran) - Soft Pastel Blue
        [0.15, "#D0E2F6"],   # Selisih ~3-5% (Variasi wajar) - Light Sky Blue
        [0.35, "#FCEEC7"],   # Selisih ~10-12% (Peringatan Dini) - Warm Pale Gold
        [0.65, "#EAA827"],   # Selisih ~20-25% (Kebocoran Signifikan) - MNC Amber Gold
        [1.0, MNC_ERROR],    # Selisih >= 35% (Kebocoran Kritis / Cherry-Picking) - MNC Red (#D94B4B)
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=discrepancy_df.values,
            x=list(discrepancy_df.columns),
            y=list(discrepancy_df.index),
            colorscale=mnc_leakage_palette,
            zmin=-2.0,
            zmax=35.0,
            xgap=1.5,
            ygap=1.5,
            colorbar=dict(
                title=dict(text="Selisih Gap %", font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY)),
                tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
                ticksuffix="%",
            ),
            hovertemplate=(
                "<b>Kohort:</b> %{y}<br>"
                "<b>Bulan:</b> %{x}<br>"
                "<b>Selisih Gap:</b> %{z:.1f}%<extra></extra>"
            ),
        )
    )

    if "M13" in discrepancy_df.columns:
        fig.add_shape(
            type="line",
            x0="M13",
            x1="M13",
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color=MNC_PRIMARY, width=2.5, dash="dash"),
        )
        fig.add_annotation(
            x="M13",
            y=1.04,
            yref="paper",
            text="Batas M13",
            showarrow=False,
            font=dict(size=12, color=MNC_PRIMARY, family=MNC_FONT_FAMILY),
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=MNC_PRIMARY, family=MNC_FONT_FAMILY)),
        font=dict(family=MNC_FONT_FAMILY, color=MNC_PRIMARY),
        plot_bgcolor="#CAD7E6",
        paper_bgcolor=MNC_NEUTRAL,
        xaxis=dict(
            title=dict(text="Bulan Polis (M1 - M24)", font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY)),
            tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            tickangle=-45,
            gridcolor=MNC_BORDER,
        ),
        yaxis=dict(
            title=dict(text="Bulan Kohort (Issue Date)", font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY)),
            tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            autorange="reversed",
            gridcolor=MNC_BORDER,
        ),
        margin=dict(l=40, r=40, t=55, b=40),
        height=480,
    )
    return fig


def create_anomaly_scatter_plot(detected_df: pd.DataFrame) -> go.Figure:
    """
    Generate multivariate scatter plot with high-contrast bold typography and dedicated legend styling.
    """
    df = detected_df.copy()
    color_map = {
        "Normal": "#1E6B52",               # Emerald
        "Hit and Run": MNC_ERROR,          # Red (#D94B4B)
        "Cherry Picking": MNC_TERTIARY,    # Gold (#C89B2C)
        "Hit-and-Run": MNC_ERROR,
        "Cherry-Picking": MNC_TERTIARY,
    }

    fig = px.scatter(
        df,
        x="lapse_shock_vol",
        y="lapse_shock_ape",
        color="risk_category",
        color_discrete_map=color_map,
        size="ape_disparity_ratio",
        size_max=20,
        hover_name="agent_name",
        hover_data={
            "agent_id": True,
            "channel": True,
            "branch_office": True,
            "anomaly_score": ":.2f",
            "lapse_shock_vol": ":.1f%",
            "lapse_shock_ape": ":.1f%",
            "ape_disparity_ratio": ":.2f",
            "cash_payment_ratio": ":.1f%",
            "primary_risk_drivers": True,
        },
        labels={
            "lapse_shock_vol": "Δ Persistensi Volume M12→M13 (%)",
            "lapse_shock_ape": "Δ Persistensi Premi APE M12→M13 (%)",
            "risk_category": "Status Deteksi",
            "ape_disparity_ratio": "Disparitas Premi",
        },
    )

    fig.add_vline(
        x=25.0,
        line_dash="dot",
        line_color=MNC_ERROR,
        line_width=2,
        annotation_text="Batas Tier 1 Vol (25%)",
        annotation_font=dict(color=MNC_ERROR, size=11, family=MNC_FONT_FAMILY),
        annotation_position="top left",
    )
    fig.add_hline(
        y=20.0,
        line_dash="dot",
        line_color=MNC_TERTIARY_TEXT,
        line_width=2,
        annotation_text="Peringatan APE Shock (20%)",
        annotation_font=dict(color=MNC_TERTIARY_TEXT, size=11, family=MNC_FONT_FAMILY),
        annotation_position="bottom right",
    )

    fig.add_annotation(
        x=50, y=10,
        text="<b>Zona: Hit-and-Run</b><br>Volume & APE Anjlok",
        showarrow=False,
        font=dict(size=11, color=MNC_ERROR, family=MNC_FONT_FAMILY),
        bgcolor="rgba(217, 75, 75, 0.08)",
        bordercolor="rgba(217, 75, 75, 0.3)",
        borderwidth=1,
    )
    fig.add_annotation(
        x=8, y=55,
        text="<b>Zona: Cherry-Picking</b><br>Volume Aman, APE Anjlok",
        showarrow=False,
        font=dict(size=11, color=MNC_TERTIARY_TEXT, family=MNC_FONT_FAMILY),
        bgcolor="rgba(200, 155, 44, 0.10)",
        bordercolor="rgba(200, 155, 44, 0.3)",
        borderwidth=1,
    )
    fig.add_annotation(
        x=5, y=5,
        text="<b>Zona: Kepatuhan Normal</b>",
        showarrow=False,
        font=dict(size=11, color="#10573F", family=MNC_FONT_FAMILY),
        bgcolor="rgba(30, 107, 82, 0.08)",
        bordercolor="rgba(30, 107, 82, 0.3)",
        borderwidth=1,
    )

    fig.update_layout(
        height=540,
        font=dict(family=MNC_FONT_FAMILY, color=MNC_PRIMARY),
        plot_bgcolor=MNC_NEUTRAL,
        paper_bgcolor=MNC_NEUTRAL,
        title=dict(
            text="<b>Distribusi Anomali Perilaku Agen (Volume Shock vs APE Shock)</b>",
            font=dict(color=MNC_PRIMARY, size=15, family=MNC_FONT_FAMILY),
            x=0.01,
            y=0.98,
            xanchor="left",
            yanchor="top",
        ),
        xaxis=dict(
            title=dict(
                text="Δ Persistensi Volume M12→M13 (%)",
                font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY),
            ),
            tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            gridcolor=MNC_BORDER,
        ),
        yaxis=dict(
            title=dict(
                text="Δ Persistensi Premi APE M12→M13 (%)",
                font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY),
            ),
            tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            gridcolor=MNC_BORDER,
        ),
        legend=dict(
            title=dict(
                text="<b>Status Deteksi:</b>",
                font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY),
            ),
            font=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(245, 248, 252, 0.95)",
            bordercolor=MNC_BORDER,
            borderwidth=1,
        ),
        margin=dict(l=45, r=40, t=60, b=90),
    )
    return fig


def create_agent_drilldown_curves(
    policies_df: pd.DataFrame,
    history_df: pd.DataFrame,
    agent_id: str,
) -> go.Figure:
    """Generate M1-M24 retention curve for a single selected agent with crisp contrast."""
    agent_policies = policies_df[policies_df["agent_id"] == agent_id]
    if len(agent_policies) == 0:
        return go.Figure()

    merged = history_df[history_df["policy_id"].isin(agent_policies["policy_id"])].merge(
        agent_policies[["policy_id", "ape"]],
        on="policy_id",
        how="inner",
    )

    n_init = len(agent_policies)
    ape_init = float(agent_policies["ape"].sum())

    merged["is_active"] = merged["status"].isin(["Active", "Grace Period"])
    merged["active_ape"] = np.where(merged["is_active"], merged["ape"], 0.0)

    agg = merged.groupby("month_index").agg(
        active_pols=("is_active", "sum"),
        active_ape=("active_ape", "sum"),
    ).reset_index()

    agg["vol_retention"] = (agg["active_pols"] / n_init * 100.0).round(2)
    agg["ape_retention"] = (agg["active_ape"] / ape_init * 100.0).round(2) if ape_init > 0 else 0.0

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=agg["month_index"],
            y=agg["vol_retention"],
            mode="lines+markers",
            name="Retensi Volume (%)",
            line=dict(color=MNC_PRIMARY, width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=agg["month_index"],
            y=agg["ape_retention"],
            mode="lines+markers",
            name="Retensi Premi APE (%)",
            line=dict(color=MNC_TERTIARY, width=3, dash="dash"),
        )
    )

    fig.add_hline(
        y=80.0,
        line_dash="dot",
        line_color=MNC_SECONDARY,
        line_width=2,
        annotation_text="Standar OJK/AAJI 80%",
        annotation_font=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
        annotation_position="bottom right",
    )
    fig.add_vline(
        x=13,
        line_dash="dash",
        line_color=MNC_ERROR,
        line_width=2,
        annotation_text="Batas M13",
        annotation_font=dict(color=MNC_ERROR, size=11, family=MNC_FONT_FAMILY),
    )

    fig.update_layout(
        title=dict(
            text=f"Kurva Siklus Hidup Agen {agent_id} (Volume vs APE M1-M24)",
            font=dict(color=MNC_PRIMARY, size=14, family=MNC_FONT_FAMILY),
        ),
        font=dict(family=MNC_FONT_FAMILY, color=MNC_PRIMARY),
        plot_bgcolor=MNC_NEUTRAL,
        paper_bgcolor=MNC_NEUTRAL,
        xaxis=dict(
            title=dict(text="Bulan Polis (M1 - M24)", font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY)),
            tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            tickmode="linear",
            dtick=1,
            gridcolor=MNC_BORDER,
        ),
        yaxis=dict(
            title=dict(text="Tingkat Retensi (%)", font=dict(color=MNC_PRIMARY, size=12, family=MNC_FONT_FAMILY)),
            tickfont=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            range=[0, 105],
            gridcolor=MNC_BORDER,
        ),
        height=380,
        legend=dict(
            font=dict(color=MNC_PRIMARY, size=11, family=MNC_FONT_FAMILY),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig
