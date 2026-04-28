# Streamlit Deployment Troubleshooting

## What Was Fixed

### Problem
Streamlit Cloud was failing with "installer returned a non-zero exit code" because:
1. **TensorFlow** (~2 GB) - Too large, causes timeout
2. **PyTorch** (~1-2 GB) - Too large, causes timeout
3. **Transformers** (~500 MB) - Requires TensorFlow/PyTorch
4. **Matplotlib** - Sometimes has compilation issues on Streamlit Cloud

### Solution Applied
- Removed all heavy ML frameworks (TensorFlow, PyTorch, Transformers)
- Replaced Matplotlib with **Plotly** (better compatibility, interactive charts)
- Simplified requirements to only essential packages
- Total dependencies: ~50 MB (was 2-4 GB)

## Steps to Redeploy

### Option 1: Redeploy Existing App
1. Go to your Streamlit Cloud dashboard
2. Find your app
3. Click "Rebuild" or "Restart"
4. Wait 2-3 minutes for deployment

### Option 2: Create New App
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New App"
3. Settings:
   - **Repository:** RedaDC/krockOPVM
   - **Branch:** main
   - **Main file path:** streamlit_app.py
4. Click "Deploy!"

## Current requirements.txt

```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
scikit-learn>=1.3.0
requests>=2.31.0
beautifulsoup4>=4.12.0
openpyxl>=3.1.0
feedparser>=6.0.0
langdetect>=1.0.9
schedule>=1.2.0
```

**Total install size:** ~50 MB
**Expected install time:** 1-2 minutes on Streamlit Cloud

## If It Still Fails

### Check Streamlit Cloud Logs
1. Go to your app dashboard
2. Click "Manage App"
3. Click "Logs"
4. Look for the specific error message

### Common Issues & Solutions

#### Issue: "No module named 'xyz'"
**Solution:** The module is missing from requirements.txt
- Add it to requirements.txt
- Push to GitHub
- Streamlit will automatically redeploy

#### Issue: "Installation timeout"
**Solution:** A package is too large
- Remove heavy packages (tensorflow, torch, transformers)
- Use lightweight alternatives

#### Issue: "Python version not supported"
**Solution:** Streamlit Cloud uses Python 3.9-3.11
- Make sure your packages support these versions
- Avoid Python 3.12+ specific features

#### Issue: "Out of memory"
**Solution:** App uses too much RAM
- Reduce data size
- Use @st.cache_data decorator
- Remove unnecessary imports

## Test Locally First

Before deploying, test locally:

```bash
# Create clean virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run app
streamlit run streamlit_app.py
```

If it works locally, it should work on Streamlit Cloud.

## App Features

The deployed app includes:
- Interactive Plotly charts (no matplotlib)
- Trading signals with filtering
- Technical analysis with moving averages
- Data export to CSV
- Responsive design

## Need More Help?

If deployment still fails:
1. Share the exact error message from Streamlit Cloud logs
2. Check that requirements.txt doesn't have tensorflow/torch
3. Verify streamlit_app.py is the correct main file
4. Try creating a fresh app on Streamlit Cloud
