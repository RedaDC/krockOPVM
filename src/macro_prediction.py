import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class MacroPredictor:
    """
    Predicts OPCVM VLs based on historical data and macro-economic factors.
    """
    def __init__(self):
        self.risk_keywords = ["incertitude", "volatilité", "décroche", "restrictive", "risque", "hausse"]
        self.positive_keywords = ["assouplissement", "baisse", "croissance", "stabilité", "favorable"]

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
        bam_effet = (3.0 - float(taux_bam)) * 0.0001
        
        # Apply logic by classification
        class_lower = str(classification).lower()
        if "oblig" in class_lower:
            # Bonds are highly sensitive to yield curve and rate hikes (inversely)
            modifier = (courbe_effet * 2) + bam_effet + (sentiment_score * 0.0002)
        elif "action" in class_lower:
            # Equities are sensitive to sentiment and rates
            modifier = courbe_effet + (bam_effet * 1.5) + (sentiment_score * 0.0005)
        elif "monet" in class_lower:
            # Money market is stable, benefits slightly from higher rates
            modifier = max(0, -bam_effet) * 0.1 # Very small positive impact
        else:
            # Diversified
            modifier = courbe_effet + bam_effet + (sentiment_score * 0.0003)
            
        return modifier

    def predict(self, df_history, taux_bam, courbe_taux, anticipations_text, days_ahead=30):
        """
        Generates predictions for the next `days_ahead`.
        
        Args:
            df_history (pd.DataFrame): Must contain 'date', 'nom_fonds', 'classification', 'vl_jour'
            taux_bam (float): Taux directeur (e.g., 2.75)
            courbe_taux (str): Evolution description (e.g., "Hausse", "Stable")
            anticipations_text (str): Partners macro predictions
            days_ahead (int): Number of days to predict
            
        Returns:
            pd.DataFrame: Contains original data + predictions flagged as 'Prédite'
        """
        if df_history.empty:
            return pd.DataFrame()
            
        # Ensure dates are datetime
        if not pd.api.types.is_datetime64_any_dtype(df_history['date']):
            df_history['date'] = pd.to_datetime(df_history['date'], errors='coerce')
            
        df_history = df_history.dropna(subset=['date', 'vl_jour']).sort_values('date')
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(anticipations_text)
        
        predictions = []
        
        for fonds in df_history['nom_fonds'].unique():
            df_fonds = df_history[df_history['nom_fonds'] == fonds].copy()
            if df_fonds.empty:
                continue
                
            classification = df_fonds['classification'].iloc[-1]
            last_date = df_fonds['date'].max()
            last_vl = df_fonds['vl_jour'].iloc[-1]
            
            # Calculate baseline momentum over last 30 days
            recent_data = df_fonds.tail(30)
            if len(recent_data) > 1:
                first_vl_recent = recent_data['vl_jour'].iloc[0]
                days_diff = (last_date - recent_data['date'].iloc[0]).days
                daily_momentum = (last_vl - first_vl_recent) / first_vl_recent / max(days_diff, 1)
            else:
                daily_momentum = 0.0
                
            # Get macro modifier
            macro_modifier = self._get_macro_modifier(classification, taux_bam, courbe_taux, sentiment)
            
            # Total daily drift
            daily_drift = daily_momentum + macro_modifier
            
            # Generate future data
            current_vl = last_vl
            for i in range(1, days_ahead + 1):
                next_date = last_date + timedelta(days=i)
                # Skip weekends
                if next_date.weekday() >= 5:
                    continue
                    
                # Add some random noise based on class
                volatility = 0.001
                if "action" in str(classification).lower():
                    volatility = 0.005
                elif "monet" in str(classification).lower():
                    volatility = 0.0001
                    
                noise = np.random.normal(0, volatility)
                
                # Calculate next VL
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
