# pip install pandas numpy matplotlib scikit-learn
"""
Système de backtesting walk-forward pour OPCVM Maroc
Évalue la fiabilité du modèle avant déploiement en production.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime
import logging
from sklearn.metrics import mean_absolute_error

# Configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FRAIS_OPCVM, MARGE_SECURITE, LSTM_CONFIG

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backtester.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Backtester:
    """Backtesting walk-forward validation pour modèles OPCVM"""
    
    def __init__(self, output_dir="outputs"):
        """
        Initialise le backtester
        
        Args:
            output_dir: Répertoire pour fichiers de sortie
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Résultats du backtest
        self.results = pd.DataFrame()
        self.metrics = {}
    
    def load_historical_data(self, data_path):
        """
        Charge les données historiques complètes
        
        Args:
            data_path: Chemin vers opcvm_historique_complet.csv
            
        Returns:
            pd.DataFrame: Données historiques
        """
        logger.info(f"Chargement données historiques: {data_path}")
        
        try:
            df = pd.read_csv(data_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(['nom_fonds', 'date']).reset_index(drop=True)
            
            logger.info(f"Données chargées: {df.shape[0]} lignes, {df['nom_fonds'].nunique()} fonds")
            logger.info(f"Période: {df['date'].min().strftime('%Y-%m-%d')} à {df['date'].max().strftime('%Y-%m-%d')}")
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur chargement données: {e}")
            return pd.DataFrame()
    
    def walk_forward_validation(self, df, window_size=500, step_size=1):
        """
        Validation walk-forward sans look-ahead bias
        
        Pour chaque jour J:
        - Entraîne sur [J-window_size, J-1]
        - Prédit J
        - Compare avec réel J
        
        Args:
            df: DataFrame historique complet
            window_size: Taille fenêtre d'entraînement (défaut: 500)
            step_size: Pas d'avancement (défaut: 1 jour)
            
        Returns:
            pd.DataFrame: Résultats détaillés par prédiction
        """
        logger.info(f"Walk-forward validation: window={window_size}, step={step_size}")
        
        all_results = []
        fonds_list = df['nom_fonds'].unique()
        
        for fonds in fonds_list:
            df_fonds = df[df['nom_fonds'] == fonds].sort_values('date').reset_index(drop=True)
            
            if len(df_fonds) < window_size + 10:
                logger.warning(f"{fonds}: données insuffisantes ({len(df_fonds)} < {window_size})")
                continue
            
            # Classification du fonds
            classification = df_fonds['classification'].iloc[0]
            frais = self.get_frais_for_classification(classification)
            
            # Walk-forward
            for start_idx in range(window_size, len(df_fonds) - 1, step_size):
                try:
                    # Données d'entraînement (J-window_size à J-1)
                    train_data = df_fonds.iloc[start_idx-window_size:start_idx]
                    
                    # Jour à prédire (J)
                    test_day = df_fonds.iloc[start_idx]
                    
                    # Simulation prédiction naive (moyenne mobile)
                    # Dans production: remplacer par modèle LSTM réel
                    vl_moyenne = train_data['vl_jour'].mean()
                    vl_derniere = train_data['vl_jour'].iloc[-1]
                    vl_predite = (vl_moyenne + vl_derniere) / 2
                    
                    # VL réelle
                    vl_reelle = test_day['vl_jour']
                    
                    # Variation prédite et réelle
                    variation_predite = ((vl_predite - vl_derniere) / vl_derniere) * 100
                    variation_reelle = ((vl_reelle - vl_derniere) / vl_derniere) * 100
                    
                    # Signal basé sur seuils dynamiques
                    seuil_achat = frais['souscription'] + frais['rachat'] + MARGE_SECURITE
                    seuil_vente = -seuil_achat
                    
                    if variation_predite > seuil_achat:
                        signal = 'ACHETER'
                    elif variation_predite < seuil_vente:
                        signal = 'VENDRE'
                    else:
                        signal = 'ATTENDRE'
                    
                    # Vérification si signal correct
                    signal_correct = False
                    if signal == 'ACHETER' and variation_reelle > 0:
                        signal_correct = True
                    elif signal == 'VENDRE' and variation_reelle < 0:
                        signal_correct = True
                    elif signal == 'ATTENDRE':
                        signal_correct = True  # Neutre
                    
                    # Gain/perte net (après frais)
                    if signal in ['ACHETER', 'VENDRE']:
                        gain_net = variation_reelle - (frais['souscription'] + frais['rachat'])
                    else:
                        gain_net = 0.0
                    
                    all_results.append({
                        'date': test_day['date'],
                        'nom_fonds': fonds,
                        'classification': classification,
                        'vl_reelle': vl_reelle,
                        'vl_predite': vl_predite,
                        'variation_reelle': variation_reelle,
                        'variation_predite': variation_predite,
                        'signal': signal,
                        'signal_correct': signal_correct,
                        'gain_net': gain_net,
                        'frais_total': frais['souscription'] + frais['rachat']
                    })
                    
                except Exception as e:
                    logger.error(f"Erreur walk-forward {fonds} idx {start_idx}: {e}")
                    continue
        
        df_results = pd.DataFrame(all_results)
        logger.info(f"Walk-forward terminé: {len(df_results)} prédictions")
        
        return df_results
    
    def calculate_metrics(self, df_results):
        """
        Calcule les métriques de performance
        
        Args:
            df_results: Résultats du walk-forward
            
        Returns:
            dict: Métriques globales et par fonds
        """
        logger.info("Calcul des métriques de performance...")
        
        metrics = {}
        
        # Métriques globales
        if len(df_results) == 0:
            logger.warning("Aucun résultat pour calcul métriques")
            return {}
        
        df_acheter = df_results[df_results['signal'] == 'ACHETER']
        df_vendre = df_results[df_results['signal'] == 'VENDRE']
        
        # Précision achat
        if len(df_acheter) > 0:
            precision_achat = df_acheter['signal_correct'].mean() * 100
        else:
            precision_achat = 0.0
        
        # Précision vente
        if len(df_vendre) > 0:
            precision_vente = df_vendre['signal_correct'].mean() * 100
        else:
            precision_vente = 0.0
        
        # Gain moyen par signal
        signaux_actifs = df_results[df_results['signal'].isin(['ACHETER', 'VENDRE'])]
        if len(signaux_actifs) > 0:
            gain_moyen = signaux_actifs['gain_net'].mean()
        else:
            gain_moyen = 0.0
        
        # Taux signal rentable
        if len(signaux_actifs) > 0:
            taux_rentable = (signaux_actifs['gain_net'] > 0).mean() * 100
        else:
            taux_rentable = 0.0
        
        # Sharpe Ratio (annualisé)
        if len(signaux_actifs) > 0 and signaux_actifs['gain_net'].std() > 0:
            rendement_moyen = signaux_actifs['gain_net'].mean()
            volatilite = signaux_actifs['gain_net'].std()
            sharpe_ratio = (rendement_moyen / volatilite) * np.sqrt(252)  # Annualisation
        else:
            sharpe_ratio = 0.0
        
        # Max Drawdown
        max_drawdown = self.calculate_max_drawdown(df_results)
        
        metrics = {
            'precision_achat': round(precision_achat, 2),
            'precision_vente': round(precision_vente, 2),
            'gain_moyen_par_signal': round(gain_moyen, 4),
            'taux_signal_rentable': round(taux_rentable, 2),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'max_drawdown': round(max_drawdown, 4),
            'total_signaux': len(df_results),
            'signaux_acheter': len(df_acheter),
            'signaux_vendre': len(df_vendre),
            'signaux_attendre': len(df_results[df_results['signal'] == 'ATTENDRE'])
        }
        
        # Métriques par classification
        metrics_par_classification = {}
        for classification in df_results['classification'].unique():
            df_class = df_results[df_results['classification'] == classification]
            
            if len(df_class) > 0:
                metrics_par_classification[classification] = {
                    'precision_achat': round(df_class[df_class['signal'] == 'ACHETER']['signal_correct'].mean() * 100, 2) if len(df_class[df_class['signal'] == 'ACHETER']) > 0 else 0,
                    'gain_moyen': round(df_class[df_class['signal'].isin(['ACHETER', 'VENDRE'])]['gain_net'].mean(), 4),
                    'nb_signaux': len(df_class)
                }
        
        metrics['par_classification'] = metrics_par_classification
        
        logger.info(f"Métriques calculées:")
        logger.info(f"  Précision achat: {metrics['precision_achat']}%")
        logger.info(f"  Gain moyen: {metrics['gain_moyen_par_signal']}%")
        logger.info(f"  Sharpe ratio: {metrics['sharpe_ratio']}")
        logger.info(f"  Max drawdown: {metrics['max_drawdown']}%")
        
        self.metrics = metrics
        return metrics
    
    def calculate_max_drawdown(self, df_results):
        """
        Calcule le drawdown maximum
        
        Args:
            df_results: Résultats du walk-forward
            
        Returns:
            float: Max drawdown en %
        """
        try:
            # Courbe de capital cumulative
            gains = df_results['gain_net'].values
            capital_curve = np.cumsum(gains)
            
            # Peak trailing
            peak = np.maximum.accumulate(capital_curve)
            drawdown = (capital_curve - peak) / peak
            
            return drawdown.min() * 100  # En pourcentage
            
        except Exception as e:
            logger.error(f"Erreur calcul max drawdown: {e}")
            return 0.0
    
    def simulate_capital_curve(self, df_results, capital_initial=1000):
        """
        Simule l'évolution du capital
        
        Args:
            df_results: Résultats du walk-forward
            capital_initial: Capital de départ (MAD)
            
        Returns:
            pd.DataFrame: Courbe de capital
        """
        logger.info(f"Simulation courbe de capital (initial: {capital_initial} MAD)")
        
        capital = capital_initial
        capital_curve = [{'date': df_results['date'].min(), 'capital': capital}]
        
        for _, row in df_results.iterrows():
            if row['signal'] in ['ACHETER', 'VENDRE']:
                # Application gain/perte
                capital = capital * (1 + row['gain_net'] / 100)
            
            capital_curve.append({
                'date': row['date'],
                'capital': capital
            })
        
        return pd.DataFrame(capital_curve)
    
    def generate_visual_report(self, df_results, metrics, capital_curve):
        """
        Génère le rapport visuel avec 4 graphiques
        
        Args:
            df_results: Résultats du walk-forward
            metrics: Métriques de performance
            capital_curve: Courbe de capital
        """
        logger.info("Génération du rapport visuel...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Rapport de Backtesting - OPCVM Maroc', fontsize=16, fontweight='bold')
        
        # Graphique 1: Courbe de capital
        ax1 = axes[0, 0]
        ax1.plot(capital_curve['date'], capital_curve['capital'], linewidth=2, color='blue')
        ax1.set_title('Courbe de Capital Simulée', fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Capital (MAD)')
        ax1.grid(True, alpha=0.3)
        
        # Graphique 2: Précision par mois
        ax2 = axes[0, 1]
        df_results_copy = df_results.copy()
        df_results_copy['mois'] = df_results_copy['date'].dt.to_period('M')
        
        monthly_accuracy = df_results_copy.groupby('mois')['signal_correct'].mean() * 100
        ax2.bar(range(len(monthly_accuracy)), monthly_accuracy.values, color='steelblue', alpha=0.7)
        ax2.set_xticks(range(len(monthly_accuracy)))
        ax2.set_xticklabels([str(m)[:7] for m in monthly_accuracy.index], rotation=45, ha='right')
        ax2.set_title('Précision des Signaux par Mois', fontweight='bold')
        ax2.set_ylabel('Précision (%)')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Graphique 3: Distribution gains/pertes
        ax3 = axes[1, 0]
        signaux_actifs = df_results[df_results['signal'].isin(['ACHETER', 'VENDRE'])]
        ax3.hist(signaux_actifs['gain_net'], bins=50, color='green', alpha=0.7, edgecolor='black')
        ax3.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax3.set_title('Distribution des Gains/Pertes par Signal', fontweight='bold')
        ax3.set_xlabel('Gain Net (%)')
        ax3.set_ylabel('Fréquence')
        ax3.grid(True, alpha=0.3)
        
        # Graphique 4: Performance par classification
        ax4 = axes[1, 1]
        if 'par_classification' in metrics:
            classifications = list(metrics['par_classification'].keys())
            gains = [metrics['par_classification'][c]['gain_moyen'] for c in classifications]
            
            colors = ['green' if g > 0 else 'red' for g in gains]
            ax4.bar(classifications, gains, color=colors, alpha=0.7, edgecolor='black')
            ax4.set_title('Gain Moyen par Classification', fontweight='bold')
            ax4.set_xlabel('Classification')
            ax4.set_ylabel('Gain Moyen (%)')
            ax4.tick_params(axis='x', rotation=45)
            ax4.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Sauvegarde
        output_path = os.path.join(self.output_dir, "backtest_report.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Rapport visuel sauvegardé: {output_path}")
    
    def make_deployment_decision(self, metrics):
        """
        Prend une décision automatique de déploiement
        
        Args:
            metrics: Métriques de performance
            
        Returns:
            str: Décision et recommandation
        """
        precision_achat = metrics.get('precision_achat', 0)
        gain_moyen = metrics.get('gain_moyen_par_signal', 0)
        
        decision = ""
        recommendation = ""
        
        if precision_achat > 60 and gain_moyen > 0:
            decision = "DEPLOIEMENT RECOMMANDE"
            recommendation = "Le modèle est fiable et peut être déployé en production"
        elif precision_achat >= 50:
            decision = "MODELE MOYEN"
            recommendation = "Utiliser avec prudence - monitoring renforcé recommandé"
        else:
            decision = "MODELE NON FIABLE"
            recommendation = "Ne pas déployer - réentraîner le modèle avec plus de données"
        
        logger.info(f"\n{'='*60}")
        logger.info(f"DÉCISION DE DÉPLOIEMENT")
        logger.info(f"{'='*60}")
        logger.info(f"Décision: {decision}")
        logger.info(f"Précision achat: {precision_achat}%")
        logger.info(f"Gain moyen: {gain_moyen}%")
        logger.info(f"Recommandation: {recommendation}")
        
        return {
            'decision': decision,
            'precision_achat': precision_achat,
            'gain_moyen': gain_moyen,
            'recommendation': recommendation
        }
    
    def get_frais_for_classification(self, classification):
        """
        Récupère les frais pour une classification
        
        Args:
            classification: Classification du fonds
            
        Returns:
            dict: Frais OPCVM
        """
        for key in FRAIS_OPCVM:
            if key.lower() in classification.lower() or classification.lower() in key.lower():
                return FRAIS_OPCVM[key]
        
        return FRAIS_OPCVM['Diversifié']
    
    def run_backtest(self, data_path, window_size=500):
        """
        Pipeline complet de backtesting
        
        Args:
            data_path: Chemin vers opcvm_historique_complet.csv
            window_size: Taille fenêtre d'entraînement
            
        Returns:
            dict: Décision de déploiement et métriques
        """
        logger.info("="*60)
        logger.info("BACKTESTING WALK-FORWARD")
        logger.info("="*60)
        
        # Étape 1: Chargement données
        df = self.load_historical_data(data_path)
        
        if len(df) == 0:
            logger.error("Aucune donnée disponible pour backtest")
            return None
        
        # Étape 2: Walk-forward validation
        df_results = self.walk_forward_validation(df, window_size=window_size)
        
        if len(df_results) == 0:
            logger.error("Walk-forward n'a généré aucun résultat")
            return None
        
        # Étape 3: Calcul métriques
        metrics = self.calculate_metrics(df_results)
        
        # Étape 4: Simulation courbe de capital
        capital_curve = self.simulate_capital_curve(df_results)
        
        # Étape 5: Rapport visuel
        self.generate_visual_report(df_results, metrics, capital_curve)
        
        # Étape 6: Décision de déploiement
        decision = self.make_deployment_decision(metrics)
        
        # Sauvegarde résultats
        results_path = os.path.join(self.output_dir, "backtest_results.csv")
        df_results.to_csv(results_path, index=False, encoding='utf-8')
        logger.info(f"\nRésultats sauvegardés: {results_path}")
        
        return {
            'decision': decision,
            'metrics': metrics,
            'results_path': results_path
        }


if __name__ == "__main__":
    backtester = Backtester()
    
    # Test avec données mock si fichier historique n'existe pas
    data_path = "data/processed/opcvm_historique_complet.csv"
    
    if not os.path.exists(data_path):
        logger.warning("Fichier historique non trouvé, utilisation données mock")
        # Génération données mock
        from historical_collector import HistoricalDataCollector
        collector = HistoricalDataCollector()
        data_path, _ = collector.run_pipeline(use_mock=True)
    
    if data_path:
        result = backtester.run_backtest(data_path, window_size=100)  # Window réduite pour démo
        print(f"\nDécision: {result['decision']}")
