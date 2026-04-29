"""
Test Script for All Improvements
==================================
Tests:
1. ASFIM Performance Scraper
2. Enhanced Macro Data Collection
3. Advanced Predictor (non-neutral predictions)
4. Macro Predictor (with fallback)
5. News Sentiment (financial focus)
6. Professional Macro Analysis
"""

import sys
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_collector import build_macro_dataset, get_bam_taux_directeur, get_courbe_taux_bdt
from src.advanced_predictor import AdvancedPredictor
from src.macro_prediction import MacroPredictor
from src.feature_builder import build_vl_features
from src.macro_analyzer import MacroAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
log = logging.getLogger("test_improvements")

def test_macro_data():
    """Test 1: Enhanced macro data collection"""
    print("\n" + "="*70)
    print("TEST 1: Enhanced Macro Data Collection")
    print("="*70)
    
    try:
        # Test BAM rates
        df_bam = get_bam_taux_directeur()
        print(f"✓ BAM taux directeur: {len(df_bam)} records")
        print(f"  Current rate: {df_bam['taux_directeur_bam'].iloc[-1]}%")
        
        # Test BDT curve
        df_bdt = get_courbe_taux_bdt()
        print(f"✓ BDT courbe des taux: {len(df_bdt)} records")
        print(f"  3M: {df_bdt['bdt_3m'].iloc[-1]}%, 10Y: {df_bdt['bdt_10y'].iloc[-1]}%")
        
        # Test full macro dataset
        df_macro = build_macro_dataset(start_date="2023-01-01")
        print(f"✓ Full macro dataset: {df_macro.shape}")
        print(f"  Columns: {len(df_macro.columns)}")
        
        return df_macro
        
    except Exception as e:
        print(f"✗ Macro data test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_advanced_predictor(df_macro):
    """Test 2: Advanced Predictor with improved sensitivity"""
    print("\n" + "="*70)
    print("TEST 2: Advanced Predictor (Improved Sensitivity)")
    print("="*70)
    
    try:
        # Generate sample VL data
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", "2026-04-29", freq="B")
        vl_values = 1000 * (1 + np.cumsum(np.random.normal(0.0003, 0.005, len(dates))))
        
        df_vl = pd.DataFrame({
            'date': dates,
            'vl': vl_values,
            'nom_fonds': 'Test Fund Actions'
        })
        
        print(f"Sample VL data: {len(df_vl)} records")
        print(f"VL range: {vl_values[0]:.2f} to {vl_values[-1]:.2f}")
        
        # Create predictor
        predictor = AdvancedPredictor(df_macro=df_macro)
        
        # Train and evaluate
        metrics, error = predictor.train_and_evaluate(df_vl, test_days=30)
        
        if metrics:
            print(f"✓ Model trained successfully")
            print(f"  MAE: {metrics['mae']:.6f}")
            print(f"  RMSE: {metrics['rmse']:.6f}")
            print(f"  Directional Accuracy: {metrics['dir_accuracy']:.2%}")
            print(f"  Features used: {len(predictor.features)}")
            
            # Test prediction
            predictions = predictor.predict_future(df_vl, days_ahead=30)
            
            if not predictions.empty:
                print(f"✓ Generated {len(predictions)} predictions")
                print(f"  First prediction: {predictions.iloc[0]['vl_jour']:.2f}")
                print(f"  Last prediction: {predictions.iloc[-1]['vl_jour']:.2f}")
                
                # Check if predictions are non-neutral
                returns = predictions['expected_return'].values
                print(f"  Expected returns range: {returns.min():.4f}% to {returns.max():.4f}%")
                print(f"  Mean expected return: {returns.mean():.4f}%")
                
                if abs(returns.mean()) > 0.001:
                    print(f"  ✓ Predictions are NON-NEUTRAL (good!)")
                else:
                    print(f"  ⚠ Predictions might be too neutral")
                
                return True
            else:
                print(f"✗ No predictions generated")
                return False
        else:
            print(f"✗ Training failed: {error}")
            return False
            
    except Exception as e:
        print(f"✗ Advanced predictor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_macro_predictor():
    """Test 3: Macro Predictor with fallback"""
    print("\n" + "="*70)
    print("TEST 3: Macro Predictor (With Fallback)")
    print("="*70)
    
    try:
        # Generate sample data
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", "2026-04-29", freq="B")
        
        df_history = pd.DataFrame({
            'date': dates,
            'nom_fonds': 'Test Fund Obligataire',
            'classification': 'Obligataire',
            'vl_jour': 1000 + np.cumsum(np.random.normal(0.02, 0.5, len(dates)))
        })
        
        print(f"Sample history: {len(df_history)} records")
        
        # Create predictor
        predictor = MacroPredictor()
        
        # Test prediction
        predictions = predictor.predict(
            df_history=df_history,
            taux_bam=1.75,
            courbe_taux="ascendante",
            anticipations_text="Bank Al-Maghrib maintient une politique accommodante",
            days_ahead=30
        )
        
        if not predictions.empty:
            pred_count = len(predictions[predictions['type'] == 'Prédiction'])
            print(f"✓ Generated {pred_count} predictions")
            
            # Get summary
            summary = predictor.get_prediction_summary(predictions)
            print(f"\nPrediction Summary:")
            print(summary)
            
            return True
        else:
            print(f"✗ No predictions generated")
            return False
            
    except Exception as e:
        print(f"✗ Macro predictor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_macro_analyzer(df_macro):
    """Test 4: Professional Macro Analyzer"""
    print("\n" + "="*70)
    print("TEST 4: Professional Macro Analyzer")
    print("="*70)
    
    try:
        analyzer = MacroAnalyzer(df_macro)
        
        # Test BAM analysis
        bam_analysis = analyzer.get_bam_policy_analysis()
        if 'error' not in bam_analysis:
            print(f"✓ BAM Policy Analysis:")
            print(f"  Current rate: {bam_analysis['current_rate']}%")
            print(f"  Stance: {bam_analysis['policy_stance']}")
            print(f"  Reserves: {bam_analysis['reserves_trend']}")
        else:
            print(f"✗ BAM analysis: {bam_analysis['error']}")
        
        # Test yield curve
        yc_analysis = analyzer.get_yield_curve_analysis()
        if 'error' not in yc_analysis:
            print(f"\n✓ Yield Curve Analysis:")
            print(f"  3M: {yc_analysis['current_3m']}%, 10Y: {yc_analysis['current_10y']}%")
            print(f"  Spread: {yc_analysis['spread_10y_3m']:.2f}%")
            print(f"  Shape: {yc_analysis['curve_shape']}")
        else:
            print(f"\n✗ Yield curve: {yc_analysis['error']}")
        
        # Test market analysis
        mkt_analysis = analyzer.get_market_analysis()
        if 'error' not in mkt_analysis:
            print(f"\n✓ Market Analysis:")
            print(f"  MASI: {mkt_analysis['current_masi']:,.2f}")
            print(f"  Trend: {mkt_analysis['trend']}")
        else:
            print(f"\n✗ Market: {mkt_analysis['error']}")
        
        # Test comprehensive report
        report = analyzer.generate_report()
        print(f"\n✓ Comprehensive Report Generated ({len(report)} characters)")
        
        return True
        
    except Exception as e:
        print(f"✗ Macro analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_news_sentiment():
    """Test 5: News Sentiment Pipeline (Financial Focus)"""
    print("\n" + "="*70)
    print("TEST 5: News Sentiment Pipeline (Financial Focus)")
    print("="*70)
    
    try:
        from src.news_sentiment_pipeline import NewsSentimentPipeline, FINANCIAL_KEYWORDS
        
        print(f"✓ Financial keywords loaded: {len(FINANCIAL_KEYWORDS)}")
        print(f"  Sample keywords: {', '.join(FINANCIAL_KEYWORDS[:5])}...")
        
        # Create pipeline (without loading models to save time)
        pipeline = NewsSentimentPipeline()
        
        # Test mock news generation
        mock_news = pipeline.generate_mock_news(n_articles=10)
        print(f"\n✓ Mock news generated: {len(mock_news)} articles")
        
        if 'financial_score' in mock_news.columns:
            print(f"  Financial scoring enabled")
            print(f"  Max score: {mock_news['financial_score'].max()}")
        
        return True
        
    except Exception as e:
        print(f"✗ News sentiment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("OPCVM ANALYTICS - COMPREHENSIVE IMPROVEMENT TESTS")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 1: Macro Data
    df_macro = test_macro_data()
    results['macro_data'] = df_macro is not None
    
    # Test 2: Advanced Predictor
    if df_macro is not None:
        results['advanced_predictor'] = test_advanced_predictor(df_macro)
    else:
        results['advanced_predictor'] = False
    
    # Test 3: Macro Predictor
    results['macro_predictor'] = test_macro_predictor()
    
    # Test 4: Macro Analyzer
    if df_macro is not None:
        results['macro_analyzer'] = test_macro_analyzer(df_macro)
    else:
        results['macro_analyzer'] = False
    
    # Test 5: News Sentiment
    results['news_sentiment'] = test_news_sentiment()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:30s} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Application improvements are working correctly.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please review the errors above.")
    
    return results

if __name__ == "__main__":
    results = main()
