"""
krockOPVM - Page Streamlit : Données Macro (Couche 1)
=====================================================
Intégration dans streamlit_app.py :

    from pages.macro_data_page import render_macro_data_tab
    with tab_macro:
        render_macro_data_tab()
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))
from data_collector import (
    build_macro_dataset, get_bam_taux_directeur, get_courbe_taux_bdt,
    get_masi_madex, get_worldbank_macro, load_asfim_vl
)
from feature_builder import build_vl_features, get_feature_summary


def render_macro_data_tab():
    st.header("Données Macro-Économiques — Couche 1")
    st.caption("Agrégation des données BAM, BDT, Bourse de Casablanca, ASFIM et World Bank")

    # ── Contrôles ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Date de début", value=pd.to_datetime("2021-01-01"))
    with col2:
        refresh = st.button("Actualiser les données", use_container_width=True)
    with col3:
        asfim_file = st.file_uploader("Importer ASFIM (Excel/CSV)", type=["xlsx", "xls", "csv"])

    st.divider()

    # ── Chargement ──────────────────────────────────────────────────────────────
    with st.spinner("Chargement des données macro..."):
        cache_key = f"macro_{start_date}"
        if cache_key not in st.session_state or refresh:
            try:
                df_macro = build_macro_dataset(start_date=str(start_date))
                st.session_state[cache_key] = df_macro
            except Exception as e:
                st.error(f"Erreur lors du chargement : {e}")
                return
        else:
            df_macro = st.session_state[cache_key]

    # ASFIM upload
    df_asfim = None
    if asfim_file:
        try:
            import tempfile, os
            suffix = Path(asfim_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(asfim_file.read())
                tmp_path = tmp.name
            df_asfim = load_asfim_vl(tmp_path, original_filename=asfim_file.name)
            os.unlink(tmp_path)
            st.success(f"ASFIM chargé : {len(df_asfim):,} lignes, {df_asfim['fonds'].nunique()} fonds")
        except Exception as e:
            st.error(f"Erreur ASFIM : {e}")

    # ── KPIs Macro ──────────────────────────────────────────────────────────────
    st.subheader("Indicateurs Clés")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    last = df_macro.iloc[-1] if not df_macro.empty else {}

    with kpi1:
        val = last.get("taux_directeur_bam", "N/A")
        st.metric("Taux Directeur BAM", f"{val:.2f}%" if isinstance(val, float) else val)

    with kpi2:
        val = last.get("reserves_change_mrd_mad", "N/A")
        st.metric("Réserves Change", f"{val:.1f} Mrd MAD" if isinstance(val, float) else val)

    with kpi3:
        val = last.get("spread_10y_3m", "N/A")
        forme = last.get("courbe_forme", "")
        st.metric("Spread 10Y-3M", f"{val:.2f}%" if isinstance(val, float) else val, delta=forme)

    with kpi4:
        val = last.get("masi", "N/A")
        ret = last.get("masi_ret", 0)
        st.metric("MASI", f"{val:,.0f}" if isinstance(val, float) else val,
                  delta=f"{ret*100:.2f}%" if isinstance(ret, float) else None)

    with kpi5:
        val = last.get("inflation_cpi", "N/A")
        st.metric("Inflation (IPC)", f"{val:.1f}%" if isinstance(val, float) else val)

    st.divider()

    # ── Onglets par source ──────────────────────────────────────────────────────
    tab_bam, tab_bdt, tab_bourse, tab_wb, tab_asfim, tab_features = st.tabs([
        "BAM", "Courbe BDT", "Bourse", "World Bank", "ASFIM", "Features"
    ])

    # ── Tab BAM ────────────────────────────────────────────────────────────────
    with tab_bam:
        st.subheader("Taux Directeur & Réserves de Change")
        if "taux_directeur_bam" in df_macro.columns:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                subplot_titles=["Taux Directeur BAM (%)", "Réserves de Change (Mrd MAD)"],
                                vertical_spacing=0.1)
            fig.add_trace(go.Scatter(x=df_macro.index, y=df_macro["taux_directeur_bam"],
                                     name="Taux directeur", line=dict(color="#E24B4A", width=2),
                                     mode="lines+markers", marker=dict(size=3)), row=1, col=1)
            if "reserves_change_mrd_mad" in df_macro.columns:
                fig.add_trace(go.Scatter(x=df_macro.index, y=df_macro["reserves_change_mrd_mad"],
                                         name="Réserves change", line=dict(color="#1D9E75", width=2),
                                         fill="tozeroy", fillcolor="rgba(29,158,117,0.1)"), row=2, col=1)
            fig.update_layout(height=450, showlegend=False, margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # ── Tab BDT ────────────────────────────────────────────────────────────────
    with tab_bdt:
        st.subheader("Courbe des Taux BDT (Bons du Trésor)")
        bdt_cols = [c for c in df_macro.columns if c.startswith("bdt_") and "y" in c or c.endswith("m")]

        if bdt_cols:
            latest_bdt = df_macro[bdt_cols].dropna().iloc[-1]
            maturities = [c.replace("bdt_", "").replace("m", "M").replace("y", "Y") for c in bdt_cols]

            fig_yield = go.Figure()
            fig_yield.add_trace(go.Scatter(
                x=maturities, y=latest_bdt.values,
                mode="lines+markers", line=dict(color="#378ADD", width=2),
                marker=dict(size=8, color="#378ADD"), name="BDT actuel"
            ))
            fig_yield.update_layout(
                title="Courbe des Taux BDT (dernière observation)",
                yaxis_title="Rendement (%)", xaxis_title="Maturité",
                height=350
            )
            st.plotly_chart(fig_yield, use_container_width=True)

            # Spread historique
            if "spread_10y_3m" in df_macro.columns:
                fig_spread = px.area(
                    df_macro.reset_index(), x="date", y="spread_10y_3m",
                    title="Spread 10Y-3M (Signal de forme de courbe)",
                    color_discrete_sequence=["#534AB7"]
                )
                fig_spread.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Inversion")
                st.plotly_chart(fig_spread, use_container_width=True)
        else:
            st.info("Données BDT non disponibles dans le dataset courant.")

    # ── Tab Bourse ─────────────────────────────────────────────────────────────
    with tab_bourse:
        st.subheader("Bourse de Casablanca — MASI / MADEX")
        bourse_cols = [c for c in df_macro.columns if c in ["masi", "madex"]]

        if bourse_cols:
            fig = go.Figure()
            colors = {"masi": "#378ADD", "madex": "#E24B4A"}
            for col in bourse_cols:
                fig.add_trace(go.Scatter(
                    x=df_macro.index, y=df_macro[col],
                    name=col.upper(), line=dict(color=colors.get(col, "#888"), width=1.5)
                ))
            fig.update_layout(title="Indices MASI / MADEX", yaxis_title="Points", height=380)
            st.plotly_chart(fig, use_container_width=True)

            # Volatilité
            vol_cols = [c for c in df_macro.columns if "_vol_20j" in c]
            if vol_cols:
                fig_vol = px.line(df_macro.reset_index(), x="date", y=vol_cols,
                                  title="Volatilité réalisée 20 jours (annualisée)",
                                  labels={"value": "Volatilité (%)", "variable": "Indice"})
                st.plotly_chart(fig_vol, use_container_width=True)
        else:
            st.info("Données Bourse non disponibles. Vérifiez la connexion internet.")

    # ── Tab World Bank ─────────────────────────────────────────────────────────
    with tab_wb:
        st.subheader("Indicateurs World Bank — Maroc")
        wb_cols = [c for c in df_macro.columns
                   if c in ["inflation_cpi", "taux_change_mad_usd", "m3_pct_pib", "croissance_pib"]]

        if wb_cols:
            for col in wb_cols:
                col_data = df_macro[[col]].dropna()
                if not col_data.empty:
                    label_map = {
                        "inflation_cpi": "Inflation IPC (%)",
                        "taux_change_mad_usd": "Taux de change MAD/USD",
                        "m3_pct_pib": "M3 (% du PIB)",
                        "croissance_pib": "Croissance PIB réel (%)"
                    }
                    fig = px.line(col_data.reset_index(), x="date", y=col,
                                  title=label_map.get(col, col),
                                  color_discrete_sequence=["#BA7517"])
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Données World Bank non disponibles.")

    # ── Tab ASFIM ──────────────────────────────────────────────────────────────
    with tab_asfim:
        st.subheader("Données ASFIM — Valeurs Liquidatives")
        if df_asfim is not None and not df_asfim.empty:
            col_left, col_right = st.columns([1, 2])
            with col_left:
                fonds_list = sorted(df_asfim["fonds"].unique())
                selected_fonds = st.selectbox("Sélectionner un fonds", fonds_list)

            df_fonds = df_asfim[df_asfim["fonds"] == selected_fonds].sort_values("date")

            with col_right:
                st.metric("Observations", f"{len(df_fonds):,}")
                if "vl" in df_fonds.columns:
                    vl_last = df_fonds["vl"].iloc[-1]
                    vl_prev = df_fonds["vl"].iloc[-2] if len(df_fonds) > 1 else vl_last
                    st.metric("Dernière VL", f"{vl_last:,.4f}", delta=f"{(vl_last/vl_prev-1)*100:.3f}%")

            if "vl" in df_fonds.columns:
                fig_vl = px.line(df_fonds, x="date", y="vl",
                                 title=f"VL — {selected_fonds}",
                                 color_discrete_sequence=["#378ADD"])
                st.plotly_chart(fig_vl, use_container_width=True)

            if "souscriptions" in df_asfim.columns:
                st.subheader("Flux souscriptions / rachats")
                fig_flux = go.Figure()
                fig_flux.add_bar(x=df_fonds["date"], y=df_fonds.get("souscriptions", []),
                                 name="Souscriptions", marker_color="#1D9E75")
                fig_flux.add_bar(x=df_fonds["date"], y=-df_fonds.get("rachats", pd.Series()),
                                 name="Rachats", marker_color="#E24B4A")
                fig_flux.update_layout(barmode="relative", title="Flux nets")
                st.plotly_chart(fig_flux, use_container_width=True)
        else:
            st.info("Importez un fichier ASFIM (Excel ou CSV) via le bouton en haut de page.")

    # ── Tab Features ───────────────────────────────────────────────────────────
    with tab_features:
        st.subheader("Feature Engineering — Aperçu")
        st.caption("Prévisualisation des features calculées sur un fonds exemple")

        if df_asfim is not None and not df_asfim.empty:
            fonds_list = sorted(df_asfim["fonds"].unique())
            sel = st.selectbox("Fonds pour feature engineering", fonds_list, key="feat_fonds")
            df_vl_sample = df_asfim[df_asfim["fonds"] == sel][["date", "vl"]].copy()

            with st.spinner("Calcul des features..."):
                df_feat = build_vl_features(df_vl_sample, df_macro)

            st.success(f"{len(df_feat.columns)} features calculées sur {len(df_feat):,} observations")

            summary = get_feature_summary(df_feat)
            st.dataframe(summary, use_container_width=True, height=400)

            if st.button("📥 Télécharger les features (CSV)"):
                csv = df_feat.to_csv()
                st.download_button("Confirmer le téléchargement", csv,
                                   file_name=f"features_{sel}.csv", mime="text/csv")
        else:
            st.info("Importez un fichier ASFIM pour générer les features enrichies.")

    # ── Export Global ───────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📥 Export Dataset Macro Complet")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        csv_data = df_macro.to_csv()
        st.download_button(
            label="Télécharger macro_dataset.csv",
            data=csv_data,
            file_name="macro_dataset.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_exp2:
        st.info(f"Dataset : **{df_macro.shape[0]:,}** lignes × **{df_macro.shape[1]}** colonnes")
