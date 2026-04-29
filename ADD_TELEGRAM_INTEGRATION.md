# Instructions to Add Telegram Integration to streamlit_app.py

## Step 1: Add Telegram Checkbox (After line 536)

Find this line in streamlit_app.py:
```python
predict_all = st.checkbox("Prédire pour toute la catégorie", value=False)
```

Add these lines AFTER it:
```python

# Telegram notification option
send_telegram = st.checkbox(
    "Envoyer le rapport à Telegram",
    value=False,
    help="Envoie les prédictions détaillées avec justifications à votre bot Telegram"
)
```

---

## Step 2: Add Telegram Sending Code (After line 625)

Find this section (after predictions are generated):
```python
progress_bar.progress((i + 1) / len(funds_to_process))

if all_results:
```

Add these lines BETWEEN them (after the progress_bar line, before "if all_results"):
```python

# Send to Telegram if checkbox is checked
if send_telegram and all_results:
    st.info("Envoi du rapport à Telegram...")
    try:
        metadata = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'funds_processed': len(all_results),
            'macro_params': {
                'taux_bam': taux_bam,
                'courbe_taux': courbe_taux
            }
        }
        
        success = send_predictions_to_telegram(
            prediction_results=all_results,
            metadata=metadata,
            send_detailed=True
        )
        
        if success:
            st.success("Rapport envoyé à Telegram avec succès!")
        else:
            st.error("Échec de l'envoi à Telegram")
    except Exception as e:
        st.error(f"Erreur envoi Telegram: {e}")
```

---

## Complete Example

The final code should look like this:

```python
# Line 536
predict_all = st.checkbox("Prédire pour toute la catégorie", value=False)

# NEW: Telegram checkbox
send_telegram = st.checkbox(
    "Envoyer le rapport à Telegram",
    value=False,
    help="Envoie les prédictions détaillées avec justifications à votre bot Telegram"
)

st.markdown("### 2. Paramètres Macro")
# ... rest of macro params ...

# Line 547
predict_btn = st.button("Lancer la Prédiction", type="primary")

# ... prediction logic ...

# Line 625
progress_bar.progress((i + 1) / len(funds_to_process))

# NEW: Send to Telegram
if send_telegram and all_results:
    st.info("Envoi du rapport à Telegram...")
    try:
        metadata = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'funds_processed': len(all_results),
            'macro_params': {
                'taux_bam': taux_bam,
                'courbe_taux': courbe_taux
            }
        }
        
        success = send_predictions_to_telegram(
            prediction_results=all_results,
            metadata=metadata,
            send_detailed=True
        )
        
        if success:
            st.success("✅ Rapport envoyé à Telegram avec succès!")
        else:
            st.error("❌ Échec de l'envoi à Telegram")
    except Exception as e:
        st.error(f"❌ Erreur envoi Telegram: {e}")

if all_results:
    # ... display predictions ...
```

---

## Quick Test

After making these changes:

1. Restart Streamlit app
2. Go to "Prédictions Macro-Économiques" tab
3. Upload ASFIM file
4. Check ☑️ "Envoyer le rapport à Telegram"
5. Click "Lancer la Prédiction"
6. Check Telegram - you'll receive the report!

---

## What Changed

✅ Added Telegram checkbox in UI  
✅ Added code to send predictions to Telegram  
✅ Sends summary + detailed justifications  
✅ Shows success/error messages  
✅ Handles errors gracefully  
