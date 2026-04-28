# pip install pandas requests beautifulsoup4 openpyxl numpy
"""
Collecteur de données historiques ASFIM
Télécharge, consolide, valide et interpole les données historiques OPCVM
depuis janvier 2023 jusqu'à aujourd'hui.
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
import time
import numpy as np
import logging

# Configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ASFIM_BASE_URL, HISTORICAL_START_DATE, HISTORICAL_DELAY, FRAIS_OPCVM

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/historical_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HistoricalDataCollector:
    """Collecte et valide les données historiques OPCVM"""
    
    def __init__(self, data_dir="data/raw", processed_dir="data/processed", output_dir="outputs"):
        """
        Initialise le collecteur historique
        
        Args:
            data_dir: Répertoire pour données brutes
            processed_dir: Répertoire pour données traitées
            output_dir: Répertoire pour fichiers de sortie
        """
        self.data_dir = data_dir
        self.historique_dir = os.path.join(data_dir, "historique")
        self.processed_dir = processed_dir
        self.output_dir = output_dir
        
        os.makedirs(self.historique_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Mapping flexible des colonnes (réutilisé de ASFIMCollector)
        self.column_mapping = {
            'nom_fonds': ['nom_fonds', 'Nom Fonds', 'Fonds', 'DESIGNATION', 'Nom', 'OPCVM'],
            'sdg': ['sdg', 'SDG', 'Societe Gestion', 'GESTIONNAIRE', 'Société de Gestion'],
            'classification': ['classification', 'Classification', 'Type', 'Catégorie', 'CATEGORIE'],
            'vl_jour': ['vl_jour', 'VL', 'Valeur Liquidative', 'VL Jour', 'VL_JOUR'],
            'vl_precedente': ['vl_precedente', 'VL N-1', 'VL Précédente', 'VL_PRECEDENTE'],
            'aum': ['aum', 'AUM', 'Encours', 'Actif Net', 'ENCOURS'],
            'flux_souscription': ['flux_souscription', 'Souscription', 'SOUSCRIPTION', 'Flux Souscription'],
            'flux_rachat': ['flux_rachat', 'Rachat', 'RACHAT', 'Flux Rachat']
        }
    
    def get_moroccan_holidays(self, year):
        """
        Retourne la liste des jours fériés marocains pour une année donnée
        
        Args:
            year: Année (int)
            
        Returns:
            list: Liste de datetime des jours fériés
        """
        try:
            holidays = []
            
            # Jours fériés fixes
            from config import JOURS_FERIES_FIXES
            for nom, dates in JOURS_FERIES_FIXES.items():
                for month, day in dates:
                    try:
                        holidays.append(datetime(year, month, day))
                    except:
                        logger.warning(f"Date invalide: {nom} {year}-{month}-{day}")
            
            # Jours fériés variables (estimés pour 2023-2026)
            # Ces dates sont approximatives - à mettre à jour
            variable_holidays = {
                2023: [
                    datetime(2023, 4, 21),  # Aïd Al Fitr (estimé)
                    datetime(2023, 4, 22),  # Aïd Al Fitr jour 2
                    datetime(2023, 6, 28),  # Aïd Al Adha (estimé)
                    datetime(2023, 6, 29),  # Aïd Al Adha jour 2
                    datetime(2023, 7, 19),  # Nouvel An Islamique (estimé)
                ],
                2024: [
                    datetime(2024, 4, 10),  # Aïd Al Fitr
                    datetime(2024, 4, 11),
                    datetime(2024, 6, 16),  # Aïd Al Adha
                    datetime(2024, 6, 17),
                    datetime(2024, 7, 7),   # Nouvel An Islamique
                ],
                2025: [
                    datetime(2025, 3, 30),  # Aïd Al Fitr
                    datetime(2025, 3, 31),
                    datetime(2025, 6, 6),   # Aïd Al Adha
                    datetime(2025, 6, 7),
                    datetime(2025, 6, 26),  # Nouvel An Islamique
                ],
                2026: [
                    datetime(2026, 3, 20),  # Aïd Al Fitr
                    datetime(2026, 3, 21),
                    datetime(2026, 5, 27),  # Aïd Al Adha
                    datetime(2026, 5, 28),
                    datetime(2026, 6, 15),  # Nouvel An Islamique
                ]
            }
            
            if year in variable_holidays:
                holidays.extend(variable_holidays[year])
            
            return holidays
            
        except Exception as e:
            logger.error(f"Erreur calcul jours fériés {year}: {e}")
            return []
    
    def is_trading_day(self, date):
        """
        Vérifie si une date est un jour ouvré boursier marocain
        
        Args:
            date: datetime à vérifier
            
        Returns:
            bool: True si jour de trading
        """
        try:
            # Weekends (samedi=5, dimanche=6)
            if date.weekday() >= 5:
                return False
            
            # Jours fériés
            holidays = self.get_moroccan_holidays(date.year)
            if date in holidays:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur vérification jour ouvré {date}: {e}")
            return True  # Par défaut, on suppose ouvré
    
    def download_single_date(self, date_str):
        """
        Télécharge le fichier ASFIM pour une date spécifique
        
        Args:
            date_str: Date format YYYY-MM-DD
            
        Returns:
            str: Chemin du fichier téléchargé ou None
        """
        try:
            output_path = os.path.join(self.historique_dir, f"ASFIM_{date_str}.xlsx")
            
            # Si fichier existe déjà, skip
            if os.path.exists(output_path):
                logger.info(f"Fichier existe déjà: {date_str}")
                return output_path
            
            # Construction URL (à adapter selon structure réelle ASFIM)
            url = f"{ASFIM_BASE_URL}/exports/{date_str}.xlsx"
            
            logger.info(f"Téléchargement: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Sauvegardé: {output_path}")
                return output_path
            else:
                logger.warning(f"HTTP {response.status_code} pour {date_str}")
                return None
                
        except Exception as e:
            logger.error(f"Erreur téléchargement {date_str}: {e}")
            return None
    
    def scrape_date_range(self, start_date, end_date):
        """
        Télécharge tous les fichiers ASFIM sur une plage de dates
        
        Args:
            start_date: datetime date début
            end_date: datetime date fin
            
        Returns:
            list: Liste des fichiers téléchargés
        """
        logger.info(f"Scraping de {start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}")
        
        downloaded_files = []
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        day_count = 0
        
        while current_date <= end_date:
            day_count += 1
            
            # Uniquement jours ouvrés
            if self.is_trading_day(current_date):
                date_str = current_date.strftime('%Y-%m-%d')
                logger.info(f"Progression: {day_count}/{total_days} - {date_str}")
                
                filepath = self.download_single_date(date_str)
                if filepath:
                    downloaded_files.append(filepath)
                
                # Délai 3 secondes entre requêtes
                time.sleep(HISTORICAL_DELAY)
            
            current_date += timedelta(days=1)
        
        logger.info(f"Téléchargement terminé: {len(downloaded_files)} fichiers")
        return downloaded_files
    
    def parse_file(self, filepath, date_str):
        """
        Parse un fichier ASFIM avec la date associée
        
        Args:
            filepath: Chemin du fichier
            date_str: Date format YYYY-MM-DD
            
        Returns:
            pd.DataFrame: Données parsées
        """
        try:
            if filepath.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            else:
                df = pd.read_csv(filepath, encoding='utf-8')
            
            # Application du mapping flexible
            rename_dict = {}
            for standard_name, possible_names in self.column_mapping.items():
                for col in df.columns:
                    if col.strip() in possible_names:
                        rename_dict[col] = standard_name
                        break
            
            df = df.rename(columns=rename_dict)
            
            # Ajout de la date
            df['date'] = date_str
            
            # Conversion types numériques
            numeric_cols = ['vl_jour', 'vl_precedente', 'aum', 'flux_souscription', 'flux_rachat']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur parsing {filepath}: {e}")
            return pd.DataFrame()
    
    def consolidate_all_files(self):
        """
        Charge et fusionne tous les fichiers téléchargés
        
        Returns:
            pd.DataFrame: Données consolidées
        """
        logger.info("Consolidation de tous les fichiers...")
        
        files = [f for f in os.listdir(self.historique_dir) if f.endswith(('.xlsx', '.xls', '.csv'))]
        logger.info(f"{len(files)} fichiers trouvés")
        
        all_data = []
        
        for filename in files:
            try:
                # Extraction date depuis nom fichier ASFIM_YYYY-MM-DD.xlsx
                date_str = filename.replace('ASFIM_', '').split('.')[0]
                filepath = os.path.join(self.historique_dir, filename)
                
                df = self.parse_file(filepath, date_str)
                if len(df) > 0:
                    all_data.append(df)
                    
            except Exception as e:
                logger.error(f"Erreur consolidation {filename}: {e}")
        
        if len(all_data) == 0:
            logger.warning("Aucune donnée consolidée")
            return pd.DataFrame()
        
        # Concaténation
        df_consolidated = pd.concat(all_data, ignore_index=True)
        
        # Déduplication (même fonds, même date)
        before_dedup = len(df_consolidated)
        df_consolidated = df_consolidated.drop_duplicates(subset=['nom_fonds', 'date'], keep='last')
        after_dedup = len(df_consolidated)
        
        logger.info(f"Déduplication: {before_dedup} -> {after_dedup} lignes")
        
        # Tri chronologique
        df_consolidated = df_consolidated.sort_values(['nom_fonds', 'date']).reset_index(drop=True)
        
        logger.info(f"Données consolidées: {df_consolidated.shape}")
        return df_consolidated
    
    def validate_data_quality(self, df):
        """
        Valide la qualité des données par fonds
        
        Args:
            df: DataFrame consolidé
            
        Returns:
            pd.DataFrame: Rapport de qualité
        """
        logger.info("Validation de la qualité des données...")
        
        quality_report = []
        
        for fonds in df['nom_fonds'].unique():
            df_fonds = df[df['nom_fonds'] == fonds].sort_values('date')
            
            # Métriques
            nb_points = len(df_fonds)
            date_debut = df_fonds['date'].min()
            date_fin = df_fonds['date'].max()
            
            # Calcul jours manquants
            date_range = pd.date_range(start=date_debut, end=date_fin)
            trading_days = sum(1 for d in date_range if self.is_trading_day(d))
            missing_days = trading_days - nb_points
            pct_missing = (missing_days / trading_days * 100) if trading_days > 0 else 0
            
            # Classification
            if nb_points < 60:
                statut = "INSUFFISANT"
            elif nb_points < 500:
                statut = "PROPHET_ONLY"
            else:
                statut = "LSTM_READY"
            
            quality_report.append({
                'nom_fonds': fonds,
                'classification': df_fonds['classification'].iloc[0] if 'classification' in df_fonds.columns else 'Inconnu',
                'nb_points': nb_points,
                'date_debut': date_debut,
                'date_fin': date_fin,
                'trading_days': trading_days,
                'missing_days': missing_days,
                'pct_missing': round(pct_missing, 2),
                'statut': statut
            })
        
        df_quality = pd.DataFrame(quality_report)
        
        # Statistiques globales
        logger.info(f"\nRésumé qualité:")
        logger.info(f"  LSTM_READY: {len(df_quality[df_quality['statut'] == 'LSTM_READY'])} fonds")
        logger.info(f"  PROPHET_ONLY: {len(df_quality[df_quality['statut'] == 'PROPHET_ONLY'])} fonds")
        logger.info(f"  INSUFFISANT: {len(df_quality[df_quality['statut'] == 'INSUFFISANT'])} fonds")
        
        return df_quality
    
    def interpolate_missing_days(self, df):
        """
        Interpole les valeurs manquantes pour jours fériés/weekends
        
        Args:
            df: DataFrame consolidé
            
        Returns:
            pd.DataFrame: Données interpolées
        """
        logger.info("Interpolation des jours manquants...")
        
        df_interpolated = []
        
        for fonds in df['nom_fonds'].unique():
            df_fonds = df[df['nom_fonds'] == fonds].copy()
            df_fonds['date'] = pd.to_datetime(df_fonds['date'])
            df_fonds = df_fonds.sort_values('date')
            df_fonds = df_fonds.set_index('date')
            
            # Résolution quotidienne et interpolation linéaire
            numeric_cols = df_fonds.select_dtypes(include=[np.number]).columns
            df_fonds = df_fonds.resample('D').first()  # Tous les jours
            
            # Interpolation uniquement sur colonnes numériques
            for col in numeric_cols:
                if col in df_fonds.columns:
                    df_fonds[col] = df_fonds[col].interpolate(method='linear')
            
            # Forward fill pour colonnes catégorielles
            categorical_cols = ['nom_fonds', 'sdg', 'classification']
            for col in categorical_cols:
                if col in df_fonds.columns:
                    df_fonds[col] = df_fonds[col].ffill()
            
            df_fonds = df_fonds.reset_index()
            df_interpolated.append(df_fonds)
        
        df_result = pd.concat(df_interpolated, ignore_index=True)
        df_result['date'] = df_result['date'].dt.strftime('%Y-%m-%d')
        
        logger.info(f"Interpolation terminée: {df_result.shape}")
        return df_result
    
    def generate_mock_historical_data(self, start_date='2023-01-01', end_date='2026-04-28'):
        """
        Génère des données historiques réalistes pour démonstration
        
        Args:
            start_date: Date début
            end_date: Date fin
            
        Returns:
            pd.DataFrame: Données historiques simulées
        """
        logger.info("Génération de données historiques mock...")
        
        np.random.seed(42)
        
        sdgs = ["BMCE Capital", "Attijari Intermédiaire", "CDG Capital", "Bank of Africa Capital", "SG Gestion"]
        classifications = list(FRAIS_OPCVM.keys())
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        date_range = pd.date_range(start=start, end=end, freq='B')  # Jours ouvrés
        
        all_data = []
        
        for i in range(50):  # 50 fonds
            nom_fonds = f"Fonds OPCVM {i+1:03d}"
            classification = np.random.choice(classifications)
            sdg = np.random.choice(sdgs)
            vl_base = np.random.uniform(100, 1500)
            
            for date in date_range:
                if self.is_trading_day(date):
                    variation = np.random.uniform(-1.5, 1.5)
                    vl_precedente = vl_base / (1 + variation/100)
                    
                    all_data.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'nom_fonds': nom_fonds,
                        'sdg': sdg,
                        'classification': classification,
                        'vl_jour': round(vl_base, 2),
                        'vl_precedente': round(vl_precedente, 2),
                        'variation_pct': round(variation, 2),
                        'aum': round(np.random.uniform(10_000_000, 500_000_000), 2),
                        'flux_souscription': round(np.random.uniform(0, 5_000_000), 2),
                        'flux_rachat': round(np.random.uniform(0, 5_000_000), 2)
                    })
                    
                    vl_base = vl_base * (1 + np.random.uniform(-0.01, 0.012))
        
        df = pd.DataFrame(all_data)
        logger.info(f"Données mock générées: {df.shape}")
        return df
    
    def run_pipeline(self, start_date=None, end_date=None, use_mock=False):
        """
        Pipeline complet: Scraping → Consolidation → Validation → Interpolation
        
        Args:
            start_date: Date début (défaut: 2023-01-01)
            end_date: Date fin (défaut: aujourd'hui)
            use_mock: Utiliser données mock si True
            
        Returns:
            tuple: (chemin_données, chemin_rapport_qualité)
        """
        logger.info("="*60)
        logger.info("COLLECTEUR DE DONNÉES HISTORIQUES")
        logger.info("="*60)
        
        if start_date is None:
            start_date = pd.to_datetime(HISTORICAL_START_DATE)
        else:
            start_date = pd.to_datetime(start_date)
        
        if end_date is None:
            end_date = pd.to_datetime(datetime.now())
        else:
            end_date = pd.to_datetime(end_date)
        
        if use_mock:
            # Mode mock pour démonstration
            df = self.generate_mock_historical_data(start_date, end_date)
        else:
            # Scraping réel
            downloaded_files = self.scrape_date_range(start_date, end_date)
            
            if len(downloaded_files) == 0:
                logger.warning("Aucun fichier téléchargé, utilisation mode mock")
                df = self.generate_mock_historical_data(start_date, end_date)
            else:
                df = self.consolidate_all_files()
        
        if len(df) == 0:
            logger.error("Aucune donnée disponible")
            return None, None
        
        # Validation qualité
        df_quality = self.validate_data_quality(df)
        quality_path = os.path.join(self.output_dir, "data_quality_report.csv")
        df_quality.to_csv(quality_path, index=False, encoding='utf-8')
        logger.info(f"Rapport qualité sauvegardé: {quality_path}")
        
        # Interpolation
        df_interpolated = self.interpolate_missing_days(df)
        
        # Sauvegarde finale
        output_path = os.path.join(self.processed_dir, "opcvm_historique_complet.csv")
        df_interpolated.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Données historiques sauvegardées: {output_path}")
        logger.info(f"Total: {len(df_interpolated)} lignes, {df_interpolated['nom_fonds'].nunique()} fonds")
        
        return output_path, quality_path


if __name__ == "__main__":
    collector = HistoricalDataCollector()
    # Mode mock pour démonstration rapide
    data_path, quality_path = collector.run_pipeline(use_mock=True)
    print(f"\nDonnées: {data_path}")
    print(f"Qualité: {quality_path}")
