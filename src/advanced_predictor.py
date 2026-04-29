import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from src.feature_builder import build_vl_features

log = logging.getLogger("advanced_predictor")

class AdvancedPredictor:
    """
    Advanced Predictor V2 - Grade Production.
    Uses Machine Learning (RandomForest) with walk-forward validation.
    """
    def __init__(self, df_macro=None):
        self.df_macro = df_macro
        # Improved regularization: Less restrictive to capture more signal
        self.model = RandomForestRegressor(
            n_estimators=200,  # Increased from 100
            max_depth=7,       # Increased from 5 to capture more patterns
            min_samples_leaf=5,  # Decreased from 10 for more sensitivity
            min_samples_split=10,  # Added: minimum samples to split a node
            max_features='sqrt',  # Added: prevents overfitting
            random_state=42
        )
        self.is_trained = False
        self.features = []

    def train_and_evaluate(self, df_vl, test_days=30):
        """
        Trains the model using walk-forward validation and returns metrics.
        Includes Feature Selection (Importance) to avoid overfitting.
        """
        if df_vl.empty or self.df_macro is None:
            return None, "Données insuffisantes"

        # 1. Build features
        df_feat = build_vl_features(df_vl, self.df_macro)
        df_feat = df_feat.dropna()
        
        if len(df_feat) < 40:  # Reduced from 60 to allow shorter histories
            return None, f"Historique trop court (< 40 jours, actuel: {len(df_feat)})"

        # Target: Next day log return
        df_feat["target"] = df_feat["vl_ret_log"].shift(-1)
        df_feat = df_feat.dropna()

        # Initial features selection (exclude target and non-numeric)
        all_numeric_features = [c for c in df_feat.columns if c not in ["target", "vl", "vl_ret", "vl_ret_log"]]
        X_all = df_feat[all_numeric_features]
        y_all = df_feat["target"]

        # 2. Feature Selection via Importance (Preliminary fit)
        selector_model = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
        selector_model.fit(X_all, y_all)
        
        # Select top 15 features (try to get more if available)
        importances = pd.Series(selector_model.feature_importances_, index=all_numeric_features)
        n_features = min(15, len(all_numeric_features))
        self.features = importances.sort_values(ascending=False).head(n_features).index.tolist()
        
        log.info(f"Selected top {len(self.features)} features for prediction")
        
        X = df_feat[self.features]
        y = y_all

        # 3. Walk-forward Split
        train_size = len(df_feat) - test_days
        X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
        y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

        # 4. Train final regularized model
        self.model.fit(X_train, y_train)
        self.is_trained = True

        # 4. Evaluate
        y_pred = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = root_mean_squared_error(y_test, y_pred)
        
        # Directional Accuracy
        correct_direction = (np.sign(y_test) == np.sign(y_pred)).sum()
        dir_acc = correct_direction / len(y_test)

        metrics = {
            "mae": round(mae, 6),
            "rmse": round(rmse, 6),
            "dir_accuracy": round(dir_acc, 2),
            "test_period": test_days
        }

        log.info(f"Modèle entraîné. MAE: {mae}, Dir Acc: {dir_acc}")
        return metrics, None

    def predict_future(self, df_vl, days_ahead=30):
        """
        Predicts future VLs by rolling the model forward.
        Enhanced with better error handling and fallback strategies.
        """
        if not self.is_trained:
            log.warning("Model not trained, using fallback prediction")
            return self._fallback_prediction(df_vl, days_ahead)

        try:
            # Get last known state
            df_feat = build_vl_features(df_vl, self.df_macro)
            if df_feat.empty:
                log.warning("Feature building failed, using fallback")
                return self._fallback_prediction(df_vl, days_ahead)
                
            last_row = df_feat.tail(1)
            
            current_vl = df_vl["vl"].iloc[-1]
            last_date = df_vl["date"].iloc[-1]
            
            # Check if we have the required features
            missing_features = [f for f in self.features if f not in df_feat.columns]
            if missing_features:
                log.warning(f"Missing features: {missing_features}, using fallback")
                return self._fallback_prediction(df_vl, days_ahead)
            
            predictions = []
            temp_df = df_vl.copy()

            for i in range(1, days_ahead + 1):
                next_date = last_date + timedelta(days=i)
                if next_date.weekday() >= 5:  # Skip weekends
                    continue

                # Re-build features for the current point
                feat_current = build_vl_features(temp_df, self.df_macro).tail(1)
                X_curr = feat_current[self.features]
                
                # Predict log return
                pred_log_ret = self.model.predict(X_curr)[0]
                
                # Clamp prediction to reasonable range (-2% to +2% daily)
                pred_log_ret = max(-0.02, min(0.02, pred_log_ret))
                
                # Update VL
                current_vl = current_vl * np.exp(pred_log_ret)
                
                predictions.append({
                    "date": next_date,
                    "nom_fonds": df_vl["nom_fonds"].iloc[0] if "nom_fonds" in df_vl.columns else "Fonds",
                    "vl_jour": round(current_vl, 2),
                    "type": "Prediction V2",
                    "expected_return": round(pred_log_ret * 100, 4)  # Convert to percentage
                })
                
                # Append to temp_df to allow next feature building (lags, etc)
                new_row = pd.DataFrame({"date": [next_date], "vl": [current_vl]})
                temp_df = pd.concat([temp_df, new_row]).reset_index(drop=True)

            log.info(f"Generated {len(predictions)} predictions")
            return pd.DataFrame(predictions)
            
        except Exception as e:
            log.error(f"Prediction failed: {e}, using fallback")
            return self._fallback_prediction(df_vl, days_ahead)
    
    def _fallback_prediction(self, df_vl, days_ahead):
        """
        Fallback prediction using simple momentum trend.
        Used when ML model fails or is not trained.
        """
        if df_vl.empty or len(df_vl) < 5:
            log.error("Insufficient data for even fallback prediction")
            return pd.DataFrame()
        
        # Handle both 'vl' and 'vl_jour' column names
        vl_col = 'vl' if 'vl' in df_vl.columns else 'vl_jour'
        if vl_col not in df_vl.columns:
            log.error("No VL column found (need 'vl' or 'vl_jour')")
            return pd.DataFrame()
        
        # Calculate recent momentum (last 20 days)
        recent_data = df_vl.tail(20)
        if len(recent_data) < 5:
            recent_data = df_vl
        
        # Simple linear trend
        x = np.arange(len(recent_data))
        y = recent_data[vl_col].values
        
        # Calculate daily return trend
        if y[0] > 0:
            total_return = (y[-1] - y[0]) / y[0]
            daily_trend = total_return / len(recent_data)
        else:
            daily_trend = 0.0
        
        # Generate predictions
        current_vl = df_vl[vl_col].iloc[-1]
        last_date = df_vl["date"].iloc[-1]
        
        predictions = []
        for i in range(1, days_ahead + 1):
            next_date = last_date + timedelta(days=i)
            if next_date.weekday() >= 5:
                continue
            
            # Apply trend with small noise
            noise = np.random.normal(0, 0.001)  # 0.1% daily noise
            daily_return = daily_trend + noise
            current_vl = current_vl * (1 + daily_return)
            
            predictions.append({
                "date": next_date,
                "nom_fonds": df_vl["nom_fonds"].iloc[0] if "nom_fonds" in df_vl.columns else "Fonds",
                "vl_jour": round(current_vl, 2),
                "type": "Prediction (Fallback)",
                "expected_return": round(daily_return * 100, 4)
            })
        
        log.info(f"Generated {len(predictions)} fallback predictions")
        return pd.DataFrame(predictions)
