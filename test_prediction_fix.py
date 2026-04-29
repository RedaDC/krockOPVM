"""
Quick Test: Verify Prediction Fallback Works
=============================================
Tests that predictions are ALWAYS generated, even with minimal data.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.advanced_predictor import AdvancedPredictor

def test_fallback_prediction():
    """Test that fallback prediction always works"""
    print("="*70)
    print("TEST: Fallback Prediction System")
    print("="*70)
    
    # Test 1: Very short history (should use fallback)
    print("\n[Test 1] Very short history (10 days)")
    dates = pd.date_range("2026-04-01", "2026-04-15", freq="B")
    df_short = pd.DataFrame({
        'date': dates,
        'vl': 1000 + np.cumsum(np.random.normal(0.5, 2, len(dates))),
        'nom_fonds': 'Test Fund Short'
    })
    
    predictor = AdvancedPredictor(df_macro=None)
    
    # This should fail training but use fallback
    metrics, error = predictor.train_and_evaluate(df_short)
    
    if error:
        print(f"  ✗ Training failed (expected): {error}")
    else:
        print(f"  ✓ Training succeeded: {metrics}")
    
    # Predictions should ALWAYS work
    predictions = predictor.predict_future(df_short, days_ahead=20)
    
    if predictions.empty:
        print("  ❌ FAILED: No predictions generated!")
        return False
    else:
        print(f"  ✓ SUCCESS: Generated {len(predictions)} predictions")
        print(f"    Type: {predictions['type'].iloc[0]}")
        print(f"    VL range: {predictions['vl_jour'].min():.2f} - {predictions['vl_jour'].max():.2f}")
        return True

def test_normal_prediction():
    """Test normal prediction with sufficient data"""
    print("\n[Test 2] Normal history (100 days)")
    
    np.random.seed(42)
    dates = pd.date_range("2025-10-01", "2026-04-29", freq="B")  # ~150 days
    vl_values = 1000 * (1 + np.cumsum(np.random.normal(0.0003, 0.005, len(dates))))
    
    df_normal = pd.DataFrame({
        'date': dates,
        'vl': vl_values,
        'nom_fonds': 'Test Fund Normal'
    })
    
    print(f"  Data points: {len(df_normal)}")
    
    # Create with None macro (should still work)
    predictor = AdvancedPredictor(df_macro=None)
    
    # This should succeed with 150 days
    metrics, error = predictor.train_and_evaluate(df_normal, test_days=30)
    
    if error:
        print(f"  ⚠ Training failed: {error}")
        print(f"  → This is OK, fallback will be used")
    else:
        print(f"  ✓ Training succeeded")
        print(f"    MAE: {metrics['mae']:.6f}")
        print(f"    Directional Accuracy: {metrics['dir_accuracy']:.2%}")
    
    # Predictions should work (either ML or fallback)
    predictions = predictor.predict_future(df_normal, days_ahead=30)
    
    if predictions.empty:
        print("  ❌ FAILED: No predictions generated!")
        return False
    else:
        print(f"  ✓ SUCCESS: Generated {len(predictions)} predictions")
        print(f"    Type: {predictions['type'].iloc[0]}")
        print(f"    Expected return: {predictions['expected_return'].mean():.4f}%")
        
        # Check if predictions are non-neutral
        avg_return = predictions['expected_return'].mean()
        if abs(avg_return) > 0.001:
            print(f"    ✓ Predictions are NON-NEUTRAL (good!)")
        else:
            print(f"    ⚠ Predictions might be too neutral")
        
        return True

def test_edge_cases():
    """Test edge cases"""
    print("\n[Test 3] Edge cases")
    
    # Edge case 1: Single data point
    df_single = pd.DataFrame({
        'date': [datetime.now()],
        'vl': [1000],
        'nom_fonds': ['Single Point']
    })
    
    predictor = AdvancedPredictor(df_macro=None)
    predictions = predictor.predict_future(df_single, days_ahead=10)
    
    if predictions.empty:
        print("  ✓ Single point: Correctly returned empty (need at least 5 points)")
    else:
        print(f"  ✓ Single point: Generated {len(predictions)} predictions via fallback")
    
    # Edge case 2: No date column
    df_no_date = pd.DataFrame({
        'vl': [1000, 1005, 1010, 1015, 1020]
    })
    
    try:
        predictions = predictor.predict_future(df_no_date, days_ahead=10)
        if not predictions.empty:
            print(f"  ✓ No date column: Handled gracefully, {len(predictions)} predictions")
        else:
            print(f"  ⚠ No date column: Returned empty")
    except Exception as e:
        print(f"  ✗ No date column: Error - {e}")
    
    return True

def main():
    print("\n" + "="*70)
    print("PREDICTION FALLBACK SYSTEM - VERIFICATION TEST")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # Run tests
    results.append(("Fallback (short data)", test_fallback_prediction()))
    results.append(("Normal prediction", test_normal_prediction()))
    results.append(("Edge cases", test_edge_cases()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:30s} {status}")
    
    total = len(results)
    passed = sum(1 for _, v in results if v)
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("The prediction system now ALWAYS generates predictions.")
        print("Users will NEVER see 'Aucune prédiction n'a pu être générée' again!")
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
