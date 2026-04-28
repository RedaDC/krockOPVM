# pip install pandas numpy
"""
Guide d'installation complète - OPCVM Analytics Maroc

Ce script vérifie les dépendances et guide l'installation.
"""

import sys
import subprocess

def check_module(module_name, install_name=None):
    """Vérifie si un module est installé"""
    if install_name is None:
        install_name = module_name
    
    try:
        __import__(module_name)
        print(f"✓ {module_name}")
        return True
    except ImportError:
        print(f"✗ {module_name} - NON INSTALLÉ")
        return False

def main():
    print("="*60)
    print("VÉRIFICATION DES DÉPENDANCES")
    print("="*60)
    
    modules = {
        'pandas': 'pandas',
        'numpy': 'numpy',
        'requests': 'requests',
        'bs4': 'beautifulsoup4',
        'openpyxl': 'openpyxl',
        'feedparser': 'feedparser',
        'langdetect': 'langdetect',
        'sklearn': 'scikit-learn',
        'matplotlib': 'matplotlib',
        'schedule': 'schedule',
        'tensorflow': 'tensorflow',
        'torch': 'torch',
        'transformers': 'transformers',
        'telegram': 'python-telegram-bot'
    }
    
    print("\nVérification des modules:\n")
    
    installed = {}
    for module, install_name in modules.items():
        installed[module] = check_module(module, install_name)
    
    # Résumé
    missing = [name for name, status in installed.items() if not status]
    
    print(f"\n{'='*60}")
    print("RÉSUMÉ")
    print(f"{'='*60}")
    
    if not missing:
        print("\n✓ Tous les modules sont installés!")
        print("Vous pouvez exécuter: python main.py")
        return
    
    print(f"\nModules manquants: {len(missing)}/{len(modules)}")
    
    # Installation par catégorie
    print("\n" + "="*60)
    print("INSTALLATION RECOMMANDÉE")
    print("="*60)
    
    print("\n1. Installation de base (requis pour fonctionner):")
    print("   pip install pandas numpy requests beautifulsoup4 openpyxl feedparser langdetect scikit-learn matplotlib schedule")
    
    print("\n2. Pour le modèle LSTM (optionnel, ~2 GB):")
    print("   pip install tensorflow")
    print("   OU (si erreur Windows Long Path):")
    print("   - Activer Long Paths: https://pip.pypa.io/warnings/enable-long-paths")
    print("   - OU utiliser Google Colab pour l'entraînement")
    
    print("\n3. Pour l'analyse de sentiment (optionnel, ~1 GB):")
    print("   pip install torch transformers")
    
    print("\n4. Pour le bot Telegram (optionnel):")
    print("   pip install python-telegram-bot")
    
    print("\n" + "="*60)
    print("INSTALLATION AUTOMATIQUE")
    print("="*60)
    
    response = input("\nVoulez-vous installer les modules de base maintenant? (o/n): ")
    
    if response.lower() == 'o':
        print("\nInstallation en cours...")
        
        basic_packages = [
            'pandas', 'numpy', 'requests', 'beautifulsoup4',
            'openpyxl', 'feedparser', 'langdetect',
            'scikit-learn', 'matplotlib', 'schedule'
        ]
        
        for package in basic_packages:
            if not installed.get(package.split('.')[0], True):
                print(f"Installation de {package}...")
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                    print(f"✓ {package} installé")
                except Exception as e:
                    print(f"✗ Erreur installation {package}: {e}")
        
        print("\n✓ Installation terminée!")
        print("Exécutez: python main.py")
    else:
        print("\nInstallation annulée.")
        print("Pour installer manuellement:")
        print("  pip install -r requirements.txt")


if __name__ == "__main__":
    main()
