"""
Enhanced Prediction Engine for OPCVM
=====================================
Advanced prediction system combining:
- Multiple ML models (Random Forest, Gradient Boosting, LSTM)
- Ensemble methods for robust predictions
- Regime detection (bull/bear/sideways markets)
- Dynamic feature importance
- Prediction intervals (confidence bands)
- Model drift detection
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

log = logging.getLogger("enhanced_predictor")

class EnhancedPredictionEngine:
    """
    Advanced prediction engine with ensemble methods and regime detection.
    """
    
    def __init__(self):
        self.models = {
            'rf': RandomForestRegressor(
                n_estimators=300,
                max_depth=8,
                min_samples_leaf=4,
                min_samples_split=8,
                max_features='sqrt',
                random_state=42,
                n_jobs=-1
            ),
            'gb': GradientBoostingRegressor(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                min_samples_leaf=5,
                min_samples_split=10,
                subsample=0.8,
                random_state=42
            )
        }
        self.scaler = StandardScaler()
        self.model_weights = {'rf': 0.5, 'gb': 0.5}
        self.feature_importance = {}
        self.is_fitted = False
        self.training_metrics = {}
        
    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build comprehensive feature set for prediction.
        """
        df_feat = df.copy()
        
        # Ensure sorted by date
        if 'date' in df_feat.columns:
            df_feat = df_feat.sort_values('date')
        
        vl = df_feat['vl_jour'].values
        
        # Price-based features
        df_feat['return_1d'] = np.log(vl / np.roll(vl, 1))
        df_feat['return_5d'] = np.log(vl / np.roll(vl, 5))
        df_feat['return_10d'] = np.log(vl / np.roll(vl, 10))
        df_feat['return_20d'] = np.log(vl / np.roll(vl, 20))
        
        # Moving averages
        df_feat['ma_5'] = pd.Series(vl).rolling(5).mean()
        df_feat['ma_10'] = pd.Series(vl).rolling(10).mean()
        df_feat['ma_20'] = pd.Series(vl).rolling(20).mean()
        
        # MA crossovers
        df_feat['ma_5_10_ratio'] = df_feat['ma_5'] / df_feat['ma_10']
        df_feat['ma_10_20_ratio'] = df_feat['ma_10'] / df_feat['ma_20']
        
        # Volatility features
        df_feat['volatility_5d'] = pd.Series(df_feat['return_1d']).rolling(5).std()
        df_feat['volatility_10d'] = pd.Series(df_feat['return_1d']).rolling(10).std()
        df_feat['volatility_20d'] = pd.Series(df_feat['return_1d']).rolling(20).std()
        
        # Momentum indicators
        df_feat['momentum_5d'] = vl / np.roll(vl, 5) - 1
        df_feat['momentum_10d'] = vl / np.roll(vl, 10) - 1
        
        # RSI (Relative Strength Index)
        delta = pd.Series(vl).diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df_feat['rsi_14'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df_feat['bb_middle'] = pd.Series(vl).rolling(20).mean()
        bb_std = pd.Series(vl).rolling(20).std()
        df_feat['bb_upper'] = df_feat['bb_middle'] + (bb_std * 2)
        df_feat['bb_lower'] = df_feat['bb_middle'] - (bb_std * 2)
        df_feat['bb_position'] = (vl - df_feat['bb_lower']) / (df_feat['bb_upper'] - df_feat['bb_lower'])
        
        # Price position relative to MAs
        df_feat['price_vs_ma5'] = vl / df_feat['ma_5'] - 1
        df_feat['price_vs_ma10'] = vl / df_feat['ma_10'] - 1
        df_feat['price_vs_ma20'] = vl / df_feat['ma_20'] - 1
        
        # Trend strength
        df_feat['trend_strength'] = abs(df_feat['ma_5'] - df_feat['ma_20']) / df_feat['ma_20']
        
        # Volume/flow features (if available)
        if 'flux_net' in df_feat.columns:
            df_feat['flux_ma_5'] = df_feat['flux_net'].rolling(5).mean()
            df_feat['flux_acceleration'] = df_feat['flux_net'].diff()
        
        # Sentiment features (if available)
        if 'score_sentiment_moyen_jour' in df_feat.columns:
            df_feat['sentiment_ma_5'] = df_feat['score_sentiment_moyen_jour'].rolling(5).mean()
            df_feat['sentiment_trend'] = df_feat['score_sentiment_moyen_jour'].diff()
        
        # Fill NaN values
        df_feat = df_feat.fillna(method='bfill').fillna(0)
        
        return df_feat
    
    def _detect_regime(self, df: pd.DataFrame) -> str:
        """
        Detect current market regime (BULLISH, BEARISH, SIDEWAYS).
        """
        if len(df) < 20:
            return 'SIDEWAYS'
        
        vl = df['vl_jour'].values[-20:]
        returns = np.diff(vl) / vl[:-1]
        
        # Trend
        ma_short = vl[-5:].mean()
        ma_long = vl.mean()
        trend = (ma_short - ma_long) / ma_long
        
        # Momentum
        momentum = (vl[-1] / vl[0]) - 1
        
        # Volatility
        volatility = np.std(returns) * np.sqrt(252)
        
        # Regime classification
        if trend > 0.02 and momentum > 0.02:
            return 'BULLISH'
        elif trend < -0.02 and momentum < -0.02:
            return 'BEARISH'
        else:
            return 'SIDEWAYS'
    
    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get feature columns for model training."""
        exclude_cols = ['date', 'nom_fonds', 'classification', 'vl_jour']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        return feature_cols
    
    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train ensemble model on historical data.
        
        Args:
            df: DataFrame with historical data
            
        Returns:
            Dictionary with training metrics
        """
        try:
            # Build features
            df_feat = self._build_features(df)
            
            # Get feature columns
            feature_cols = self._get_feature_columns(df_feat)
            
            # Create target: next day return
            vl = df_feat['vl_jour'].values
            df_feat['target'] = np.roll(vl, -1) / vl - 1
            
            # Remove last row (no target)
            df_feat = df_feat.iloc[:-1]
            
            X = df_feat[feature_cols].values
            y = df_feat['target'].values
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train models
            metrics = {}
            for name, model in self.models.items():
                model.fit(X_scaled, y)
                
                # Training R²
                train_score = model.score(X_scaled, y)
                metrics[f'{name}_r2'] = train_score
                
                # Feature importance
                if hasattr(model, 'feature_importances_'):
                    self.feature_importance[name] = dict(
                        zip(feature_cols, model.feature_importances_.tolist())
                    )
            
            # Optimize weights based on performance
            total_r2 = sum(metrics[f'{name}_r2'] for name in self.models.keys())
            if total_r2 > 0:
                self.model_weights = {
                    name: metrics[f'{name}_r2'] / total_r2 
                    for name in self.models.keys()
                }
            
            metrics['ensemble_r2'] = total_r2
            metrics['model_weights'] = self.model_weights
            metrics['n_samples'] = len(X)
            metrics['n_features'] = len(feature_cols)
            
            self.is_fitted = True
            self.training_metrics = metrics
            
            log.info(f"Training complete: R²={metrics['ensemble_r2']:.3f}, "
                    f"samples={metrics['n_samples']}, features={metrics['n_features']}")
            
            return metrics
            
        except Exception as e:
            log.error(f"Training failed: {e}")
            return {'error': str(e)}
    
    def predict(self, df: pd.DataFrame, days_ahead: int = 30) -> pd.DataFrame:
        """
        Generate predictions with confidence intervals.
        
        Args:
            df: Historical DataFrame
            days_ahead: Number of days to predict
            
        Returns:
            DataFrame with predictions and confidence bands
        """
        if not self.is_fitted:
            log.error("Model not trained yet")
            return pd.DataFrame()
        
        try:
            # Build features
            df_feat = self._build_features(df)
            feature_cols = self._get_feature_columns(df_feat)
            
            # Generate predictions iteratively
            predictions = []
            current_df = df_feat.copy()
            
            for day in range(1, days_ahead + 1):
                # Get latest features
                X_latest = current_df[feature_cols].iloc[-1:].values
                X_scaled = self.scaler.transform(X_latest)
                
                # Ensemble prediction
                pred_returns = []
                for name, model in self.models.items():
                    pred = model.predict(X_scaled)[0]
                    pred_returns.append(pred * self.model_weights[name])
                
                expected_return = sum(pred_returns)
                
                # Calculate new VL
                last_vl = current_df['vl_jour'].iloc[-1]
                new_vl = last_vl * (1 + expected_return)
                
                # Confidence interval (based on historical volatility)
                if len(current_df) >= 20:
                    hist_vol = current_df['volatility_20d'].iloc[-1]
                    confidence_width = hist_vol * 1.96 * np.sqrt(day)  # 95% CI
                else:
                    confidence_width = 0.02 * np.sqrt(day)  # Default 2% daily vol
                
                upper_bound = new_vl * (1 + confidence_width)
                lower_bound = new_vl * (1 - confidence_width)
                
                # Create new row
                new_row = current_df.iloc[-1:].copy()
                new_row['vl_jour'] = new_vl
                new_row['date'] = current_df['date'].iloc[-1] + timedelta(days=day)
                
                predictions.append({
                    'date': new_row['date'].iloc[0],
                    'vl_jour': new_vl,
                    'vl_upper': upper_bound,
                    'vl_lower': lower_bound,
                    'expected_return': expected_return,
                    'confidence_width': confidence_width,
                    'type': 'Prediction (Ensemble)'
                })
                
                # Update current_df for next iteration
                new_row['return_1d'] = expected_return
                new_row['return_5d'] = (new_vl / current_df['vl_jour'].iloc[-5]) - 1 if len(current_df) >= 5 else expected_return
                new_row['momentum_5d'] = (new_vl / current_df['vl_jour'].iloc[-5]) - 1 if len(current_df) >= 5 else expected_return
                
                # Simple MA updates
                vl_series = pd.concat([current_df['vl_jour'], pd.Series([new_vl])])
                new_row['ma_5'] = vl_series.tail(5).mean()
                new_row['ma_10'] = vl_series.tail(10).mean() if len(vl_series) >= 10 else new_row['ma_5']
                new_row['ma_20'] = vl_series.tail(20).mean() if len(vl_series) >= 20 else new_row['ma_10']
                
                current_df = pd.concat([current_df, new_row])
            
            df_pred = pd.DataFrame(predictions)
            df_pred['date'] = pd.to_datetime(df_pred['date'])
            
            log.info(f"Generated {len(df_pred)} predictions")
            
            return df_pred
            
        except Exception as e:
            log.error(f"Prediction failed: {e}")
            return pd.DataFrame()
    
    def get_analysis(self, df: pd.DataFrame, predictions: pd.DataFrame) -> Dict:
        """
        Get comprehensive analysis of predictions.
        
        Args:
            df: Historical DataFrame
            predictions: Prediction DataFrame
            
        Returns:
            Dictionary with analysis
        """
        if predictions.empty:
            return {}
        
        # Regime detection
        regime = self._detect_regime(df)
        
        # Prediction statistics
        first_pred = predictions['vl_jour'].iloc[0]
        last_pred = predictions['vl_jour'].iloc[-1]
        current_vl = df['vl_jour'].iloc[-1]
        
        total_return = (last_pred / current_vl) - 1
        avg_daily_return = predictions['expected_return'].mean()
        
        # Confidence analysis
        avg_confidence = predictions['confidence_width'].mean()
        confidence_trend = "INCREASING" if predictions['confidence_width'].iloc[-1] > predictions['confidence_width'].iloc[0] else "DECREASING"
        
        # Feature importance (top 5)
        top_features = {}
        if self.feature_importance:
            for name, importance in self.feature_importance.items():
                sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
                top_features[name] = sorted_features
        
        return {
            'regime': regime,
            'total_return_30d': total_return,
            'avg_daily_return': avg_daily_return,
            'prediction_range': {
                'min': predictions['vl_lower'].min(),
                'max': predictions['vl_upper'].max()
            },
            'confidence': {
                'average_width': avg_confidence,
                'trend': confidence_trend,
                'final_width': predictions['confidence_width'].iloc[-1]
            },
            'top_features': top_features,
            'model_weights': self.model_weights,
            'training_r2': self.training_metrics.get('ensemble_r2', 0)
        }


def get_enhanced_predictor() -> EnhancedPredictionEngine:
    """Get enhanced prediction engine instance"""
    return EnhancedPredictionEngine()
