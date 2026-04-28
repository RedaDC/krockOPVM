"""
OPCVM Analytics Maroc - Complete Local Launcher
Runs the full system with all ML frameworks locally
"""

import subprocess
import sys
import os
from datetime import datetime

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def check_installation():
    """Check if all required packages are installed"""
    print_header("CHECKING INSTALLATION")
    
    required_packages = {
        'pandas': 'Data processing',
        'numpy': 'Numerical computing',
        'tensorflow': 'Deep Learning (LSTM)',
        'torch': 'PyTorch (NLP)',
        'transformers': 'HuggingFace models',
        'sklearn': 'Machine learning',
        'matplotlib': 'Visualization',
        'plotly': 'Interactive charts',
        'streamlit': 'Web dashboard',
        'telegram': 'Telegram bot',
    }
    
    missing = []
    installed = []
    
    for package, description in required_packages.items():
        try:
            if package == 'sklearn':
                __import__('sklearn')
            elif package == 'telegram':
                __import__('telegram')
            else:
                __import__(package)
            installed.append((package, description))
            print(f"  [OK] {package:20s} - {description}")
        except ImportError:
            missing.append((package, description))
            print(f"  [MISSING] {package:20s} - {description}")
    
    print(f"\nInstalled: {len(installed)}/{len(required_packages)}")
    
    if missing:
        print(f"\nMissing packages: {', '.join([p[0] for p in missing])}")
        return False
    return True

def install_dependencies():
    """Install all dependencies from requirements_full.txt"""
    print_header("INSTALLING DEPENDENCIES")
    
    if not os.path.exists('requirements_full.txt'):
        print("ERROR: requirements_full.txt not found!")
        return False
    
    print("Installing full dependencies (this may take 10-30 minutes)...")
    print("Downloading TensorFlow (~500MB), PyTorch (~800MB), Transformers (~500MB)...\n")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements_full.txt'
        ])
        print("\nInstallation complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nInstallation failed: {e}")
        return False

def run_pipeline():
    """Run the complete OPCVM analytics pipeline"""
    print_header("RUNNING COMPLETE PIPELINE")
    
    print("Step 1: Data Collection (ASFIM & Maroclear)")
    print("-" * 70)
    try:
        result = subprocess.run([sys.executable, 'main.py'], capture_output=False)
        if result.returncode != 0:
            print(f"\nPipeline failed with code {result.returncode}")
            return False
    except Exception as e:
        print(f"Pipeline error: {e}")
        return False
    
    return True

def run_streamlit():
    """Run Streamlit dashboard"""
    print_header("STARTING STREAMLIT DASHBOARD")
    
    print("Opening dashboard at http://localhost:8501")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 'streamlit_app.py',
            '--server.headless', 'true'
        ])
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    except Exception as e:
        print(f"Error starting Streamlit: {e}")

def run_telegram_bot():
    """Run Telegram bot"""
    print_header("STARTING TELEGRAM BOT")
    
    print("Starting Telegram bot for daily reports at 18:00...")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run([
            sys.executable, 'src/telegram_bot.py'
        ])
    except KeyboardInterrupt:
        print("\nBot stopped.")
    except Exception as e:
        print(f"Error starting bot: {e}")

def run_single_module(module_name):
    """Run a single module"""
    print_header(f"RUNNING: {module_name}")
    
    module_path = f"src/{module_name}.py"
    
    if not os.path.exists(module_path):
        print(f"ERROR: Module {module_path} not found!")
        return False
    
    try:
        subprocess.run([sys.executable, module_path])
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def show_menu():
    """Show interactive menu"""
    print_header("OPCVM ANALYTICS MAROC - LOCAL LAUNCHER")
    
    while True:
        print("\nSelect an option:")
        print("  1. Check installation")
        print("  2. Install all dependencies (requirements_full.txt)")
        print("  3. Run complete pipeline (main.py)")
        print("  4. Start Streamlit dashboard")
        print("  5. Start Telegram bot")
        print("  6. Run historical data collector")
        print("  7. Run sentiment analysis pipeline")
        print("  8. Run LSTM model training")
        print("  9. Run backtesting")
        print("  10. Run dynamic thresholds")
        print("  0. Exit")
        print()
        
        try:
            choice = input("Enter choice [0-10]: ").strip()
            
            if choice == '0':
                print("\nGoodbye!")
                break
            elif choice == '1':
                check_installation()
            elif choice == '2':
                if install_dependencies():
                    print("\nInstallation successful! Run option 1 to verify.")
                else:
                    print("\nInstallation failed. Check error messages above.")
            elif choice == '3':
                run_pipeline()
            elif choice == '4':
                run_streamlit()
            elif choice == '5':
                run_telegram_bot()
            elif choice == '6':
                run_single_module('historical_collector')
            elif choice == '7':
                run_single_module('news_sentiment_pipeline')
            elif choice == '8':
                run_single_module('lstm_model')
            elif choice == '9':
                run_single_module('backtester')
            elif choice == '10':
                run_single_module('dynamic_thresholds')
            else:
                print("Invalid choice. Please try again.")
                
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
            continue
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # If argument provided, run directly
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == '--install':
            install_dependencies()
        elif action == '--check':
            if not check_installation():
                sys.exit(1)
        elif action == '--pipeline':
            run_pipeline()
        elif action == '--streamlit':
            run_streamlit()
        elif action == '--telegram':
            run_telegram_bot()
        else:
            print(f"Unknown action: {action}")
            print("Use --install, --check, --pipeline, --streamlit, or --telegram")
            sys.exit(1)
    else:
        # Show interactive menu
        show_menu()
