# pip install pandas numpy
"""
Calculateur de seuils dynamiques basé sur les frais réels OPCVM
Remplace le seuil fixe ±0.5% par des seuils adaptés aux frais AMMC
pour chaque classification de fonds.
"""

import pandas as pd
import numpy as np
import os
import logging

# Configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FRAIS_OPCVM, MARGE_SECURITE

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DynamicThresholdCalculator:
    """Calcule les seuils de rentabilité dynamiques par fonds"""
    
    def __init__(self):
        """Initialise le calculateur avec les frais OPCVM"""
        self.frais_db = FRAIS_OPCVM
        self.marge_securite = MARGE_SECURITE
    
    def get_frais_for_classification(self, classification):
        """
        Récupère les frais pour une classification donnée
        
        Args:
            classification: Classification du fonds (ex: 'Actions', 'Obligataire')
            
        Returns:
            dict: {'souscription': X, 'rachat': Y, 'delai_liquidite': Z}
        """
        try:
            # Recherche exacte
            if classification in self.frais_db:
                return self.frais_db[classification]
            
            # Recherche partielle (ex: "Obligataire LT" -> "Obligataire")
            for key in self.frais_db:
                if key.lower() in classification.lower() or classification.lower() in key.lower():
                    logger.info(f"Classification '{classification}' mappée à '{key}'")
                    return self.frais_db[key]
            
            # Valeurs par défaut si non trouvé
            logger.warning(f"Classification '{classification}' non trouvée, utilisation valeurs par défaut")
            return {'souscription': 1.5, 'rachat': 0.8, 'delai_liquidite': 3}
            
        except Exception as e:
            logger.error(f"Erreur récupération frais pour {classification}: {e}")
            return {'souscription': 1.5, 'rachat': 0.8, 'delai_liquidite': 3}
    
    def calculate_thresholds(self, classification):
        """
        Calcule les seuils d'achat et de vente pour une classification
        
        Args:
            classification: Classification du fonds
            
        Returns:
            dict: {
                'seuil_achat': X%,
                'seuil_vente': -X%,
                'frais_total': Y%,
                'delai_liquidite': Z jours
            }
        """
        try:
            frais = self.get_frais_for_classification(classification)
            
            frais_souscription = frais['souscription']
            frais_rachat = frais['rachat']
            delai_liquidite = frais['delai_liquidite']
            
            # Calcul des seuils
            frais_total = frais_souscription + frais_rachat
            seuil_achat = frais_total + self.marge_securite
            seuil_vente = -(frais_total + self.marge_securite)
            
            return {
                'seuil_achat': round(seuil_achat, 2),
                'seuil_vente': round(seuil_vente, 2),
                'frais_souscription': frais_souscription,
                'frais_rachat': frais_rachat,
                'frais_total': round(frais_total, 2),
                'delai_liquidite': delai_liquidite
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul seuils pour {classification}: {e}")
            return {
                'seuil_achat': 3.0,
                'seuil_vente': -3.0,
                'frais_souscription': 1.5,
                'frais_rachat': 0.8,
                'frais_total': 2.3,
                'delai_liquidite': 3
            }
    
    def determine_confidence_level(self, variation_pct, seuil_achat):
        """
        Détermine le niveau de confiance du signal
        
        Args:
            variation_pct: Variation prédite (%)
            seuil_achat: Seuil d'achat (%)
            
        Returns:
            str: 'FORTE', 'MODEREE', ou 'FAIBLE'
        """
        try:
            ratio = abs(variation_pct) / seuil_achat
            
            if ratio > 2.0:
                return 'FORTE'
            elif ratio >= 1.0:
                return 'MODEREE'
            else:
                return 'FAIBLE'
                
        except Exception as e:
            logger.error(f"Erreur calcul confiance: {e}")
            return 'FAIBLE'
    
    def generate_enriched_signals(self, df_predictions, df_fonds_data):
        """
        Génère des signaux enrichis avec seuils dynamiques
        
        Args:
            df_predictions: DataFrame avec predictions
                Colonnes requises: nom_fonds, vl_actuelle, vl_predite, variation_pct
            df_fonds_data: DataFrame avec données fonds
                Colonnes requises: nom_fonds, classification
            
        Returns:
            pd.DataFrame: Signaux enrichis
        """
        logger.info(f"Génération de signaux enrichis pour {len(df_predictions)} fonds...")
        
        signals_enriched = []
        
        for idx, row in df_predictions.iterrows():
            try:
                nom_fonds = row['nom_fonds']
                vl_actuelle = row['vl_actuelle']
                vl_predite = row['vl_predite']
                variation_pct = row['variation_pct']
                
                # Récupération classification
                fonds_info = df_fonds_data[df_fonds_data['nom_fonds'] == nom_fonds]
                if len(fonds_info) > 0:
                    classification = fonds_info.iloc[0].get('classification', 'Diversifié')
                else:
                    classification = 'Diversifié'
                
                # Calcul seuils dynamiques
                thresholds = self.calculate_thresholds(classification)
                seuil_achat = thresholds['seuil_achat']
                seuil_vente = thresholds['seuil_vente']
                frais_total = thresholds['frais_total']
                
                # Détermination du signal
                if variation_pct > seuil_achat:
                    signal = 'ACHETER'
                elif variation_pct < seuil_vente:
                    signal = 'VENDRE'
                else:
                    signal = 'ATTENDRE'
                
                # Niveau de confiance
                confiance = self.determine_confidence_level(variation_pct, seuil_achat)
                
                # Gain net estimé (après frais)
                gain_net_estime = variation_pct - frais_total
                
                # Rentabilité
                rentable = gain_net_estime > 0
                
                signals_enriched.append({
                    'nom_fonds': nom_fonds,
                    'classification': classification,
                    'vl_actuelle': round(vl_actuelle, 2),
                    'vl_predite': round(vl_predite, 2),
                    'variation_pct': round(variation_pct, 3),
                    'signal': signal,
                    'confiance': confiance,
                    'gain_net_estime': round(gain_net_estime, 3),
                    'rentable': rentable,
                    'seuil_utilise': seuil_achat if signal == 'ACHETER' else abs(seuil_vente),
                    'frais_total': frais_total,
                    'delai_liquidite': thresholds['delai_liquidite']
                })
                
            except Exception as e:
                logger.error(f"Erreur génération signal pour {row.get('nom_fonds', 'inconnu')}: {e}")
                continue
        
        df_signals = pd.DataFrame(signals_enriched)
        
        # Statistiques
        if len(df_signals) > 0:
            logger.info(f"\nSignaux enrichis générés:")
            logger.info(f"  ACHETER: {len(df_signals[df_signals['signal'] == 'ACHETER'])}")
            logger.info(f"  VENDRE: {len(df_signals[df_signals['signal'] == 'VENDRE'])}")
            logger.info(f"  ATTENDRE: {len(df_signals[df_signals['signal'] == 'ATTENDRE'])}")
            logger.info(f"  Rentables: {len(df_signals[df_signals['rentable'] == True])}")
            logger.info(f"  Confiance FORTE: {len(df_signals[df_signals['confiance'] == 'FORTE'])}")
        
        return df_signals
    
    def apply_to_signals_csv(self, signals_path, opcvm_data_path, output_path=None):
        """
        Applique les seuils dynamiques à un fichier signals_today.csv existant
        
        Args:
            signals_path: Chemin vers signals_today.csv
            opcvm_data_path: Chemin vers opcvm_data.csv (pour classifications)
            output_path: Chemin de sortie (défaut: remplace signals_path)
            
        Returns:
            pd.DataFrame: Signaux enrichis
        """
        try:
            # Chargement des données
            df_signals = pd.read_csv(signals_path)
            df_fonds = pd.read_csv(opcvm_data_path)
            
            logger.info(f"Signaux chargés: {len(df_signals)}")
            logger.info(f"Fonds chargés: {len(df_fonds)}")
            
            # Conversion variation_pct en float si nécessaire
            if 'variation_pct' in df_signals.columns:
                df_signals['variation_pct'] = pd.to_numeric(df_signals['variation_pct'], errors='coerce')
            
            # Génération signaux enrichis
            df_enriched = self.generate_enriched_signals(df_signals, df_fonds)
            
            # Sauvegarde
            if output_path is None:
                output_path = signals_path
            
            df_enriched.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"Signaux enrichis sauvegardés: {output_path}")
            
            return df_enriched
            
        except Exception as e:
            logger.error(f"Erreur application seuils dynamiques: {e}")
            return pd.DataFrame()


def integrate_with_lstm_model():
    """
    Fonction d'intégration avec le modèle LSTM
    À appeler depuis src/lstm_model.py pour remplacer generate_signals()
    """
    from lstm_model import OPCVMLSTMModel
    
    # Sauvegarde de l'ancienne méthode
    original_generate_signals = OPCVMLSTMModel.generate_signals
    
    def new_generate_signals(self, y_pred, y_test, fonds_list, df_fonds_data=None):
        """Nouvelle méthode avec seuils dynamiques"""
        logger.info("Utilisation des seuils dynamiques...")
        
        # Création DataFrame predictions
        df_predictions = pd.DataFrame({
            'nom_fonds': fonds_list,
            'vl_actuelle': y_test,
            'vl_predite': y_pred,
            'variation_pct': ((y_pred - y_test) / y_test) * 100
        })
        
        # Si pas de données fonds, utilisation DataFrame vide
        if df_fonds_data is None:
            df_fonds_data = pd.DataFrame({'nom_fonds': fonds_list, 'classification': 'Diversifié'})
        
        # Calcul seuils dynamiques
        calculator = DynamicThresholdCalculator()
        df_signals = calculator.generate_enriched_signals(df_predictions, df_fonds_data)
        
        return df_signals
    
    # Remplacement de la méthode
    OPCVMLSTMModel.generate_signals = new_generate_signals
    logger.info("Méthode generate_signals remplacée avec succès")


if __name__ == "__main__":
    # Test du calculateur
    calculator = DynamicThresholdCalculator()
    
    # Test sur différentes classifications
    classifications = ['Actions', 'Obligataire', 'Monétaire', 'Diversifié']
    
    print("="*60)
    print("TEST SEUILS DYNAMIQUES PAR CLASSIFICATION")
    print("="*60)
    
    for classification in classifications:
        thresholds = calculator.calculate_thresholds(classification)
        print(f"\n{classification}:")
        print(f"  Seuil achat: {thresholds['seuil_achat']}%")
        print(f"  Seuil vente: {thresholds['seuil_vente']}%")
        print(f"  Frais totaux: {thresholds['frais_total']}%")
        print(f"  Délai liquidité: {thresholds['delai_liquidite']} jours")
    
    # Test génération signaux enrichis
    print("\n" + "="*60)
    print("TEST SIGNAUX ENRICHIS")
    print("="*60)
    
    df_predictions = pd.DataFrame([
        {'nom_fonds': 'Fonds A', 'vl_actuelle': 1000, 'vl_predite': 1040, 'variation_pct': 4.0},
        {'nom_fonds': 'Fonds B', 'vl_actuelle': 1000, 'vl_predite': 1015, 'variation_pct': 1.5},
        {'nom_fonds': 'Fonds C', 'vl_actuelle': 1000, 'vl_predite': 990, 'variation_pct': -1.0},
    ])
    
    df_fonds = pd.DataFrame([
        {'nom_fonds': 'Fonds A', 'classification': 'Actions'},
        {'nom_fonds': 'Fonds B', 'classification': 'Obligataire'},
        {'nom_fonds': 'Fonds C', 'classification': 'Monétaire'},
    ])
    
    df_signals = calculator.generate_enriched_signals(df_predictions, df_fonds)
    print("\nSignaux enrichis:")
    print(df_signals.to_string(index=False))
