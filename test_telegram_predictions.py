"""
Test Telegram prediction sending with mock data
"""
from src.telegram_prediction_bot import TelegramPredictionBot
from datetime import datetime

print("=" * 60)
print("Testing Telegram Prediction Report")
print("=" * 60)

# Create mock prediction results
mock_results = [
    {
        "Produit": "BMCE Capital Actions",
        "VL Actuelle": 1050.25,
        "VL Cible (30j)": 1075.50,
        "Performance Attendue (%)": 2.40,
        "Signal": "BULLISH",
        "Conviction": "HIGH",
        "Fiabilité (Accuracy)": "85.2%",
        "Confiance IA": "85%",
        "Score Sentiment": 0.65,
        "Méthode": "ML Avancé",
        "AI_Analysis": {
            'signal': 'BULLISH',
            'conviction': 'HIGH',
            'reasoning': 'Based on technical uptrend with strong momentum and favorable macro conditions. The fund shows consistent outperformance with low volatility.',
            'recommendation': 'OVERWEIGHT',
            'risk_assessment': 'MODERATE',
            'confidence_level': 85.0,
            'technical_summary': 'UPTREND (STRONG), Momentum: +1.85%, Volatility: 12.45%',
            'macro_summary': 'Taux BAM: 2.00%, Impact: BULLISH'
        }
    },
    {
        "Produit": "Attijari Intissar",
        "VL Actuelle": 1125.80,
        "VL Cible (30j)": 1115.30,
        "Performance Attendue (%)": -0.93,
        "Signal": "BEARISH",
        "Conviction": "MODERATE",
        "Fiabilité (Accuracy)": "78.5%",
        "Confiance IA": "72%",
        "Score Sentiment": -0.35,
        "Méthode": "Fallback (Tendance)",
        "AI_Analysis": {
            'signal': 'BEARISH',
            'conviction': 'MODERATE',
            'reasoning': 'Downward pressure from rising interest rates and negative sentiment. Technical indicators suggest continued weakness.',
            'recommendation': 'UNDERWEIGHT',
            'risk_assessment': 'HIGH',
            'confidence_level': 72.0,
            'technical_summary': 'DOWNTREND (MODERATE), Momentum: -0.93%, Volatility: 15.20%',
            'macro_summary': 'Taux BAM: 2.75%, Impact: BEARISH'
        }
    }
]

# Create metadata
mock_metadata = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'funds_processed': 2,
    'macro_params': {
        'taux_bam': 2.75,
        'courbe_taux': 'Stable'
    }
}

# Send to Telegram
print("\nSending prediction report to Telegram...")
bot = TelegramPredictionBot()

try:
    success = bot.send_prediction_report(
        prediction_results=mock_results,
        metadata=mock_metadata,
        send_detailed=True
    )
    
    if success:
        print("\n✅ SUCCESS! Check your Telegram now!")
        print("   You should receive 3 messages:")
        print("   1. Summary report")
        print("   2. BMCE Capital Actions details")
        print("   3. Attijari Intissar details")
    else:
        print("\n❌ FAILED! Check the logs above for errors.")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
