"""
Professional AI Prediction Reasoning Engine
=============================================
Generates professional investment analysis with reasoning based on:
- Technical indicators (trends, momentum, volatility)
- Macro factors (BAM rates, yield curve, MASI)
- News sentiment analysis
- Fund classification characteristics

Provides actionable insights like Bloomberg/Reuters terminal analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging

log = logging.getLogger("ai_reasoning")

class AIReasoningEngine:
    """
    Professional AI reasoning engine for OPCVM predictions.
    Explains WHY a prediction is bullish/bearish with supporting evidence.
    """
    
    def __init__(self):
        self.analysis_components = {
            'technical': 0.35,      # Weight for technical analysis
            'macro': 0.30,          # Weight for macro factors
            'sentiment': 0.20,      # Weight for news sentiment
            'fund_specific': 0.15   # Weight for fund characteristics
        }
    
    def analyze_prediction(
        self,
        df_fund_history: pd.DataFrame,
        prediction_value: float,
        current_vl: float,
        prediction_type: str = "fallback",
        macro_data: Dict = None,
        sentiment_data: Dict = None
    ) -> Dict:
        """
        Generate comprehensive professional analysis for a prediction.
        
        Args:
            df_fund_history: Historical VL data for the fund
            prediction_value: Predicted VL value
            current_vl: Current VL value
            prediction_type: 'ml' or 'fallback'
            macro_data: Macro indicators (optional)
            sentiment_data: News sentiment scores (optional)
            
        Returns:
            Dictionary with complete analysis
        """
        # Calculate performance metrics
        expected_return = ((prediction_value / current_vl) - 1) * 100
        
        # Determine signal
        if expected_return > 1.0:
            signal = "BULLISH"
            conviction = "HIGH" if expected_return > 2.0 else "MODERATE"
        elif expected_return > 0.3:
            signal = "MODERATELY BULLISH"
            conviction = "MODERATE"
        elif expected_return < -1.0:
            signal = "BEARISH"
            conviction = "HIGH" if expected_return < -2.0 else "MODERATE"
        elif expected_return < -0.3:
            signal = "MODERATELY BEARISH"
            conviction = "MODERATE"
        else:
            signal = "NEUTRAL"
            conviction = "LOW"
        
        # Build analysis components
        technical_analysis = self._analyze_technicals(df_fund_history, expected_return)
        macro_analysis = self._analyze_macro(macro_data, df_fund_history)
        sentiment_analysis = self._analyze_sentiment(sentiment_data)
        fund_analysis = self._analyze_fund_specific(df_fund_history)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            signal, expected_return, technical_analysis, 
            macro_analysis, sentiment_analysis, fund_analysis
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            signal, conviction, df_fund_history, expected_return
        )
        
        # Risk assessment
        risk_assessment = self._assess_risk(df_fund_history, prediction_type)
        
        return {
            'signal': signal,
            'conviction': conviction,
            'expected_return_30d': round(expected_return, 2),
            'target_vl': round(prediction_value, 2),
            'current_vl': round(current_vl, 2),
            'technical_analysis': technical_analysis,
            'macro_analysis': macro_analysis,
            'sentiment_analysis': sentiment_analysis,
            'fund_analysis': fund_analysis,
            'reasoning': reasoning,
            'recommendation': recommendation,
            'risk_assessment': risk_assessment,
            'confidence_level': self._calculate_confidence(
                df_fund_history, prediction_type
            ),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _analyze_technicals(self, df_history: pd.DataFrame, expected_return: float) -> Dict:
        """Analyze technical indicators"""
        if len(df_history) < 10:
            return {
                'trend': 'INSUFFICIENT DATA',
                'momentum': 'N/A',
                'volatility': 'N/A',
                'support_resistance': {}
            }
        
        vl_values = df_history['vl_jour'].values
        
        # Trend analysis
        short_ma = vl_values[-5:].mean()
        medium_ma = vl_values[-20:].mean() if len(vl_values) >= 20 else vl_values.mean()
        
        if short_ma > medium_ma * 1.01:
            trend = "UPTREND"
            trend_strength = "STRONG" if short_ma > medium_ma * 1.02 else "MODERATE"
        elif short_ma < medium_ma * 0.99:
            trend = "DOWNTREND"
            trend_strength = "STRONG" if short_ma < medium_ma * 0.98 else "MODERATE"
        else:
            trend = "SIDEWAYS"
            trend_strength = "WEAK"
        
        # Momentum
        if len(vl_values) >= 10:
            momentum = ((vl_values[-1] / vl_values[-10]) - 1) * 100
        else:
            momentum = 0.0
        
        # Volatility
        if len(vl_values) >= 20:
            daily_returns = np.diff(vl_values[-20:]) / vl_values[-20:-1]
            volatility = np.std(daily_returns) * np.sqrt(252) * 100
        else:
            volatility = 0.0
        
        return {
            'trend': trend,
            'trend_strength': trend_strength,
            'momentum_10d': round(momentum, 2),
            'volatility_annual': round(volatility, 2),
            'short_ma_5d': round(short_ma, 2),
            'medium_ma_20d': round(medium_ma, 2)
        }
    
    def _analyze_macro(self, macro_data: Dict, df_history: pd.DataFrame) -> Dict:
        """Analyze macroeconomic factors"""
        if not macro_data:
            return {
                'bam_rate_impact': 'NEUTRAL',
                'yield_curve_impact': 'NEUTRAL',
                'market_environment': 'INSUFFICIENT DATA'
            }
        
        bam_rate = macro_data.get('bam_rate', 2.75)
        yield_curve_shape = macro_data.get('yield_curve', 'normal')
        
        # BAM rate impact
        if bam_rate < 2.0:
            bam_impact = "POSITIVE - Accommodative monetary policy supports bond prices"
            bam_direction = "BULLISH"
        elif bam_rate > 3.0:
            bam_impact = "NEGATIVE - Restrictive policy pressures bond valuations"
            bam_direction = "BEARISH"
        else:
            bam_impact = "NEUTRAL - Moderate rate environment"
            bam_direction = "NEUTRAL"
        
        # Yield curve impact
        if yield_curve_shape == 'steep':
            yc_impact = "POSITIVE - Steep curve benefits bank profitability"
            yc_direction = "BULLISH"
        elif yield_curve_shape == 'inverted':
            yc_impact = "NEGATIVE - Inversion signals economic concerns"
            yc_direction = "BEARISH"
        else:
            yc_impact = "NEUTRAL - Normal curve conditions"
            yc_direction = "NEUTRAL"
        
        return {
            'bam_rate': bam_rate,
            'bam_impact': bam_impact,
            'bam_direction': bam_direction,
            'yield_curve_shape': yield_curve_shape,
            'yield_curve_impact': yc_impact,
            'yield_curve_direction': yc_direction
        }
    
    def _analyze_sentiment(self, sentiment_data: Dict) -> Dict:
        """Analyze news sentiment"""
        if not sentiment_data:
            return {
                'overall_sentiment': 'NEUTRAL',
                'sentiment_score': 0.0,
                'news_impact': 'No recent news data available'
            }
        
        score = sentiment_data.get('score', 0.0)
        article_count = sentiment_data.get('article_count', 0)
        
        if score > 0.2:
            sentiment = "POSITIVE"
            impact = "Favorable news flow supports risk assets"
        elif score > 0.05:
            sentiment = "SLIGHTLY POSITIVE"
            impact = "Mildly optimistic news environment"
        elif score < -0.2:
            sentiment = "NEGATIVE"
            impact = "Adverse news flow creates headwinds"
        elif score < -0.05:
            sentiment = "SLIGHTLY NEGATIVE"
            impact = "Cautious news sentiment prevails"
        else:
            sentiment = "NEUTRAL"
            impact = "Balanced news coverage, no strong directional bias"
        
        return {
            'overall_sentiment': sentiment,
            'sentiment_score': round(score, 3),
            'article_count': article_count,
            'news_impact': impact
        }
    
    def _analyze_fund_specific(self, df_history: pd.DataFrame) -> Dict:
        """Analyze fund-specific characteristics"""
        classification = df_history.get('classification', ['Unknown']).iloc[0] if 'classification' in df_history.columns else 'Unknown'
        
        class_lower = str(classification).lower()
        
        if 'action' in class_lower:
            fund_type = "EQUITY"
            risk_profile = "HIGH"
            key_drivers = "Equity market performance, economic growth, corporate earnings"
        elif 'oblig' in class_lower:
            fund_type = "BOND"
            risk_profile = "MODERATE"
            key_drivers = "Interest rate movements, BAM policy, credit spreads"
        elif 'monet' in class_lower:
            fund_type = "MONEY MARKET"
            risk_profile = "LOW"
            key_drivers = "Short-term rates, liquidity conditions, BAM interventions"
        else:
            fund_type = "DIVERSIFIED"
            risk_profile = "MODERATE-HIGH"
            key_drivers = "Asset allocation, market conditions, manager skill"
        
        return {
            'fund_type': fund_type,
            'classification': classification,
            'risk_profile': risk_profile,
            'key_drivers': key_drivers
        }
    
    def _generate_reasoning(
        self, signal, expected_return, technicals, macro, sentiment, fund_info
    ) -> str:
        """Generate professional reasoning paragraph"""
        reasoning_parts = []
        
        # Opening statement
        reasoning_parts.append(
            f"Based on our analysis, we maintain a {signal} outlook with "
            f"an expected 30-day return of {expected_return:+.2f}%."
        )
        
        # Technical reasoning
        if technicals['trend'] != 'INSUFFICIENT DATA':
            reasoning_parts.append(
                f"Technically, the fund exhibits a {technicals['trend']} "
                f"({technicals['trend_strength']}) with {technicals['momentum_10d']:+.2f}% "
                f"momentum over the past 10 trading days."
            )
        
        # Macro reasoning
        if macro.get('bam_direction') != 'NEUTRAL':
            reasoning_parts.append(
                f"From a macroeconomic perspective, the current BAM rate of "
                f"{macro['bam_rate']}% is {macro['bam_direction'].lower()} for this fund type. "
                f"{macro['bam_impact']}."
            )
        
        # Sentiment reasoning
        if sentiment.get('sentiment_score', 0) != 0:
            reasoning_parts.append(
                f"News sentiment analysis reveals a {sentiment['overall_sentiment'].lower()} "
                f"environment (score: {sentiment['sentiment_score']:+.3f}). "
                f"{sentiment['news_impact']}."
            )
        
        # Fund-specific context
        reasoning_parts.append(
            f"As a {fund_info['fund_type']} fund with {fund_info['risk_profile']} risk profile, "
            f"primary drivers include: {fund_info['key_drivers']}."
        )
        
        return ' '.join(reasoning_parts)
    
    def _generate_recommendation(
        self, signal, conviction, df_history, expected_return
    ) -> Dict:
        """Generate actionable recommendation"""
        classification = df_history.get('classification', ['Unknown']).iloc[0] if 'classification' in df_history.columns else 'Unknown'
        class_lower = str(classification).lower()
        
        if 'BULLISH' in signal:
            if conviction == 'HIGH':
                action = "OVERWEIGHT"
                rationale = f"Strong bullish signals suggest increasing allocation. Expected {expected_return:+.2f}% return over 30 days."
            else:
                action = "MODERATE BUY"
                rationale = f"Moderate bullish indicators support gradual position building."
        elif 'BEARISH' in signal:
            if conviction == 'HIGH':
                action = "UNDERWEIGHT"
                rationale = f"Significant bearish pressures warrant reducing exposure. Expected {expected_return:+.2f}% return."
            else:
                action = "CAUTIOUS"
                rationale = "Bearish signals suggest defensive positioning with reduced allocation."
        else:
            action = "NEUTRAL"
            rationale = "Mixed signals indicate maintaining current allocation levels."
        
        # Fund-specific advice
        if 'monet' in class_lower:
            liquidity_note = "Maintain adequate liquidity for redemptions"
        elif 'oblig' in class_lower:
            liquidity_note = "Monitor duration risk and interest rate sensitivity"
        else:
            liquidity_note = "Review stop-loss levels and rebalance thresholds"
        
        return {
            'action': action,
            'rationale': rationale,
            'liquidity_guidance': liquidity_note,
            'monitoring_points': [
                "BAM policy rate decisions",
                "Yield curve movements",
                "News sentiment shifts",
                "Technical trend changes"
            ]
        }
    
    def _assess_risk(self, df_history: pd.DataFrame, prediction_type: str) -> Dict:
        """Assess prediction risk and reliability"""
        data_points = len(df_history)
        
        if prediction_type == 'ml':
            model_risk = "LOW - Machine learning model with feature engineering"
        else:
            model_risk = "MODERATE - Trend-based fallback analysis"
        
        if data_points >= 40:
            data_risk = "LOW - Sufficient historical data (40+ days)"
        elif data_points >= 20:
            data_risk = "MODERATE - Adequate data (20-40 days)"
        elif data_points >= 5:
            data_risk = "ELEVATED - Limited data (5-20 days)"
        else:
            data_risk = "HIGH - Insufficient data (<5 days)"
        
        # Calculate historical volatility
        if data_points >= 10:
            vl_values = df_history['vl_jour'].values
            daily_returns = np.diff(vl_values) / vl_values[:-1]
            hist_vol = np.std(daily_returns) * np.sqrt(252) * 100
            
            if hist_vol < 5:
                vol_risk = "LOW"
            elif hist_vol < 10:
                vol_risk = "MODERATE"
            elif hist_vol < 20:
                vol_risk = "ELEVATED"
            else:
                vol_risk = "HIGH"
        else:
            hist_vol = 0.0
            vol_risk = "UNKNOWN"
        
        return {
            'model_risk': model_risk,
            'data_risk': data_risk,
            'volatility_risk': vol_risk,
            'historical_volatility': round(hist_vol, 2),
            'overall_risk': 'MODERATE' if 'MODERATE' in data_risk else ('LOW' if 'LOW' in data_risk else 'ELEVATED')
        }
    
    def _calculate_confidence(self, df_history: pd.DataFrame, prediction_type: str) -> float:
        """Calculate confidence score (0-100)"""
        confidence = 50.0  # Base confidence
        
        # Data length factor
        data_points = len(df_history)
        if data_points >= 60:
            confidence += 20
        elif data_points >= 40:
            confidence += 15
        elif data_points >= 20:
            confidence += 10
        elif data_points >= 10:
            confidence += 5
        
        # Model type factor
        if prediction_type == 'ml':
            confidence += 15
        else:
            confidence += 5
        
        # Volatility factor
        if data_points >= 20:
            vl_values = df_history['vl_jour'].values
            daily_returns = np.diff(vl_values[-20:]) / vl_values[-20:-1]
            volatility = np.std(daily_returns) * np.sqrt(252) * 100
            
            if volatility < 5:
                confidence += 10
            elif volatility < 10:
                confidence += 5
            else:
                confidence -= 5
        
        return min(max(confidence, 0), 100)
    
    def format_professional_report(self, analysis: Dict) -> str:
        """Format analysis as professional report (no emojis)"""
        report = []
        report.append("=" * 80)
        report.append("AI PREDICTION ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {analysis['timestamp']}")
        report.append(f"Fund Type: {analysis['fund_analysis']['fund_type']}")
        report.append(f"Classification: {analysis['fund_analysis']['classification']}")
        report.append("")
        
        report.append("SIGNAL SUMMARY")
        report.append("-" * 80)
        report.append(f"Signal: {analysis['signal']}")
        report.append(f"Conviction: {analysis['conviction']}")
        report.append(f"Expected Return (30D): {analysis['expected_return_30d']:+.2f}%")
        report.append(f"Target VL: {analysis['target_vl']:.2f}")
        report.append(f"Current VL: {analysis['current_vl']:.2f}")
        report.append(f"Confidence Level: {analysis['confidence_level']:.0f}%")
        report.append("")
        
        report.append("ANALYTICAL REASONING")
        report.append("-" * 80)
        report.append(analysis['reasoning'])
        report.append("")
        
        report.append("TECHNICAL ANALYSIS")
        report.append("-" * 80)
        tech = analysis['technical_analysis']
        report.append(f"Trend: {tech['trend']} ({tech['trend_strength']})")
        report.append(f"Momentum (10D): {tech['momentum_10d']:+.2f}%")
        report.append(f"Volatility (Annual): {tech['volatility_annual']:.2f}%")
        report.append(f"Short MA (5D): {tech['short_ma_5d']:.2f}")
        report.append(f"Medium MA (20D): {tech['medium_ma_20d']:.2f}")
        report.append("")
        
        report.append("MACROECONOMIC FACTORS")
        report.append("-" * 80)
        macro = analysis['macro_analysis']
        report.append(f"BAM Rate: {macro['bam_rate']}%")
        report.append(f"BAM Impact: {macro['bam_impact']}")
        report.append(f"Yield Curve: {macro['yield_curve_shape']}")
        report.append(f"Yield Curve Impact: {macro['yield_curve_impact']}")
        report.append("")
        
        report.append("NEWS SENTIMENT")
        report.append("-" * 80)
        sent = analysis['sentiment_analysis']
        report.append(f"Overall Sentiment: {sent['overall_sentiment']}")
        report.append(f"Sentiment Score: {sent['sentiment_score']:+.3f}")
        report.append(f"Articles Analyzed: {sent['article_count']}")
        report.append(f"Impact Assessment: {sent['news_impact']}")
        report.append("")
        
        report.append("RECOMMENDATION")
        report.append("-" * 80)
        rec = analysis['recommendation']
        report.append(f"Action: {rec['action']}")
        report.append(f"Rationale: {rec['rationale']}")
        report.append(f"Liquidity Guidance: {rec['liquidity_guidance']}")
        report.append("")
        report.append("Key Monitoring Points:")
        for point in rec['monitoring_points']:
            report.append(f"  - {point}")
        report.append("")
        
        report.append("RISK ASSESSMENT")
        report.append("-" * 80)
        risk = analysis['risk_assessment']
        report.append(f"Overall Risk: {risk['overall_risk']}")
        report.append(f"Model Risk: {risk['model_risk']}")
        report.append(f"Data Risk: {risk['data_risk']}")
        report.append(f"Volatility Risk: {risk['volatility_risk']}")
        if risk['historical_volatility'] > 0:
            report.append(f"Historical Volatility: {risk['historical_volatility']:.2f}%")
        report.append("")
        
        report.append("=" * 80)
        report.append("DISCLAIMER: This analysis is generated by AI models and should not be")
        report.append("the sole basis for investment decisions. Past performance does not")
        report.append("guarantee future results. Always conduct independent due diligence.")
        report.append("=" * 80)
        
        return '\n'.join(report)


# Global instance
def get_ai_reasoning_engine() -> AIReasoningEngine:
    """Get AI reasoning engine instance"""
    return AIReasoningEngine()
