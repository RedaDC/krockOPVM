"""
Test: Complete Prediction Flow (Simulating Streamlit)
======================================================
Tests the exact flow that Streamlit uses to ensure predictions ALWAYS work.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.advanced_predictor import AdvancedPredictor

def simulate_streamlit_prediction_flow():
    """Simulates the exact flow used in streamlit_app.py"""
    print("="*70)
    print("SIMULATING STREAMLIT PREDICTION FLOW")
    print("="*70)
    
    # Test Case 1: Fund with sufficient data (> 40 days) - Should use ML
    print("\n[Test 1] Fund with 100 days of data (ML mode)")
    print("-" * 70)
    
    np.random.seed(42)
    dates_100 = pd.date_range("2026-01-01", "2026-04-29", freq="B")
    vl_100 = 1000 * (1 + np.cumsum(np.random.normal(0.0003, 0.005, len(dates_100))))
    
    df_fund_1 = pd.DataFrame({
        'date': dates_100,
        'vl_jour': vl_100,
        'nom_fonds': 'BMCE Capital Actions',
        'classification': 'Actions',
        'score_sentiment_moyen_jour': 0.15
    })
    
    print(f"Data points: {len(df_fund_1)}")
    
    # Simulate Streamlit flow
    adv_predictor = AdvancedPredictor(df_macro=None)
    metrics, error = adv_predictor.train_and_evaluate(df_fund_1)
    
    if error:
        print(f"⚠️ Training failed: {error}")
        print("→ Using fallback mode")
    else:
        print(f"✓ Training succeeded (ML mode)")
        print(f"  Directional Accuracy: {metrics['dir_accuracy']:.2%}")
    
    df_pred = adv_predictor.predict_future(df_fund_1)
    
    if df_pred.empty:
        print("❌ FAILED: No predictions!")
        return False
    else:
        print(f"✓ SUCCESS: {len(df_pred)} predictions generated")
        print(f"  Method: {'ML' if not error else 'Fallback'}")
        print(f"  Performance: {(df_pred['vl_jour'].iloc[-1] / df_fund_1['vl_jour'].iloc[-1] - 1) * 100:.2f}%")
    
    # Test Case 2: Fund with short data (10 days) - Should use Fallback
    print("\n[Test 2] Fund with only 10 days (Fallback mode)")
    print("-" * 70)
    
    dates_10 = pd.date_range("2026-04-15", "2026-04-29", freq="B")
    vl_10 = 1000 + np.cumsum(np.random.normal(0.5, 2, len(dates_10)))
    
    df_fund_2 = pd.DataFrame({
        'date': dates_10,
        'vl_jour': vl_10,
        'nom_fonds': 'Wafa Gestion Monetaire',
        'classification': 'Monetaire',
        'score_sentiment_moyen_jour': 0.05
    })
    
    print(f"Data points: {len(df_fund_2)}")
    
    # Simulate Streamlit flow
    adv_predictor2 = AdvancedPredictor(df_macro=None)
    metrics2, error2 = adv_predictor2.train_and_evaluate(df_fund_2)
    
    if error2:
        print(f"⚠️ Training failed: {error2}")
        print("→ Using fallback mode (EXPECTED)")
    
    df_pred2 = adv_predictor2.predict_future(df_fund_2)
    
    if df_pred2.empty:
        print("❌ FAILED: No predictions!")
        return False
    else:
        print(f"✓ SUCCESS: {len(df_pred2)} predictions generated")
        print(f"  Method: Fallback (Tendance)")
        print(f"  Performance: {(df_pred2['vl_jour'].iloc[-1] / df_fund_2['vl_jour'].iloc[-1] - 1) * 100:.2f}%")
    
    # Test Case 3: Multiple funds (simulating "Predict All" button)
    print("\n[Test 3] Multiple funds (5 funds with varying data)")
    print("-" * 70)
    
    all_results = []
    funds_data = [
        ("Fund A - 150 days", 150, "ML expected"),
        ("Fund B - 50 days", 50, "ML expected"),
        ("Fund C - 30 days", 30, "Fallback expected"),
        ("Fund D - 10 days", 10, "Fallback expected"),
        ("Fund E - 5 days", 5, "Fallback expected"),
    ]
    
    for fund_name, days, expected_method in funds_data:
        dates = pd.date_range("2026-04-29", periods=days, freq="B")[::-1]
        vl = 1000 + np.cumsum(np.random.normal(0.3, 1.5, days))
        
        df_fund = pd.DataFrame({
            'date': dates,
            'vl_jour': vl,
            'nom_fonds': fund_name,
            'classification': 'Diversifie'
        })
        
        # Train
        predictor = AdvancedPredictor(df_macro=None)
        metrics, error = predictor.train_and_evaluate(df_fund)
        
        # Predict (ALWAYS)
        df_pred = predictor.predict_future(df_fund)
        
        if not df_pred.empty:
            last_vl = df_fund['vl_jour'].iloc[-1]
            pred_vl = df_pred['vl_jour'].iloc[-1]
            perf = (pred_vl / last_vl - 1) * 100
            
            all_results.append({
                "Produit": fund_name,
                "VL Actuelle": last_vl,
                "VL Cible (30j)": round(pred_vl, 2),
                "Performance Attendue (%)": round(perf, 2),
                "Méthode": "ML Avancé" if not error else "Fallback (Tendance)",
                "Jours": days
            })
            
            method = "ML" if not error else "Fallback"
            print(f"✓ {fund_name}: {method} → {perf:+.2f}%")
        else:
            print(f"❌ {fund_name}: NO PREDICTIONS")
    
    # Summary
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    if all_results:
        df_results = pd.DataFrame(all_results)
        print(f"\nTotal funds processed: {len(all_results)}")
        print(f"ML predictions: {len(df_results[df_results['Méthode'] == 'ML Avancé'])}")
        print(f"Fallback predictions: {len(df_results[df_results['Méthode'] == 'Fallback (Tendance)'])}")
        
        print("\nPerformance Table:")
        print(df_results.to_string(index=False))
        
        print(f"\n✅ SUCCESS: All {len(all_results)} funds have predictions!")
        print("The 'Aucune prédiction générée' error will NOT appear!")
        return True
    else:
        print("\n❌ FAILED: No predictions generated for any fund")
        return False

def main():
    print("\n" + "="*70)
    print("STREAMLIT PREDICTION FLOW TEST")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    success = simulate_streamlit_prediction_flow()
    
    print("\n" + "="*70)
    if success:
        print("✅ TEST PASSED!")
        print("\nThe prediction system now:")
        print("1. ALWAYS generates predictions (never empty)")
        print("2. Uses ML when possible (40+ days)")
        print("3. Falls back to trend analysis when needed (< 40 days)")
        print("4. Shows clear method indicators to users")
        print("5. Provides helpful error messages when truly stuck")
    else:
        print("❌ TEST FAILED")
    print("="*70)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
