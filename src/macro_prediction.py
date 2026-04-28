import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats

class MacroPredictor:
    """
    Predicts OPCVM VLs based on historical data and macro-economic factors.
    """
    def __init__(self, df_macro=None):
        self.risk_keywords = ["incertitude", "volatilité", "décroche", "restrictive", "risque", "hausse"]
        self.positive_keywords = ["assouplissement", "baisse", "croissance", "stabilité", "favorable"]
        self.df_macro = df_macro
        self.SEED = 42

    def _analyze_sentiment(self, text):
        """Simple keyword-based sentiment analysis for macro text."""
        if not text or not isinstance(text, str):
            return 0.0
        
        text_lower = text.lower()
        risk_score = sum(text_lower.count(kw) for kw in self.risk_keywords)
        pos_score = sum(text_lower.count(kw) for kw in self.positive_keywords)
        
        # Returns a value between -1 and 1
        total = risk_score + pos_score
        if total == 0:
            return 0.0
        return (pos_score - risk_score) / max(total, 5) # Dampen effect if few words

    def _get_macro_modifier(self, classification, taux_bam, courbe_taux, sentiment_score):
        """
        Calculates a daily modifier percentage based on macro factors and fund class.
        """
        modifier = 0.0
        
        # Base modifier from Courbe des Taux (Yield curve)
        courbe_effet = 0.0
        if "hausse" in courbe_taux.lower() or "ascendante" in courbe_taux.lower():
            courbe_effet = -0.0005 # Negative for bonds/equity
        elif "baisse" in courbe_taux.lower():
            courbe_effet = 0.0005
            
        # Base modifier from BAM Rate (assuming normal is ~2.5 to 3.0)
        # BUG 2 FIX: Increased sensitivity
        bam_effet = (3.0 - float(taux_bam)) * 0.001
        
        # Apply logic by classification
        class_lower = str(classification).lower()
        if "oblig" in class_lower:
            modifier = (courbe_effet * 2) + bam_effet + (sentiment_score * 0.0002)
        elif "action" in class_lower:
            modifier = courbe_effet + (bam_effet * 1.5) + (sentiment_score * 0.0005)
        elif "monet" in class_lower:
            modifier = max(0, -bam_effet) * 0.1
        else:
            modifier = courbe_effet + bam_effet + (sentiment_score * 0.0003)
            
        return modifier

    def predict(self, df_history, taux_bam, courbe_taux, anticipations_text, days_ahead=30):
        """
        Generates predictions for the next `days_ahead`.
        """
        if df_history.empty:
            return pd.DataFrame()

        # BUG 1 FIX: Stable predictions with fixed seed
        np.random.seed(self.SEED)
            
        # Ensure dates are datetime
        if not pd.api.types.is_datetime64_any_dtype(df_history['date']):
            df_history['date'] = pd.to_datetime(df_history['date'], errors='coerce')
            
        df_history = df_history.dropna(subset=['date', 'vl_jour']).sort_values('date')
        
        # Analyze sentiment (Couche 5: Prioritize BERT scores from enriched data)
        if 'score_sentiment_moyen_jour' in df_history.columns:
            sentiment = df_history['score_sentiment_moyen_jour'].iloc[-1]
        else:
            sentiment = self._analyze_sentiment(anticipations_text)
        
        predictions = []
        
        for fonds in df_history['nom_fonds'].unique():
            df_fonds = df_history[df_history['nom_fonds'] == fonds].copy()
            if df_fonds.empty:
                continue
                
            classification = df_fonds['classification'].iloc[-1]
            last_date = df_fonds['date'].max()
            last_vl = df_fonds['vl_jour'].iloc[-1]
            
            # BUG 3 FIX: Theil-Sen regression for long-term trend
            if len(df_fonds) > 3:
                x = np.arange(len(df_fonds))
                y = df_fonds['vl_jour'].values
                # Robust linear regression
                res = stats.theilslopes(y, x, 0.90)
                slope = res[0]
                daily_momentum = slope / last_vl if last_vl > 0 else 0.0
            elif len(df_fonds) > 1:
                first_vl = df_fonds['vl_jour'].iloc[0]
                days_diff = (last_date - df_fonds['date'].iloc[0]).days
                daily_momentum = (last_vl - first_vl) / first_vl / max(days_diff, 1)
            else:
                daily_momentum = 0.0
                
            # Get macro modifier
            macro_modifier = self._get_macro_modifier(classification, taux_bam, courbe_taux, sentiment)
            
            # Capping macro modifier to 0.05% as per request
            macro_modifier = max(-0.0005, min(0.0005, macro_modifier))
            
            # Weighting: 80% trend, 20% macro modifier
            daily_drift = (daily_momentum * 0.8) + (macro_modifier * 0.2)
            
            # Generate future data
            current_vl = last_vl
            for i in range(1, days_ahead + 1):
                next_date = last_date + timedelta(days=i)
                if next_date.weekday() >= 5: # Skip weekends
                    continue
                    
                # Noise based on class
                volatility = 0.001
                if "action" in str(classification).lower():
                    volatility = 0.005
                elif "monet" in str(classification).lower():
                    volatility = 0.0001
                    
                noise = np.random.normal(0, volatility)
                current_vl = current_vl * (1 + daily_drift + noise)
                
                predictions.append({
                    'date': next_date,
                    'nom_fonds': fonds,
                    'classification': classification,
                    'vl_jour': round(current_vl, 2),
                    'type': 'Prédiction',
                    'momentum_base': daily_momentum,
                    'macro_modifier': macro_modifier
                })
                
            # Mark historical data
            df_fonds['type'] = 'Historique'
            df_fonds['momentum_base'] = np.nan
            df_fonds['macro_modifier'] = np.nan
            predictions.extend(df_fonds.to_dict('records'))
            
        result_df = pd.DataFrame(predictions)
        return result_df.sort_values(['nom_fonds', 'date']).reset_index(drop=True)

    def get_prediction_summary(self, df_result):
        """Generates a text summary of the prediction logic for the user."""
        if df_result.empty or 'type' not in df_result.columns:
            return "Pas assez de données pour générer un résumé."
            
        preds = df_result[df_result['type'] == 'Prédiction']
        if preds.empty:
            return "Aucune prédiction générée."
            
        fonds = preds['nom_fonds'].iloc[0]
        momentum = preds['momentum_base'].iloc[0]
        macro = preds['macro_modifier'].iloc[0]
        
        trend_str = "haussière" if momentum > 0 else "baissière"
        macro_str = "favorable" if macro > 0 else "défavorable"
        
        summary = f"**Analyse pour {fonds} :**\n\n"
        summary += f"- **Tendance de fond (Theil-Sen) :** {trend_str} ({momentum*100:.4f}% / jour)\n"
        summary += f"- **Impact Macro :** {macro_str} (ajustement de {macro*100:.4f}% / jour)\n"
        summary += f"- **Synthèse :** La prédiction combine 80% de la tendance historique robuste et 20% des facteurs macro (BAM, Courbe, Sentiment)."
        
        return summary
