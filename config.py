# Configuration centrale - OPCVM Analytics Maroc

# URLs de données
ASFIM_BASE_URL = "https://fundshare.asfim.ma"
MAROCLEAR_DATA_PATH = "data/raw/maroclear_bonds.csv"
BKAM_URL = "https://www.bkam.ma"
MASI_URL = "https://www.casablanca-bourse.com"

# Mots-clés pour collecte actualités
SENTIMENT_KEYWORDS = [
    "OPCVM", "bourse", "BAM", "Bank Al-Maghrib", "investis",
    "taux", "obligataire", "actions", "Maroc", "économie", "croissance"
]

# Seuil pour signaux de trading (0.5%) - SERA REMPLACÉ PAR DYNAMIC_THRESHOLDS
SIGNAL_THRESHOLD = 0.005

# Configuration LSTM
LSTM_CONFIG = {
    'window_size': 30,
    'lstm_units': [64, 32],
    'dropout': 0.2,
    'epochs': 50,
    'batch_size': 32
}

# Configuration Telegram
TELEGRAM = {
    'token': '8702694582:AAHp0VEX6JhYlUzvn2MViWqBj7FrMRKQpVs',
    'chat_id': '5334121900',
    'report_time': '18:00'
}

# Flux RSS actualités marocaines
RSS_FEEDS = {
    'medias24': 'https://medias24.com/feed',
    'leconomiste': 'https://www.leconomiste.com/rss.xml',
    'map': 'https://www.mapexpress.ma/feed'
}

# Délai entre requêtes web (secondes)
REQUEST_DELAY = 2

# =====================================================
# NOUVELLES CONFIGURATIONS PRODUCTION
# =====================================================

# Frais OPCVM par classification (grilles AMMC typiques)
FRAIS_OPCVM = {
    'Actions': {'souscription': 2.0, 'rachat': 1.0, 'delai_liquidite': 3},
    'Actions Maroc': {'souscription': 2.0, 'rachat': 1.0, 'delai_liquidite': 3},
    'Obligataire': {'souscription': 1.0, 'rachat': 0.5, 'delai_liquidite': 3},
    'Obligataire LT': {'souscription': 1.0, 'rachat': 0.5, 'delai_liquidite': 3},
    'Obligataire CT': {'souscription': 0.5, 'rachat': 0.3, 'delai_liquidite': 2},
    'Monétaire': {'souscription': 0.1, 'rachat': 0.05, 'delai_liquidite': 1},
    'Diversifié': {'souscription': 1.5, 'rachat': 0.8, 'delai_liquidite': 3},
    'Immobilier': {'souscription': 2.5, 'rachat': 1.5, 'delai_liquidite': 5},
    'Sukuk': {'souscription': 1.0, 'rachat': 0.5, 'delai_liquidite': 3},
}

# Marge de sécurité pour seuils (%)
MARGE_SECURITE = 0.2

# Keywords d'impact par classification pour sentiment spécialisé
IMPACT_KEYWORDS = {
    'Obligataire': {
        'positif': ['baisse taux directeur', 'bank al-maghrib réduit', 'déflation', 'bons du trésor sursouscrit', 'taux bas'],
        'negatif': ['hausse taux', 'inflation', 'déficit budgétaire', 'dégradation notation', 'récession']
    },
    'Obligataire LT': {
        'positif': ['baisse taux directeur', 'bank al-maghrib réduit', 'déflation', 'bons du trésor sursouscrit'],
        'negatif': ['hausse taux', 'inflation', 'déficit budgétaire', 'dégradation notation']
    },
    'Obligataire CT': {
        'positif': ['liquidité abondante', 'taux stables', 'bank al-maghrib'],
        'negatif': ['crise liquidité', 'hausse taux court', 'tension monétaire']
    },
    'Actions': {
        'positif': ['croissance pib', 'résultats bénéficiaires', 'hausse bourse', 'investissements étrangers', 'performance records'],
        'negatif': ['récession', 'pertes', 'faillite', 'ralentissement économique', 'crise financière']
    },
    'Actions Maroc': {
        'positif': ['croissance pib', 'masi hausse', 'résultats bénéficiaires', 'investissements étrangers'],
        'negatif': ['récession', 'pertes', 'faillite', 'tension géopolitique']
    },
    'Monétaire': {
        'positif': [],  # quasi insensible
        'negatif': ['crise liquidité', 'défaut paiement', 'risque systémique']
    },
    'Diversifié': {
        'positif': ['croissance', 'stabilité', 'performance', 'équilibre'],
        'negatif': ['crise', 'volatilité', 'incertitude', 'turbulences']
    },
    'Immobilier': {
        'positif': ['hausse prix immobilier', 'demande forte', 'construction'],
        'negatif': ['crise immobilière', 'bulle spéculative', 'effondrement prix']
    },
    'Sukuk': {
        'positif': ['finance islamique', 'demande sukuk', 'croissance'],
        'negatif': ['crise financière', 'défaut', 'instabilité']
    }
}

# Poids pour score hybride sentiment
Poids_BERT = 0.4
POIDS_KEYWORDS = 0.6

# Jours fériés marocains (dates fixes, variables calculées dynamiquement)
JOURS_FERIES_FIXES = {
    'Fête du Trône': [(7, 30)],
    'Marche Verte': [(11, 6)],
    'Fête de l\'Indépendance': [(11, 18)],
    'Nouvel An': [(1, 1)],
    'Fête du Travail': [(5, 1)],
}

# Historique date range
HISTORICAL_START_DATE = '2023-01-01'
HISTORICAL_DELAY = 3  # secondes entre requêtes
