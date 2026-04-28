# pip install pandas argparse
"""
Orchestrateur principal - OPCVM Analytics Maroc
Exécute le pipeline complet dans l'ordre:
1. Collecte données historiques (optionnel)
2. Collecte données ASFIM & Maroclear
3. Analyse sentiment actualités
4. Backtesting (optionnel)
5. Entraînement modèle LSTM + signaux
6. Envoi rapport Telegram (optionnel)
"""

import os
import sys
import argparse
from datetime import datetime

# Ajout du chemin racine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.asfim_maroclear_collector import ASFIMCollector
from src.news_sentiment_pipeline import NewsSentimentPipeline
from src.lstm_model import OPCVMLSTMModel
from src.telegram_bot import TelegramOPCVMBot
from src.historical_collector import HistoricalDataCollector
from src.dynamic_thresholds import DynamicThresholdCalculator
from src.backtester import Backtester


def main():
    """Exécution du pipeline complet"""
    
    # Parse arguments CLI
    parser = argparse.ArgumentParser(description='OPCVM Analytics Maroc - Pipeline Complet')
    parser.add_argument('--backtest', action='store_true', help='Lancer le backtesting avant déploiement')
    parser.add_argument('--historical', action='store_true', help='Collecter les données historiques')
    parser.add_argument('--mock', action='store_true', help='Utiliser des données mock')
    parser.add_argument('--telegram', action='store_true', help='Envoyer le rapport Telegram')
    args = parser.parse_args()
    
    print("="*60)
    print(" OPCVM Analytics Maroc - Pipeline Complet")
    print("="*60)
    print(f"Date d'exécution: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Vérification des dépendances
    print("Vérification des modules...")
    try:
        import pandas
        import numpy
        print("OK: pandas, numpy")
    except ImportError as e:
        print(f"Erreur: {e}")
        print("Installez les dépendances: pip install -r requirements.txt")
        return
    
    try:
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # ==========================================
        # ÉTAPE 0: Collecte données historiques (optionnel)
        # ==========================================
        if args.historical:
            print("\n" + "="*60)
            print("[0/6] COLLECTE DONNÉES HISTORIQUES")
            print("="*60)
            
            try:
                hist_collector = HistoricalDataCollector(output_dir=output_dir)
                hist_data_path, quality_path = hist_collector.run_pipeline(use_mock=args.mock)
                
                if hist_data_path:
                    print(f"\nDonnées historiques: {hist_data_path}")
                    print(f"Rapport qualité: {quality_path}")
                else:
                    print("\nErreur collecte historique")
                    
            except Exception as e:
                print(f"\nErreur étape 0: {e}")
        
        # ==========================================
        # ÉTAPE 1: Collecte données ASFIM/Maroclear
        # ==========================================
        print("\n" + "="*60)
        print("[1/4] COLLECTE DONNÉES ASFIM & MAROCLEAR")
        print("="*60)
        
        try:
            collector = ASFIMCollector(output_dir=output_dir)
            opcvm_data_path = collector.run_pipeline()
            print(f"\nÉtape 1 terminée: {opcvm_data_path}")
        except Exception as e:
            print(f"\nErreur étape 1: {e}")
            print("Continuation avec données mock...")
            opcvm_data_path = os.path.join(output_dir, "opcvm_data.csv")
            # Création d'un fichier minimal
            import pandas as pd
            df_mock = pd.DataFrame([{
                'date': datetime.now().strftime('%Y-%m-%d'),
                'nom_fonds': 'Fonds Démo',
                'sdg': 'Démo SDG',
                'classification': 'Diversifié',
                'vl_jour': 1000.0,
                'vl_precedente': 995.0,
                'variation_pct': 0.5,
                'aum': 100_000_000,
                'flux_souscription': 1_000_000,
                'flux_rachat': 500_000,
                'flux_net': 500_000,
                'taux_moyen_coupon': 3.5,
                'nb_isin_obligataires': 20
            }])
            df_mock.to_csv(opcvm_data_path, index=False)
        
        # ==========================================
        # ÉTAPE 2: Analyse sentiment actualités
        # ==========================================
        print("\n" + "="*60)
        print("[2/6] ANALYSE SENTIMENT SPÉCIALISÉ")
        print("="*60)
        
        try:
            sentiment_pipeline = NewsSentimentPipeline(output_dir=output_dir)
            opcvm_enriched_path = sentiment_pipeline.run_pipeline(opcvm_data_path)
            print(f"\nÉtape 2 terminée: {opcvm_enriched_path}")
        except ImportError as e:
            print(f"\nModule manquant: {e}")
            print("Installation: pip install torch transformers")
            print("Continuation avec sentiment par défaut...")
            import pandas as pd
            df = pd.read_csv(opcvm_data_path)
            df['score_sentiment_moyen_jour'] = 0.0
            df['nb_actus_jour'] = 0
            df['sources_actus'] = ''
            opcvm_enriched_path = os.path.join(output_dir, "opcvm_enriched.csv")
            df.to_csv(opcvm_enriched_path, index=False)
        except Exception as e:
            print(f"\nErreur étape 2: {e}")
            print("Continuation avec sentiment par défaut...")
            import pandas as pd
            df = pd.read_csv(opcvm_data_path)
            df['score_sentiment_moyen_jour'] = 0.0
            df['nb_actus_jour'] = 0
            df['sources_actus'] = ''
            opcvm_enriched_path = os.path.join(output_dir, "opcvm_enriched.csv")
            df.to_csv(opcvm_enriched_path, index=False)
        
        # ==========================================
        # ÉTAPE 3: Backtesting (optionnel)
        # ==========================================
        if args.backtest:
            print("\n" + "="*60)
            print("[3/6] BACKTESTING WALK-FORWARD")
            print("="*60)
            
            try:
                backtester = Backtester(output_dir=output_dir)
                
                # Utilisation données historiques si disponibles, sinon données courantes
                hist_path = "data/processed/opcvm_historique_complet.csv"
                if os.path.exists(hist_path):
                    backtest_data = hist_path
                else:
                    backtest_data = opcvm_enriched_path
                    print("Données historiques non disponibles, utilisation données courantes")
                
                backtest_result = backtester.run_backtest(backtest_data, window_size=100 if args.mock else 500)
                
                if backtest_result:
                    decision = backtest_result['decision']['decision']
                    print(f"\nBacktest terminé: {decision}")
                    
                    # Vérification décision
                    if 'NON FIABLE' in decision:
                        print("\nATTENTION: Modèle non fiable selon backtest")
                        response = input("Continuer quand même? (o/n): ")
                        if response.lower() != 'o':
                            print("Pipeline arrêté.")
                            return
                else:
                    print("\nErreur backtest")
                    
            except Exception as e:
                print(f"\nErreur étape 3: {e}")
                import traceback
                traceback.print_exc()
        
        # ==========================================
        # ÉTAPE 4: Modèle LSTM + signaux avec seuils dynamiques
        # ==========================================
        print("\n" + "="*60)
        print("[4/6] ENTRAÎNEMENT MODÈLE LSTM")
        print("="*60)
        
        try:
            model = OPCVMLSTMModel(output_dir=output_dir)
            signals = model.run_pipeline(opcvm_enriched_path)
            signals_path = os.path.join(output_dir, "signals_today.csv")
            print(f"\nÉtape 4 terminée: {signals_path}")
            
            # Application des seuils dynamiques
            print("\nApplication des seuils dynamiques basés sur les frais AMMC...")
            try:
                calculator = DynamicThresholdCalculator()
                signals_enriched = calculator.apply_to_signals_csv(
                    signals_path=signals_path,
                    opcvm_data_path=opcvm_data_path
                )
                
                if len(signals_enriched) > 0:
                    print(f"Signaux enrichis avec:")
                    print(f"  - Confiance (FORTE/MODEREE/FAIBLE)")
                    print(f"  - Gain net estimé (après frais)")
                    print(f"  - Rentabilité")
                    print(f"  - Seuils personnalisés par classification")
            except Exception as e:
                print(f"Erreur seuils dynamiques: {e}")
                print("Continuation avec signaux standards...")
                
        except ImportError as e:
            print(f"\nModule manquant: {e}")
            print("Installation: pip install tensorflow")
            print("Génération de signaux mock...")
            import pandas as pd
            import numpy as np
            df = pd.read_csv(opcvm_data_path)
            signals = []
            for _, row in df.iterrows():
                variation = np.random.uniform(-1, 1)
                signals.append({
                    'nom_fonds': row['nom_fonds'],
                    'vl_actuelle': row['vl_jour'],
                    'vl_predite': round(row['vl_jour'] * (1 + variation/100), 2),
                    'variation_pct': round(variation, 3),
                    'signal': 'ACHETER' if variation > 0.5 else 'VENDRE' if variation < -0.5 else 'ATTENDRE'
                })
            df_signals = pd.DataFrame(signals)
            signals_path = os.path.join(output_dir, "signals_today.csv")
            df_signals.to_csv(signals_path, index=False)
        except Exception as e:
            print(f"\nErreur étape 3: {e}")
            print("Génération de signaux mock...")
            import pandas as pd
            import numpy as np
            df = pd.read_csv(opcvm_data_path)
            signals = []
            for _, row in df.iterrows():
                variation = np.random.uniform(-1, 1)
                signals.append({
                    'nom_fonds': row['nom_fonds'],
                    'vl_actuelle': row['vl_jour'],
                    'vl_predite': round(row['vl_jour'] * (1 + variation/100), 2),
                    'variation_pct': round(variation, 3),
                    'signal': 'ACHETER' if variation > 0.5 else 'VENDRE' if variation < -0.5 else 'ATTENDRE'
                })
            df_signals = pd.DataFrame(signals)
            signals_path = os.path.join(output_dir, "signals_today.csv")
            df_signals.to_csv(signals_path, index=False)
        
        # ==========================================
        # ÉTAPE 5: Rapport Telegram (optionnel)
        # ==========================================
        print("\n" + "="*60)
        print("[5/6] CONFIGURATION BOT TELEGRAM")
        print("="*60)
        
        try:
            bot = TelegramOPCVMBot(output_dir=output_dir)
            
            # Envoi immédiat du rapport (mode démo si token non configuré)
            bot.send_report(
                signals_path=signals_path,
                opcvm_data_path=opcvm_data_path
            )
            
            print("\nPour activer le bot en continu:")
            print("   1. Configurez votre token dans config.py")
            print("   2. Exécutez: python src/04_telegram_bot.py")
            print("   3. Le bot enverra un rapport chaque jour à 18h00")
            
        except Exception as e:
            print(f"\n✗ Erreur étape 4: {e}")
            print("Le bot Telegram est optionnel. Le pipeline principal est terminé.")
        
        # ==========================================
        # RÉSUMÉ FINAL
        # ==========================================
        print("\n" + "="*60)
        print("PIPELINE TERMINE AVEC SUCCES")
        print("="*60)
        print(f"\nFichiers generes:")
        print(f"   • Données OPCVM: outputs/opcvm_data.csv")
        print(f"   • Données enrichies: outputs/opcvm_enriched.csv")
        print(f"   • Signaux de trading: outputs/signals_today.csv")
        print(f"   • Modèle LSTM: outputs/model_opcvm.h5")
        print(f"   • Graphique: outputs/vl_prediction.png")
        print(f"   • Log Telegram: logs/telegram_log.csv")
        
        print(f"\nProchaines etapes:")
        print(f"   1. Consultez outputs/signals_today.csv pour les signaux")
        print(f"   2. Ouvrez outputs/vl_prediction.png pour le graphique")
        print(f"   3. Configurez le bot Telegram pour les rapports quotidiens")
        
        print(f"\n⏰ Pour automatiser l'exécution quotidienne:")
        print(f"   Windows: Task Scheduler → python main.py")
        print(f"   Linux: cron job → 0 17 * * * cd /path && python main.py")
        
        print(f"\n{'='*60}")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"✗ ERREUR CRITIQUE")
        print(f"{'='*60}")
        print(f"Erreur: {e}")
        print(f"\nVérifiez:")
        print(f"1. Dépendances installées: pip install -r requirements.txt")
        print(f"2. Permissions d'écriture dans le dossier")
        print(f"3. Connexion Internet pour les modèles HuggingFace")
        
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
