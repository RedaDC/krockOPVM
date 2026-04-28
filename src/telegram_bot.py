# pip install python-telegram-bot schedule pandas
"""
Bot Telegram pour rapports OPCVM quotidiens
Envoie un rapport structuré chaque jour à 18h00 après clôture de la Bourse de Casablanca.
"""

import pandas as pd
import requests
import schedule
import time
from datetime import datetime
import os

# Configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TELEGRAM


class TelegramOPCVMBot:
    """Bot Telegram pour rapports OPCVM quotidiens"""
    
    def __init__(self, token=None, chat_id=None, output_dir="outputs", log_dir="logs"):
        """
        Initialise le bot Telegram
        
        Args:
            token: Token du bot (défaut: config.py)
            chat_id: ID du chat (défaut: config.py)
            output_dir: Répertoire des fichiers de données
            log_dir: Répertoire des logs
        """
        self.token = token or TELEGRAM['token']
        self.chat_id = chat_id or TELEGRAM['chat_id']
        self.output_dir = output_dir
        self.log_file = os.path.join(log_dir, "telegram_log.csv")
        os.makedirs(log_dir, exist_ok=True)
    
    def format_report(self, signals_path=None, opcvm_data_path=None, news_path=None):
        """
        Formate le message de rapport
        
        Args:
            signals_path: Chemin vers signals_today.csv
            opcvm_data_path: Chemin vers opcvm_data.csv
            news_path: Chemin vers news_sentiment.csv
            
        Returns:
            str: Message formaté pour Telegram
        """
        try:
            # Chemins par défaut
            if signals_path is None:
                signals_path = os.path.join(self.output_dir, "signals_today.csv")
            if opcvm_data_path is None:
                opcvm_data_path = os.path.join(self.output_dir, "opcvm_data.csv")
            if news_path is None:
                news_path = os.path.join(self.output_dir, "news_sentiment.csv")
            
            # Vérification des fichiers
            if not os.path.exists(signals_path):
                return "ERREUR: Fichier signals_today.csv non trouve.\n\nVeuillez executer le pipeline complet d'abord:\npython main.py"
            
            if not os.path.exists(opcvm_data_path):
                return "ERREUR: Fichier opcvm_data.csv non trouve."
            
            # Chargement des données
            signals = pd.read_csv(signals_path)
            opcvm_data = pd.read_csv(opcvm_data_path)
            
            # Calcul AUM total
            aum_total = opcvm_data['aum'].sum() if 'aum' in opcvm_data.columns else 0
            aum_total_md = aum_total / 1e9  # Conversion en Md MAD
            
            # Séparation par signal
            acheter = signals[signals['signal'] == 'ACHETER']
            attendre = signals[signals['signal'] == 'ATTENDRE']
            vendre = signals[signals['signal'] == 'VENDRE']
            
            # Date du jour
            date_jour = datetime.now().strftime('%d/%m/%Y')
            
            # Construction du message
            message = f"Rapport OPCVM Maroc — {date_jour}\n\n"
            message += f"AUM Total: {aum_total_md:.2f} Md MAD\n"
            message += f"Total Fonds: {len(signals)}\n\n"
            message += f"{'─'*40}\n\n"
            
            # Section ACHETER
            message += f"ACHETER ({len(acheter)} fonds)\n"
            if len(acheter) > 0:
                for _, row in acheter.iterrows():
                    sentiment_score = row.get('score_sentiment', 0)
                    if pd.notna(sentiment_score):
                        sentiment_label = "Positif" if sentiment_score > 0 else "Neutre" if sentiment_score == 0 else "Negatif"
                    else:
                        sentiment_label = "Neutre"
                    
                    message += f"[ACHETER] {row['nom_fonds']}\n"
                    message += f"   VL: {row['vl_actuelle']:.2f} -> {row['vl_predite']:.2f} MAD\n"
                    message += f"   Variation: {row['variation_pct']:+.2f}% | Sentiment: {sentiment_label}\n\n"
            else:
                message += "   Aucun fond a acheter aujourd'hui\n\n"
            
            message += f"{'─'*40}\n\n"
            
            # Section ATTENDRE
            message += f"ATTENDRE ({len(attendre)} fonds)\n"
            if len(attendre) > 0:
                # Limiter a 10 pour eviter message trop long
                for _, row in attendre.head(10).iterrows():
                    message += f"[ATTENDRE] {row['nom_fonds']} -- VL stable ({row['vl_actuelle']:.2f} MAD)\n"
                if len(attendre) > 10:
                    message += f"   ... et {len(attendre) - 10} autres\n"
            else:
                message += "   Aucun fond en attente\n"
            
            message += f"\n{'─'*40}\n\n"
            
            # Section VENDRE
            message += f"VENDRE ({len(vendre)} fonds)\n"
            if len(vendre) > 0:
                for _, row in vendre.iterrows():
                    sentiment_score = row.get('score_sentiment', 0)
                    if pd.notna(sentiment_score):
                        sentiment_label = "Negatif" if sentiment_score < 0 else "Neutre" if sentiment_score == 0 else "Positif"
                    else:
                        sentiment_label = "Neutre"
                    
                    message += f"[VENDRE] {row['nom_fonds']}\n"
                    message += f"   VL: {row['vl_actuelle']:.2f} -> {row['vl_predite']:.2f} MAD\n"
                    message += f"   Variation: {row['variation_pct']:+.2f}% | Sentiment: {sentiment_label}\n\n"
            else:
                message += "   Aucun fond a vendre aujourd'hui\n"
            
            message += f"\n{'─'*40}\n\n"
            
            # Top actualites
            if os.path.exists(news_path):
                try:
                    news = pd.read_csv(news_path)
                    if len(news) > 0:
                        message += f"Top actualites du jour:\n\n"
                        
                        # Top 5 articles par score absolu
                        news['abs_score'] = news['score_sentiment'].abs()
                        top_news = news.nlargest(5, 'abs_score')
                        
                        for idx, (_, article) in enumerate(top_news.iterrows(), 1):
                            score = article['score_sentiment']
                            trend = "Hausse" if score > 0.3 else "Baisse" if score < -0.3 else "Stable"
                            
                            # Tronquer le titre si trop long
                            title = article['title'][:80] + "..." if len(article['title']) > 80 else article['title']
                            
                            message += f"{idx}. {title}\n"
                            message += f"   Score: {score:+.2f} ({trend})\n\n"
                    else:
                        message += "Aucune actualite significative aujourd'hui\n"
                except Exception as e:
                    message += f"Erreur chargement actualites: {str(e)}\n"
            else:
                message += "Donnees d'actualites non disponibles\n"
            
            message += f"\n{'─'*40}\n"
            message += f"\nDisclaimer: Ce rapport est genere automatiquement a titre indicatif. Consultez un conseiller financier avant toute decision d'investissement."
            
            return message
            
        except Exception as e:
            error_msg = f"Erreur generation rapport:\n\n{str(e)}\n\nVerifiez que les fichiers de sortie existent dans le dossier outputs/."
            return error_msg
    
    def send_report(self, signals_path=None, opcvm_data_path=None, news_path=None):
        """
        Envoie le rapport via Telegram
        
        Args:
            signals_path: Chemin vers signals_today.csv
            opcvm_data_path: Chemin vers opcvm_data.csv
            news_path: Chemin vers news_sentiment.csv
        """
        print(f"\n{'='*60}")
        print(f"ENVOI RAPPORT TELEGRAM - {datetime.now()}")
        print(f"{'='*60}")
        
        try:
            # Vérification token
            if self.token == "YOUR_BOT_TOKEN" or not self.token:
                print("Token Telegram non configure")
                print("Pour configurer:")
                print("1. Créez un bot via @BotFather sur Telegram")
                print("2. Copiez le token")
                print("3. Modifiez config.py: TELEGRAM['token'] = 'VOTRE_TOKEN'")
                
                # Message pour console
                message = self.format_report(signals_path, opcvm_data_path, news_path)
                print(f"\nMessage généré (longueur: {len(message)} caractères):")
                print(message[:500] + "..." if len(message) > 500 else message)
                
                self.log_send(status="MOCK", message_length=len(message))
                return
            
            # Formatage du message
            message = self.format_report(signals_path, opcvm_data_path, news_path)
            
            # Envoi via Telegram API
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            print(f"✓ Rapport envoyé avec succès")
            self.log_send(status="SUCCESS", message_length=len(message))
            
        except Exception as e:
            print(f"✗ Erreur envoi Telegram: {e}")
            self.log_send(status="ERROR", error=str(e))
    
    def log_send(self, status, message_length=0, error=""):
        """
        Journalise chaque envoi dans telegram_log.csv
        
        Args:
            status: Statut (SUCCESS, ERROR, MOCK)
            message_length: Longueur du message
            error: Message d'erreur si applicable
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'message_length': message_length,
            'error': error
        }
        
        df_log = pd.DataFrame([log_entry])
        
        if os.path.exists(self.log_file):
            df_log.to_csv(self.log_file, mode='a', header=False, index=False)
        else:
            df_log.to_csv(self.log_file, index=False)
        
        print(f"✓ Log enregistré: {status}")
    
    def schedule_daily_report(self, hour=18, minute=0, signals_path=None, opcvm_data_path=None, news_path=None):
        """
        Planifie l'envoi quotidien à 18h00
        
        Args:
            hour: Heure d'envoi (défaut: 18)
            minute: Minute d'envoi (défaut: 0)
            signals_path: Chemin vers signals_today.csv
            opcvm_data_path: Chemin vers opcvm_data.csv
            news_path: Chemin vers news_sentiment.csv
        """
        print(f"\n{'='*60}")
        print(f"PLANIFICATION BOT TELEGRAM")
        print(f"{'='*60}")
        print(f"Envoi quotidien planifié à {hour:02d}:{minute:02d}")
        print(f"Chat ID: {self.chat_id}")
        print(f"Pour arrêter: Ctrl+C\n")
        
        # Fonction wrapper pour passer les arguments
        def send_daily():
            self.send_report(signals_path, opcvm_data_path, news_path)
        
        # Planification
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(send_daily)
        
        # Envoi immédiat pour test
        print("Envoi d'un rapport de test maintenant...")
        send_daily()
        
        # Loop principale
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Vérification toutes les minutes
        except KeyboardInterrupt:
            print("\nBot arrêté par l'utilisateur")
        except Exception as e:
            print(f"\nErreur critique: {e}")
            self.log_send(status="CRITICAL_ERROR", error=str(e))


if __name__ == "__main__":
    # Exemple d'utilisation
    bot = TelegramOPCVMBot()
    
    # Mode 1: Envoi immédiat
    # bot.send_report()
    
    # Mode 2: Planification quotidienne à 18h
    bot.schedule_daily_report(hour=18, minute=0)
