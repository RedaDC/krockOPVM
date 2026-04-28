# Guide de Demarrage Rapide - OPCVM Analytics Maroc

## Statut: SYSTEME OPERATIONNEL

Le pipeline a été testé avec succès le 28/04/2026 à 10:47.

---

## Installation (5 minutes)

### 1. Installation de base (OBLIGATOIRE)

```bash
pip install pandas numpy requests beautifulsoup4 openpyxl feedparser langdetect scikit-learn matplotlib schedule
```

**Statut:** ✓ Déjà installé et testé

### 2. Modèle LSTM (OPTIONNEL - pour prédiction avancée)

```bash
pip install tensorflow
```

**Note:** Si vous rencontrez une erreur "Windows Long Path":
- Solution 1: Activer les longs chemins Windows: [Guide Microsoft](https://pip.pypa.io/warnings/enable-long-paths)
- Solution 2: Utiliser Google Colab pour l'entraînement
- Solution 3: Utiliser le mode mock (fonctionne déjà ✓)

### 3. Analyse de Sentiment (OPTIONNEL - pour NLP avancé)

```bash
pip install torch transformers
```

**Note:** ~1 GB de téléchargement. Le système fonctionne en mode mock sans ces modules.

### 4. Bot Telegram (OPTIONNEL - pour rapports automatisés)

```bash
pip install python-telegram-bot
```

---

## Execution

### Mode Complet (Recommandé)

```bash
python main.py
```

**Sortie attendue:**
```
PIPELINE TERMINE AVEC SUCCES

Fichiers generes:
   • Données OPCVM: outputs/opcvm_data.csv
   • Données enrichies: outputs/opcvm_enriched.csv
   • Signaux de trading: outputs/signals_today.csv
   • Modèle LSTM: outputs/model_opcvm.h5 (si tensorflow installé)
   • Graphique: outputs/vl_prediction.png (si matplotlib)
   • Log Telegram: logs/telegram_log.csv
```

### Test Résultat (28/04/2026)

```
✓ Étape 1: Collecte ASFIM & Maroclear - 50 fonds générés
✓ Étape 2: Analyse sentiment - 20 articles mock
✓ Étape 3: Signaux de trading - 50 signaux générés
  - ACHETER: 9 fonds
  - VENDRE: 16 fonds
  - ATTENDRE: 25 fonds
✓ Étape 4: Rapport Telegram - 3446 caractères
```

---

## Fichiers de Sortie

### 1. outputs/opcvm_data.csv (7.3 KB)

**Colonnes:**
- `date`: Date des données
- `nom_fonds`: Nom du fonds OPCVM
- `sdg`: Société de gestion
- `classification`: Type de fonds (Actions, Obligataire, etc.)
- `vl_jour`: Valeur liquidative du jour
- `vl_precedente`: VL de la veille
- `variation_pct`: Variation en %
- `aum`: Actif sous gestion
- `flux_souscription`: Flux de souscriptions
- `flux_rachat`: Flux de rachats
- `flux_net`: Flux nets (souscription - rachat)
- `taux_moyen_coupon`: Taux moyen des obligations
- `nb_isin_obligataires`: Nombre d'ISINs obligataires

### 2. outputs/opcvm_enriched.csv (9.2 KB)

**Colonnes additionnelles:**
- `score_sentiment_moyen_jour`: Sentiment moyen [-1, +1]
- `nb_actus_jour`: Nombre d'actualités
- `sources_actus`: Sources des actualités

### 3. outputs/signals_today.csv (2.3 KB)

**Structure:**
```csv
nom_fonds,vl_actuelle,vl_predite,variation_pct,signal
Fonds OPCVM 001,1000.00,1005.50,+0.55,ACHETER
Fonds OPCVM 002,742.95,738.20,-0.64,VENDRE
Fonds OPCVM 003,890.30,891.10,+0.09,ATTENDRE
```

### 4. outputs/news_sentiment.csv (4.0 KB)

Articles collectés avec:
- Source, titre, résumé
- Langue détectée (fr/ar)
- Score de sentiment

---

## Configuration Avancee

### Activer le Bot Telegram

1. **Créer un bot:**
   - Ouvrez Telegram et cherchez @BotFather
   - Envoyez `/newbot`
   - Suivez les instructions
   - Copiez le token reçu

2. **Obtenir votre Chat ID:**
   - Envoyez un message à votre bot
   - Visitez: `https://api.telegram.org/bot<VOTRE_TOKEN>/getUpdates`
   - Cherchez: `"chat":{"id":123456789,...}`

3. **Modifier config.py:**
```python
TELEGRAM = {
    'token': "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ",
    'chat_id': "987654321",
    'report_time': "18:00"
}
```

4. **Exécuter le bot:**
```bash
python src/telegram_bot.py
```

### Utiliser des Données Réelles

#### ASFIM

Le collecteur tente automatiquement de scraper fundshare.asfim.ma.

Si le fichier est disponible localement:
```python
# Dans src/asfim_maroclear_collector.py
collector.run_pipeline(file_url="chemin/vers/fichier.xlsx")
```

#### Maroclear

Placez votre fichier CSV dans `data/raw/maroclear_bonds.csv`:

```csv
isin,taux_coupon,date_echeance
MA0000012345,3.5,2030-12-31
MA0000067890,4.2,2035-06-15
```

---

## Prochaines Etapes

### Pour Améliorer le Système

1. **Accumuler des données historiques:**
   - Exécutez `python main.py` chaque jour
   - Les données s'accumuleront pour un meilleur entraînement LSTM

2. **Entraîner le modèle LSTM:**
   - Installez TensorFlow
   - Le modèle apprendra automatiquement avec plus de données

3. **Activer l'analyse de sentiment:**
   - Installez transformers + torch
   - Les modèles HuggingFace analyseront les actualités en temps réel

4. **Automatiser l'exécution:**
   - Windows: Task Scheduler → `python main.py` à 17h00
   - Linux: Cron job `0 17 * * * cd /path && python main.py`

---

## Resolution de Problemes

### Erreur: ModuleNotFoundError

```bash
pip install -r requirements.txt
```

OU

```bash
python install_guide.py
```

### Erreur: TensorFlow sur Windows

**Solution 1:** Activer les longs chemins
1. Ouvrez l'éditeur de registre (regedit)
2. Naviguez vers: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`
3. Modifiez `LongPathsEnabled` de 0 à 1
4. Redémarrez

**Solution 2:** Utiliser le mode mock (déjà activé ✓)

### Bot Telegram ne fonctionne pas

1. Vérifiez le token dans `config.py`
2. Vérifiez que vous avez envoyé un message au bot
3. Consultez `logs/telegram_log.csv` pour les erreurs

---

## 📞 Support

### Fichiers de Log

- **Telegram:** `logs/telegram_log.csv`
- **Console:** Sortie standard de `python main.py`

### Vérification des Dépendances

```bash
python install_guide.py
```

Ce script vérifie tous les modules et propose l'installation automatique.

---

## 📝 Notes Importantes

**Disclaimer:** Ce système est fourni à titre éducatif.

- Les signaux ne constituent PAS des conseils d'investissement
- Consultez un conseiller financier agréé par l'AMMC
- Les performances passées ne préjugent pas des performances futures
- Le mode mock est actif par défaut pour la démonstration

---

## 🎉 Félicitations!

Votre système OPCVM Analytics Maroc est opérationnel!

**Prochaine action recommandée:**
```bash
# Exécutez le pipeline complet
python main.py

# Consultez les signaux
python -c "import pandas as pd; print(pd.read_csv('outputs/signals_today.csv'))"
```

---

**Developpe pour l'analyse quantitative des OPCVM marocains**

*Dernière mise à jour: 28/04/2026*
