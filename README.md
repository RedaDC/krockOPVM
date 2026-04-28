# OPCVM Analytics Maroc - Systeme d'Analyse Quantitative

Système complet d'analyse des OPCVM marocains utilisant le machine learning et le traitement du langage naturel pour générer des signaux de trading automatisés.

## Fonctionnalites

- **Collecte automatique** des données ASFIM (521 fonds, 18 SDG)
- **Enrichissement** avec données obligataires Maroclear (6,286 ISINs)
- **Analyse de sentiment** des actualités financières (Médias24, L'Économiste, MAP)
- **Modèle LSTM** pour prédiction des valeurs liquidatives
- **Signaux de trading** automatiques (ACHETER/VENDRE/ATTENDRE)
- **Bot Telegram** pour rapports quotidiens à 18h00

## Structure du Projet

```
APP OPCVM MOROCCO/
├── main.py                              # Orchestrateur principal
├── config.py                            # Configuration centrale
├── requirements.txt                     # Dépendances Python
├── src/
│   ├── asfim_maroclear_collector.py     # Collecteur de données
│   ├── news_sentiment_pipeline.py       # Pipeline sentiment actualités
│   ├── lstm_model.py                    # Modèle LSTM + signaux
│   └── telegram_bot.py                  # Bot Telegram quotidien
├── data/
│   ├── raw/                             # Données brutes
│   └── processed/                       # Données traitées
├── outputs/
│   ├── opcvm_data.csv                   # Données OPCVM parsées
│   ├── opcvm_enriched.csv               # Données enrichies avec sentiment
│   ├── signals_today.csv                # Signaux de trading du jour
│   ├── model_opcvm.h5                   # Modèle LSTM sauvegardé
│   └── vl_prediction.png                # Graphique prédictions
└── logs/
    └── telegram_log.csv                 # Journal des envois Telegram
```

## Installation

### 1. Prérequis

- Python 3.8 ou supérieur
- 8 Go RAM minimum (16 Go recommandé pour le LSTM)
- Connexion Internet (pour modèles HuggingFace)

### 2. Installation des dépendances

```bash
pip install -r requirements.txt
```

**Note:** L'installation peut prendre 10-15 minutes due à TensorFlow et PyTorch.

## ⚡ Utilisation

### Exécution complète (recommandé)

```bash
python main.py
```

Ce script exécute automatiquement:
1. Collecte des données ASFIM & Maroclear
2. Analyse de sentiment des actualités
3. Entraînement du modèle LSTM
4. Génération des signaux de trading
5. Envoi du rapport Telegram (si configuré)

### Exécution modulaire

```bash
# Étape 1: Collecte données
python src/asfim_maroclear_collector.py

# Étape 2: Analyse sentiment
python src/news_sentiment_pipeline.py

# Étape 3: Modèle LSTM
python src/lstm_model.py

# Étape 4: Bot Telegram
python src/telegram_bot.py
```

## Configuration

### 1. Telegram Bot

Pour activer les rapports quotidiens:

1. Créez un bot via [@BotFather](https://t.me/botfather) sur Telegram
2. Envoyez `/newbot` et suivez les instructions
3. Copiez le token reçu
4. Modifiez `config.py`:

```python
TELEGRAM = {
    'token': "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ",  # Votre token
    'chat_id': "987654321",              # Votre ID Telegram
    'report_time': "18:00"
}
```

**Pour obtenir votre chat_id:**
- Envoyez un message à votre bot
- Visitez: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
- Cherchez `"chat":{"id":987654321,...}`

### 2. Données ASFIM Réelles

Pour utiliser les données réelles au lieu des données mock:

1. Modifiez `config.py`:
```python
ASFIM_BASE_URL = "https://fundshare.asfim.ma"
```

2. Le collecteur tentera automatiquement de scraper le site
3. Si le format change, le système utilise un mapping flexible de colonnes

### 3. Données Maroclear

Placez votre fichier CSV dans `data/raw/maroclear_bonds.csv` avec les colonnes:
- `isin`: Code ISIN de l'obligation
- `taux_coupon`: Taux du coupon (%)
- `date_echeance`: Date d'échéance

## Sorties

### 1. opcvm_data.csv

Données OPCVM parsées avec:
- `date`, `nom_fonds`, `sdg`, `classification`
- `vl_jour`, `vl_precedente`, `variation_pct`
- `aum`, `flux_souscription`, `flux_rachat`, `flux_net`
- `taux_moyen_coupon`, `nb_isin_obligataires`

### 2. opcvm_enriched.csv

Données enrichies avec sentiment:
- Toutes les colonnes de opcvm_data.csv
- `score_sentiment_moyen_jour` (entre -1 et +1)
- `nb_actus_jour`: Nombre d'actualités
- `sources_actus`: Sources des actualités

### 3. signals_today.csv

Signaux de trading générés:
- `nom_fonds`: Nom du fonds
- `vl_actuelle`: VL actuelle (MAD)
- `vl_predite`: VL prédite pour J+1 (MAD)
- `variation_pct`: Variation prédite (%)
- `signal`: ACHETER / VENDRE / ATTENDRE

### 4. vl_prediction.png

Graphique montrant:
- VL réelle vs prédite
- Zones colorees par signal ([ACHETER], [VENDRE], [ATTENDRE])

## 🤖 Bot Telegram

### Rapport Quotidien Automatisé

Le bot envoie chaque jour à 18h00 (après clôture Bourse de Casablanca):

```
Rapport OPCVM Maroc — 28/04/2026
AUM Total : 245.67 Md MAD

ACHETER (12 fonds)
[ACHETER] BMCE Capital Actions
   VL: 1245.30 -> 1252.80 MAD
   Variation: +0.60% | Sentiment: Positif

ATTENDRE (25 fonds)
[ATTENDRE] CDG Capital Obligataire — VL stable

VENDRE (8 fonds)
[VENDRE] Wafa Gestion Monetaire
   VL: 1089.50 -> 1082.10 MAD
   Variation: -0.68% | Sentiment: Negatif

Top actualites du jour:
1. Bank Al-Maghrib maintient son taux directeur
   Score: +0.82 (Hausse)
```

### Exécution en Continu

```bash
python src/telegram_bot.py
```

Le bot s'exécute en boucle et vérifie chaque minute si c'est l'heure d'envoi.

## 🧠 Modèle LSTM

### Architecture

```
Input (30 jours, 7 features)
    ↓
LSTM (64 unités, return_sequences=True)
    ↓
Dropout (0.2)
    ↓
LSTM (32 unités)
    ↓
Dropout (0.2)
    ↓
Dense (1) → VL prédite J+1
```

### Features d'Entrée

1. `vl_jour`: Valeur liquidative du jour
2. `variation_pct`: Variation en pourcentage
3. `aum`: Actif sous gestion
4. `flux_net`: Flux nets (souscriptions - rachats)
5. `score_sentiment_moyen_jour`: Sentiment des actualités
6. `taux_moyen_coupon`: Taux moyen des obligations détenues
7. `nb_actus_jour`: Volume d'actualités

### Entraînement

- **Split:** 80% train, 20% test (chronologique)
- **Optimizer:** Adam
- **Loss:** MAE (Mean Absolute Error)
- **Epochs:** 50
- **Batch Size:** 32

## Sources de Donnees

### 1. ASFIM (fundshare.asfim.ma)
- 521 fonds OPCVM
- 18 sociétés de gestion (SDG)
- VL quotidiennes, AUM, flux

### 2. Maroclear
- 6,286 ISINs obligataires
- Taux coupon, échéances
- Caractéristiques des titres

### 3. Actualités Financières
- Médias24
- L'Économiste
- MAP (Maghreb Arabe Presse)

### 4. Modèles NLP

**Français:**
- `nlptown/bert-base-multilingual-uncased-sentiment`
- 5 classes (1-5 étoiles) → normalisé [-1, +1]

**Arabe:**
- `CAMeL-Lab/bert-base-arabic-camelbert-msa-sentiment`
- 3 classes (positive/negative/neutral)

## Limitations & Disclaimer

**Ce système est fourni à titre éducatif et de démonstration.**

- Les signaux générés ne constituent **PAS** des conseils d'investissement
- Consultez un **conseiller financier agréé par l'AMMC** avant toute décision
- Les performances passées ne préjugent pas des performances futures
- Le modèle LSTM est une approximation statistique, pas une prédiction certaine

## Depannage

### Erreur: Module not found

```bash
pip install -r requirements.txt
```

### Erreur: CUDA/GPU (TensorFlow)

Le modèle fonctionne sur CPU par défaut. Pour GPU:
```bash
pip install tensorflow-gpu
```

### Erreur: HuggingFace models

Vérifiez votre connexion Internet. Les modèles sont téléchargés au premier lancement (~500 MB).

### Bot Telegram ne fonctionne pas

1. Vérifiez le token dans `config.py`
2. Vérifiez que le bot n'est pas bloqué
3. Consultez `logs/telegram_log.csv` pour les erreurs

## 📅 Automatisation

### Windows (Task Scheduler)

1. Ouvrez Task Scheduler
2. Créez une tâche basique
3. Programmez: Tous les jours à 17h00
4. Action: `python.exe C:\Users\reda\Desktop\APP OPCVM MOROCCO\main.py`

### Linux (Cron)

```bash
crontab -e
# Ajouter: 0 17 * * * cd /path/to/OPCVM && python main.py
```

## 📞 Support

Pour toute question ou problème:
- Vérifiez la documentation ci-dessus
- Consultez les logs dans `logs/`
- Vérifiez les fichiers de sortie dans `outputs/`

## 📝 License

Projet éducatif - Usage non commercial

---

**Developpe pour l'analyse quantitative des OPCVM marocains**
