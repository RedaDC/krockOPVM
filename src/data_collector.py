"""
krockOPVM - Couche 1 : Collecteur de Données Enrichies
=======================================================
Collecte automatique de :
  - Taux directeur BAM + réserves de change + M3
  - Courbe des taux BDT (Bons du Trésor)
  - MASI / MADEX (Bourse de Casablanca)
  - Flux ASFIM (import Excel/CSV)
  - Taux de change MAD + inflation (World Bank)
"""

import os
import time
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO

# ── Configuration ──────────────────────────────────────────────────────────────

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("data_collector")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (krockOPVM/1.0 research bot)"
}

# ── 1. Données BAM ─────────────────────────────────────────────────────────────

# Taux directeur BAM (historique manuel — BAM ne fournit pas d'API publique).
# À compléter avec les décisions du Conseil de BAM.
# Source : https://www.bam.ma/fr/politique-monetaire/taux-directeur
BAM_TAUX_DIRECTEUR_HISTORIQUE = {
    "2019-03-19": 2.25,
    "2020-03-17": 2.00,
    "2020-06-16": 1.50,
    "2022-09-27": 2.00,
    "2022-12-27": 2.50,
    "2023-03-21": 3.00,
    "2023-06-27": 3.00,
    "2024-06-18": 2.75,
    "2024-09-24": 2.50,
}

# Réserves de change (milliards MAD) — publication mensuelle BAM
BAM_RESERVES_CHANGE_HISTORIQUE = {
    "2023-01": 337.5,
    "2023-06": 325.8,
    "2023-12": 341.2,
    "2024-03": 354.1,
    "2024-06": 361.7,
    "2024-09": 368.3,
    "2024-12": 372.0,
}


def get_bam_taux_directeur(start_date: str = "2019-01-01") -> pd.DataFrame:
    """
    Retourne une série temporelle quotidienne du taux directeur BAM.
    Le taux est 'forward filled' entre les décisions.
    """
    log.info("Construction série taux directeur BAM...")
    records = []
    for date_str, taux in sorted(BAM_TAUX_DIRECTEUR_HISTORIQUE.items()):
        records.append({"date": pd.to_datetime(date_str), "taux_directeur_bam": taux})

    df = pd.DataFrame(records).set_index("date")

    # Génère un index quotidien et forward-fill
    start = max(pd.to_datetime(start_date), df.index.min())
    end = datetime.today()
    full_index = pd.date_range(start=start, end=end, freq="B")  # jours ouvrés
    df = df.reindex(full_index).ffill().rename_axis("date")

    log.info(f"Taux directeur BAM : {len(df)} observations")
    return df


def get_bam_reserves_change() -> pd.DataFrame:
    """
    Retourne une série mensuelle des réserves de change.
    """
    records = [
        {"date": pd.to_datetime(d + "-01"), "reserves_change_mrd_mad": v}
        for d, v in BAM_RESERVES_CHANGE_HISTORIQUE.items()
    ]
    df = pd.DataFrame(records).set_index("date").sort_index()
    # Resample en fréquence quotidienne, forward-fill
    full_index = pd.date_range(df.index.min(), datetime.today(), freq="B")
    df = df.reindex(full_index).ffill().rename_axis("date")
    return df


# ── 2. Courbe des Taux BDT ──────────────────────────────────────────────────────

# Données de rendements BDT publiées par le Trésor / BAM
# Source manuelle : https://www.finances.gov.ma/Publication/dtfe/Recueil_Statistiques.pdf
# Ces valeurs sont à mettre à jour mensuellement.
BDT_RENDEMENTS_SNAPSHOT = {
    "2024-12-31": {
        "bdt_3m": 3.15,
        "bdt_6m": 3.22,
        "bdt_1y": 3.38,
        "bdt_2y": 3.52,
        "bdt_5y": 3.89,
        "bdt_10y": 4.20,
        "bdt_15y": 4.45,
        "bdt_20y": 4.60,
    }
}


def get_courbe_taux_bdt(start_date: str = "2022-01-01") -> pd.DataFrame:
    """
    Retourne la courbe des taux BDT.
    En production, à connecter à un scraper du site finances.gov.ma
    ou à l'API Bloomberg/Refinitiv si disponible.
    """
    log.info("Chargement courbe des taux BDT...")
    cache_file = CACHE_DIR / "bdt_courbe.csv"

    if cache_file.exists():
        df = pd.read_csv(cache_file, index_col="date", parse_dates=True)
        log.info(f"BDT courbe taux chargée depuis cache : {len(df)} lignes")
        return df

    # Données snapshot → forward fill jusqu'à aujourd'hui
    records = []
    for date_str, taux_dict in BDT_RENDEMENTS_SNAPSHOT.items():
        rec = {"date": pd.to_datetime(date_str)}
        rec.update(taux_dict)
        records.append(rec)

    df = pd.DataFrame(records).set_index("date")
    full_index = pd.date_range(
        max(pd.to_datetime(start_date), df.index.min()),
        datetime.today(),
        freq="B"
    )
    df = df.reindex(full_index).ffill().rename_axis("date")

    # Calcul spread (signal de forme de courbe)
    df["spread_10y_3m"] = df["bdt_10y"] - df["bdt_3m"]
    df["spread_5y_1y"] = df["bdt_5y"] - df["bdt_1y"]
    df["courbe_forme"] = df["spread_10y_3m"].apply(
        lambda x: "normale" if x > 0.5 else ("inversée" if x < 0 else "plate")
    )

    df.to_csv(cache_file)
    log.info(f"BDT courbe taux : {len(df)} observations, sauvegardée dans {cache_file}")
    return df


# ── 3. MASI / MADEX via Yahoo Finance ──────────────────────────────────────────

def get_masi_madex(start_date: str = "2020-01-01") -> pd.DataFrame:
    """
    Télécharge MASI et MADEX via Yahoo Finance (ou stooq).
    Symboles Yahoo : ^MASI.CS  — Si indisponible, fallback sur stooq.
    """
    log.info("Téléchargement MASI/MADEX...")
    cache_file = CACHE_DIR / "masi_madex.csv"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < 86400:  # Cache valide 24h
            df = pd.read_csv(cache_file, index_col="date", parse_dates=True)
            log.info(f"MASI/MADEX depuis cache : {len(df)} lignes")
            return df

    dfs = []

    for ticker, col in [("^MASI.CS", "masi"), ("^MADEX.CS", "madex")]:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            f"?interval=1d&range=5y"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            timestamps = data["chart"]["result"][0]["timestamp"]
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            df_t = pd.DataFrame({
                "date": pd.to_datetime(timestamps, unit="s").normalize(),
                col: closes
            }).set_index("date")
            dfs.append(df_t)
            log.info(f"{col.upper()} : {len(df_t)} observations téléchargées")
        except Exception as e:
            log.warning(f"Yahoo Finance échec pour {ticker}: {e}")
            log.info(f"Tentative stooq pour {col.upper()}...")
            dfs.append(_get_stooq_index(col))

    if not dfs:
        log.error("Impossible de télécharger MASI/MADEX")
        return pd.DataFrame()

    df = dfs[0].join(dfs[1], how="outer") if len(dfs) > 1 else dfs[0]
    df = df[df.index >= start_date].sort_index()

    # Calcul des rendements et volatilité
    for col in [c for c in df.columns if not c.endswith("_ret") and not c.endswith("_vol")]:
        df[f"{col}_ret"] = df[col].pct_change()
        df[f"{col}_ret_log"] = np.log(df[col] / df[col].shift(1))
        df[f"{col}_vol_20j"] = df[f"{col}_ret"].rolling(20).std() * np.sqrt(252)
        df[f"{col}_sma_50"] = df[col].rolling(50).mean()
        df[f"{col}_sma_200"] = df[col].rolling(200).mean()

    df.to_csv(cache_file)
    return df


def _get_stooq_index(col: str) -> pd.DataFrame:
    """Fallback stooq pour MASI/MADEX."""
    symbol_map = {"masi": "masi.ma", "madex": "madex.ma"}
    symbol = symbol_map.get(col, col)
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        df = pd.read_csv(StringIO(resp.text), parse_dates=["Date"])
        df = df.rename(columns={"Date": "date", "Close": col}).set_index("date")[[col]]
        return df
    except Exception as e:
        log.error(f"stooq échec pour {col}: {e}")
        return pd.DataFrame()


# ── 4. Flux ASFIM ───────────────────────────────────────────────────────────────

def load_asfim_vl(filepath: str | Path) -> pd.DataFrame:
    """
    Charge un fichier ASFIM (Excel ou CSV) exporté depuis asfim.ma.
    Gère automatiquement les en-têtes décalés et les formats communs.

    Colonnes attendues (flexibles) :
        - date / Date / DATE
        - vl / VL / valeur_liquidative / Valeur Liquidative
        - fonds / Fonds / nom_fonds
        - classe / Classe / categorie
    """
    filepath = Path(filepath)
    log.info(f"Chargement ASFIM : {filepath}")

    if not filepath.exists():
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")

    # Lecture brute
    if filepath.suffix.lower() in [".xlsx", ".xls"]:
        df_raw = pd.read_excel(filepath, header=None)
    else:
        df_raw = pd.read_csv(filepath, header=None, sep=None, engine="python")

    # Détection automatique de la ligne d'en-têtes
    header_row = _detect_header_row(df_raw)
    log.info(f"En-tête détecté à la ligne {header_row}")

    if filepath.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(filepath, header=header_row)
    else:
        df = pd.read_csv(filepath, header=header_row, sep=None, engine="python")

    df = _normalize_asfim_columns(df)
    df = df.dropna(subset=["date", "vl"])
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["vl"] = pd.to_numeric(df["vl"], errors="coerce")
    df = df.dropna(subset=["date", "vl"]).sort_values("date")

    log.info(f"ASFIM chargé : {len(df)} lignes, {df['fonds'].nunique()} fonds")
    return df


def _detect_header_row(df_raw: pd.DataFrame) -> int:
    """Détecte la ligne contenant les en-têtes dans un fichier ASFIM brut."""
    keywords = {"date", "vl", "fonds", "valeur", "liquidative", "nom", "classe"}
    for i, row in df_raw.iterrows():
        row_lower = [str(v).lower().strip() for v in row.values]
        if len(keywords & set(row_lower)) >= 2:
            return i
    return 0


def _normalize_asfim_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les noms de colonnes ASFIM vers un format standard."""
    col_map = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if any(k in col_lower for k in ["date", "jour"]):
            col_map[col] = "date"
        elif any(k in col_lower for k in ["vl", "liquidative", "nav"]):
            col_map[col] = "vl"
        elif any(k in col_lower for k in ["fonds", "fund", "nom", "opcvm"]):
            col_map[col] = "fonds"
        elif any(k in col_lower for k in ["classe", "catégor", "categor", "type"]):
            col_map[col] = "classe"
        elif any(k in col_lower for k in ["aum", "actif", "encours"]):
            col_map[col] = "aum"
        elif any(k in col_lower for k in ["souscription", "subscription"]):
            col_map[col] = "souscriptions"
        elif any(k in col_lower for k in ["rachat", "redemption"]):
            col_map[col] = "rachats"

    df = df.rename(columns=col_map)

    # Colonnes obligatoires manquantes
    if "fonds" not in df.columns:
        df["fonds"] = "FONDS_INCONNU"
    if "classe" not in df.columns:
        df["classe"] = "Non classifié"

    return df


# ── 5. Taux de Change et Inflation (World Bank) ─────────────────────────────────

def get_worldbank_macro(
    indicateurs: dict = None,
    pays: str = "MA",
    start_year: int = 2015
) -> pd.DataFrame:
    """
    Télécharge des indicateurs macroéconomiques depuis l'API World Bank.

    Indicateurs par défaut :
        - FP.CPI.TOTL.ZG : Inflation (IPC, %)
        - PA.NUS.FCRF     : Taux de change officiel MAD/USD
        - FM.LBL.BMNY.GD.ZS : Monnaie large M3 (% PIB)
        - NY.GDP.MKTP.KD.ZG  : Croissance PIB réel (%)
    """
    if indicateurs is None:
        indicateurs = {
            "FP.CPI.TOTL.ZG": "inflation_cpi",
            "PA.NUS.FCRF": "taux_change_mad_usd",
            "FM.LBL.BMNY.GD.ZS": "m3_pct_pib",
            "NY.GDP.MKTP.KD.ZG": "croissance_pib",
        }

    log.info(f"Téléchargement World Bank pour {pays}...")
    cache_file = CACHE_DIR / f"worldbank_{pays}.csv"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < 604800:  # Cache valide 7 jours
            return pd.read_csv(cache_file, index_col="date", parse_dates=True)

    all_series = []
    base_url = "https://api.worldbank.org/v2/country/{pays}/indicator/{ind}"

    for indicator_code, col_name in indicateurs.items():
        url = (
            f"https://api.worldbank.org/v2/country/{pays}/indicator/{indicator_code}"
            f"?format=json&per_page=100&mrv=30"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if len(data) < 2 or not data[1]:
                log.warning(f"Pas de données WB pour {indicator_code}")
                continue

            records = [
                {"date": pd.to_datetime(f"{item['date']}-01-01"), col_name: item["value"]}
                for item in data[1]
                if item["value"] is not None and int(item["date"]) >= start_year
            ]
            if records:
                df_ind = pd.DataFrame(records).set_index("date").sort_index()
                all_series.append(df_ind)
                log.info(f"World Bank {col_name} : {len(df_ind)} observations")

        except Exception as e:
            log.warning(f"World Bank échec pour {indicator_code}: {e}")

    if not all_series:
        log.error("Aucune donnée World Bank récupérée")
        return pd.DataFrame()

    df = all_series[0].join(all_series[1:], how="outer").sort_index()

    # Resample annuel → mensuel via interpolation linéaire
    monthly_idx = pd.date_range(df.index.min(), datetime.today(), freq="MS")
    df = df.reindex(df.index.union(monthly_idx)).interpolate(method="time")
    df = df.reindex(monthly_idx)

    # Forward fill en fréquence quotidienne
    daily_idx = pd.date_range(df.index.min(), datetime.today(), freq="B")
    df = df.reindex(df.index.union(daily_idx)).ffill().reindex(daily_idx)
    df.index.name = "date"

    df.to_csv(cache_file)
    log.info(f"World Bank macro sauvegardé : {len(df)} lignes")
    return df


# ── 6. Assemblage Final ─────────────────────────────────────────────────────────

def build_macro_dataset(
    asfim_filepath: str | Path = None,
    start_date: str = "2020-01-01"
) -> pd.DataFrame:
    """
    Assemble toutes les sources macro en un seul DataFrame.
    Prêt à être utilisé comme features pour le modèle de prédiction.

    Paramètres :
        asfim_filepath : chemin vers le fichier Excel/CSV ASFIM (optionnel)
        start_date     : date de début des séries

    Retourne :
        DataFrame avec colonnes :
            taux_directeur_bam, reserves_change_mrd_mad,
            bdt_3m ... bdt_20y, spread_10y_3m, courbe_forme,
            masi, madex, masi_ret, madex_ret, masi_vol_20j,
            inflation_cpi, taux_change_mad_usd, m3_pct_pib, croissance_pib
    """
    log.info("=== Assemblage dataset macro enrichi ===")

    datasets = []

    # BAM
    datasets.append(get_bam_taux_directeur(start_date))
    datasets.append(get_bam_reserves_change())

    # BDT
    datasets.append(get_courbe_taux_bdt(start_date))

    # Bourse
    df_bourse = get_masi_madex(start_date)
    if not df_bourse.empty:
        datasets.append(df_bourse)

    # World Bank
    df_wb = get_worldbank_macro(start_year=int(start_date[:4]))
    if not df_wb.empty:
        datasets.append(df_wb)

    # Merge sur l'index date
    df_final = datasets[0]
    for df in datasets[1:]:
        df_final = df_final.join(df, how="left", rsuffix="_dup")
        # Supprime les colonnes dupliquées éventuelles
        df_final = df_final[[c for c in df_final.columns if not c.endswith("_dup")]]

    df_final = df_final[df_final.index >= start_date].ffill()

    # ASFIM (optionnel — joint si fourni)
    if asfim_filepath:
        df_asfim = load_asfim_vl(asfim_filepath)
        log.info(f"ASFIM intégré : {df_asfim['fonds'].nunique()} fonds disponibles")
        # Note : les VL ASFIM sont jointes par fonds dans le module de prédiction
        df_final.attrs["asfim"] = df_asfim

    output_path = CACHE_DIR / "macro_dataset.csv"
    df_final.to_csv(output_path)
    log.info(f"Dataset macro final : {len(df_final)} lignes × {len(df_final.columns)} colonnes")
    log.info(f"Colonnes : {list(df_final.columns)}")
    log.info(f"Sauvegardé : {output_path}")

    return df_final


# ── Point d'entrée ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="krockOPVM - Collecteur Couche 1")
    parser.add_argument("--asfim", type=str, default=None, help="Chemin fichier ASFIM")
    parser.add_argument("--start", type=str, default="2020-01-01", help="Date de début")
    parser.add_argument("--preview", action="store_true", help="Affiche un aperçu")
    args = parser.parse_args()

    df = build_macro_dataset(asfim_filepath=args.asfim, start_date=args.start)

    if args.preview:
        print("\n📊 Aperçu du dataset macro :")
        print(df.tail(10).to_string())
        print(f"\nShape : {df.shape}")
        print(f"\nValeurs manquantes :\n{df.isnull().sum()[df.isnull().sum() > 0]}")
