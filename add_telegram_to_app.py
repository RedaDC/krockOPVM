"""
Script to automatically add Telegram integration to streamlit_app.py
"""

def add_telegram_integration():
    """Add Telegram checkbox and sending logic to streamlit_app.py"""
    
    print("Adding Telegram integration to streamlit_app.py...")
    
    # Read the file
    with open('streamlit_app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the line with predict_all checkbox
    insert_checkbox_after = None
    for i, line in enumerate(lines):
        if 'predict_all = st.checkbox' in line:
            insert_checkbox_after = i
            break
    
    if insert_checkbox_after is None:
        print("ERROR: Could not find predict_all checkbox line")
        return False
    
    # Insert Telegram checkbox
    checkbox_code = """
            # Telegram notification option
            send_telegram = st.checkbox(
                "Envoyer le rapport à Telegram",
                value=False,
                help="Envoie les prédictions détaillées avec justifications à votre bot Telegram"
            )
"""
    
    lines.insert(insert_checkbox_after + 1, checkbox_code)
    
    print(f"✓ Added Telegram checkbox after line {insert_checkbox_after + 1}")
    
    # Find the line with progress_bar.progress before "if all_results:"
    insert_telegram_before = None
    for i, line in enumerate(lines):
        if 'if all_results:' in line and i > 600:  # Make sure it's the right one
            insert_telegram_before = i
            break
    
    if insert_telegram_before is None:
        print("ERROR: Could not find 'if all_results:' line")
        return False
    
    # Insert Telegram sending code
    telegram_code = """
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
                            st.success("✅ Rapport envoyé à Telegram avec succès!")
                        else:
                            st.error("❌ Échec de l'envoi à Telegram")
                    except Exception as e:
                        st.error(f"❌ Erreur envoi Telegram: {e}")

"""
    
    lines.insert(insert_telegram_before, telegram_code)
    
    print(f"✓ Added Telegram sending code before line {insert_telegram_before + 1}")
    
    # Write back
    with open('streamlit_app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("\n✅ Telegram integration added successfully!")
    print("\nNext steps:")
    print("1. Restart Streamlit app")
    print("2. Go to 'Prédictions Macro-Économiques' tab")
    print("3. Check 'Envoyer le rapport à Telegram'")
    print("4. Click 'Lancer la Prédiction'")
    print("5. Check Telegram for the report!")
    
    return True

if __name__ == "__main__":
    try:
        success = add_telegram_integration()
        if success:
            print("\n🎉 Done! You can now use Telegram notifications!")
        else:
            print("\n❌ Failed. Please check the instructions in ADD_TELEGRAM_INTEGRATION.md")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease manually follow the instructions in ADD_TELEGRAM_INTEGRATION.md")
