"""
streamlit_signal_tab.py — Onglet Signal IA pour krockOPVM V2
=============================================================
Intègre dans Streamlit la visualisation du score de confiance (0–100)
produit par signal_engine.py.

Intégration dans streamlit_app.py :
    from streamlit_signal_tab import render_signal_tab
    render_signal_tab(df_features, df_macro, asset_class, fund_name)
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from src.signal_engine import SignalEngine, SignalResult, WEIGHTS


# ---------------------------------------------------------------------------
# Helpers visuels
# ---------------------------------------------------------------------------

def _score_color(score: float) -> str:
    """Couleur hex selon le niveau du score."""
    if score >= 70:
        return "#1A9E6B"   # vert foncé
    elif score >= 55:
        return "#5DBF8A"   # vert clair
    elif score >= 45:
        return "#E8A922"   # ambre
    elif score >= 30:
        return "#E8703A"   # orange
    else:
        return "#C9352E"   # rouge


def _gauge_figure(score: float, title: str = "Score de Confiance") -> go.Figure:
    """Crée une jauge Plotly pour le score 0–100."""
    color = _score_color(score)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        title={"text": title, "font": {"size": 14, "color": "#6B7280"}},
        number={"font": {"size": 36, "color": color}, "suffix": "/100"},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickvals": [0, 30, 45, 55, 70, 100],
                "ticktext": ["0", "30", "45", "55", "70", "100"],
                "tickfont": {"size": 10, "color": "#9CA3AF"},
            },
            "bar": {"color": color, "thickness": 0.25},
            "steps": [
                {"range": [0, 30],  "color": "#FEE2E2"},
                {"range": [30, 45], "color": "#FEF3C7"},
                {"range": [45, 55], "color": "#F3F4F6"},
                {"range": [55, 70], "color": "#D1FAE5"},
                {"range": [70, 100],"color": "#A7F3D0"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))

    fig.update_layout(
        height=220,
        margin={"t": 30, "b": 10, "l": 20, "r": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "IBM Plex Sans, sans-serif"},
    )
    return fig


def _subscores_bar(result: SignalResult) -> go.Figure:
    """Barres horizontales des trois sous-scores avec leurs poids."""
    labels = ["Macro Score", "Momentum Score", "RF Score"]
    values = [result.macro_score, result.momentum_score, result.rf_score]
    weights = [
        result.weights_used["macro"],
        result.weights_used["momentum"],
        result.weights_used["rf"],
    ]
    colors = [_score_color(v) for v in values]

    fig = go.Figure()
    for i, (label, val, w, col) in enumerate(zip(labels, values, weights, colors)):
        fig.add_trace(go.Bar(
            y=[f"{label}<br><span style='font-size:10px;color:#9CA3AF'>poids {w:.0%}</span>"],
            x=[val],
            orientation="h",
            marker_color=col,
            marker_line_width=0,
            text=f"  {val:.1f}",
            textposition="outside",
            textfont={"size": 13, "color": col},
            showlegend=False,
            name=label,
        ))

    fig.add_vline(x=50, line_width=1, line_dash="dash", line_color="#9CA3AF")
    fig.update_xaxes(range=[0, 115], showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(tickfont={"size": 11}, showgrid=False)
    fig.update_layout(
        height=200,
        margin={"t": 10, "b": 10, "l": 10, "r": 50},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.35,
        barmode="group",
    )
    return fig


def _features_importance_chart(top_features: list[str]) -> go.Figure:
    """Affiche les Top features sélectionnées."""
    # Indices décroissants simulant un rang d'importance relatif
    n = len(top_features)
    importance = np.linspace(1.0, 0.3, n)

    fig = go.Figure(go.Bar(
        x=importance[::-1],
        y=top_features[::-1],
        orientation="h",
        marker_color="#4F7FFA",
        marker_opacity=0.75,
        marker_line_width=0,
    ))
    fig.update_xaxes(showgrid=False, visible=False)
    fig.update_yaxes(tickfont={"size": 10})
    fig.update_layout(
        height=max(200, n * 22),
        margin={"t": 10, "b": 10, "l": 10, "r": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _score_history_chart(score_history: pd.Series) -> go.Figure:
    """Courbe historique du score de confiance."""
    colors = [_score_color(v) for v in score_history.values]
    fig = go.Figure()

    # Zone de fond par niveau
    for ymin, ymax, fcolor in [
        (0, 30, "rgba(201,53,46,0.06)"),
        (30, 45, "rgba(232,112,58,0.06)"),
        (45, 55, "rgba(200,200,200,0.06)"),
        (55, 70, "rgba(93,191,138,0.06)"),
        (70, 100, "rgba(26,158,107,0.06)"),
    ]:
        fig.add_hrect(y0=ymin, y1=ymax, fillcolor=fcolor, line_width=0)

    fig.add_trace(go.Scatter(
        x=score_history.index,
        y=score_history.values,
        mode="lines+markers",
        line={"width": 2, "color": "#4F7FFA"},
        marker={"size": 5, "color": colors},
        fill="tozeroy",
        fillcolor="rgba(79,127,250,0.08)",
        name="Score IA",
    ))
    fig.add_hline(y=50, line_width=1, line_dash="dot", line_color="#9CA3AF")
    fig.update_yaxes(range=[0, 100], tickvals=[0, 30, 45, 55, 70, 100])
    fig.update_layout(
        height=220,
        margin={"t": 10, "b": 10, "l": 40, "r": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Composant principal
# ---------------------------------------------------------------------------

def render_signal_tab(
    df_features: pd.DataFrame,
    df_macro: pd.DataFrame,
    asset_class: str,
    fund_name: str,
    score_history: pd.Series | None = None,
) -> SignalResult | None:
    """
    Affiche l'onglet Signal IA complet dans Streamlit.

    Paramètres
    ----------
    df_features : DataFrame
        Features calculées (issues du pipeline feature engineering).
    df_macro : DataFrame
        Données macro (BAM, BDT, World Bank).
    asset_class : str
        Classe d'actif du fond sélectionné.
    fund_name : str
        Nom du fond (affiché dans l'en-tête).
    score_history : Series, optional
        Historique des scores (index=date, values=score) pour la courbe temporelle.

    Retourne
    --------
    SignalResult ou None en cas d'erreur.
    """
    st.markdown(f"### Signal IA — {fund_name}")
    st.caption(f"Classe d'actif : **{asset_class.capitalize()}** · Modèle : RandomForest + Momentum + Macro")

    # -- Contrôles --
    with st.expander("Paramètres du moteur", expanded=False):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            n_features = st.slider("Top N features", 5, 25, 15, key="sig_n_feat")
        with col_p2:
            wf_days = st.slider("Walk-forward (jours)", 10, 60, 30, key="sig_wf")
        with col_p3:
            target_col = st.selectbox(
                "Variable cible",
                [c for c in df_features.columns if "log_return" in c or "rendement" in c],
                key="sig_target",
            )
            if not target_col:
                target_col = df_features.columns[0]

    # -- Calcul --
    with st.spinner("Calcul du signal IA en cours…"):
        try:
            engine = SignalEngine(
                asset_class=asset_class,
                n_top_features=n_features,
                walk_forward_days=wf_days,
            )
            result = engine.compute(df_features, df_macro, target_col=target_col)
        except Exception as e:
            st.error(f"Erreur moteur : {e}")
            return None

    # -- En-tête : interprétation --
    color = _score_color(result.score)
    st.markdown(
        f"""
        <div style="
            border-left: 4px solid {color};
            padding: 10px 16px;
            background: {color}11;
            border-radius: 4px;
            margin-bottom: 16px;
        ">
            <span style="font-size:18px;font-weight:600;color:{color}">
                {result.interpretation}
            </span>
            <span style="font-size:13px;color:#6B7280;margin-left:12px;">
                Score : {result.score}/100
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -- Ligne 1 : Jauge + Sous-scores --
    col_gauge, col_bars = st.columns([1, 1.4])

    with col_gauge:
        st.plotly_chart(
            _gauge_figure(result.score),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with col_bars:
        st.markdown("**Décomposition des sous-scores**")
        st.plotly_chart(
            _subscores_bar(result),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # -- Ligne 2 : Métriques de confiance --
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Directional Accuracy", f"{result.directional_accuracy:.1%}")
    m2.metric("MAE (log return)", f"{result.mae:.5f}")
    m3.metric("RF Score", f"{result.rf_score:.1f}/100")
    m4.metric("Macro Score", f"{result.macro_score:.1f}/100")

    # -- Ligne 3 : Historique du score --
    if score_history is not None and len(score_history) > 1:
        st.markdown("**Évolution historique du score**")
        st.plotly_chart(
            _score_history_chart(score_history),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # -- Ligne 4 : Top features --
    with st.expander("Top features sélectionnées (permutation importance)", expanded=False):
        col_feat, col_info = st.columns([1.5, 1])
        with col_feat:
            st.plotly_chart(
                _features_importance_chart(result.top_features),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        with col_info:
            st.markdown("**Pondérations appliquées**")
            for k, v in result.weights_used.items():
                st.write(f"- {k.capitalize()} : {v:.0%}")
            st.markdown("---")
            st.markdown("**Prochaine VL estimée**")
            next_ret = engine.predict_next(df_features)
            if next_ret is not None:
                direction = "▲" if next_ret > 0 else "▼"
                st.markdown(
                    f"<span style='color:{_score_color(60 if next_ret > 0 else 35)};font-size:16px'>"
                    f"{direction} {next_ret:+.5f} (log return)"
                    f"</span>",
                    unsafe_allow_html=True,
                )

    # -- Export CSV --
    st.divider()
    export_data = {
        "fond": fund_name,
        "classe_actif": asset_class,
        "score_global": result.score,
        "rf_score": result.rf_score,
        "momentum_score": result.momentum_score,
        "macro_score": result.macro_score,
        "directional_accuracy": result.directional_accuracy,
        "mae": result.mae,
        "interpretation": result.interpretation,
        "top_features": "; ".join(result.top_features),
    }
    df_export = pd.DataFrame([export_data])
    st.download_button(
        label="Exporter le signal (CSV)",
        data=df_export.to_csv(index=False).encode("utf-8"),
        file_name=f"signal_{fund_name.replace(' ', '_')}.csv",
        mime="text/csv",
    )

    return result
