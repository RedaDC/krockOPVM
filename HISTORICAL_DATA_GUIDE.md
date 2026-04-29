# How to Use Historical Data Accumulator

## Problem Solved
ASFIM files typically contain only **1 day of data**. This made predictions impossible because ML models need at least 40 days of history.

## Solution
The **Historical Data Accumulator** automatically saves each daily upload and combines them to build a growing historical database.

---

## How It Works

### 1. **First Upload**
```
Upload ASFIM file for 2026-04-29
→ System saves: data/historical/opcvm_daily_20260429.csv
→ Creates: data/historical/opcvm_historical_complete.csv
→ You now have: 1 day of history
```

### 2. **Second Upload (Next Day)**
```
Upload ASFIM file for 2026-04-30
→ System saves: data/historical/opcvm_daily_20260430.csv
→ Appends to: data/historical/opcvm_historical_complete.csv
→ You now have: 2 days of history
```

### 3. **After 5+ Days**
```
✅ Predictions enabled for all funds
→ Fallback predictions work with 5+ days
→ ML predictions work with 40+ days
```

---

## Daily Workflow

### **Option 1: Manual Daily Upload**
1. Download ASFIM performance file from https://asfim.ma/publications/tableaux-des-performances/
2. Open Streamlit app
3. Go to "Prédictions Macro-Économiques" tab
4. Upload the file
5. System automatically adds it to history

### **Option 2: Automatic (Future Enhancement)**
```python
# Run daily cron job or scheduled task
from src.asfim_performance_scraper import ASFIMPerformanceScraper
from src.historical_accumulator import get_accumulator

scraper = ASFIMPerformanceScraper()
df_daily = scraper.get_latest_performance_data()

accumulator = get_accumulator()
accumulator.add_daily_data(df_daily)
```

---

## What Gets Stored

**File Structure**:
```
data/historical/
├── opcvm_historical_complete.csv  # All historical data
├── opcvm_daily_20260429.csv       # Daily snapshot
├── opcvm_daily_20260430.csv       # Daily snapshot
└── opcvm_daily_20260501.csv       # Daily snapshot
```

**Data Format**:
```csv
date,nom_fonds,classification,vl_jour
2026-04-29,BMCE Capital Actions,Actions,1050.25
2026-04-29,CDG Capital Obligataire,Obligataire,1020.50
2026-04-30,BMCE Capital Actions,Actions,1055.75
2026-04-30,CDG Capital Obligataire,Obligataire,1021.30
```

---

## Benefits

✅ **No More "1 Day of Data" Errors** - History accumulates automatically  
✅ **Daily Backups** - Each upload is saved separately  
✅ **Deduplication** - Re-uploading same day replaces old data  
✅ **Progress Tracking** - See how many days you have  
✅ **Fund-Level Metrics** - Know which funds have enough data  

---

## Current Status Dashboard

When you open the app, you'll see:

```
📊 Historique disponible: 15 jours | 85 fonds | 2026-04-15 to 2026-04-29

┌─────────────────┬──────────────────┬──────────────────┐
│ Jours de données│ Fonds avec 5+ j. │ Fonds avec 40+ j.│
│      15         │        85        │        0         │
└─────────────────┴──────────────────┴──────────────────┘
```

---

## Prediction Availability

| Days of History | Prediction Type | Availability |
|----------------|----------------|--------------|
| 1-4 days | ❌ None | Not enough data |
| 5-39 days | ✅ Fallback (Trend-based) | Works for all funds |
| 40+ days | ✅ ML (Advanced) | Best accuracy |

---

## Tips for Fast Results

### **Quick Start (5 Days)**
1. Upload today's ASFIM file
2. Repeat daily for 5 days
3. After 5 days: Fallback predictions available

### **Full ML (40 Days)**
1. Keep uploading daily for 40 days
2. OR: Import historical CSV if you have it
3. After 40 days: Full ML predictions available

### **Import Existing History**
If you have historical data in CSV format:
```python
import pandas as pd
from src.historical_accumulator import get_accumulator

# Load your historical data
df_history = pd.read_csv("my_history.csv", parse_dates=['date'])

# Add to accumulator
accumulator = get_accumulator()
accumulator.add_daily_data(df_history)
```

---

## Clearing History

To reset and start fresh:
```python
from src.historical_accumulator import get_accumulator

accumulator = get_accumulator()
accumulator.clear_history()
```

---

## Troubleshooting

**Q: Still seeing "1 day of data" after uploading?**  
A: You need to upload files for multiple days. Each daily file adds 1 day to history.

**Q: Can I upload multiple files at once?**  
A: Upload them one at a time. The system will deduplicate automatically.

**Q: What if I upload the same day twice?**  
A: The system keeps only the latest upload for that date (no duplicates).

**Q: Where is the data stored?**  
A: In `data/historical/` directory as CSV files.

---

## Future Enhancements

- [ ] Auto-download from ASFIM website daily
- [ ] Web UI to clear history
- [ ] Export historical data to CSV
- [ ] Import bulk historical data
- [ ] Data validation and quality checks

---

**Last Updated**: April 29, 2026  
**Version**: 1.0
