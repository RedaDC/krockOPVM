"""
Stable Prediction Display with Session State Management
========================================================
Fixes the issue where table and graph disappear on rerun.
Uses Streamlit session state to persist prediction results.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def initialize_prediction_state():
    """Initialize prediction session state variables"""
    if 'prediction_results' not in st.session_state:
        st.session_state.prediction_results = None
    if 'prediction_metadata' not in st.session_state:
        st.session_state.prediction_metadata = None
    if 'prediction_df' not in st.session_state:
        st.session_state.prediction_df = None

def display_stable_predictions():
    """
    Display predictions from session state (stable across reruns).
    Returns True if predictions exist, False otherwise.
    """
    initialize_prediction_state()
    
    if not st.session_state.prediction_results:
        return False
    
    all_results = st.session_state.prediction_results
    
    # Show metadata if available
    if st.session_state.prediction_metadata:
        meta = st.session_state.prediction_metadata
        st.info(
            f"Derniere prediction: {meta['timestamp']} | "
            f"{meta['funds_processed']} fonds | "
            f"BAM: {meta['macro_params']['taux_bam']}%"
        )
    
    # Create display dataframe (without AI_Analysis column)
    display_cols = [
        "Produit", "VL Actuelle", "VL Cible (30j)", 
        "Performance Attendue (%)", "Signal", "Conviction",
        "Fiabilite (Accuracy)", "Confiance IA", "Methode",
        "Data_Points"
    ]
    
    # Only include columns that exist
    available_cols = [col for col in display_cols if col in all_results[0].keys()]
    df_display = pd.DataFrame(all_results)[available_cols]
    df_display = df_display.sort_values("Performance Attendue (%)", ascending=False)
    
    # Display table
    st.markdown("### Tableau de Performance Previsionnelle (IA)")
    styled_df = df_display.style.background_gradient(
        subset=["Performance Attendue (%)"], 
        cmap="RdYlGn"
    )
    st.dataframe(styled_df, use_container_width=True)
    
    # Summary metrics
    ml_count = len(df_display[df_display['Methode'].str.contains('ML', na=False)])
    fallback_count = len(df_display[df_display['Methode'].str.contains('Fallback', na=False)])
    bullish_count = len(df_display[df_display['Signal'].str.contains('BULLISH', na=False)])
    bearish_count = len(df_display[df_display['Signal'].str.contains('BEARISH', na=False)])
    
    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
    col_s1.metric("Total Fonds", len(df_display))
    col_s2.metric("Predictions ML", ml_count)
    col_s3.metric("Fallback (Tendance)", fallback_count)
    col_s4.metric("Signaux Haussiers", bullish_count)
    col_s5.metric("Signaux Baissiers", bearish_count)
    
    if fallback_count > 0:
        st.info(
            "Les predictions Fallback utilisent l'analyse de tendance recente "
            "car l'historique est insuffisant pour le modele ML (< 40 jours)."
        )
    
    # Detailed AI Reasoning
    st.markdown("---")
    st.markdown("### Analyse Detaillee par Fonds (AI Reasoning)")
    st.markdown("Cliquez sur un fonds pour voir l'analyse professionnelle complete.")
    
    for result in all_results:
        ai_analysis = result.get('AI_Analysis')
        if ai_analysis:
            with st.expander(f"{result['Produit']} - {result['Signal']} ({result['Conviction']})"):
                # Professional report
                st.markdown(f"**Signal:** {result['Signal']}")
                st.markdown(f"**Conviction:** {result['Conviction']}")
                st.markdown(f"**Rendement Attendu (30j):** {result['Performance Attendue (%)']:+.2f}%")
                st.markdown(f"**Confiance IA:** {result.get('Confiance IA', 'N/A')}")
                st.markdown(f"**Points de donnees:** {result.get('Data_Points', 'N/A')} jours")
                st.markdown("")
                
                # Justification
                st.markdown("**Justification de la Prediction:**")
                st.write(result.get('Prediction_Justification', 'Non disponible'))
                st.markdown("")
                
                # Technical analysis
                st.markdown("**Analyse Technique:**")
                tech = ai_analysis['technical_analysis']
                col_t1, col_t2, col_t3 = st.columns(3)
                col_t1.metric("Tendance", tech['trend'])
                col_t2.metric("Momentum (10j)", f"{tech['momentum_10d']:+.2f}%")
                col_t3.metric("Volatilite", f"{tech['volatility_annual']:.2f}%")
                st.markdown("")
                
                # Macro analysis
                st.markdown("**Facteurs Macroeconomiques:**")
                macro = ai_analysis['macro_analysis']
                st.markdown(f"- **Taux BAM:** {macro['bam_rate']}%")
                st.markdown(f"- **Impact BAM:** {macro['bam_impact']}")
                st.markdown(f"- **Courbe des taux:** {macro['yield_curve_shape']}")
                st.markdown("")
                
                # Recommendation
                st.markdown("**Recommandation:**")
                rec = ai_analysis['recommendation']
                st.markdown(f"**Action:** {rec['action']}")
                st.markdown(f"**Justification:** {rec['rationale']}")
                st.markdown("")
                st.markdown("**Points de Surveillance:**")
                for point in rec['monitoring_points']:
                    st.markdown(f"- {point}")
    
    return True

def run_prediction_with_validation(
    funds_to_process,
    df_to_predict,
    adv_predictor,
    taux_bam,
    courbe_taux,
    progress_callback=None
):
    """
    Run predictions with full validation and store in session state.
    
    Args:
        funds_to_process: List of fund names to predict
        df_to_predict: DataFrame with historical data
        adv_predictor: AdvancedPredictor instance
        taux_bam: BAM rate input
        courbe_taux: Yield curve selection
        progress_callback: Optional callback for progress updates
    
    Returns:
        List of prediction results
    """
    from src.ai_reasoning_engine import get_ai_reasoning_engine
    import logging
    
    log = logging.getLogger("prediction_runner")
    
    all_results = []
    
    for i, fund_name in enumerate(funds_to_process):
        df_fund_hist = df_to_predict[df_to_predict['nom_fonds'] == fund_name].copy()
        
        # Validation 1: Minimum data points
        if len(df_fund_hist) < 5:
            st.warning(f"{fund_name}: Pas assez de donnees ({len(df_fund_hist)} jours, min 5 requis)")
            if progress_callback:
                progress_callback((i + 1) / len(funds_to_process))
            continue
        
        # Validation 2: No null VL values
        if df_fund_hist['vl_jour'].isnull().all():
            st.warning(f"{fund_name}: Donnees VL manquantes")
            if progress_callback:
                progress_callback((i + 1) / len(funds_to_process))
            continue
        
        # Validation 3: Valid numeric values
        try:
            vl_values = pd.to_numeric(df_fund_hist['vl_jour'], errors='coerce')
            valid_count = vl_values.notna().sum()
            if valid_count < 5:
                st.warning(f"{fund_name}: Seulement {valid_count} valeurs VL valides (min 5 requis)")
                if progress_callback:
                    progress_callback((i + 1) / len(funds_to_process))
                continue
        except Exception as e:
            st.warning(f"{fund_name}: Erreur de validation: {str(e)}")
            if progress_callback:
                progress_callback((i + 1) / len(funds_to_process))
            continue
        
        # Run prediction
        metrics, error = adv_predictor.train_and_evaluate(df_fund_hist)
        
        if error:
            st.info(f"{fund_name}: {error} -> Utilisation du mode fallback")
        
        df_pred_v2 = adv_predictor.predict_future(df_fund_hist)
        
        if df_pred_v2.empty:
            st.error(f"{fund_name}: Impossible de generer des predictions")
            if progress_callback:
                progress_callback((i + 1) / len(funds_to_process))
            continue
        
        # Extract prediction values
        last_vl = float(df_fund_hist['vl_jour'].iloc[-1])
        pred_vl = float(df_pred_v2['vl_jour'].iloc[-1])
        perf_30j = (pred_vl / last_vl - 1) * 100
        
        # Validation 4: Reasonable prediction
        if abs(perf_30j) > 50:  # More than 50% is suspicious
            st.warning(
                f"{fund_name}: Prediction non-realiste ({perf_30j:+.2f}%), "
                f"verification necessaire"
            )
            if progress_callback:
                progress_callback((i + 1) / len(funds_to_process))
            continue
        
        # Generate AI reasoning
        try:
            reasoning_engine = get_ai_reasoning_engine()
            macro_data = {
                'bam_rate': taux_bam,
                'yield_curve': 'normal' if 'Stable' in courbe_taux else ('steep' if 'Hausse' in courbe_taux else 'flat')
            }
            sentiment_score = df_fund_hist['score_sentiment_moyen_jour'].iloc[-1] if 'score_sentiment_moyen_jour' in df_fund_hist.columns else 0
            
            ai_analysis = reasoning_engine.analyze_prediction(
                df_fund_hist=df_fund_hist,
                prediction_value=pred_vl,
                current_vl=last_vl,
                prediction_type='fallback' if error else 'ml',
                macro_data=macro_data,
                sentiment_data={'score': sentiment_score, 'article_count': 0}
            )
        except Exception as e:
            log.warning(f"AI reasoning failed for {fund_name}: {e}")
            ai_analysis = None
        
        # Build result
        result = {
            "Produit": fund_name,
            "VL Actuelle": last_vl,
            "VL Cible (30j)": round(pred_vl, 2),
            "Performance Attendue (%)": round(perf_30j, 2),
            "Signal": ai_analysis['signal'] if ai_analysis else 'NEUTRAL',
            "Conviction": ai_analysis['conviction'] if ai_analysis else 'LOW',
            "Fiabilite (Accuracy)": f"{(metrics['dir_accuracy'] if metrics and not error else 0.5)*100:.1f}%",
            "Confiance IA": f"{ai_analysis['confidence_level']:.0f}%" if ai_analysis else 'N/A',
            "Score Sentiment": sentiment_score,
            "Methode": "ML Avance" if not error else "Fallback (Tendance)",
            "AI_Analysis": ai_analysis,
            "Data_Points": len(df_fund_hist),
            "Prediction_Justification": ai_analysis['reasoning'] if ai_analysis else "Analyse non disponible"
        }
        
        all_results.append(result)
        
        if progress_callback:
            progress_callback((i + 1) / len(funds_to_process))
    
    return all_results

def save_predictions_to_state(all_results, taux_bam, courbe_taux):
    """Save prediction results to session state for stability"""
    st.session_state.prediction_results = all_results
    st.session_state.prediction_metadata = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'funds_processed': len(all_results),
        'macro_params': {
            'taux_bam': taux_bam,
            'courbe_taux': courbe_taux
        }
    }
