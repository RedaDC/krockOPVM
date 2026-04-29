"""
OPCVM Analytics Maroc - Streamlit Dashboard
Interactive dashboard for Moroccan investment fund analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import plotly.express as px
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.macro_prediction import MacroPredictor
from src.advanced_predictor import AdvancedPredictor
try:
    from pages.macro_data_page import render_macro_data_tab
except ImportError as e:
    st.error(f"Impossible de charger la page macro : {e}")
    render_macro_data_tab = None

from src.news_sentiment_pipeline import NewsSentimentPipeline
from src.streamlit_signal_tab import render_signal_tab
from src.feature_builder import build_vl_features

# Page configuration
st.set_page_config(
    page_title="OPCVM Analytics Maroc",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)


def load_mock_data():
    """Generate mock data for demonstration"""
    np.random.seed(42)
    
    # Fund names
    funds = [
        "BMCE Capital Actions", "CDG Capital Actions", "Wafa Gestion Actions",
        "BMCE Capital Obligataire", "CDG Capital Obligataire", "Wafa Gestion Obligataire",
        "BMCE Capital Monetaire", "CDG Capital Monetaire", "Wafa Gestion Monetaire",
        "BMCE Capital Diversifie", "CDG Capital Diversifie", "Wafa Gestion Diversifie",
        "Attijari Intissar Actions", "Attijari Intissar Obligataire",
        "CFG Bank Actions", "CFG Bank Obligataire"
    ]
    
    classifications = []
    for fund in funds:
        if "Actions" in fund:
            classifications.append("Actions")
        elif "Obligataire" in fund:
            classifications.append("Obligataire")
        elif "Monetaire" in fund:
            classifications.append("Monetaire")
        else:
            classifications.append("Diversifie")
    
    # Generate data
    data = []
    base_date = datetime.now() - timedelta(days=365*3)
    
    for i, (fund, classification) in enumerate(zip(funds, classifications)):
        for day in range(365*3):
            date = base_date + timedelta(days=day)
            
            # Skip weekends
            if date.weekday() >= 5:
                continue
            
            # Generate realistic VL
            base_vl = 1000 + (i * 50)
            vl = base_vl + np.random.normal(0, 5) + (day * 0.1)
            vl_prev = vl - np.random.normal(0, 2)
            variation = ((vl - vl_prev) / vl_prev) * 100
            
            # AUM and flows
            aum = np.random.uniform(100, 5000)
            flux_souscription = np.random.uniform(0, 50)
            flux_rachat = np.random.uniform(0, 40)
            flux_net = flux_souscription - flux_rachat
            
            # Sentiment (mock)
            sentiment = np.random.uniform(-1, 1)
            nb_actus = np.random.randint(0, 20)
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'nom_fonds': fund,
                'classification': classification,
                'vl_jour': round(vl, 2),
                'vl_precedente': round(vl_prev, 2),
                'variation_pct': round(variation, 3),
                'aum': round(aum, 2),
                'flux_souscription': round(flux_souscription, 2),
                'flux_rachat': round(flux_rachat, 2),
                'flux_net': round(flux_net, 2),
                'score_sentiment': round(sentiment, 3),
                'nb_actus_jour': nb_actus
            })
    
    return pd.DataFrame(data)


def generate_signals(df):
    """Generate trading signals calibrated by fund category to avoid false signals."""
    signals = []
    
    for fund in df['nom_fonds'].unique():
        df_fund = df[df['nom_fonds'] == fund].sort_values('date')
        
        if len(df_fund) < 30:
            continue
        
        # Latest data
        latest = df_fund.iloc[-1]
        prev = df_fund.iloc[-2]
        classification = str(latest['classification']).lower()
        
        # Calibration par catégorie (Couche 3)
        if "monet" in classification or "oblig" in classification:
            # Moins liquide : fenêtres plus longues et seuils plus stricts
            w_short, w_long = 15, 60
            threshold = 1.002  # 0.2% d'écart minimum pour l'obligataire (sensibilité plus fine)
        else:
            # Actions : fenêtres standard
            w_short, w_long = 10, 30
            threshold = 1.01   # 1% d'écart minimum pour les actions
        
        # Calculate moving averages
        sma_s = df_fund['vl_jour'].tail(w_short).mean()
        sma_l = df_fund['vl_jour'].tail(w_long).mean()
        
        # Signal logic
        if sma_s > sma_l * threshold:
            signal = "ACHETER"
            confidence = "FORTE" if sma_s > sma_l * (threshold + 0.005) else "MODEREE"
        elif sma_s < sma_l * (2 - threshold):
            signal = "VENDRE"
            confidence = "FORTE" if sma_s < sma_l * (2 - threshold - 0.005) else "MODEREE"
        else:
            signal = "ATTENDRE"
            confidence = "FAIBLE"
        
        # Predict next VL (simple momentum)
        momentum = latest['vl_jour'] - prev['vl_jour']
        vl_predite = latest['vl_jour'] + momentum
        
        signals.append({
            'nom_fonds': fund,
            'classification': latest['classification'],
            'vl_actuelle': latest['vl_jour'],
            'vl_predite': round(vl_predite, 2),
            'variation_pct': round(((vl_predite - latest['vl_jour']) / latest['vl_jour']) * 100, 2),
            'signal': signal,
            'confiance': confidence,
            'sentiment': latest['score_sentiment'],
            'aum': latest['aum']
        })
    
    return pd.DataFrame(signals)


def main():
    # Header
    st.markdown('<h1 class="main-header">OPCVM Analytics Maroc</h1>', unsafe_allow_html=True)
    st.markdown("Systeme d'analyse quantitative des fonds d'investissement marocains")
    st.markdown("---")
    
    # Load data
    @st.cache_data
    def get_data(v="1.9"):
        df = load_mock_data()
        # Initialiser le pipeline de sentiment (CamemBERT / BERT)
        sentiment_pipeline = NewsSentimentPipeline()
        # Collecter les VRAIES news depuis les flux RSS
        df_news = sentiment_pipeline.collect_news_rss()
        
        # Analyser le sentiment des news (CamemBERT / BERT)
        if not df_news.empty:
            df_news = sentiment_pipeline.analyze_sentiment(df_news)
        else:
            # Fallback mock si vraiment rien trouvé (ex: erreur réseau)
            df_news = sentiment_pipeline.generate_mock_news(n_articles=10)
            
        df_agg = sentiment_pipeline.aggregate_by_classification(df_news, df)
        df = sentiment_pipeline.merge_with_opcvm(df, df_agg)
        return df, df_news
    
    df, df_news = get_data(v="1.9")
    
    # Sidebar
    st.sidebar.header("Filtres")
    
    if st.sidebar.button("Vider le cache & Actualiser"):
        st.cache_data.clear()
        st.rerun()
    
    # Classification filter
    classifications = st.sidebar.multiselect(
        "Classification",
        options=df['classification'].unique(),
        default=df['classification'].unique()
    )
    
    # Filter data
    df_filtered = df[df['classification'].isin(classifications)]
    
    # Fund selector
    selected_fund = st.sidebar.selectbox(
        "Selectionner un fonds",
        options=sorted(df_filtered['nom_fonds'].unique())
    )
    
    # Date range
    if df_filtered.empty:
        min_date = datetime.now() - timedelta(days=30)
        max_date = datetime.now()
    else:
        min_date = pd.to_datetime(df_filtered['date']).min()
        max_date = pd.to_datetime(df_filtered['date']).max()
        
    if pd.isna(min_date) or pd.isna(max_date):
        min_date = datetime.now() - timedelta(days=30)
        max_date = datetime.now()
        
    # Convert pandas Timestamp to standard datetime.date to avoid Streamlit errors
    if hasattr(min_date, 'to_pydatetime'):
        min_date = min_date.to_pydatetime().date()
    elif hasattr(min_date, 'date'):
        min_date = min_date.date()
        
    if hasattr(max_date, 'to_pydatetime'):
        max_date = max_date.to_pydatetime().date()
    elif hasattr(max_date, 'date'):
        max_date = max_date.date()
    
    start_date = st.sidebar.date_input("Date debut", min_date)
    end_date = st.sidebar.date_input("Date fin", max_date)
    
    # Apply filters
    df_filtered = df_filtered[
        (pd.to_datetime(df_filtered['date']) >= pd.to_datetime(start_date)) &
        (pd.to_datetime(df_filtered['date']) <= pd.to_datetime(end_date))
    ]
    
    # Main metrics
    st.subheader("Indicateurs Cles")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_aum = df_filtered['aum'].sum()
    avg_variation = df_filtered['variation_pct'].mean()
    total_funds = df_filtered['nom_fonds'].nunique()
    # Utiliser le score de sentiment enrichi (Couche 5)
    avg_sentiment = df_filtered['score_sentiment_moyen_jour'].mean()
    
    col1.metric("AUM Total (Md MAD)", f"{total_aum/1000:.2f}")
    col2.metric("Nombre de Fonds", total_funds)
    col3.metric("Variation Moyenne (%)", f"{avg_variation:.2f}%")
    col4.metric("Sentiment IA (CamemBERT)", f"{avg_sentiment:.2f}")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Signaux de Trading", "Analyse Technique", "Prévisions IA", "Actualités & Sentiment", "Données Brutes", "Analyse Macro", "Signal IA Avancé"])
    
    with tab1:
        st.subheader("Signaux de Trading du Jour")
        
        signals = generate_signals(df_filtered)
        
        if len(signals) > 0:
            # Filter by signal type
            signal_filter = st.radio(
                "Filtrer par signal",
                ["Tous", "ACHETER", "VENDRE", "ATTENDRE"],
                horizontal=True
            )
            
            if signal_filter != "Tous":
                signals_filtered = signals[signals['signal'] == signal_filter]
            else:
                signals_filtered = signals
            
            # Display signals
            col1, col2, col3 = st.columns(3)
            
            buy_count = len(signals[signals['signal'] == 'ACHETER'])
            sell_count = len(signals[signals['signal'] == 'VENDRE'])
            wait_count = len(signals[signals['signal'] == 'ATTENDRE'])
            
            col1.metric("ACHETER", buy_count)
            col2.metric("VENDRE", sell_count)
            col3.metric("ATTENDRE", wait_count)
            
            # Signals table
            st.markdown("### Liste des Signaux")
            
            # Format for display
            display_df = signals_filtered.copy()
            display_df['sentiment_label'] = display_df['sentiment'].apply(
                lambda x: 'Positif' if x > 0.2 else ('Negatif' if x < -0.2 else 'Neutre')
            )
            
            display_df = display_df[[
                'nom_fonds', 'classification', 'vl_actuelle', 'vl_predite',
                'variation_pct', 'signal', 'confiance', 'sentiment_label'
            ]].rename(columns={
                'nom_fonds': 'Fonds',
                'classification': 'Classification',
                'vl_actuelle': 'VL Actuelle',
                'vl_predite': 'VL Predite',
                'variation_pct': 'Variation (%)',
                'signal': 'Signal',
                'confiance': 'Confiance',
                'sentiment_label': 'Sentiment'
            })
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Aucun signal disponible pour les filtres selectionnes.")
    
    with tab2:
        st.subheader("Analyse Technique")
        
        if selected_fund:
            # Get fund data
            df_fund = df_filtered[df_filtered['nom_fonds'] == selected_fund].sort_values('date')
            
            if len(df_fund) > 0:
                # Use Plotly for interactive charts
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                
                # Create figure
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.7, 0.3],
                    subplot_titles=(f'Evolution VL - {selected_fund}', 'Variation Journaliere (%)')
                )
                
                # Add VL trace
                fig.add_trace(
                    go.Scatter(x=df_fund['date'], y=df_fund['vl_jour'], 
                              name='VL', line=dict(color='#1f77b4', width=2)),
                    row=1, col=1
                )
                
                # Add moving averages
                df_fund['SMA_10'] = df_fund['vl_jour'].rolling(window=10).mean()
                df_fund['SMA_30'] = df_fund['vl_jour'].rolling(window=30).mean()
                
                fig.add_trace(
                    go.Scatter(x=df_fund['date'], y=df_fund['SMA_10'], 
                              name='SMA 10j', line=dict(color='#ff7f0e', width=1.5)),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=df_fund['date'], y=df_fund['SMA_30'], 
                              name='SMA 30j', line=dict(color='#2ca02c', width=1.5)),
                    row=1, col=1
                )
                
                # Add variation trace
                fig.add_trace(
                    go.Bar(x=df_fund['date'], y=df_fund['variation_pct'],
                          name='Variation',
                          marker_color=df_fund['variation_pct'].apply(
                              lambda x: '#2ecc71' if x > 0 else '#e74c3c')),
                    row=2, col=1
                )
                
                fig.update_layout(height=700, showlegend=True, hovermode='x unified')
                fig.update_xaxes(rangeslider_visible=False)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Fund stats
                col1, col2, col3 = st.columns(3)
                
                current_vl = df_fund['vl_jour'].iloc[-1]
                min_vl = df_fund['vl_jour'].min()
                max_vl = df_fund['vl_jour'].max()
                avg_vl = df_fund['vl_jour'].mean()
                volatility = df_fund['variation_pct'].std()
                
                col1.metric("VL Actuelle", f"{current_vl:.2f} MAD")
                col2.metric("VL Min/Max", f"{min_vl:.2f} / {max_vl:.2f}")
                col3.metric("Volatilite (%)", f"{volatility:.2f}%")
    
    with tab3:
        st.subheader("Prédictions Macro-Économiques")
        st.markdown("Uploadez l'historique ASFIM et saisissez les données macro pour obtenir une projection des VL.")
        
        uploaded_file = st.file_uploader("Fichier Historique (CSV/Excel)", type=["csv", "xlsx"])
        
        # Traitement du fichier avant l'affichage des colonnes pour récupérer la liste des fonds
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_asfim = pd.read_csv(uploaded_file)
                else:
                    df_asfim = pd.read_excel(uploaded_file)
                    if len(df_asfim.columns) > 0 and 'Tableau des performances' in str(df_asfim.columns[0]):
                        df_asfim = pd.read_excel(uploaded_file, header=1)
                        
                col_mapping = {'OPCVM': 'nom_fonds', 'Classification': 'classification', 'VL': 'vl_jour'}
                rename_dict = {}
                for col in df_asfim.columns:
                    for k, v in col_mapping.items():
                        if str(k).lower() == str(col).lower().strip():
                            rename_dict[col] = v
                if rename_dict:
                    df_asfim = df_asfim.rename(columns=rename_dict)
                    
                uploaded_cols_lower = [str(col).lower() for col in df_asfim.columns]
                
                if 'date' not in uploaded_cols_lower:
                    import re
                    date_match = re.search(r'(\d{1,2})[ _-]([a-zA-Z]+|\d{1,2})[ _-](\d{4})', uploaded_file.name)
                    if date_match:
                        try:
                            day, month_str, year = date_match.groups()
                            months_fr = {'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03', 'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08', 'aout': '08', 'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12', 'decembre': '12'}
                            month = months_fr.get(month_str.lower(), month_str) if not month_str.isdigit() else month_str
                            df_asfim['date'] = pd.to_datetime(f"{year}-{month}-{day}")
                        except:
                            df_asfim['date'] = pd.Timestamp.now().normalize()
                    else:
                        df_asfim['date'] = pd.Timestamp.now().normalize()
                        
                df_asfim.columns = [str(col).lower() for col in df_asfim.columns]
                req_cols = ['date', 'nom_fonds', 'classification', 'vl_jour']
                missing = [c for c in req_cols if c not in df_asfim.columns]
                
                if missing:
                    st.warning(f"Le fichier uploadé ne contient pas les colonnes requises ({', '.join(missing)}). Utilisation des données par défaut.")
                    df_to_predict = df_filtered.copy()
                else:
                    df_to_predict = df_asfim.copy()
            except Exception as e:
                st.error(f"Erreur de lecture: {e}")
                df_to_predict = df_filtered.copy()
        else:
            df_to_predict = df_filtered.copy()
        
        col_m1, col_m2 = st.columns([1, 2])
        
        with col_m1:
            st.markdown("### 1. Sélection des Produits")
            macro_categories = ["Tous"] + list(df_to_predict['classification'].dropna().unique())
            selected_cat = st.selectbox("Catégorie de produits", options=macro_categories)
            
            if selected_cat == "Tous":
                macro_funds = sorted(df_to_predict['nom_fonds'].dropna().unique())
            else:
                macro_funds = sorted(df_to_predict[df_to_predict['classification'] == selected_cat]['nom_fonds'].dropna().unique())
                
            default_idx = macro_funds.index(selected_fund) if selected_fund in macro_funds else 0
            selected_fund_macro = st.selectbox("Fonds focus (pour graphique)", options=macro_funds, index=default_idx if macro_funds else 0)
            
            predict_all = st.checkbox("Prédire pour toute la catégorie", value=False)
            
            st.markdown("### 2. Paramètres Macro")
            taux_bam = st.number_input("Taux Directeur BAM (%)", value=2.75, step=0.25)
            courbe_taux = st.selectbox("Évolution de la Courbe des Taux", ["Hausse (Ascendante)", "Stable", "Baisse"])
            
            st.markdown("### 3. Anticipations Partenaires")
            anticipations_text = st.text_area("Texte des anticipations (Court/Moyen/Long terme)", 
                                              value="La courbe conserve une allure ascendante, mais sa pente s'accentue sous l'effet d'une hausse généralisée des taux. Court Terme (2,54%) : La liquidité se tend. L'écart avec le taux directeur grimpe à +29 pbs, signalant que le marché anticipe un maintien de la politique restrictive de BAM. Moyen Terme (3,33%) : Le segment 5 ans reste le foyer de volatilité majeur (+18 pbs). Long Terme (4,35%) : Fin de l'aplatissement. Le 30 ans décroche brutalement...",
                                              height=250)
            
            predict_btn = st.button("Lancer la Prédiction", type="primary")
            
        with col_m2:
            if uploaded_file is None:
                st.info("Aucun fichier uploadé. Utilisation des données du tableau de bord par défaut.")
                
            if predict_btn:
                funds_to_process = macro_funds if predict_all else [selected_fund_macro]
                all_results = []
                
                with st.spinner(f"Analyse IA de {len(funds_to_process)} produit(s)..."):
                    adv_predictor = AdvancedPredictor(df_macro=st.session_state.get("macro_dataset"))
                    progress_bar = st.progress(0)
                    
                    for i, fund_name in enumerate(funds_to_process):
                        df_fund_hist = df_to_predict[df_to_predict['nom_fonds'] == fund_name].copy()
                        metrics, error = adv_predictor.train_and_evaluate(df_fund_hist)
                        
                        if not error:
                            df_pred_v2 = adv_predictor.predict_future(df_fund_hist)
                            last_vl = df_fund_hist['vl_jour'].iloc[-1]
                            pred_vl = df_pred_v2['vl_jour'].iloc[-1]
                            perf_30j = (pred_vl / last_vl - 1) * 100
                            
                            all_results.append({
                                "Produit": fund_name,
                                "VL Actuelle": last_vl,
                                "VL Cible (30j)": pred_vl,
                                "Performance Attendue (%)": round(perf_30j, 2),
                                "Fiabilité (Accuracy)": f"{metrics['dir_accuracy']*100:.1f}%",
                                "Score Sentiment": df_fund_hist['score_sentiment_moyen_jour'].iloc[-1] if 'score_sentiment_moyen_jour' in df_fund_hist.columns else 0
                            })
                        
                        progress_bar.progress((i + 1) / len(funds_to_process))
                
                if all_results:
                    st.markdown("### Tableau de Performance Prévisionnelle (IA)")
                    df_res = pd.DataFrame(all_results).sort_values("Performance Attendue (%)", ascending=False)
                    
                    # Highlight top performance
                    st.dataframe(df_res.style.background_gradient(subset=["Performance Attendue (%)"], cmap="RdYlGn"), use_container_width=True)
                    
                    # Focus on specific fund chart
                    if selected_fund_macro:
                        st.markdown(f"---")
                        st.markdown(f"### Focus Détail : {selected_fund_macro}")
                        df_fund_hist = df_to_predict[df_to_predict['nom_fonds'] == selected_fund_macro].copy()
                        
                        # Try to train and predict with fallback
                        try:
                            metrics, error = adv_predictor.train_and_evaluate(df_fund_hist)
                            
                            if error:
                                st.warning(f"⚠️ Entraînement ML impossible: {error}")
                                st.info("💡 Utilisation de la méthode de fallback (tendance recente)")
                            
                            df_pred_v2 = adv_predictor.predict_future(df_fund_hist)
                            
                            if df_pred_v2.empty:
                                st.error("❌ Impossible de générer des prédictions. Vérifiez que le fonds a suffisamment de données historiques (minimum 40 jours).")
                            else:
                                df_fund_hist['type'] = 'Historique'
                                df_plot = pd.concat([df_fund_hist, df_pred_v2]).sort_values('date')
                                
                                fig = px.line(df_plot, x='date', y='vl_jour', color='type',
                                              title=f"Trajectoire IA détaillée - {selected_fund_macro}",
                                              color_discrete_map={"Historique": "blue", "Prediction V2": "green", "Prediction (Fallback)": "orange"},
                                              line_dash='type')
                                fig.update_layout(height=450, hovermode='x unified')
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Show prediction type
                                pred_type = df_pred_v2['type'].iloc[0] if not df_pred_v2.empty else 'Unknown'
                                if 'Fallback' in str(pred_type):
                                    st.info("📊 Note: Prédictions générées par analyse de tendance (fallback) car le modèle ML n'a pas pu être entraîné.")
                        except Exception as e:
                            st.error(f"❌ Erreur lors de la prédiction: {str(e)}")
                            st.info("💡 Conseil: Vérifiez que le fonds sélectionné a au moins 40 jours de données historiques.")
                else:
                    st.error("❌ Aucune prédiction n'a pu être générée.")
                    st.warning("**Causes possibles:**")
                    st.write("• Historique de données insuffisant (< 40 jours)")
                    st.write("• Données de prix manquantes ou invalides")
                    st.write("• Aucun fonds sélectionné")
                    st.info("**Solution:** Importez le fichier ASFIM le plus récent ou vérifiez la qualité des données.")

    with tab4:
        st.subheader("Analyse de Sentiment IA (Couche 5)")
        
        if not df_news.empty:
            # Stats de sentiment
            s1, s2, s3, s4 = st.columns(4)
            pos_news = len(df_news[df_news['score_sentiment'] > 0])
            neg_news = len(df_news[df_news['score_sentiment'] < 0])
            avg_s = df_news['score_sentiment'].mean()
            
            s1.metric("Articles Analysés", len(df_news))
            s2.metric("Sentiment Moyen", f"{avg_s:.2f}")
            s3.metric("Articles Haussiers", f"{pos_news}")
            s4.metric("Articles Baissiers", f"{neg_news}")

            # IA Synthesis Report
            st.markdown("### Rapport de Synthèse IA Complet")
            outlook = "FAVORABLE" if avg_s > 0.1 else "PRUDENT" if avg_s < -0.1 else "NEUTRE"
            bg_color = "#D4EDDA" if avg_s > 0.1 else "#F8D7DA" if avg_s < -0.1 else "#FFF3CD"
            text_color = "#155724" if avg_s > 0.1 else "#721C24" if avg_s < -0.1 else "#856404"
            
            st.markdown(f"""
            <div style="background-color:{bg_color}; padding:20px; border-radius:10px; border-left: 5px solid {text_color};">
                <h4 style="color:{text_color}; margin-top:0;">PERSPECTIVE DE MARCHÉ : {outlook}</h4>
                <p style="color:{text_color};">
                    L'analyse par <b>CamemBERT</b> des flux d'actualités financières marocaines (Médias24, L'Économiste, MAP) 
                    révèle une tendance de fond <b>{outlook.lower()}</b>. <br><br>
                    <b>Impact par segment :</b><br>
                    - <b>Actions :</b> Sensibilité forte aux nouvelles de croissance PIB ({'Positive' if avg_s > 0 else 'Négative'}).<br>
                    - <b>Obligataire :</b> Réaction aux anticipations BAM (Taux à {taux_bam}%).<br>
                    - <b>Monétaire :</b> Impact limité par la volatilité actuelle.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Liste des articles
            st.markdown("---")
            st.markdown("### Détail des Actualités & Rapports par Article")
            for _, article in df_news.iterrows():
                sentiment_val = article['score_sentiment']
                color = "green" if sentiment_val > 0 else "red" if sentiment_val < 0 else "orange"
                
                with st.expander(f"{article['title']} (Sentiment: {sentiment_val:+.2f})"):
                    st.markdown(f"**Source :** {article['source']} | **Date :** {article['published']}")
                    st.markdown(f"**Rapport de Contenu :**")
                    st.write(article['summary'])
                    st.markdown(f"**Analyse IA (CamemBERT) :**")
                    if sentiment_val > 0.2:
                        st.success(f"Signal HAUSSIER détecté avec une confiance de {abs(sentiment_val)*100:.1f}%")
                    elif sentiment_val < -0.2:
                        st.error(f"Signal BAISSIER détecté avec une confiance de {abs(sentiment_val)*100:.1f}%")
                    else:
                        st.warning(f"Signal NEUTRE ou INCERTAIN")
                    
                    if article['link']:
                        st.markdown(f"[Lire l'article complet]({article['link']})")
        else:
            st.warning("Aucune actualité collectée pour le moment.")

    with tab5:
        st.subheader("Données Brutes")
        st.dataframe(df_filtered, use_container_width=True)
        # Download button
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="Télécharger en CSV",
            data=csv,
            file_name=f"opcvm_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    with tab6:
        if render_macro_data_tab is not None:
            render_macro_data_tab()
        else:
            st.warning("Le module des données macro avancées n'est pas disponible.")
    
    with tab7:
        st.subheader("Moteur de Signal IA (Random Forest + Momentum + Macro)")
        st.write("Sélectionnez le **Fonds** dans la barre latérale pour analyser son signal détaillé.")
        
        # Prepare data for the selected fund
        df_fund_hist = df_filtered[df_filtered['nom_fonds'] == selected_fund].copy()
        
        # Le FeatureBuilder attend une colonne 'vl'
        if 'vl_jour' in df_fund_hist.columns and 'vl' not in df_fund_hist.columns:
            df_fund_hist = df_fund_hist.rename(columns={'vl_jour': 'vl'})
            
        if len(df_fund_hist) < 60:
            st.warning("Historique insuffisant pour ce fonds (besoin d'au moins 60 jours pour le calcul des indicateurs techniques).")
        else:
            # Get macro data from session state
            df_macro_data = st.session_state.get("macro_dataset")
            
            # Build features
            try:
                df_feat = build_vl_features(df_fund_hist, df_macro_data).dropna()
                
                # Determine asset class from classification
                fund_class_raw = str(df_fund_hist['classification'].iloc[-1]).lower()
                if "action" in fund_class_raw:
                    asset_class = "actions"
                elif "oblig" in fund_class_raw:
                    asset_class = "obligataire"
                elif "monet" in fund_class_raw:
                    asset_class = "monetaire"
                else:
                    asset_class = "diversifie"
                
                # Render the signal tab
                if not df_feat.empty:
                    render_signal_tab(
                        df_features=df_feat, 
                        df_macro=df_macro_data, 
                        asset_class=asset_class, 
                        fund_name=selected_fund
                    )
                else:
                    st.warning("Pas assez de données après le calcul des moyennes mobiles longues (200j).")
            except Exception as e:
                st.error(f"Erreur lors du calcul des features : {e}")

    # Footer
    st.markdown("---")
    st.markdown(
        "**Disclaimer:** Ce dashboard est fourni a titre educatif. "
        "Les signaux ne constituent pas des conseils d'investissement. "
        "Consultez un conseiller financier agree par l'AMMC."
    )


if __name__ == "__main__":
    main()
