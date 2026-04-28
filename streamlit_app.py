"""
OPCVM Analytics Maroc - Streamlit Dashboard
Interactive dashboard for Moroccan investment fund analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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
    base_date = datetime.now() - timedelta(days=365)
    
    for i, (fund, classification) in enumerate(zip(funds, classifications)):
        for day in range(365):
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
    """Generate trading signals based on simple moving average crossover"""
    signals = []
    
    for fund in df['nom_fonds'].unique():
        df_fund = df[df['nom_fonds'] == fund].sort_values('date')
        
        if len(df_fund) < 30:
            continue
        
        # Latest data
        latest = df_fund.iloc[-1]
        prev = df_fund.iloc[-2]
        
        # Calculate simple moving averages
        sma_10 = df_fund['vl_jour'].tail(10).mean()
        sma_30 = df_fund['vl_jour'].tail(30).mean()
        
        # Signal logic
        if sma_10 > sma_30 * 1.01:
            signal = "ACHETER"
            confidence = "FORTE" if sma_10 > sma_30 * 1.02 else "MODEREE"
        elif sma_10 < sma_30 * 0.99:
            signal = "VENDRE"
            confidence = "FORTE" if sma_10 < sma_30 * 0.98 else "MODEREE"
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
    def get_data():
        return load_mock_data()
    
    df = get_data()
    
    # Sidebar
    st.sidebar.header("Filtres")
    
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
    min_date = pd.to_datetime(df_filtered['date']).min()
    max_date = pd.to_datetime(df_filtered['date']).max()
    
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
    avg_sentiment = df_filtered['score_sentiment'].mean()
    
    col1.metric("AUM Total (Md MAD)", f"{total_aum/1000:.2f}")
    col2.metric("Nombre de Fonds", total_funds)
    col3.metric("Variation Moyenne (%)", f"{avg_variation:.2f}%")
    col4.metric("Sentiment Moyen", f"{avg_sentiment:.2f}")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["Signaux de Trading", "Analyse Technique", "Donnees Brutes"])
    
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
        st.subheader("Donnees Brutes")
        st.dataframe(df_filtered, use_container_width=True)
        
        # Download button
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="Telecharger en CSV",
            data=csv,
            file_name=f"opcvm_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**Disclaimer:** Ce dashboard est fourni a titre educatif. "
        "Les signaux ne constituent pas des conseils d'investissement. "
        "Consultez un conseiller financier agree par l'AMMC."
    )


if __name__ == "__main__":
    main()
