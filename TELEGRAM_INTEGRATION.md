# Telegram Integration for AI Predictions

## Overview

Send **detailed prediction reports with AI justifications** directly to your Telegram bot!

---

## What You'll Receive on Telegram

### Message 1: Summary Report

```
📊 RAPPORT PREDICTIONS OPCVM

📅 Date: 2026-04-29 15:30:45
🏦 Taux BAM: 2.75%
📈 Fonds analysés: 42

━━━━━━━━━━━━━━━━━━━━

🟢 Signaux Haussiers: 23
🔴 Signaux Baissiers: 12
⚪ Signaux Neutres: 7

━━━━━━━━━━━━━━━━━━━━

TOP 5 PREDICTIONS:

1. 🟢 BMCE Capital Actions
   Performance: +2.40%
   Signal: BULLISH (HIGH)
   Méthode: ML Avancé
   VL: 1050.25 → 1075.50
   Confiance IA: 85%

2. 🔴 CDG Capital Obligataire  
   Performance: -1.25%
   Signal: BEARISH (MODERATE)
   Méthode: Fallback (Tendance)
   VL: 1020.50 → 1007.75
   Confiance IA: 72%

3. 🟢 Wafa Gestion Actions
   Performance: +1.85%
   Signal: BULLISH (MODERATE)
   Méthode: ML Avancé
   VL: 1125.30 → 1146.12
   Confiance IA: 78%

4. ⚪ Attijari Intissar
   Performance: +0.15%
   Signal: NEUTRAL (LOW)
   Méthode: Fallback (Tendance)
   VL: 1005.20 → 1006.71
   Confiance IA: 65%

5. 🟢 CFG Bank Actions
   Performance: +1.65%
   Signal: BULLISH (MODERATE)
   Méthode: ML Avancé
   VL: 1088.45 → 1106.41
   Confiance IA: 80%

━━━━━━━━━━━━━━━━━━━━

⚠️ Disclaimer: Rapport généré automatiquement par IA. 
Consultez un conseiller financier avant toute décision.
```

---

### Message 2-N: Detailed Justifications (Per Fund)

```
🟢 BMCE Capital Actions
Signal: BULLISH (HIGH)
Performance 30j: +2.40%
VL Actuelle: 1050.25 MAD
VL Cible: 1075.50 MAD
Confiance IA: 85%
Données: 45 jours

━━━━━━━━━━━━━━━━━━━━

📝 JUSTIFICATION:

Based on our analysis, we maintain a BULLISH outlook with an 
expected 30-day return of +2.40%. Technically, the fund exhibits 
an UPTREND (STRONG) with +1.85% momentum over the past 10 trading 
days. From a macroeconomic perspective, the current BAM rate of 
2.00% is BULLISH for this fund type. Accommodative monetary policy 
supports bond prices. News sentiment analysis reveals a POSITIVE 
environment (score: +0.234). Favorable news flow supports risk 
assets. As an EQUITY fund with HIGH risk profile, primary drivers 
include: Equity market performance, economic growth, corporate 
earnings.

━━━━━━━━━━━━━━━━━━━━

📊 ANALYSE TECHNIQUE:
• Tendance: UPTREND (STRONG)
• Momentum (10j): +1.85%
• Volatilité: 12.45%

🏦 FACTEURS MACRO:
• Taux BAM: 2.00%
• Impact BAM: BULLISH
• Courbe des taux: steep

📰 SENTIMENT ACTUALITÉS:
• Sentiment: POSITIVE
• Score: +0.234

━━━━━━━━━━━━━━━━━━━━

💡 RECOMMANDATION:
Action: OVERWEIGHT
Justification: Strong bullish signals suggest increasing allocation. 
Expected +2.40% return over 30 days.

Points de surveillance:
  - BAM policy rate decisions
  - Yield curve movements
  - News sentiment shifts

━━━━━━━━━━━━━━━━━━━━
⚠️ Ce rapport est généré automatiquement. Ne constitue pas un 
conseil financier.
```

---

## How to Enable

### Step 1: Configure Telegram Bot (If Not Done)

Edit `config.py`:

```python
TELEGRAM = {
    'token': 'YOUR_BOT_TOKEN_HERE',
    'chat_id': 'YOUR_CHAT_ID_HERE'
}
```

**Get Token:**
1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Follow instructions
5. Copy the token

**Get Chat ID:**
1. Search for `@userinfobot`
2. Send any message
3. Copy your ID (e.g., `123456789`)

### Step 2: Run Predictions in Streamlit

1. Open Streamlit app
2. Go to "Prédictions Macro-Économiques" tab
3. Upload ASFIM file
4. Configure macro parameters
5. ✅ Check "Envoyer le rapport à Telegram"
6. Click "Lancer la Prédiction"

### Step 3: Receive on Telegram

**Instantly receive:**
- Summary report (all funds)
- Detailed justifications (each fund)
- Professional analysis
- Actionable recommendations

---

## Integration Code

### In streamlit_app.py

After predictions are generated and saved to session state:

```python
# After this line:
save_predictions_to_state(all_results, taux_bam, courbe_taux)

# Add Telegram sending:
if send_telegram and all_results:
    with st.spinner("Envoi du rapport à Telegram..."):
        metadata = st.session_state.prediction_metadata
        
        success = send_predictions_to_telegram(
            prediction_results=all_results,
            metadata=metadata,
            send_detailed=True  # Send full justifications
        )
        
        if success:
            st.success("✅ Rapport envoyé à Telegram avec succès!")
        else:
            st.error("❌ Échec de l'envoi à Telegram. Vérifiez la configuration.")
```

---

## Features

### ✅ Summary Report
- Top 5 predictions by absolute performance
- Signal classification (🟢 BULLISH, 🔴 BEARISH, ⚪ NEUTRAL)
- Conviction levels (HIGH, MODERATE, LOW)
- VL current vs target
- AI confidence percentage
- Macro parameters (BAM rate)

### ✅ Detailed Justifications
Each fund includes:

**Basic Info:**
- Signal & conviction
- Performance prediction
- Current & target VL
- AI confidence
- Data points used

**AI Reasoning:**
- Full justification paragraph
- Technical analysis
- Macro factors
- News sentiment
- Professional recommendations

**Technical Analysis:**
- Trend direction & strength
- Momentum (10-day)
- Annualized volatility

**Macro Analysis:**
- BAM rate impact
- Yield curve shape
- Monetary policy stance

**Sentiment Analysis:**
- Overall sentiment
- Sentiment score (-1 to +1)
- News impact assessment

**Recommendations:**
- Action (OVERWEIGHT/UNDERWEIGHT/HOLD)
- Detailed rationale
- Monitoring points

---

## Message Handling

### Automatic Splitting

Telegram has a **4096 character limit** per message. The bot automatically:

1. **Splits at natural breakpoints** (section dividers)
2. **Sends multiple messages** if needed
3. **Maintains formatting** across splits
4. **Handles errors gracefully**

### Example Multi-Message Flow

```
Message 1: Summary Report (1,200 chars)
Message 2: Fund 1 Detail (3,800 chars)
Message 3: Fund 2 Detail (3,500 chars)
Message 4: Fund 3 Detail (2,900 chars)
...
```

---

## Configuration Options

### Send Summary Only

```python
send_predictions_to_telegram(
    prediction_results=all_results,
    metadata=metadata,
    send_detailed=False  # Only summary
)
```

### Send Detailed (Default)

```python
send_predictions_to_telegram(
    prediction_results=all_results,
    metadata=metadata,
    send_detailed=True  # Summary + all details
)
```

### Custom Token/Chat ID

```python
send_predictions_to_telegram(
    prediction_results=all_results,
    metadata=metadata,
    token='CUSTOM_TOKEN',
    chat_id='CUSTOM_CHAT_ID',
    send_detailed=True
)
```

---

## Testing

### Test Bot Configuration

```python
from src.telegram_prediction_bot import TelegramPredictionBot

bot = TelegramPredictionBot()
success = bot.send_test_message()

if success:
    print("✅ Bot configured correctly!")
else:
    print("❌ Check token and chat_id")
```

### Expected Test Message

```
✅ Test Bot OPCVM

Le bot de predictions est correctement configuré.

📅 Timestamp: 2026-04-29 15:30:45

Vous recevrez désormais les rapports de predictions détaillés 
avec justifications IA.
```

---

## Benefits

### For Portfolio Managers
✅ **Instant Notifications** - Know predictions immediately  
✅ **Detailed Analysis** - Full AI reasoning on mobile  
✅ **Professional Format** - Bloomberg-style reports  
✅ **Actionable Insights** - Clear recommendations  

### For Analysts
✅ **Justification Tracking** - Understand WHY predictions made  
✅ **Multi-Source Analysis** - Technical + Macro + Sentiment  
✅ **Risk Assessment** - Confidence levels & monitoring  
✅ **Mobile Access** - Review predictions anywhere  

### For Decision Makers
✅ **Summary View** - Top 5 predictions at a glance  
✅ **Signal Clarity** - BULLISH/BEARISH/NEUTRAL  
✅ **Conviction Levels** - HIGH/MODERATE/LOW confidence  
✅ **Quick Actions** - OVERWEIGHT/UNDERWEIGHT/HOLD  

---

## Example Use Cases

### Use Case 1: Morning Review

**Scenario:** Portfolio manager checks predictions before market opens

**Telegram Messages Received:**
1. Summary: 23 bullish, 12 bearish, 7 neutral
2. Detail: BMCE Capital Actions - BULLISH (+2.40%)
3. Detail: CDG Capital Obligataire - BEARISH (-1.25%)
4. ... (continues for all funds)

**Action:** Adjust portfolio allocations based on signals

### Use Case 2: Risk Monitoring

**Scenario:** Analyst monitors high-conviction signals

**Telegram Shows:**
```
🟢 BMCE Capital Actions
Signal: BULLISH (HIGH)
Confiance IA: 85%
Action: OVERWEIGHT
```

**Action:** Increase position in BMCE Capital Actions

### Use Case 3: Macro Impact Assessment

**Scenario:** Assess impact of BAM rate change

**Telegram Shows:**
```
🏦 FACTEURS MACRO:
• Taux BAM: 2.00%
• Impact BAM: BULLISH
• Courbe des taux: steep
```

**Action:** Favor bond funds in accommodative environment

---

## Troubleshooting

### Problem: No messages received

**Solution:**
1. Check `config.py` has correct token and chat_id
2. Test with `bot.send_test_message()`
3. Verify bot is not blocked
4. Check internet connection

### Problem: Messages too long

**Solution:**
- Bot automatically splits at 4000 chars
- No action needed
- Messages arrive in sequence

### Problem: Formatting broken

**Solution:**
- Ensure `parse_mode='Markdown'` is set
- Avoid special characters in fund names
- Check for unclosed markdown symbols

### Problem: Token invalid

**Solution:**
1. Get new token from @BotFather
2. Update `config.py`
3. Restart Streamlit app

---

## Files Created

**Commit:** `31e938b`

1. ✅ [src/telegram_prediction_bot.py](file:///c:/Users/reda/Desktop/APP%20OPCVM%20MOROCCO/src/telegram_prediction_bot.py) - 327 lines
   - TelegramPredictionBot class
   - Summary formatter
   - Detail formatter
   - Message splitting logic
   - Error handling

2. ✅ [streamlit_app.py](file:///c:/Users/reda/Desktop/APP%20OPCVM%20MOROCCO/streamlit_app.py) - Import added

---

## Next Steps

### Immediate
1. Configure Telegram bot token in config.py
2. Test with `send_test_message()`
3. Enable "Envoyer le rapport à Telegram" checkbox
4. Run predictions and verify messages

### Future Enhancements
- [ ] Schedule daily prediction reports
- [ ] Add historical performance tracking
- [ ] Include MASI/MADEX index predictions
- [ ] Add chart images to messages
- [ ] Multi-language support
- [ ] Priority alerts for high-conviction signals

---

## Quick Start

```python
# 1. Import
from src.telegram_prediction_bot import send_predictions_to_telegram

# 2. After generating predictions
success = send_predictions_to_telegram(
    prediction_results=st.session_state.prediction_results,
    metadata=st.session_state.prediction_metadata,
    send_detailed=True
)

# 3. Check result
if success:
    print("✅ Report sent to Telegram!")
else:
    print("❌ Failed to send")
```

---

**Status:** Ready for use  
**Pushed to GitHub:** ✅ Commit `31e938b`  
**Documentation:** Complete  

Now your AI predictions with **detailed justifications** will be sent directly to **Telegram**! 📱✨
