# Streamlit Cloud Deployment Guide

## Quick Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New App"
3. Connect your GitHub repository: `RedaDC/krockOPVM`
4. Configure:
   - **Repository:** krockOPVM
   - **Branch:** main
   - **Main file path:** streamlit_app.py
   - **Requirements file:** requirements_streamlit.txt
5. Click "Deploy!"

## What Was Fixed

The original `requirements.txt` contained heavy ML frameworks that caused deployment failures:

### Removed (Too Heavy for Streamlit Cloud):
- **tensorflow** (~2 GB) - Causes timeout during installation
- **torch** (~1-2 GB) - Large download, often fails on free tier
- **transformers** (~500 MB) - Requires PyTorch/TensorFlow
- **python-telegram-bot** - Not needed for web dashboard
- **matplotlib** - Replaced with plotly for better interactivity

### Kept (Lightweight):
- pandas, numpy - Data processing
- scikit-learn - Lightweight ML (only ~10 MB)
- requests, beautifulsoup4 - Web scraping
- plotly - Interactive charts (better for Streamlit)
- streamlit - Framework itself

## App Features

The Streamlit dashboard includes:

1. **Trading Signals Tab**
   - Buy/Sell/Wait signals for all funds
   - Filter by signal type
   - Confidence levels (FORTE/MODEREE/FAIBLE)
   - Sentiment analysis integration

2. **Technical Analysis Tab**
   - Interactive VL trend charts
   - Moving averages (10-day, 30-day)
   - Volatility analysis
   - Distribution histograms

3. **Raw Data Tab**
   - Full dataset viewer
   - CSV download functionality
   - Date range filtering
   - Classification filtering

## Configuration

The app uses mock data by default. To use real data:

1. **Option 1: Upload CSV files**
   - Place CSV files in `data/processed/`
   - Update the `load_data()` function in `streamlit_app.py`

2. **Option 2: Connect to database**
   - Add database credentials in Streamlit secrets
   - Modify data loading functions

## Streamlit Secrets (Optional)

If you want to add real data sources, create `.streamlit/secrets.toml`:

```toml
[database]
host = "your-db-host"
port = 5432
username = "your-username"
password = "your-password"

[api_keys]
news_api = "your-news-api-key"
```

## Troubleshooting

### App Won't Deploy
- Check that `requirements_streamlit.txt` is being used (not `requirements.txt`)
- Ensure all dependencies are compatible with Python 3.9+
- Check Streamlit Cloud logs for specific errors

### App Runs Slowly
- Reduce the amount of mock data generated
- Use `@st.cache_data` decorator for expensive computations
- Consider using Plotly instead of Matplotlib for better performance

### Module Not Found Error
- Verify the module is in `requirements_streamlit.txt`
- Check for typos in import statements
- Ensure the package name matches (import name may differ from pip install name)

## Local Testing

Before deploying, test locally:

```bash
# Install Streamlit requirements
pip install -r requirements_streamlit.txt

# Run the app
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`

## Updating the App

After making changes:

```bash
git add .
git commit -m "Update Streamlit app"
git push
```

Streamlit Cloud will automatically redeploy within 1-2 minutes.

## Resource Limits (Streamlit Cloud Free Tier)

- **RAM:** 1 GB
- **CPU:** 2 vCPUs
- **Disk:** 1 GB
- **Timeout:** 30 seconds per request
- **Sleep:** App sleeps after 30 minutes of inactivity

The current app is optimized to stay within these limits.

## Next Steps

1. Deploy the app on Streamlit Cloud
2. Share the public URL
3. Add real data sources
4. Customize the dashboard styling
5. Add more interactive features
