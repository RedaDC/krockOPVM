"""
krockOPVM - Feature Builder
============================
Construit les features enrichies à partir des données brutes macro
et des VL OPCVM. Prêt pour LSTM / XGBoost / TFT.
"""

import numpy as np
import pandas as pd
import logging

log = logging.getLogger("feature_builder")


def build_vl_features(df_vl: pd.DataFrame, df_macro: pd.DataFrame) -> pd.DataFrame:
    """
    Construit les features techniques et macro pour un fonds donné.

    Paramètres :
        df_vl    : DataFrame avec colonnes ['date', 'vl']
        df_macro : DataFrame macro issu de build_macro_dataset()

    Retourne :
        DataFrame avec toutes les features prêtes pour le modèle
    """
    df = df_vl.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # ── Rendements ──────────────────────────────────────────────────
    df["vl_ret"] = df["vl"].pct_change()
    df["vl_ret_log"] = np.log(df["vl"] / df["vl"].shift(1))
    df["vl_ret_5j"] = df["vl"].pct_change(5)
    df["vl_ret_20j"] = df["vl"].pct_change(20)

    # ── Moyennes Mobiles ─────────────────────────────────────────────
    for window in [5, 10, 20, 30, 50, 100, 200]:
        df[f"sma_{window}"] = df["vl"].rolling(window).mean()
        df[f"ema_{window}"] = df["vl"].ewm(span=window, adjust=False).mean()

    # Croisements de MM (signal technique)
    df["crossover_10_30"] = (df["sma_10"] - df["sma_30"]) / df["sma_30"]
    df["crossover_50_200"] = (df["sma_50"] - df["sma_200"]) / df["sma_200"]
    df["signal_golden_cross"] = (df["sma_50"] > df["sma_200"]).astype(int)

    # ── Volatilité ───────────────────────────────────────────────────
    df["vol_5j"] = df["vl_ret"].rolling(5).std() * np.sqrt(252)
    df["vol_20j"] = df["vl_ret"].rolling(20).std() * np.sqrt(252)
    df["vol_60j"] = df["vl_ret"].rolling(60).std() * np.sqrt(252)

    # ── RSI (14 jours) ───────────────────────────────────────────────
    df["rsi_14"] = _compute_rsi(df["vl"], 14)
    df["rsi_oversold"] = (df["rsi_14"] < 30).astype(int)
    df["rsi_overbought"] = (df["rsi_14"] > 70).astype(int)

    # ── Bollinger Bands (20 jours, 2 sigma) ─────────────────────────
    bb_mid = df["vl"].rolling(20).mean()
    bb_std = df["vl"].rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid
    df["bb_position"] = (df["vl"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    # ── MACD (12-26-9) ───────────────────────────────────────────────
    ema12 = df["vl"].ewm(span=12, adjust=False).mean()
    ema26 = df["vl"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # ── Momentum ─────────────────────────────────────────────────────
    df["momentum_10"] = df["vl"] / df["vl"].shift(10) - 1
    df["momentum_20"] = df["vl"] / df["vl"].shift(20) - 1
    df["momentum_60"] = df["vl"] / df["vl"].shift(60) - 1

    # ── Lagged features (fuite d'info impossible) ────────────────────
    for lag in [1, 2, 3, 5, 10, 20]:
        df[f"vl_lag_{lag}"] = df["vl"].shift(lag)
        df[f"ret_lag_{lag}"] = df["vl_ret"].shift(lag)

    # ── Calendrier ───────────────────────────────────────────────────
    df["day_of_week"] = df.index.dayofweek
    df["month"] = df.index.month
    df["quarter"] = df.index.quarter
    df["is_month_end"] = df.index.is_month_end.astype(int)
    df["is_quarter_end"] = df.index.is_quarter_end.astype(int)

    # ── Merge avec données macro ──────────────────────────────────────
    df = df.join(df_macro, how="left", rsuffix="_macro")
    df = _remove_dup_columns(df)

    # ── Features dérivées cross-sources ──────────────────────────────
    if "taux_directeur_bam" in df.columns and "bdt_10y" in df.columns:
        df["prime_risque_bam"] = df["bdt_10y"] - df["taux_directeur_bam"]

    if "inflation_cpi" in df.columns and "bdt_1y" in df.columns:
        df["taux_reel_1y"] = df["bdt_1y"] - df["inflation_cpi"]

    if "masi_ret" in df.columns:
        df["corr_masi_20j"] = df["vl_ret"].rolling(20).corr(df["masi_ret"])
        df["beta_masi_60j"] = (
            df["vl_ret"].rolling(60).cov(df["masi_ret"]) /
            df["masi_ret"].rolling(60).var()
        )

    # ── Macro Spreads Laggés ──────────────────────────────────────────
    if "spread_10y_3m" in df.columns:
        df["lag_spread_10y_3m"] = df["spread_10y_3m"].shift(1)
    if "reserves_change_mrd_mad" in df.columns:
        df["reserves_change_mom"] = df["reserves_change_mrd_mad"].pct_change(20)

    log.info(f"Features construites : {len(df.columns)} colonnes, {len(df)} lignes")
    return df


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calcule le RSI (Relative Strength Index)."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _remove_dup_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les colonnes dupliquées après join."""
    return df[[c for c in df.columns if not c.endswith("_macro")]]


def get_feature_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne un résumé des features pour diagnostic."""
    summary = pd.DataFrame({
        "type": df.dtypes,
        "non_null": df.count(),
        "null_pct": (df.isnull().sum() / len(df) * 100).round(1),
        "mean": df.select_dtypes(include=np.number).mean().round(4),
        "std": df.select_dtypes(include=np.number).std().round(4),
    })
    return summary.sort_values("null_pct", ascending=False)


if __name__ == "__main__":
    # Test rapide
    from data_collector import build_macro_dataset

    print("Construction dataset macro...")
    df_macro = build_macro_dataset()

    # Simule une VL de test
    dates = pd.date_range("2022-01-01", "2024-12-31", freq="B")
    df_vl = pd.DataFrame({
        "date": dates,
        "vl": 100 * (1 + np.random.normal(0.0002, 0.001, len(dates))).cumprod()
    })

    print("Construction features...")
    df_features = build_vl_features(df_vl, df_macro)

    print(f"\nShape final : {df_features.shape}")
    print(f"\nAperçu features :")
    print(df_features.tail(3).T.to_string())
