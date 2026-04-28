# pip install tensorflow scikit-learn pandas numpy matplotlib
"""
Modèle LSTM pour prédiction des VL OPCVM
Entraîne un réseau de neurones récurrent, génère des signaux de trading,
et produit des visualisations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta

# Import optionnel pour TensorFlow
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("INFO: tensorflow non disponible - utilisation du mode mock")

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LSTM_CONFIG, SIGNAL_THRESHOLD


class OPCVMLSTMModel:
    """Modèle LSTM pour prédiction VL OPCVM"""
    
    def __init__(self, window_size=None, output_dir="outputs"):
        """
        Initialise le modèle LSTM
        
        Args:
            window_size: Taille de la fenêtre glissante (défaut: 30)
            output_dir: Répertoire pour fichiers de sortie
        """
        self.window_size = window_size or LSTM_CONFIG['window_size']
        self.output_dir = output_dir
        self.scaler = MinMaxScaler()
        self.model = None
        os.makedirs(output_dir, exist_ok=True)
    
    def prepare_features(self, df):
        """
        Prépare les features d'entrée avec fenêtre glissante
        
        Args:
            df: DataFrame enrichi avec toutes les colonnes nécessaires
            
        Returns:
            tuple: (X, y, fonds_list) - Features, targets, liste des fonds
        """
        print("\nPréparation des features...")
        
        # Colonnes features
        features = ['vl_jour', 'variation_pct', 'aum', 'flux_net',
                    'score_sentiment_moyen_jour', 'taux_moyen_coupon', 'nb_actus_jour']
        
        # Vérification des colonnes
        missing = [f for f in features if f not in df.columns]
        if missing:
            print(f"Colonnes manquantes: {missing}")
            print("Ajout de valeurs par défaut...")
            for col in missing:
                df[col] = 0.0
        
        X, y, fonds_list = [], [], []
        
        for fonds in df['nom_fonds'].unique():
            df_fonds = df[df['nom_fonds'] == fonds].sort_values('date')
            
            if len(df_fonds) <= self.window_size:
                print(f"  {fonds}: pas assez de données ({len(df_fonds)} jours)")
                continue
            
            # Sélection des features
            data = df_fonds[features].values
            
            # Normalisation
            scaled_data = self.scaler.fit_transform(data)
            
            # Création des séquences
            for i in range(len(scaled_data) - self.window_size):
                X.append(scaled_data[i:i+self.window_size])
                y.append(df_fonds.iloc[i+self.window_size]['vl_jour'])  # vl_j_plus_1
                fonds_list.append(fonds)
        
        X = np.array(X)
        y = np.array(y)
        fonds_list = np.array(fonds_list)
        
        print(f"Features préparées: X={X.shape}, y={y.shape}")
        print(f"  Nombre de fonds: {len(np.unique(fonds_list))}")
        print(f"  Séquences totales: {len(X)}")
        
        return X, y, fonds_list
    
    def build_model(self, input_shape):
        """
        Architecture LSTM: 2 couches + Dropout + Dense
        
        Args:
            input_shape: Shape des données d'entrée (window_size, n_features)
            
        Returns:
            Model: Modèle Keras compilé
        """
        print("\nConstruction du modèle LSTM...")
        
        self.model = Sequential([
            LSTM(LSTM_CONFIG['lstm_units'][0], return_sequences=True, input_shape=input_shape),
            Dropout(LSTM_CONFIG['dropout']),
            LSTM(LSTM_CONFIG['lstm_units'][1], return_sequences=False),
            Dropout(LSTM_CONFIG['dropout']),
            Dense(1)
        ])
        
        self.model.compile(
            optimizer='adam',
            loss='mae',
            metrics=['mae']
        )
        
        print(f"Modèle construit:")
        print(f"  Input: {input_shape}")
        print(f"  LSTM 1: {LSTM_CONFIG['lstm_units'][0]} unités")
        print(f"  LSTM 2: {LSTM_CONFIG['lstm_units'][1]} unités")
        print(f"  Dropout: {LSTM_CONFIG['dropout']}")
        print(f"  Optimizer: Adam, Loss: MAE")
        
        self.model.summary()
        return self.model
    
    def train_evaluate(self, X, y, test_split=0.2):
        """
        Entraîne et évalue avec split chronologique 80/20
        
        Args:
            X: Features
            y: Targets
            test_split: Proportion test (défaut: 0.2)
            
        Returns:
            tuple: (mae, rmse, y_pred, y_test)
        """
        print("\nEntraînement du modèle...")
        
        # Split chronologique (pas aléatoire)
        split_idx = int(len(X) * (1 - test_split))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        print(f"  Train: {len(X_train)} samples")
        print(f"  Test: {len(X_test)} samples")
        
        # Construction du modèle
        if self.model is None:
            self.build_model(input_shape=(X_train.shape[1], X_train.shape[2]))
        
        # Entraînement
        history = self.model.fit(
            X_train, y_train,
            epochs=LSTM_CONFIG['epochs'],
            batch_size=LSTM_CONFIG['batch_size'],
            validation_split=0.1,
            verbose=1
        )
        
        # Prédiction
        print("\nPrédiction sur test set...")
        y_pred = self.model.predict(X_test)
        
        # Évaluation
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        
        print(f"\nÉvaluation:")
        print(f"  MAE: {mae:.4f}")
        print(f"  RMSE: {rmse:.4f}")
        
        return mae, rmse, y_pred.flatten(), y_test
    
    def generate_signals(self, y_pred, y_test, fonds_list):
        """
        Génère signaux ACHETER/VENDRE/ATTENDRE
        
        Args:
            y_pred: VL prédites
            y_test: VL réelles
            fonds_list: Liste des fonds
            
        Returns:
            pd.DataFrame: Signaux par fonds
        """
        print("\nGénération des signaux de trading...")
        
        signals = []
        threshold = SIGNAL_THRESHOLD  # 0.5%
        
        for i in range(len(y_pred)):
            vl_pred = y_pred[i]
            vl_actuelle = y_test[i]
            variation = (vl_pred - vl_actuelle) / vl_actuelle
            
            if variation > threshold:
                signal = 'ACHETER'
            elif variation < -threshold:
                signal = 'VENDRE'
            else:
                signal = 'ATTENDRE'
            
            signals.append({
                'nom_fonds': fonds_list[i],
                'vl_actuelle': round(vl_actuelle, 2),
                'vl_predite': round(vl_pred, 2),
                'variation_pct': round(variation * 100, 3),
                'signal': signal
            })
        
        df_signals = pd.DataFrame(signals)
        
        # Statistiques
        n_acheter = len(df_signals[df_signals['signal'] == 'ACHETER'])
        n_vendre = len(df_signals[df_signals['signal'] == 'VENDRE'])
        n_attendre = len(df_signals[df_signals['signal'] == 'ATTENDRE'])
        
        print(f"Signaux générés:")
        print(f"  ACHETER: {n_acheter} fonds")
        print(f"  VENDRE: {n_vendre} fonds")
        print(f"  ATTENDRE: {n_attendre} fonds")
        
        return df_signals
    
    def plot_predictions(self, y_test, y_pred, save_path=None):
        """
        Graphique VL réelle vs prédite + zones de signal colorées
        
        Args:
            y_test: VL réelles
            y_pred: VL prédites
            save_path: Chemin de sauvegarde du graphique
        """
        if save_path is None:
            save_path = os.path.join(self.output_dir, "vl_prediction.png")
        
        print("\nGénération du graphique...")
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # Graphique 1: VL Réelle vs Prédite
        axes[0].plot(y_test, label='VL Réelle', linewidth=2, color='blue')
        axes[0].plot(y_pred, label='VL Prédite', linewidth=2, color='red', linestyle='--')
        axes[0].set_title('OPCVM Maroc - VL Réelle vs Prédite (LSTM)', fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Sample Index')
        axes[0].set_ylabel('VL (MAD)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Graphique 2: Zones de signal
        # Calcul des signaux pour coloration
        signals = []
        for i in range(len(y_pred)):
            variation = (y_pred[i] - y_test[i]) / y_test[i]
            if variation > SIGNAL_THRESHOLD:
                signals.append(1)  # ACHETER
            elif variation < -SIGNAL_THRESHOLD:
                signals.append(-1)  # VENDRE
            else:
                signals.append(0)  # ATTENDRE
        
        signals = np.array(signals)
        
        # Zones colorées
        for i in range(len(y_test)):
            if signals[i] == 1:
                axes[1].axvspan(i-0.5, i+0.5, alpha=0.3, color='green')
            elif signals[i] == -1:
                axes[1].axvspan(i-0.5, i+0.5, alpha=0.3, color='red')
            else:
                axes[1].axvspan(i-0.5, i+0.5, alpha=0.1, color='gray')
        
        axes[1].plot(y_test, label='VL Réelle', linewidth=2, color='blue', alpha=0.7)
        axes[1].set_title('Zones de Signal: ACHETER | VENDRE | ATTENDRE', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Sample Index')
        axes[1].set_ylabel('VL (MAD)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Graphique sauvegardé: {save_path}")
    
    def run_pipeline(self, enriched_data_path):
        """
        Pipeline complet: Load → Prepare → Train → Evaluate → Signal → Plot → Save
        
        Args:
            enriched_data_path: Chemin vers opcvm_enriched.csv
            
        Returns:
            pd.DataFrame: Signaux générés
        """
        print("="*60)
        print("PIPELINE MODÈLE LSTM")
        print("="*60)
        
        # Étape 1: Chargement des données
        print(f"\nChargement des données: {enriched_data_path}")
        df = pd.read_csv(enriched_data_path)
        print(f"✓ Données chargées: {df.shape[0]} lignes, {df.shape[1]} colonnes")
        
        # Pour la démo, on génère des données historiques simulées
        # (Dans la réalité, il faut accumuler les données jour après jour)
        if len(df) < 100:
            print("\nPas assez de données historiques, génération de séries temporelles simulées...")
            df = self.generate_historical_data(df)
        
        # Étape 2: Préparation des features
        X, y, fonds_list = self.prepare_features(df)
        
        if len(X) == 0:
            print("Pas assez de donnees pour entrainer le modele")
            print("Génération de signaux mock pour démonstration...")
            return self.generate_mock_signals(df)
        
        # Étape 3: Entraînement et évaluation
        mae, rmse, y_pred, y_test = self.train_evaluate(X, y)
        
        # Étape 4: Génération des signaux
        df_signals = self.generate_signals(y_pred, y_test, fonds_list)
        
        # Étape 5: Visualisation
        self.plot_predictions(y_test, y_pred)
        
        # Étape 6: Sauvegarde du modèle
        model_path = os.path.join(self.output_dir, "model_opcvm.h5")
        self.model.save(model_path)
        print(f"\n✓ Modèle sauvegardé: {model_path}")
        
        # Étape 7: Sauvegarde des signaux
        signals_path = os.path.join(self.output_dir, "signals_today.csv")
        df_signals.to_csv(signals_path, index=False, encoding='utf-8')
        print(f"✓ Signaux sauvegardés: {signals_path}")
        
        print(f"\n{'='*60}")
        print(f"RÉSUMÉ LSTM")
        print(f"{'='*60}")
        print(f"MAE: {mae:.4f}")
        print(f"RMSE: {rmse:.4f}")
        print(f"Signaux ACHETER: {len(df_signals[df_signals['signal'] == 'ACHETER'])}")
        print(f"Signaux VENDRE: {len(df_signals[df_signals['signal'] == 'VENDRE'])}")
        print(f"Signaux ATTENDRE: {len(df_signals[df_signals['signal'] == 'ATTENDRE'])}")
        
        return df_signals
    
    def generate_historical_data(self, df_base, n_days=60):
        """
        Génère des données historiques simulées pour entraînement
        
        Args:
            df_base: DataFrame de base avec les fonds
            n_days: Nombre de jours d'historique
            
        Returns:
            pd.DataFrame: Données historiques
        """
        print(f"Génération de {n_days} jours d'historique simulé...")
        
        np.random.seed(42)
        historical_data = []
        
        for _, row in df_base.iterrows():
            vl_current = row['vl_jour']
            
            for day in range(n_days):
                date = (datetime.now() - timedelta(days=n_days-day)).strftime('%Y-%m-%d')
                
                # Simulation de variation réaliste
                variation = np.random.uniform(-1.5, 1.5)
                vl_prev = vl_current / (1 + variation/100)
                
                historical_data.append({
                    'date': date,
                    'nom_fonds': row['nom_fonds'],
                    'sdg': row.get('sdg', 'Inconnu'),
                    'classification': row.get('classification', 'Diversifié'),
                    'vl_jour': round(vl_current, 2),
                    'vl_precedente': round(vl_prev, 2),
                    'variation_pct': round(variation, 2),
                    'aum': row.get('aum', 100_000_000),
                    'flux_souscription': row.get('flux_souscription', 0),
                    'flux_rachat': row.get('flux_rachat', 0),
                    'flux_net': row.get('flux_net', 0),
                    'taux_moyen_coupon': row.get('taux_moyen_coupon', 3.5),
                    'nb_isin_obligataires': row.get('nb_isin_obligataires', 0),
                    'score_sentiment_moyen_jour': np.random.uniform(-0.5, 0.8),
                    'nb_actus_jour': np.random.randint(0, 10),
                    'sources_actus': 'medias24, leconomiste'
                })
                
                # VL pour le jour suivant
                vl_current = vl_current * (1 + np.random.uniform(-0.01, 0.012))
        
        df_hist = pd.DataFrame(historical_data)
        print(f"✓ Données historiques: {df_hist.shape[0]} lignes")
        
        return df_hist
    
    def generate_mock_signals(self, df):
        """
        Génère des signaux mock si pas assez de données
        
        Args:
            df: DataFrame des fonds
            
        Returns:
            pd.DataFrame: Signaux mock
        """
        print("Génération de signaux de démonstration...")
        
        np.random.seed(42)
        signals = []
        
        for _, row in df.iterrows():
            variation = np.random.uniform(-2, 2)
            vl_pred = row['vl_jour'] * (1 + variation/100)
            
            if variation > 0.5:
                signal = 'ACHETER'
            elif variation < -0.5:
                signal = 'VENDRE'
            else:
                signal = 'ATTENDRE'
            
            signals.append({
                'nom_fonds': row['nom_fonds'],
                'vl_actuelle': row['vl_jour'],
                'vl_predite': round(vl_pred, 2),
                'variation_pct': round(variation, 3),
                'signal': signal
            })
        
        df_signals = pd.DataFrame(signals)
        
        # Sauvegarde
        signals_path = os.path.join(self.output_dir, "signals_today.csv")
        df_signals.to_csv(signals_path, index=False, encoding='utf-8')
        print(f"✓ Signaux mock sauvegardés: {signals_path}")
        
        # Graphique mock
        self.plot_mock_prediction(df)
        
        return df_signals
    
    def plot_mock_prediction(self, df):
        """
        Génère un graphique mock pour démonstration
        
        Args:
            df: DataFrame des fonds
        """
        save_path = os.path.join(self.output_dir, "vl_prediction.png")
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Simulation VL réelle et prédite
        n_points = 50
        vl_reelle = np.cumsum(np.random.randn(n_points)) + 1000
        vl_predite = vl_reelle + np.random.randn(n_points) * 5
        
        ax.plot(vl_reelle, label='VL Réelle', linewidth=2, color='blue')
        ax.plot(vl_predite, label='VL Prédite (LSTM)', linewidth=2, color='red', linestyle='--')
        ax.set_title('OPCVM Maroc - VL Réelle vs Prédite (Démo)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Jour')
        ax.set_ylabel('VL (MAD)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Graphique démo sauvegardé: {save_path}")


if __name__ == "__main__":
    model = OPCVMLSTMModel()
    model.run_pipeline("outputs/opcvm_enriched.csv")
