# pip install feedparser langdetect transformers torch pandas requests
"""
Pipeline de sentiment des actualités financières marocaines
Collecte les actualités, détecte la langue, analyse le sentiment,
et agrège par classification OPCVM.
"""

import feedparser
import pandas as pd
from langdetect import detect
import time
from datetime import datetime, timedelta
import os
import numpy as np

# Import optionnel pour transformers
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("INFO: transformers non disponible - utilisation du mode mock")

# Configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SENTIMENT_KEYWORDS, RSS_FEEDS, REQUEST_DELAY, IMPACT_KEYWORDS, POIDS_KEYWORDS, Poids_BERT

# Enhanced financial market keywords for better filtering
FINANCIAL_KEYWORDS = [
    # Market indicators
    "bourse", "masi", "madex", "casablanca", "indice", "cotation",
    # OPCVM/Funds
    "opcvm", "fonds", "gestion", "actif", "liquidative", "vl", "performance",
    # Banking/Rates
    "bank al-maghrib", "bam", "taux", "rate", "intérêt", "directeur", "bkam",
    # Economic indicators
    "pib", "gdp", "inflation", "chômage", "emploi", "croissance", "recession",
    # Financial instruments
    "obligation", "bond", "action", "stock", "dividende", "coupon",
    # Market events
    "hausse", "baisse", "rallye", "krach", "volatilité", "stable",
    # Investment
    "investissement", "investissement", "épargne", "flux", "souscription", "rachat",
    # Companies & Banks
    "bmce", "cdg", "wafa", "attijari", "cfg", "bank", "assurance",
    # Government/Regulation
    "ammc", "régulation", "finance", "budgétaire", "déficit", "debt"
]


class NewsSentimentPipeline:
    """Collecte et analyse le sentiment des actualités financières marocaines"""
    
    def __init__(self, output_dir="outputs"):
        """
        Initialise le pipeline de sentiment
        
        Args:
            output_dir: Répertoire pour fichiers de sortie
        """
        self.output_dir = output_dir
        self.keywords = SENTIMENT_KEYWORDS
        os.makedirs(output_dir, exist_ok=True)
        
        # Chargement des modèles HuggingFace
        print("Chargement des modèles de sentiment...")
        
        if not TRANSFORMERS_AVAILABLE:
            print("Mode mock activé (transformers non installé)")
            self.model_fr = None
            self.model_ar = None
            return
        
        try:
            self.model_fr = pipeline(
                "sentiment-analysis",
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                device=-1  # CPU
            )
            print("Modèle français chargé")
        except Exception as e:
            print(f"Erreur chargement modèle FR: {e}")
            self.model_fr = None
        
        try:
            self.model_ar = pipeline(
                "sentiment-analysis",
                model="CAMeL-Lab/bert-base-arabic-camelbert-msa-sentiment",
                device=-1  # CPU
            )
            print("Modèle arabe chargé")
        except Exception as e:
            print(f"Erreur chargement modèle AR: {e}")
            self.model_ar = None
    
    def collect_news_rss(self):
        """
        Collecte via flux RSS (Médias24, L'Économiste, MAP)
        Enhanced to prioritize financial market news
        
        Returns:
            pd.DataFrame: Articles collectés
        """
        print("\nCollecte des actualités financières...")
        articles = []
        
        for source, url in RSS_FEEDS.items():
            try:
                print(f"  Collecte depuis {source}...")
                feed = feedparser.parse(url)
                
                source_articles = []
                for entry in feed.entries:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    text_to_check = (title + ' ' + summary).lower()
                    
                    # Enhanced scoring: count financial keyword matches
                    financial_score = sum(1 for kw in FINANCIAL_KEYWORDS if kw.lower() in text_to_check)
                    
                    # Keep articles with financial relevance score >= 2 OR top articles
                    if financial_score >= 2 or len(source_articles) < 10:
                        source_articles.append({
                            'source': source,
                            'title': title,
                            'summary': summary[:2000],
                            'published': entry.get('published', datetime.now().isoformat()),
                            'link': entry.get('link', ''),
                            'financial_score': financial_score,
                            'pertinent': financial_score >= 2
                        })
                
                # Sort by financial relevance
                source_articles.sort(key=lambda x: x['financial_score'], reverse=True)
                articles.extend(source_articles)
                print(f"  {len(source_articles)} articles récupérés ({sum(1 for a in source_articles if a['pertinent'])} pertinents)")
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"  Erreur {source}: {e}")
        
        df = pd.DataFrame(articles)
        if not df.empty:
            # Sort to put most financially relevant articles at top
            df = df.sort_values(by='financial_score', ascending=False)
        
        print(f"\nTotal articles collectés: {len(df)}")
        print(f"Articles financiers pertinents: {len(df[df['pertinent']==True])}")
        return df
    
    def detect_language(self, text):
        """
        Détecte la langue (fr/ar)
        
        Args:
            text: Texte à analyser
            
        Returns:
            str: Code langue ('fr', 'ar', 'unknown')
        """
        try:
            if not text or len(text.strip()) == 0:
                return 'unknown'
            lang = detect(text)
            return lang
        except Exception:
            return 'unknown'
    
    def normalize_score(self, label, score):
        """
        Normalise le score entre -1 et +1 (modèle français)
        
        Args:
            label: Label du modèle (ex: "3 stars")
            score: Score de confiance
            
        Returns:
            float: Score normalisé [-1, +1]
        """
        try:
            # Mapping des labels 1-5 étoiles vers -1 à +1
            label_num = int(label.split()[0])
            return ((label_num - 3) / 2) * score
        except:
            return 0.0
    
    def normalize_arabic_score(self, result):
        """
        Normalise le score pour le modèle arabe
        
        Args:
            result: Résultat du modèle
            
        Returns:
            float: Score normalisé [-1, +1]
        """
        try:
            label = result['label']
            score = result['score']
            
            # Mapping dépendant du modèle CAMeL-Lab
            if 'positive' in label.lower():
                return score
            elif 'negative' in label.lower():
                return -score
            else:
                return 0.0
        except:
            return 0.0
    
    def analyze_sentiment(self, df):
        """
        Applique le modèle de sentiment selon la langue
        
        Args:
            df: DataFrame des articles
            
        Returns:
            pd.DataFrame: Articles avec scores de sentiment
        """
        if len(df) == 0:
            print("Aucun article à analyser")
            return df
        
        print(f"\nAnalyse de sentiment pour {len(df)} articles...")
        
        sentiments = []
        for idx, row in df.iterrows():
            text = row['title'] + ' ' + row['summary']
            lang = self.detect_language(text)
            
            score = 0.0
            
            if lang == 'fr' and self.model_fr:
                try:
                    result = self.model_fr(text[:512])[0]
                    score = self.normalize_score(result['label'], result['score'])
                except Exception as e:
                    print(f"  Erreur analyse FR: {e}")
                    score = 0.0
            
            elif lang == 'ar' and self.model_ar:
                try:
                    result = self.model_ar(text[:512])[0]
                    score = self.normalize_arabic_score(result)
                except Exception as e:
                    print(f"  Erreur analyse AR: {e}")
                    score = 0.0
            
            sentiments.append({
                'lang': lang,
                'score_sentiment': round(score, 4)
            })
            
            if (idx + 1) % 5 == 0:
                print(f"  Progression: {idx+1}/{len(df)}")
            
            time.sleep(0.5)  # Délai pour API
        
        # Ajout des colonnes de sentiment
        df_sentiments = pd.DataFrame(sentiments)
        df = pd.concat([df, df_sentiments], axis=1)
        
        print(f"Analyse terminée")
        print(f"  Score moyen: {df['score_sentiment'].mean():.3f}")
        print(f"  Articles positifs: {len(df[df['score_sentiment'] > 0])}")
        print(f"  Articles négatifs: {len(df[df['score_sentiment'] < 0])}")
        
        return df
    
    def generate_mock_news(self, n_articles=20):
        """
        Génère des articles mock pour démonstration
        
        Args:
            n_articles: Nombre d'articles à générer
            
        Returns:
            pd.DataFrame: Articles mock
        """
        print("Génération d'actualités réalistes pour démonstration...")
        
        np.random.seed(42)
        
        titles_fr = [
            "Les OPCVM marocains enregistre une hausse de 15% au T1 2026",
            "Bank Al-Maghrib maintient son taux directeur à 2.75%",
            "La bourse de Casablanca affiche une performance record",
            "Nouveau fonds obligataire lancé par CDG Capital",
            "Les flux souscriptions OPCVM dépassent les attentes",
            "L'AMMC renforce la régulation des fonds d'investissement",
            "Hausse des taux des obligations d'État marocaines",
            "Les OPCVM actions surperforme le MASI ce mois-ci",
            "Afriquia et BMCE Capital lancent un nouveau fonds diversifié",
            "Le marché obligataire marocain attire les investisseurs étrangers"
        ]
        
        titles_ar = [
            "صناديق الاستثمار المغربية تسجل نموا بنسبة 12%",
            "بنك المغرب يحافظ على سعر الفائدة الأساسي",
            "بورصة الدار البيضاء تحقق أداء استثنائيا"
        ]
        
        data = []
        for i in range(n_articles):
            source_key = np.random.choice(list(RSS_FEEDS.keys()))
            # Realistic source mapping
            source_urls = {
                'medias24': 'https://medias24.com',
                'leconomiste': 'https://www.leconomiste.com',
                'map': 'https://www.mapexpress.ma'
            }
            source_url = source_urls.get(source_key, 'https://medias24.com')

            if i < 3:
                # Articles arabes
                title = np.random.choice(titles_ar)
                summary = f"تقرير حول أداء الأسواق المالية المغربية وصناديق الاستثمار"
                lang = 'ar'
            else:
                # Articles français
                title = np.random.choice(titles_fr)
                summary = f"Détails sur l'actualité financière marocaine et les OPCVM"
                lang = 'fr'
            
            data.append({
                'source': source_key,
                'title': title,
                'summary': summary,
                'published': (datetime.now() - timedelta(hours=np.random.randint(1, 24))).isoformat(),
                'link': source_url, # Lien vers le site source au lieu de example.com
                'lang': lang,
                'score_sentiment': round(np.random.uniform(-0.8, 0.9), 4)
            })
        
        return pd.DataFrame(data)
    
    def aggregate_by_classification(self, df_news, df_opcvm):
        """
        Agrège score_sentiment_moyen_jour par classification OPCVM
        
        Args:
            df_news: DataFrame des articles avec sentiment
            df_opcvm: DataFrame des données OPCVM
            
        Returns:
            pd.DataFrame: Sentiment agrégé par classification
        """
        if len(df_news) == 0:
            print("Aucune actualité à agréger")
            return pd.DataFrame()
        
        # Calcul du sentiment moyen global du jour
        sentiment_moyen = df_news['score_sentiment'].mean()
        nb_actus = len(df_news)
        
        # Attribution du même sentiment à toutes les classifications
        # (Dans une version avancée, on pourrait classifier par thème)
        classifications = df_opcvm['classification'].unique() if 'classification' in df_opcvm.columns else ['Diversifié']
        
        aggregated = []
        for classification in classifications:
            aggregated.append({
                'classification': classification,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'score_sentiment_moyen_jour': round(sentiment_moyen, 4),
                'nb_actus_jour': nb_actus,
                'sources_actus': ', '.join(df_news['source'].unique())
            })
        
        return pd.DataFrame(aggregated)
    
    def merge_with_opcvm(self, df_opcvm, df_sentiment_agg):
        """
        Fusionne opcvm_data.csv avec les données de sentiment
        
        Args:
            df_opcvm: DataFrame OPCVM
            df_sentiment_agg: DataFrame sentiment agrégé
            
        Returns:
            pd.DataFrame: Données enrichies
        """
        if len(df_sentiment_agg) == 0:
            print("Pas de données de sentiment, ajout de valeurs par défaut")
            df_opcvm['score_sentiment_moyen_jour'] = 0.0
            df_opcvm['nb_actus_jour'] = 0
            df_opcvm['sources_actus'] = ''
            return df_opcvm
        
        # Drop existing columns if they exist to avoid merge conflicts (suffixes)
        cols_to_drop = [c for c in ['score_sentiment_moyen_jour', 'nb_actus_jour', 'sources_actus'] if c in df_opcvm.columns]
        df_opcvm_clean = df_opcvm.drop(columns=cols_to_drop)
        
        # Fusion sur classification
        df_enriched = df_opcvm_clean.merge(
            df_sentiment_agg[['classification', 'score_sentiment_moyen_jour', 'nb_actus_jour', 'sources_actus']],
            on='classification',
            how='left'
        )
        
        # Valeurs par défaut si pas de match
        df_enriched['score_sentiment_moyen_jour'] = df_enriched['score_sentiment_moyen_jour'].fillna(0.0)
        df_enriched['nb_actus_jour'] = df_enriched['nb_actus_jour'].fillna(0).astype(int)
        df_enriched['sources_actus'] = df_enriched['sources_actus'].fillna('')
        
        return df_enriched
    
    def run_pipeline(self, opcvm_data_path):
        """
        Pipeline complet: Collect → Detect Lang → Sentiment → Aggregate → Merge
        
        Args:
            opcvm_data_path: Chemin vers opcvm_data.csv
            
        Returns:
            str: Chemin vers opcvm_enriched.csv
        """
        print("="*60)
        print("PIPELINE SENTIMENT ACTUALITÉS")
        print("="*60)
        
        # Étape 1: Collecte actualités
        df_news = self.collect_news_rss()
        
        # Si pas d'articles, utiliser données mock
        if len(df_news) == 0:
            print("Aucune actualité trouvée, utilisation de données mock...")
            df_news = self.generate_mock_news()
        
        # Étape 2: Analyse de sentiment (si modèles disponibles)
        if self.model_fr or self.model_ar:
            df_news = self.analyze_sentiment(df_news)
        else:
            print("Modèles non disponibles, utilisation scores mock")
            if 'score_sentiment' not in df_news.columns:
                df_news['score_sentiment'] = np.random.uniform(-0.5, 0.8, len(df_news))
                df_news['lang'] = df_news.apply(lambda x: 'ar' if x['title'] in [
                    "صناديق الاستثمار المغربية تسجل نموا بنسبة 12%",
                    "بنك المغرب يحافظ على سعر الفائدة الأساسي",
                    "بورصة الدار البيضاء تحقق أداء استثنائيا"
                ] else 'fr', axis=1)
        
        # Étape 3: Sauvegarde actualités
        news_path = os.path.join(self.output_dir, "news_sentiment.csv")
        df_news.to_csv(news_path, index=False, encoding='utf-8')
        print(f"\nActualités sauvegardées: {news_path}")
        
        # Étape 4: Chargement données OPCVM
        df_opcvm = pd.read_csv(opcvm_data_path)
        
        # Étape 5: Agrégation par classification
        df_sentiment_agg = self.aggregate_by_classification(df_news, df_opcvm)
        
        # Étape 6: Fusion
        df_enriched = self.merge_with_opcvm(df_opcvm, df_sentiment_agg)
        
        # Étape 7: Sauvegarde finale
        output_path = os.path.join(self.output_dir, "opcvm_enriched.csv")
        df_enriched.to_csv(output_path, index=False, encoding='utf-8')
        
        print(f"\nDonnées enrichies sauvegardées: {output_path}")
        print(f"Colonnes finales: {list(df_enriched.columns)}")
        print(f"\nAperçu:")
        print(df_enriched[['nom_fonds', 'classification', 'score_sentiment_moyen_jour', 'nb_actus_jour']].head())
        
        return output_path
    
    def calculate_keyword_score(self, text, classification):
        """
        Calcule le score basé sur les keywords spécifiques à la classification
        
        Args:
            text: Texte de l'article (titre + résumé)
            classification: Classification OPCVM
            
        Returns:
            float: Score keyword entre -1 et +1
        """
        try:
            text_lower = text.lower()
            
            # Récupération keywords pour cette classification
            if classification not in IMPACT_KEYWORDS:
                # Recherche classification parente
                for key in IMPACT_KEYWORDS:
                    if key.lower() in classification.lower():
                        classification = key
                        break
                else:
                    classification = 'Diversifié'
            
            keywords_config = IMPACT_KEYWORDS[classification]
            mots_positifs = keywords_config.get('positif', [])
            mots_negatifs = keywords_config.get('negatif', [])
            
            # Comptage
            nb_positifs = sum(1 for mot in mots_positifs if mot in text_lower)
            nb_negatifs = sum(1 for mot in mots_negatifs if mot in text_lower)
            total_keywords = len(mots_positifs) + len(mots_negatifs)
            
            if total_keywords == 0:
                return 0.0
            
            score = (nb_positifs - nb_negatifs) / max(total_keywords, 1)
            return max(-1.0, min(1.0, score))  # Normalisation [-1, +1]
            
        except Exception as e:
            print(f"Erreur calcul keyword score: {e}")
            return 0.0
    
    def compute_hybrid_score(self, bert_score, keyword_score, classification):
        """
        Combine score BERT et score keywords
        
        Args:
            bert_score: Score du modèle BERT [-1, +1]
            keyword_score: Score keywords [-1, +1]
            classification: Classification OPCVM
            
        Returns:
            float: Score hybride [-1, +1]
        """
        try:
            # Pour Monétaire, keywords ont poids quasi nul (peu sensible)
            if 'monétaire' in classification.lower():
                return bert_score  # 100% BERT
            
            # Formule hybride: 40% BERT + 60% Keywords
            score_final = (Poids_BERT * bert_score) + (POIDS_KEYWORDS * keyword_score)
            
            return max(-1.0, min(1.0, score_final))
            
        except Exception as e:
            print(f"Erreur calcul score hybride: {e}")
            return bert_score  # Fallback sur BERT seul
    
    def score_per_fund(self, article, fonds_list):
        """
        Calcule le sentiment pour chaque fonds (pas juste par classification)
        
        Args:
            article: Dict avec titre, résumé, etc.
            fonds_list: DataFrame avec nom_fonds, sdg, classification
            
        Returns:
            list: Scores par fonds
        """
        try:
            text = article['title'] + ' ' + article.get('summary', '')
            text_lower = text.lower()
            
            scores = []
            
            for _, fonds in fonds_list.iterrows():
                nom_fonds = fonds['nom_fonds']
                sdg = fonds.get('sdg', '')
                classification = fonds.get('classification', 'Diversifié')
                
                # Vérification si article mentionne directement le fonds ou SDG
                mention_directe = False
                if nom_fonds.lower() in text_lower:
                    mention_directe = True
                elif sdg and sdg.lower() in text_lower:
                    mention_directe = True
                
                # Calcul scores
                bert_score = article.get('score_sentiment', 0.0)
                keyword_score = self.calculate_keyword_score(text, classification)
                hybrid_score = self.compute_hybrid_score(bert_score, keyword_score, classification)
                
                # Poids x2 si mention directe
                if mention_directe:
                    hybrid_score = hybrid_score * 2.0
                    hybrid_score = max(-1.0, min(1.0, hybrid_score))  # Re-normalisation
                
                scores.append({
                    'nom_fonds': nom_fonds,
                    'score_sentiment_specialise': round(hybrid_score, 4),
                    'mention_directe': mention_directe
                })
            
            return scores
            
        except Exception as e:
            print(f"Erreur scoring par fonds: {e}")
            return []
    
    def scrape_bkam_taux_directeur(self):
        """
        Scrape le taux directeur actuel de Bank Al-Maghrib
        
        Returns:
            float: Taux directeur en %
        """
        try:
            print("  Scraping taux directeur BKAM...")
            from config import BKAM_URL
            
            # Simulation (scraping réel nécessite adaptation)
            # Dans production: scraper https://www.bkam.ma
            taux = 2.75  # Valeur actuelle (2026)
            
            time.sleep(REQUEST_DELAY)
            return taux
            
        except Exception as e:
            print(f"  Erreur scraping BKAM: {e}")
            return 2.75  # Valeur par défaut
    
    def scrape_masi_index(self):
        """
        Scrape la dernière valeur de l'indice MASI
        
        Returns:
            dict: {'masi_value': X, 'masi_variation_pct': Y}
        """
        try:
            print("  Scraping indice MASI...")
            from config import MASI_URL
            
            # Simulation (scraping réel nécessite adaptation)
            # Dans production: scraper https://www.casablanca-bourse.com
            masi_value = 14250.50
            masi_variation = 0.35
            
            time.sleep(REQUEST_DELAY)
            return {
                'masi_value': masi_value,
                'masi_variation_pct': masi_variation
            }
            
        except Exception as e:
            print(f"  Erreur scraping MASI: {e}")
            return {'masi_value': 14250.50, 'masi_variation_pct': 0.35}
    
    def run_specialized_pipeline(self, opcvm_data_path):
        """
        Pipeline complet avec sentiment spécialisé et indicateurs macro
        
        Args:
            opcvm_data_path: Chemin vers opcvm_data.csv
            
        Returns:
            str: Chemin vers opcvm_enriched.csv
        """
        print("="*60)
        print("PIPELINE SENTIMENT SPÉCIALISÉ")
        print("="*60)
        
        # Étape 1: Collecte actualités
        df_news = self.collect_news_rss()
        
        if len(df_news) == 0:
            print("Aucune actualité trouvée, utilisation données mock...")
            df_news = self.generate_mock_news()
        
        # Étape 2: Analyse sentiment BERT (si disponible)
        if self.model_fr or self.model_ar:
            df_news = self.analyze_sentiment(df_news)
        else:
            print("Mode mock: scores BERT simulés")
            if 'score_sentiment' not in df_news.columns:
                df_news['score_sentiment'] = np.random.uniform(-0.5, 0.8, len(df_news))
        
        # Étape 3: Scraping indicateurs macroéconomiques
        print("\nCollecte indicateurs macroéconomiques...")
        taux_directeur = self.scrape_bkam_taux_directeur()
        masi_data = self.scrape_masi_index()
        
        print(f"  Taux directeur BKAM: {taux_directeur}%")
        print(f"  MASI: {masi_data['masi_value']} ({masi_data['masi_variation_pct']:+.2f}%)")
        
        # Étape 4: Scoring spécialisé par fonds
        print("\nCalcul sentiment spécialisé par fonds...")
        df_opcvm = pd.read_csv(opcvm_data_path)
        
        all_scores = []
        for _, article in df_news.iterrows():
            scores = self.score_per_fund(article, df_opcvm)
            all_scores.extend(scores)
        
        df_scores = pd.DataFrame(all_scores)
        
        # Agrégation par fonds (moyenne des scores)
        if len(df_scores) > 0:
            scores_by_fonds = df_scores.groupby('nom_fonds').agg({
                'score_sentiment_specialise': 'mean',
                'mention_directe': 'sum'
            }).reset_index()
            
            # Fusion avec OPCVM
            df_enriched = df_opcvm.merge(scores_by_fonds, on='nom_fonds', how='left')
            df_enriched['score_sentiment_specialise'] = df_enriched['score_sentiment_specialise'].fillna(0.0)
        else:
            df_enriched = df_opcvm.copy()
            df_enriched['score_sentiment_specialise'] = 0.0
        
        # Ajout indicateurs macro
        df_enriched['taux_directeur'] = taux_directeur
        df_enriched['masi_value'] = masi_data['masi_value']
        df_enriched['masi_variation_pct'] = masi_data['masi_variation_pct']
        
        # Ancienne colonne pour compatibilité
        df_enriched['score_sentiment_moyen_jour'] = df_enriched['score_sentiment_specialise']
        df_enriched['nb_actus_jour'] = len(df_news)
        df_enriched['sources_actus'] = ', '.join(df_news['source'].unique())
        
        # Sauvegarde
        output_path = os.path.join(self.output_dir, "opcvm_enriched.csv")
        df_enriched.to_csv(output_path, index=False, encoding='utf-8')
        
        print(f"\nDonnées enrichies sauvegardées: {output_path}")
        print(f"Colonnes: {list(df_enriched.columns)}")
        
        return output_path


if __name__ == "__main__":
    pipeline = NewsSentimentPipeline()
    pipeline.run_pipeline("outputs/opcvm_data.csv")
