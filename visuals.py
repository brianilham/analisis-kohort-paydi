"""
Plotly Visualizations & Dashboard Analytics Components for PAYDI Persistency App.
Themed with MNC Life Design System (DESIGN.md).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# MNC Life Design Tokens
MNC_PRIMARY = "#192C4D"       # Deep Navy
MNC_SECONDARY = "#666666"     # Neutral Gray
MNC_TERTIARY = "#C89B2C"      # Warm Gold
MNC_NEUTRAL = "#FFFFFF"       # Clean White
MNC_SURFACE = "#F5F8FC"       # Atmospheric Surface
MNC_ERROR = "#D94B4B"         # Clear Red
MNC_BORDER = "#EEEEFF"        # Light Border
MNC_MUTED = "#D9E5F2"         # Soft Blue-Gray


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
    """Generate interactive 2D cohort retention heatmap (M1-M24)."""
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix_df.values,
            x=list(matrix_df.columns),
            y=list(matrix_df.index),
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
            colorbar=dict(title="Retention %", ticksuffix="%"),
            hoverongaps=False,
            hovertemplate=(
                "<b>Cohort:</b> %{y}<br>"
                "<b>Policy Month:</b> %{x}<br>"
                "<b>Retention Rate:</b> %{z:.1f}%<extra></extra>"
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
            line=dict(color=MNC_ERROR, width=2, dash="dash"),
        )
        fig.add_annotation(
            x="M13",
            y=1.03,
            yref="paper",
            text="M13 Cutoff",
            showarrow=False,
            font=dict(size=11, color=MNC_ERROR, family="Plus Jakarta Sans, sans-serif"),
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=MNC_PRIMARY, family="Plus Jakarta Sans, sans-serif")),
        font=dict(family="Plus Jakarta Sans, sans-serif", color=MNC_PRIMARY),
        plot_bgcolor=MNC_NEUTRAL,
        paper_bgcolor=MNC_NEUTRAL,
        xaxis=dict(title="Policy Month Index (M1 - M24)", tickangle=-45, gridcolor=MNC_BORDER),
        yaxis=dict(title="Cohort Month (Issue Date)", autorange="reversed", gridcolor=MNC_BORDER),
        margin=dict(l=40, r=40, t=50, b=40),
        height=480,
    )
    return fig


def create_discrepancy_heatmap(
    discrepancy_df: pd.DataFrame,
    title: str = "Premium Leakage Matrix: Volume % − APE %",
) -> go.Figure:
    """Generate heatmap highlighting premium leakage (Volume % minus APE %)."""
    fig = go.Figure(
        data=go.Heatmap(
            z=discrepancy_df.values,
            x=list(discrepancy_df.columns),
            y=list(discrepancy_df.index),
            colorscale="YlOrRd",
            zmin=0.0,
            zmax=40.0,
            colorbar=dict(title="Gap %", ticksuffix="%"),
            hovertemplate=(
                "<b>Cohort:</b> %{y}<br>"
                "<b>Month:</b> %{x}<br>"
                "<b>Leakage Gap:</b> %{z:.1f}%<extra></extra>"
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
            line=dict(color=MNC_PRIMARY, width=2, dash="dash"),
        )
        fig.add_annotation(
            x="M13",
            y=1.03,
            yref="paper",
            text="M13 Cutoff",
            showarrow=False,
            font=dict(size=11, color=MNC_PRIMARY, family="Plus Jakarta Sans, sans-serif"),
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=MNC_PRIMARY, family="Plus Jakarta Sans, sans-serif")),
        font=dict(family="Plus Jakarta Sans, sans-serif", color=MNC_PRIMARY),
        plot_bgcolor=MNC_NEUTRAL,
        paper_bgcolor=MNC_NEUTRAL,
        xaxis=dict(title="Policy Month Index (M1 - M24)", tickangle=-45, gridcolor=MNC_BORDER),
        yaxis=dict(title="Cohort Month (Issue Date)", autorange="reversed", gridcolor=MNC_BORDER),
        margin=dict(l=40, r=40, t=50, b=40),
        height=480,
    )
    return fig


def create_anomaly_scatter_plot(detected_df: pd.DataFrame) -> go.Figure:
    """
    Generate multivariate scatter plot with MNC Life design system tokens.
    """
    df = detected_df.copy()
    color_map = {
        "Normal": "#1E6B52",                                    # Calm trustworthy green-teal
        "Tier 1: Rule Violation (Hit-and-Run)": MNC_ERROR,       # MNC Error Red (#D94B4B)
        "Tier 2: ML Anomaly (Cherry-Picking / Hidden Leakage)": MNC_TERTIARY, # MNC Gold (#C89B2C)
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
        title="Distribusi Anomali Perilaku Agen (Volume Shock vs APE Shock)",
    )

    fig.add_vline(x=25.0, line_dash="dot", line_color=MNC_ERROR, annotation_text="Batas Tier 1 Vol (25%)")
    fig.add_hline(y=20.0, line_dash="dot", line_color=MNC_TERTIARY, annotation_text="Peringatan APE Shock (20%)")

    fig.add_annotation(
        x=50, y=10,
        text="Zona: Hit-and-Run<br>(Volume & APE Anjlok)",
        showarrow=False,
        font=dict(size=10, color=MNC_ERROR, family="Plus Jakarta Sans, sans-serif"),
        bgcolor="rgba(217, 75, 75, 0.08)",
        bordercolor="rgba(217, 75, 75, 0.2)",
    )
    fig.add_annotation(
        x=8, y=55,
        text="Zona: Cherry-Picking<br>(Volume Aman, APE Anjlok)",
        showarrow=False,
        font=dict(size=10, color=MNC_TERTIARY, family="Plus Jakarta Sans, sans-serif"),
        bgcolor="rgba(200, 155, 44, 0.08)",
        bordercolor="rgba(200, 155, 44, 0.2)",
    )
    fig.add_annotation(
        x=5, y=5,
        text="Zona: Kepatuhan Normal",
        showarrow=False,
        font=dict(size=10, color="#1E6B52", family="Plus Jakarta Sans, sans-serif"),
        bgcolor="rgba(30, 107, 82, 0.08)",
        bordercolor="rgba(30, 107, 82, 0.2)",
    )

    fig.update_layout(
        height=520,
        font=dict(family="Plus Jakarta Sans, sans-serif", color=MNC_PRIMARY),
        plot_bgcolor=MNC_NEUTRAL,
        paper_bgcolor=MNC_NEUTRAL,
        xaxis=dict(gridcolor=MNC_BORDER),
        yaxis=dict(gridcolor=MNC_BORDER),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=70, b=40),
    )
    return fig


def create_agent_drilldown_curves(
    policies_df: pd.DataFrame,
    history_df: pd.DataFrame,
    agent_id: str,
) -> go.Figure:
    """Generate M1-M24 retention curve for a single selected agent."""
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
            line=dict(color=MNC_PRIMARY, width=2.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=agg["month_index"],
            y=agg["ape_retention"],
            mode="lines+markers",
            name="Retensi Premi APE (%)",
            line=dict(color=MNC_TERTIARY, width=2.5, dash="dash"),
        )
    )

    fig.add_hline(
        y=80.0,
        line_dash="dot",
        line_color=MNC_SECONDARY,
        annotation_text="Standar OJK/AAJI 80%",
        annotation_position="bottom right",
    )
    fig.add_vline(
        x=13,
        line_dash="dash",
        line_color=MNC_ERROR,
        annotation_text="Batas M13",
    )

    fig.update_layout(
        title=f"Kurva Siklus Hidup Agen {agent_id} (Volume vs APE M1-M24)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color=MNC_PRIMARY),
        plot_bgcolor=MNC_NEUTRAL,
        paper_bgcolor=MNC_NEUTRAL,
        xaxis=dict(title="Bulan Polis (M1 - M24)", tickmode="linear", dtick=1, gridcolor=MNC_BORDER),
        yaxis=dict(title="Tingkat Retensi (%)", range=[0, 105], gridcolor=MNC_BORDER),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig
