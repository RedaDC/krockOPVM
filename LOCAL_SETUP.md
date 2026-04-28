# Local Setup Guide - Complete Version (2+ GB)

## Overview

This guide helps you run the **complete** OPCVM Analytics system locally with all ML frameworks:
- TensorFlow (LSTM models)
- PyTorch (NLP/Sentiment analysis)
- Transformers (HuggingFace models)
- All data collection and backtesting tools

## System Requirements

- **Python:** 3.9 - 3.11 (3.12 may have compatibility issues)
- **RAM:** 8 GB minimum, 16 GB recommended
- **Disk Space:** 5 GB free (for dependencies + data)
- **Internet:** Required for downloading models (~2-3 GB)
- **OS:** Windows 10/11, macOS, or Linux

## Quick Start (Windows)

### Option 1: Using Batch Script (Recommended)

1. **Double-click** `start.bat`
2. The script will:
   - Create a virtual environment
   - Check if dependencies are installed
   - Offer to install them if missing
   - Show an interactive menu

3. **Select options from the menu:**
   ```
   1. Run complete pipeline (all steps)
   2. Start Streamlit dashboard
   3. Start Telegram bot
   4. Run historical data collector
   5. Run sentiment analysis
   6. Run LSTM model training
   7. Run backtesting
   8. Check installation
   0. Exit
   ```

### Option 2: Manual Installation

#### Step 1: Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

#### Step 2: Install Full Dependencies

```bash
pip install -r requirements_full.txt
```

**This will download:**
- TensorFlow: ~500 MB
- PyTorch: ~800 MB
- Transformers: ~500 MB
- Other packages: ~200 MB

**Total:** ~2-3 GB  
**Time:** 10-30 minutes (depends on internet speed)

#### Step 3: Verify Installation

```bash
python launch_local.py --check
```

Expected output:
```
[OK] tensorflow           - Deep Learning (LSTM)
[OK] torch                - PyTorch (NLP)
[OK] transformers         - HuggingFace models
[OK] sklearn              - Machine learning
...
```

## Run the Complete Pipeline

### Method 1: Interactive Launcher

```bash
python launch_local.py
```

Then select option 3 for complete pipeline.

### Method 2: Direct Command

```bash
python launch_local.py --pipeline
```

### Method 3: Run main.py Directly

```bash
python main.py
```

**With optional flags:**
```bash
# Run with historical data collection
python main.py --historical

# Run with backtesting
python main.py --backtest

# Run with mock data (faster)
python main.py --mock
```

## Run Individual Components

### 1. Historical Data Collector

```bash
python src/historical_collector.py
```

**Output:**
- `data/processed/opcvm_historique_complet.csv`
- `outputs/data_quality_report.csv`

### 2. Sentiment Analysis Pipeline

```bash
python src/news_sentiment_pipeline.py
```

**Downloads:**
- French sentiment model: ~440 MB
- Arabic sentiment model: ~440 MB

**Output:**
- `outputs/opcvm_enriched.csv`

### 3. LSTM Model Training

```bash
python src/lstm_model.py
```

**Output:**
- `outputs/model_opcvm.h5` (trained model)
- `outputs/signals_today.csv` (trading signals)
- `outputs/vl_prediction.png` (chart)

### 4. Backtesting

```bash
python src/backtester.py
```

**Output:**
- `outputs/backtest_results.csv`
- `outputs/backtest_report.png`
- Console: Go/No-Go decision

### 5. Dynamic Thresholds

```bash
python src/dynamic_thresholds.py
```

**Output:**
- Enriched `outputs/signals_today.csv` with fee-aware signals

### 6. Streamlit Dashboard

```bash
streamlit run streamlit_app.py
```

Opens at: http://localhost:8501

### 7. Telegram Bot

```bash
python src/telegram_bot.py
```

Runs continuously, sends daily reports at 18:00.

## Configuration

### 1. Telegram Bot Setup

Edit `config.py`:

```python
TELEGRAM = {
    'token': "YOUR_BOT_TOKEN",  # Get from @BotFather
    'chat_id': "YOUR_CHAT_ID",
    'report_time': "18:00"
}
```

**To get a bot token:**
1. Open Telegram, search for @BotFather
2. Send `/newbot`
3. Follow instructions
4. Copy the token

### 2. Data Sources

The system uses **mock data** by default. To use real data:

#### ASFIM Data
Update URLs in `config.py`:
```python
ASFIM_BASE_URL = "https://fundshare.asfim.ma"
```

#### Maroclear Data
Place CSV file at: `data/raw/maroclear_bonds.csv`

Format:
```csv
isin,taux_coupon,date_echeance,nature
MA0000000000,3.5,2030-12-31,Bon du Tresor
...
```

## Performance Tips

### Speed Up Installation

**Install TensorFlow CPU-only (smaller):**
```bash
pip install tensorflow-cpu
```

**Install PyTorch CPU-only (smaller):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**Saves:** ~1 GB disk space

### Speed Up Execution

**Use mock data for testing:**
```bash
python main.py --mock
```

**Skip sentiment analysis (slow):**
Comment out step 2 in `main.py`

**Use fewer epochs for LSTM:**
Edit `config.py`:
```python
LSTM_CONFIG = {
    'epochs': 10,  # Instead of 50
    ...
}
```

### Reduce Memory Usage

**Close other applications** before running:
- Web browsers
- IDEs
- Other Python processes

**Expected memory usage:**
- Data collection: ~500 MB
- Sentiment analysis: ~2-3 GB (loading models)
- LSTM training: ~1-2 GB
- Streamlit: ~500 MB

## Troubleshooting

### Issue: "No module named 'tensorflow'"

**Solution:**
```bash
pip install -r requirements_full.txt
```

### Issue: "CUDA out of memory"

**Solution:** Force CPU usage
```bash
# Add to top of your script:
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
```

### Issue: "ImportError: DLL load failed"

**Solution:** Install Visual C++ Redistributable
- Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
- Install and restart

### Issue: Slow sentiment analysis

**Normal:** First run downloads models (~1 GB)  
**Subsequent runs:** Models are cached, much faster

### Issue: "ModuleNotFoundError: No module named 'src'"

**Solution:** Run from project root directory
```bash
cd "C:\Users\reda\Desktop\APP OPCVM MOROCCO"
python main.py
```

## Project Structure

```
APP OPCVM MOROCCO/
├── start.bat                    # Quick start (Windows)
├── launch_local.py              # Interactive launcher
├── requirements_full.txt        # Full dependencies (2+ GB)
├── requirements.txt             # Streamlit only (50 MB)
│
├── main.py                      # Main orchestrator
├── config.py                    # Configuration
│
├── src/
│   ├── historical_collector.py  # Historical data scraper
│   ├── news_sentiment_pipeline.py # NLP sentiment analysis
│   ├── lstm_model.py            # LSTM prediction model
│   ├── backtester.py            # Walk-forward backtesting
│   ├── dynamic_thresholds.py    # Fee-aware signals
│   ├── asfim_maroclear_collector.py # Daily data collector
│   └── telegram_bot.py          # Telegram bot
│
├── streamlit_app.py             # Web dashboard
│
├── data/
│   ├── raw/                     # Raw data files
│   └── processed/               # Processed data
│
├── outputs/                     # Generated files
│   ├── opcvm_data.csv
│   ├── opcvm_enriched.csv
│   ├── signals_today.csv
│   ├── model_opcvm.h5
│   └── backtest_report.png
│
└── logs/                        # Log files
```

## Example Workflow

### Full Pipeline with Real Data

```bash
# 1. Install dependencies (one-time)
pip install -r requirements_full.txt

# 2. Collect historical data
python src/historical_collector.py

# 3. Run complete pipeline
python main.py --historical --backtest

# 4. Start dashboard
streamlit run streamlit_app.py

# 5. Start Telegram bot (in separate terminal)
python src/telegram_bot.py
```

### Quick Test with Mock Data

```bash
# Fast test (5 minutes)
python main.py --mock

# Start dashboard
streamlit run streamlit_app.py
```

## Next Steps

1. **Test with mock data** first to ensure everything works
2. **Configure real data sources** (ASFIM, Maroclear)
3. **Set up Telegram bot** for daily reports
4. **Customize thresholds** in `config.py`
5. **Deploy to production** (separate guide)

## Support

If you encounter issues:
1. Check `TROUBLESHOOTING.md`
2. Review error messages carefully
3. Ensure Python version is 3.9-3.11
4. Try creating a fresh virtual environment

---

**Ready to start?** Run `start.bat` (Windows) or `python launch_local.py` (any OS)
