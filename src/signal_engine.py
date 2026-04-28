"""
signal_engine.py — Moteur de Signal IA pour krockOPVM V2
=========================================================
Calcule un score de confiance continu (0–100) par fond OPCVM,
en agrégeant trois sous-scores pondérés selon la classe d'actif.

Sous-scores :
  1. RF Score       — RandomForest sur Top 15 features (walk-forward 30j)
  2. Momentum Score — Croisements de moyennes mobiles calibrés par classe
  3. Macro Score    — Spread BDT 10Y-3M + prime de risque BAM

Usage :
  from signal_engine import SignalEngine
  engine = SignalEngine(asset_class="obligataire")
  result = engine.compute(df_features, df_macro)
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error
from dataclasses import dataclass, field
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

AssetClass = Literal["actions", "obligataire", "monetaire", "diversifie"]

# Pondérations des trois sous-scores par classe d'actif
WEIGHTS: dict[AssetClass, dict] = {
    "actions":     {"rf": 0.40, "momentum": 0.40, "macro": 0.20},
    "obligataire": {"rf": 0.30, "momentum": 0.20, "macro": 0.50},
    "monetaire":   {"rf": 0.20, "momentum": 0.10, "macro": 0.70},
    "diversifie":  {"rf": 0.35, "momentum": 0.30, "macro": 0.35},
}

# Fenêtres de moyennes mobiles par classe d'actif
MA_WINDOWS: dict[AssetClass, tuple] = {
    "actions":     (10, 30),
    "obligataire": (15, 60),
    "monetaire":   (15, 60),
    "diversifie":  (12, 45),
}

# Seuil de déclenchement momentum (en %) par classe
MOMENTUM_THRESHOLD: dict[AssetClass, float] = {
    "actions":     0.10,
    "obligataire": 0.20,
    "monetaire":   0.20,
    "diversifie":  0.15,
}


# ---------------------------------------------------------------------------
# Résultat structuré
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    score: float                   # Score agrégé 0–100
    rf_score: float                # Sous-score RF 0–100
    momentum_score: float          # Sous-score momentum 0–100
    macro_score: float             # Sous-score macro 0–100
    directional_accuracy: float    # % de directions correctes (walk-forward)
    mae: float                     # Erreur absolue moyenne (walk-forward)
    top_features: list[str]        # Top 15 features sélectionnées
    weights_used: dict             # Pondérations appliquées
    asset_class: str
    interpretation: str = field(init=False)

    def __post_init__(self):
        if self.score >= 70:
            self.interpretation = "Signal haussier fort"
        elif self.score >= 55:
            self.interpretation = "Signal haussier modéré"
        elif self.score >= 45:
            self.interpretation = "Neutre — attendre confirmation"
        elif self.score >= 30:
            self.interpretation = "Signal baissier modéré"
        else:
            self.interpretation = "Signal baissier fort"


# ---------------------------------------------------------------------------
# Moteur principal
# ---------------------------------------------------------------------------

class SignalEngine:
    """
    Calcule le score de confiance IA (0–100) pour un fond OPCVM.

    Paramètres
    ----------
    asset_class : str
        Classe d'actif du fond : 'actions', 'obligataire', 'monetaire', 'diversifie'.
    n_top_features : int
        Nombre de features à retenir après sélection (défaut : 15).
    rf_params : dict, optional
        Hyperparamètres du RandomForest (remplace les défauts si fourni).
    walk_forward_days : int
        Taille de la fenêtre de validation walk-forward (défaut : 30j).
    random_state : int
        Graine aléatoire pour la reproductibilité.
    """

    DEFAULT_RF_PARAMS = {
        "n_estimators": 200,
        "max_depth": 5,
        "min_samples_leaf": 10,
        "max_features": "sqrt",
        "n_jobs": -1,
        "random_state": 42,
    }

    def __init__(
        self,
        asset_class: AssetClass = "obligataire",
        n_top_features: int = 15,
        rf_params: Optional[dict] = None,
        walk_forward_days: int = 30,
        random_state: int = 42,
    ):
        if asset_class not in WEIGHTS:
            raise ValueError(f"asset_class doit être dans {list(WEIGHTS.keys())}")
        self.asset_class = asset_class
        self.n_top_features = n_top_features
        self.walk_forward_days = walk_forward_days
        self.random_state = random_state
        self.weights = WEIGHTS[asset_class]
        self.ma_windows = MA_WINDOWS[asset_class]
        self.momentum_threshold = MOMENTUM_THRESHOLD[asset_class]
        self.rf_params = {**self.DEFAULT_RF_PARAMS, **(rf_params or {})}
        self._model: Optional[RandomForestRegressor] = None
        self._top_features: list[str] = []

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def compute(
        self,
        df_features: pd.DataFrame,
        df_macro: pd.DataFrame,
        target_col: str = "vl_log_return",
    ) -> SignalResult:
        """
        Calcule le score de confiance agrégé.

        Paramètres
        ----------
        df_features : DataFrame
            Features engineerées (log returns, RSI, MACD, lags…).
            Index = DatetimeIndex trié chronologiquement.
        df_macro : DataFrame
            Données macro (taux BAM, courbe BDT, IPC…).
            Index = DatetimeIndex trié chronologiquement.
        target_col : str
            Nom de la colonne cible dans df_features.

        Retourne
        --------
        SignalResult
        """
        # Validation minimale
        if target_col not in df_features.columns:
            raise ValueError(f"Colonne cible '{target_col}' absente de df_features.")
        if len(df_features) < self.walk_forward_days + 30:
            raise ValueError("Historique insuffisant (minimum 60 observations).")

        # 1. RF Score
        rf_score, mae, dir_acc, top_feats = self._compute_rf_score(
            df_features, target_col
        )

        # 2. Momentum Score
        momentum_score = self._compute_momentum_score(df_features, target_col)

        # 3. Macro Score
        macro_score = self._compute_macro_score(df_macro)

        # 4. Agrégation pondérée
        w = self.weights
        aggregated = (
            w["rf"] * rf_score
            + w["momentum"] * momentum_score
            + w["macro"] * macro_score
        )
        aggregated = float(np.clip(aggregated, 0, 100))

        return SignalResult(
            score=round(aggregated, 1),
            rf_score=round(rf_score, 1),
            momentum_score=round(momentum_score, 1),
            macro_score=round(macro_score, 1),
            directional_accuracy=round(dir_acc, 3),
            mae=round(mae, 6),
            top_features=top_feats,
            weights_used=w,
            asset_class=self.asset_class,
        )

    # ------------------------------------------------------------------
    # Sous-score 1 : RandomForest
    # ------------------------------------------------------------------

    def _compute_rf_score(
        self,
        df: pd.DataFrame,
        target_col: str,
    ) -> tuple[float, float, float, list[str]]:
        """
        Entraîne un RandomForest, sélectionne les Top N features via
        permutation importance, puis évalue en walk-forward.

        Retourne : (rf_score_0_100, mae, directional_accuracy, top_features)
        """
        feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_col]
        X = df[feature_cols].dropna()
        y = df[target_col].loc[X.index]

        split = len(X) - self.walk_forward_days
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        # Passage 1 : entraînement sur toutes les features
        model_full = RandomForestRegressor(**self.rf_params)
        model_full.fit(X_train, y_train)

        # Sélection Top N via permutation importance (plus stable que feature_importances_)
        perm = permutation_importance(
            model_full, X_test, y_test,
            n_repeats=10,
            random_state=self.random_state,
            n_jobs=-1,
        )
        importance_mean = perm.importances_mean
        top_idx = np.argsort(importance_mean)[::-1][: self.n_top_features]
        top_features = [feature_cols[i] for i in top_idx]
        self._top_features = top_features

        # Passage 2 : ré-entraînement sur Top N uniquement
        model_top = RandomForestRegressor(**self.rf_params)
        model_top.fit(X_train[top_features], y_train)
        self._model = model_top

        # Évaluation walk-forward
        y_pred = model_top.predict(X_test[top_features])
        mae = float(mean_absolute_error(y_test, y_pred))

        # Directional accuracy
        correct_dir = np.sign(y_pred) == np.sign(y_test.values)
        dir_acc = float(correct_dir.mean())

        # Conversion en score 0–100
        # dir_acc ∈ [0,1] → [0,100], pondéré par la précision relative
        rf_score = self._normalize_rf(dir_acc, mae, y_test)

        return rf_score, mae, dir_acc, top_features

    @staticmethod
    def _normalize_rf(
        dir_acc: float,
        mae: float,
        y_test: pd.Series,
    ) -> float:
        """
        Combine directional accuracy et MAE relative en score 0–100.
        dir_acc pondéré à 70%, précision relative à 30%.
        """
        # MAE relative : 0 = parfait, 1 = aussi mauvais que la std
        std = float(y_test.std()) or 1e-9
        mae_rel = min(mae / std, 1.0)
        precision_score = (1 - mae_rel) * 100

        score = 0.70 * (dir_acc * 100) + 0.30 * precision_score
        return float(np.clip(score, 0, 100))

    # ------------------------------------------------------------------
    # Sous-score 2 : Momentum
    # ------------------------------------------------------------------

    def _compute_momentum_score(
        self,
        df: pd.DataFrame,
        target_col: str,
    ) -> float:
        """
        Score momentum basé sur :
          - Croisement SMA court / SMA long
          - Force du momentum (magnitude du spread)
          - Filtre de seuil par classe d'actif
        """
        vl = df[target_col].cumsum().apply(np.exp)  # VL reconstituée
        short_w, long_w = self.ma_windows

        sma_short = vl.rolling(short_w, min_periods=short_w // 2).mean()
        sma_long = vl.rolling(long_w, min_periods=long_w // 2).mean()

        if sma_short.isna().all() or sma_long.isna().all():
            return 50.0  # Neutre si données insuffisantes

        # Spread en % entre les deux moyennes
        spread_pct = ((sma_short - sma_long) / sma_long * 100).dropna()

        if len(spread_pct) == 0:
            return 50.0

        current_spread = float(spread_pct.iloc[-1])
        threshold = self.momentum_threshold

        # Score basé sur la position relative du spread
        # Spread > +threshold → haussier, < -threshold → baissier
        if abs(current_spread) < threshold:
            return 50.0  # Zone neutre

        # Normalisation : clip à ±5% pour les actions, ±2% pour oblig/monét
        max_spread = 5.0 if self.asset_class == "actions" else 2.0
        normalized = current_spread / max_spread
        score = 50 + normalized * 50
        return float(np.clip(score, 0, 100))

    # ------------------------------------------------------------------
    # Sous-score 3 : Macro
    # ------------------------------------------------------------------

    def _compute_macro_score(self, df_macro: pd.DataFrame) -> float:
        """
        Score macro basé sur :
          - Spread BDT 10Y - 3M (courbe des taux)
          - Évolution du taux directeur BAM
          - Momentum des réserves de change
        """
        score_components = []

        # -- Spread BDT 10Y-3M --
        if "bdt_10y" in df_macro.columns and "bdt_3m" in df_macro.columns:
            spread = (df_macro["bdt_10y"] - df_macro["bdt_3m"]).dropna()
            if len(spread) > 0:
                current = float(spread.iloc[-1])
                # Spread positif et croissant = favorable (courbe normale)
                # Spread négatif = courbe inversée = risque
                # Normalisation sur [-2%, +3%] historique MAR
                spread_score = np.clip((current + 2) / 5 * 100, 0, 100)
                score_components.append(("spread_bdt", float(spread_score), 0.50))

        # -- Taux directeur BAM --
        if "taux_directeur" in df_macro.columns:
            td = df_macro["taux_directeur"].dropna()
            if len(td) >= 2:
                delta = float(td.iloc[-1] - td.iloc[-2])
                # Baisse du taux = favorable pour obligations
                if self.asset_class in ("obligataire", "monetaire"):
                    td_score = 50 - delta * 1000  # -25bp = +25pts
                else:
                    td_score = 50 + delta * 500   # Hausse = économie dynamique
                score_components.append(("taux_bam", float(np.clip(td_score, 0, 100)), 0.30))

        # -- Momentum réserves de change --
        if "reserves_change" in df_macro.columns:
            res = df_macro["reserves_change"].dropna()
            if len(res) >= 20:
                mom = float((res.iloc[-1] - res.iloc[-20]) / (res.iloc[-20] or 1))
                res_score = np.clip(50 + mom * 100, 0, 100)
                score_components.append(("reserves", float(res_score), 0.20))

        if not score_components:
            return 50.0  # Neutre si aucune donnée macro disponible

        # Agrégation pondérée (renormalisée si certains composants manquent)
        total_weight = sum(w for _, _, w in score_components)
        macro_score = sum(s * w for _, s, w in score_components) / total_weight
        return float(np.clip(macro_score, 0, 100))

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    @property
    def top_features(self) -> list[str]:
        """Retourne les features sélectionnées après le dernier compute()."""
        return self._top_features

    def predict_next(self, df_features: pd.DataFrame) -> Optional[float]:
        """
        Prédit le log return du prochain jour avec le modèle entraîné.
        Retourne None si le modèle n'a pas encore été entraîné.
        """
        if self._model is None or not self._top_features:
            return None
        last_row = df_features[self._top_features].dropna().iloc[[-1]]
        return float(self._model.predict(last_row)[0])

    def summary(self, result: SignalResult) -> str:
        """Retourne un résumé textuel du signal."""
        lines = [
            f"=== Signal IA — {result.asset_class.upper()} ===",
            f"Score global    : {result.score:.1f}/100 → {result.interpretation}",
            f"RF Score        : {result.rf_score:.1f}  (poids {result.weights_used['rf']:.0%})",
            f"Momentum Score  : {result.momentum_score:.1f}  (poids {result.weights_used['momentum']:.0%})",
            f"Macro Score     : {result.macro_score:.1f}  (poids {result.weights_used['macro']:.0%})",
            f"MAE walk-fwd    : {result.mae:.6f}",
            f"Dir. Accuracy   : {result.directional_accuracy:.1%}",
            f"Top features    : {', '.join(result.top_features[:5])}…",
        ]
        return "\n".join(lines)
