# OPCVM Data Contract - Integration Specification

## Overview
This document defines the exact data requirements for the OPCVM Analytics system. When real data access is obtained, use this contract to verify compatibility.

---

## 1. Required Data Sources

### 1.1 ASFIM Fund Data (Primary)
**Source:** fundshare.asfim.ma  
**Format:** Excel (.xlsx) or CSV  
**Frequency:** Daily (after market close ~17:00)  
**Update:** Every business day (Mon-Fri, excluding Moroccan holidays)

#### Minimum Required Columns:

| Column Name | Type | Format | Description | Example |
|------------|------|--------|-------------|---------|
| `nom_fonds` | String | Text | Fund name | "BMCE Capital Actions" |
| `sdg` | String | Text | Management company | "BMCE Capital Gestion" |
| `classification` | String | Categorical | Fund type | "Actions", "Obligataire", "Monétaire", "Diversifié" |
| `vl_jour` | Float | Decimal | Current day VL | 1245.30 |
| `vl_precedente` | Float | Decimal | Previous day VL | 1240.15 |
| `variation_pct` | Float | Percentage | Daily change | 0.42 |
| `aum` | Float | MAD millions | Assets under management | 2450.50 |
| `date` | Date | YYYY-MM-DD | Valuation date | 2026-04-28 |

#### Optional Columns (Enhances Analysis):

| Column Name | Type | Description |
|------------|------|-------------|
| `flux_souscription` | Float | Subscription flows (MAD) |
| `flux_rachat` | Float | Redemption flows (MAD) |
| `encours_global` | Float | Total outstanding |
| `parts_encours` | Float | Outstanding shares |
| `date_creation` | Date | Fund inception date |

#### Format Validation Rules:
- VL must be positive (> 0)
- AUM must be positive (> 0)
- Variation % typically between -10 and +10
- Date must be valid business day
- No duplicate (fund_name, date) pairs

---

### 1.2 Maroclear Bond Data (Secondary)
**Source:** Maroclear or manual file  
**Format:** CSV or Excel  
**Frequency:** Static (update quarterly)  
**Purpose:** Enrich bond fund analysis

#### Required Columns:

| Column Name | Type | Format | Description | Example |
|------------|------|--------|-------------|---------|
| `isin` | String | 12 chars | ISIN code | "MA0000012345" |
| `nom_obligation` | String | Text | Bond name | "Bons du Trésor 3.5% 2030" |
| `taux_coupon` | Float | Percentage | Coupon rate | 3.50 |
| `date_echeance` | Date | YYYY-MM-DD | Maturity date | 2030-12-31 |
| `nature` | String | Categorical | Bond type | "Bon du Trésor", "Obligation corporate" |
| `devise` | String | 3 chars | Currency | "MAD" |

---

### 1.3 Fund Portfolio Holdings (Optional - Advanced)
**Source:** JAL/AMMC official inventories  
**Format:** Excel/PDF  
**Frequency:** Monthly or quarterly  
**Purpose:** Deep portfolio analysis

#### Required Structure:

| Column Name | Type | Description |
|------------|------|-------------|
| `nom_fonds` | String | Fund name |
| `isin_titre` | String | Security ISIN |
| `nom_titre` | String | Security name |
| `quantite` | Float | Number of shares |
| `poids_portefeuille` | Float | Portfolio weight (%) |
| `valorisation` | Float | Position value (MAD) |
| `date_inventaire` | Date | Inventory date |

---

## 2. Data Quality Requirements

### 2.1 Completeness
- **Minimum 500 data points** per fund for LSTM training
- **Maximum 5% missing values** in VL column
- **No gaps > 5 business days** in time series

### 2.2 Accuracy
- VL values must match official fund factsheets
- AUM should be within ±1% of reported values
- Date alignment with market calendar

### 2.3 Consistency
- Fund names consistent across files
- Classification follows AMMC standard categories:
  - Actions (Equity)
  - Obligataire Long Terme (Bond LT)
  - Obligataire Court Terme (Bond ST)
  - Monétaire (Money Market)
  - Diversifié (Balanced)
  - Indiciel (Index)

---

## 3. Update Frequency & Timing

### 3.1 Daily Update (Automated)
```
17:00 - Casablanca Stock Exchange closes
17:30 - ASFIM publishes daily VL
18:00 - Our system collects data
18:30 - Sentiment analysis runs
19:00 - LSTM predictions generated
19:30 - Telegram report sent
```

### 3.2 Weekly Tasks
- Data quality validation
- Missing value interpolation
- Performance metrics update

### 3.3 Monthly Tasks
- Portfolio holdings update (if available)
- Model retraining
- Backtesting refresh

---

## 4. Integration Checklist

When data access is obtained, verify each item:

### 4.1 Access Verification
- [ ] Can download/access data files
- [ ] Files open successfully (not corrupted)
- [ ] Data is in expected format (Excel/CSV)
- [ ] All required columns present
- [ ] Column names match or can be mapped

### 4.2 Data Validation
- [ ] At least 50 funds in dataset
- [ ] At least 500 historical data points
- [ ] Date range covers 2+ years
- [ ] No critical missing values
- [ ] VL values are reasonable (100-5000 MAD range)

### 4.3 Parser Testing
- [ ] Column mapping works correctly
- [ ] Date parsing successful
- [ ] Numeric conversions accurate
- [ ] No data loss during import
- [ ] Output CSV matches expected schema

### 4.4 Pipeline Testing
- [ ] Data collector runs without errors
- [ ] Sentiment pipeline processes data
- [ ] LSTM model trains successfully
- [ ] Signals generated correctly
- [ ] Backtest produces valid metrics

---

## 5. Error Handling

### 5.1 Missing Columns
If column names differ, update mapping in `src/asfim_maroclear_collector.py`:

```python
COLUMN_MAPPING = {
    'nom_fonds': ['nom_fonds', 'Nom Fonds', 'Fonds', 'DESIGNATION', ...],
    'vl_jour': ['vl_jour', 'VL', 'Valeur Liquidative', ...],
    # Add your actual column names here
}
```

### 5.2 Date Format Issues
Common formats to handle:
- YYYY-MM-DD (ISO standard)
- DD/MM/YYYY (European)
- MM/DD/YYYY (US)
- DD-MM-YYYY

System will auto-detect, but can be forced in config.

### 5.3 Missing Data
- Gaps < 3 days: Linear interpolation
- Gaps 3-5 days: Forward fill
- Gaps > 5 days: Flag for review

---

## 6. Sample Data Structure

### Expected Output: `opcvm_data.csv`

```csv
date,nom_fonds,sdg,classification,vl_jour,vl_precedente,variation_pct,aum,flux_souscription,flux_rachat,flux_net
2026-04-28,BMCE Capital Actions,BMCE Capital Gestion,Actions,1245.30,1240.15,0.42,2450.50,15.2,8.5,6.7
2026-04-28,CDG Capital Obligataire,CDG Capital Gestion,Obligataire,1089.50,1091.20,-0.16,1820.30,5.1,12.3,-7.2
...
```

---

## 7. Contact Information for Data Access

### Primary Sources (in priority order)

1. **ASFIM**
   - Website: asfim.ma
   - Portal: fundshare.asfim.ma
   - Email: contact@asfim.ma
   - Note: May require institutional membership

2. **AMMC (Regulator)**
   - Website: ammc.ma
   - Section: Publications/Statistiques
   - Note: Public data may be available

3. **Bourse de Casablanca**
   - Website: casablanca-bourse.com
   - Section: Funds/OPCVM
   - Note: May have aggregated data

4. **Your Bank/Broker**
   - Contact fund department
   - May have internal data feeds
   - Requires business relationship

---

## 8. Integration Timeline (Once Data Obtained)

| Task | Duration | Dependencies |
|------|----------|--------------|
| Data format analysis | 2 hours | Sample file |
| Column mapping update | 1 hour | Format analysis |
| Parser testing | 2 hours | Mapping complete |
| Full pipeline test | 4 hours | Parser working |
| Data validation | 2 hours | Pipeline test |
| Model retraining | 8 hours | Valid data |
| Backtesting | 4 hours | Trained model |
| **Total** | **~23 hours** | **3 business days** |

---

## 9. Success Criteria

The system is considered production-ready when:

- [ ] Real data flows through complete pipeline
- [ ] Backtest precision_achat > 55%
- [ ] At least 50 funds with 500+ data points each
- [ ] Daily automated collection works for 1 week without errors
- [ ] Telegram reports sent successfully
- [ ] Dashboard displays real data (not mock)

---

## 10. Next Steps

1. **Obtain sample data file** (any source)
2. **Share file or describe format** with developer
3. **Update column mappings** based on actual structure
4. **Test parser** with real data
5. **Validate end-to-end** pipeline
6. **Deploy to production** if validation passes

---

**Document Version:** 1.0  
**Created:** 2026-04-28  
**Status:** Ready for Data Integration
