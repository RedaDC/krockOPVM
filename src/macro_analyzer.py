"""
Professional Macro Analysis Module
===================================
Provides comprehensive macroeconomic analysis for Morocco:
- Bank Al-Maghrib (BAM) monetary policy analysis
- World Bank economic indicators
- Bourse de Casablanca (MASI/MADEX) analysis
- ASFIM OPCVM performance tracking
- Yield curve analysis (BDT)
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

log = logging.getLogger("macro_analysis")

class MacroAnalyzer:
    """Professional macroeconomic analysis for Moroccan markets"""
    
    def __init__(self, df_macro: pd.DataFrame):
        """
        Initialize with macro dataset
        
        Args:
            df_macro: DataFrame from build_macro_dataset()
        """
        self.df_macro = df_macro.copy()
        self.df_macro = self.df_macro.sort_index()
        
    def get_bam_policy_analysis(self) -> Dict:
        """
        Analyzes Bank Al-Maghrib monetary policy stance
        
        Returns:
            Dictionary with policy analysis
        """
        if 'taux_directeur_bam' not in self.df_macro.columns:
            return {"error": "BAM rate data not available"}
        
        current_rate = self.df_macro['taux_directeur_bam'].iloc[-1]
        
        # Calculate rate changes
        rate_1m_ago = self.df_macro['taux_directeur_bam'].iloc[-20] if len(self.df_macro) >= 20 else current_rate
        rate_3m_ago = self.df_macro['taux_directeur_bam'].iloc[-60] if len(self.df_macro) >= 60 else current_rate
        rate_6m_ago = self.df_macro['taux_directeur_bam'].iloc[-120] if len(self.df_macro) >= 120 else current_rate
        
        rate_change_1m = current_rate - rate_1m_ago
        rate_change_3m = current_rate - rate_3m_ago
        rate_change_6m = current_rate - rate_6m_ago
        
        # Determine policy stance
        if rate_change_3m < -0.25:
            stance = "Dovish (Easing)"
            outlook = "Positive for bonds, mixed for equities"
        elif rate_change_3m > 0.25:
            stance = "Hawkish (Tightening)"
            outlook = "Negative for bonds, depends on economic strength"
        else:
            stance = "Neutral"
            outlook = "Stable environment for all asset classes"
        
        # Reserves analysis
        reserves_trend = "Stable"
        if 'reserves_change_mrd_mad' in self.df_macro.columns:
            current_reserves = self.df_macro['reserves_change_mrd_mad'].iloc[-1]
            reserves_3m_ago = self.df_macro['reserves_change_mrd_mad'].iloc[-60] if len(self.df_macro) >= 60 else current_reserves
            
            reserves_change = (current_reserves - reserves_3m_ago) / reserves_3m_ago * 100
            
            if reserves_change > 2:
                reserves_trend = "Increasing (Positive)"
            elif reserves_change < -2:
                reserves_trend = "Decreasing (Concerning)"
            else:
                reserves_trend = "Stable"
        
        return {
            'current_rate': current_rate,
            'rate_change_1m': rate_change_1m,
            'rate_change_3m': rate_change_3m,
            'rate_change_6m': rate_change_6m,
            'policy_stance': stance,
            'outlook': outlook,
            'reserves_trend': reserves_trend,
            'analysis_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def get_yield_curve_analysis(self) -> Dict:
        """
        Analyzes the Moroccan government bond yield curve (BDT)
        
        Returns:
            Dictionary with yield curve analysis
        """
        required_cols = ['bdt_3m', 'bdt_10y']
        if not all(col in self.df_macro.columns for col in required_cols):
            return {"error": "BDT data not available"}
        
        current_3m = self.df_macro['bdt_3m'].iloc[-1]
        current_10y = self.df_macro['bdt_10y'].iloc[-1]
        
        # Calculate spreads
        spread_10y_3m = current_10y - current_3m
        
        if 'bdt_2y' in self.df_macro.columns and 'bdt_5y' in self.df_macro.columns:
            current_2y = self.df_macro['bdt_2y'].iloc[-1]
            current_5y = self.df_macro['bdt_5y'].iloc[-1]
            spread_5y_2y = current_5y - current_2y
        else:
            spread_5y_2y = None
        
        # Determine curve shape
        if spread_10y_3m > 0.5:
            curve_shape = "Normal (Steep)"
            interpretation = "Expectations of economic growth"
        elif spread_10y_3m > 0.2:
            curve_shape = "Normal (Flat)"
            interpretation = "Stable economic outlook"
        elif spread_10y_3m > 0:
            curve_shape = "Slightly Positive"
            interpretation = "Cautious optimism"
        else:
            curve_shape = "Inverted"
            interpretation = "Recession warning"
        
        # Trend analysis
        if len(self.df_macro) >= 30:
            spread_30d_ago = self.df_macro['spread_10y_3m'].iloc[-30] if 'spread_10y_3m' in self.df_macro.columns else spread_10y_3m
            spread_change = spread_10y_3m - spread_30d_ago
            
            if spread_change > 0.1:
                trend = "Steepening (Positive for banks)"
            elif spread_change < -0.1:
                trend = "Flattening (Caution advised)"
            else:
                trend = "Stable"
        else:
            trend = "Insufficient data for trend"
        
        return {
            'current_3m': current_3m,
            'current_10y': current_10y,
            'spread_10y_3m': spread_10y_3m,
            'spread_5y_2y': spread_5y_2y,
            'curve_shape': curve_shape,
            'interpretation': interpretation,
            'trend': trend,
            'analysis_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def get_market_analysis(self) -> Dict:
        """
        Analyzes Bourse de Casablanca (MASI/MADEX) performance
        
        Returns:
            Dictionary with market analysis
        """
        if 'masi' not in self.df_macro.columns:
            return {"error": "MASI data not available"}
        
        current_masi = self.df_macro['masi'].iloc[-1]
        
        # Calculate returns
        returns = {}
        for period_days in [5, 20, 60, 252]:  # 1 week, 1 month, 3 months, 1 year
            if len(self.df_macro) > period_days:
                past_value = self.df_macro['masi'].iloc[-(period_days+1)]
                period_return = (current_masi - past_value) / past_value * 100
                returns[f'return_{period_days}d'] = period_return
        
        # Volatility
        if 'masi_ret' in self.df_macro.columns:
            vol_20d = self.df_macro['masi_ret'].iloc[-20:].std() * np.sqrt(252) * 100
            vol_60d = self.df_macro['masi_ret'].iloc[-60:].std() * np.sqrt(252) * 100
        else:
            vol_20d = None
            vol_60d = None
        
        # Moving averages
        if len(self.df_macro) >= 200:
            sma_50 = self.df_macro['masi'].iloc[-50:].mean()
            sma_200 = self.df_macro['masi'].iloc[-200:].mean()
            
            if current_masi > sma_50 > sma_200:
                trend = "Bullish (Above both MAs)"
            elif current_masi < sma_50 < sma_200:
                trend = "Bearish (Below both MAs)"
            else:
                trend = "Mixed/Transitioning"
        else:
            trend = "Insufficient data"
            sma_50 = None
            sma_200 = None
        
        return {
            'current_masi': current_masi,
            'returns': returns,
            'volatility_20d': vol_20d,
            'volatility_60d': vol_60d,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'trend': trend,
            'analysis_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def get_world_bank_analysis(self) -> Dict:
        """
        Analyzes World Bank economic indicators for Morocco
        
        Returns:
            Dictionary with World Bank indicators analysis
        """
        indicators = {}
        
        # Inflation
        if 'inflation_cpi' in self.df_macro.columns:
            current_inflation = self.df_macro['inflation_cpi'].iloc[-1]
            inflation_trend = "Stable"
            
            if len(self.df_macro) >= 12:
                inflation_1y_ago = self.df_macro['inflation_cpi'].iloc[-12]
                if current_inflation > inflation_1y_ago + 1:
                    inflation_trend = "Rising (Concerning)"
                elif current_inflation < inflation_1y_ago - 1:
                    inflation_trend = "Declining (Positive)"
            
            indicators['inflation'] = {
                'current': current_inflation,
                'trend': inflation_trend
            }
        
        # GDP Growth
        if 'croissance_pib' in self.df_macro.columns:
            current_gdp = self.df_macro['croissance_pib'].iloc[-1]
            indicators['gdp_growth'] = {
                'current': current_gdp,
                'assessment': 'Strong' if current_gdp > 3.5 else ('Moderate' if current_gdp > 2 else 'Weak')
            }
        
        # Exchange Rate
        if 'taux_change_mad_usd' in self.df_macro.columns:
            current_fx = self.df_macro['taux_change_mad_usd'].iloc[-1]
            fx_trend = "Stable"
            
            if len(self.df_macro) >= 20:
                fx_1m_ago = self.df_macro['taux_change_mad_usd'].iloc[-20]
                fx_change = (current_fx - fx_1m_ago) / fx_1m_ago * 100
                
                if fx_change > 2:
                    fx_trend = "MAD Weakening"
                elif fx_change < -2:
                    fx_trend = "MAD Strengthening"
            
            indicators['exchange_rate'] = {
                'mad_usd': current_fx,
                'trend': fx_trend
            }
        
        return {
            'indicators': indicators,
            'analysis_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def get_comprehensive_analysis(self) -> Dict:
        """
        Provides comprehensive macro analysis combining all sources
        
        Returns:
            Dictionary with full analysis
        """
        log.info("Generating comprehensive macro analysis...")
        
        analysis = {
            'bam_policy': self.get_bam_policy_analysis(),
            'yield_curve': self.get_yield_curve_analysis(),
            'market': self.get_market_analysis(),
            'world_bank': self.get_world_bank_analysis(),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Generate overall market regime
        analysis['market_regime'] = self._determine_market_regime(analysis)
        
        # Generate investment recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _determine_market_regime(self, analysis: Dict) -> str:
        """Determines current market regime based on macro indicators"""
        score = 0
        
        # BAM policy
        bam = analysis.get('bam_policy', {})
        if 'Dovish' in bam.get('policy_stance', ''):
            score += 1
        elif 'Hawkish' in bam.get('policy_stance', ''):
            score -= 1
        
        # Yield curve
        yc = analysis.get('yield_curve', {})
        if 'Normal' in yc.get('curve_shape', ''):
            score += 1
        elif 'Inverted' in yc.get('curve_shape', ''):
            score -= 2
        
        # Market trend
        mkt = analysis.get('market', {})
        if 'Bullish' in mkt.get('trend', ''):
            score += 1
        elif 'Bearish' in mkt.get('trend', ''):
            score -= 1
        
        # Determine regime
        if score >= 2:
            return "Risk-On (Favorable for equities)"
        elif score <= -2:
            return "Risk-Off (Favorable for bonds/cash)"
        else:
            return "Neutral (Balanced approach recommended)"
    
    def _generate_recommendations(self, analysis: Dict) -> Dict:
        """Generates investment recommendations by asset class"""
        regime = analysis.get('market_regime', 'Neutral')
        recommendations = {}
        
        if 'Risk-On' in regime:
            recommendations = {
                'Actions': 'Overweight - Favorable environment',
                'Obligataire': 'Neutral - Moderate duration',
                'Monétaire': 'Underweight - Low returns expected',
                'Diversifié': 'Overweight - Good risk/reward'
            }
        elif 'Risk-Off' in regime:
            recommendations = {
                'Actions': 'Underweight - Reduce exposure',
                'Obligataire': 'Overweight - Increase duration',
                'Monétaire': 'Overweight - Safe haven',
                'Diversifié': 'Neutral - Defensive positioning'
            }
        else:
            recommendations = {
                'Actions': 'Neutral - Selective opportunities',
                'Obligataire': 'Neutral - Balanced duration',
                'Monétaire': 'Neutral - Liquidity management',
                'Diversifié': 'Neutral - Balanced allocation'
            }
        
        return recommendations
    
    def generate_report(self) -> str:
        """Generates a formatted text report of the macro analysis"""
        analysis = self.get_comprehensive_analysis()
        
        report = []
        report.append("="*70)
        report.append("ANALYSE MACROÉCONOMIQUE PROFESSIONNELLE - MAROC")
        report.append("="*70)
        report.append(f"Date: {analysis['timestamp']}")
        report.append(f"Régime de marché: {analysis['market_regime']}")
        report.append("")
        
        # BAM Policy
        bam = analysis.get('bam_policy', {})
        if 'error' not in bam:
            report.append("┌─ BANK AL-MAGHRIB (Politique Monétaire)")
            report.append(f"│ Taux directeur: {bam.get('current_rate', 'N/A')}%")
            report.append(f"│ Position: {bam.get('policy_stance', 'N/A')}")
            report.append(f"│ Réserves de change: {bam.get('reserves_trend', 'N/A')}")
            report.append(f"│ Perspectives: {bam.get('outlook', 'N/A')}")
            report.append("")
        
        # Yield Curve
        yc = analysis.get('yield_curve', {})
        if 'error' not in yc:
            report.append("┌─ COURBE DES TAUX (BDT)")
            report.append(f"│ Taux 3 mois: {yc.get('current_3m', 'N/A')}%")
            report.append(f"│ Taux 10 ans: {yc.get('current_10y', 'N/A')}%")
            report.append(f"│ Spread 10Y-3M: {yc.get('spread_10y_3m', 'N/A'):.2f}%")
            report.append(f"│ Forme: {yc.get('curve_shape', 'N/A')}")
            report.append(f"│ Tendance: {yc.get('trend', 'N/A')}")
            report.append("")
        
        # Market
        mkt = analysis.get('market', {})
        if 'error' not in mkt:
            report.append("┌─ BOURSE DE CASABLANCA (MASI)")
            report.append(f"│ Niveau actuel: {mkt.get('current_masi', 'N/A'):,.2f}")
            report.append(f"│ Tendance: {mkt.get('trend', 'N/A')}")
            returns = mkt.get('returns', {})
            if returns:
                report.append(f"│ Performance 1 mois: {returns.get('return_20d', 'N/A'):+.2f}%")
                report.append(f"│ Performance 3 mois: {returns.get('return_60d', 'N/A'):+.2f}%")
            report.append("")
        
        # Recommendations
        recs = analysis.get('recommendations', {})
        if recs:
            report.append("┌─ RECOMMANDATIONS D'INVESTISSEMENT")
            for asset_class, rec in recs.items():
                report.append(f"│ {asset_class}: {rec}")
            report.append("")
        
        report.append("="*70)
        
        return "\n".join(report)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    from data_collector import build_macro_dataset
    
    print("Loading macro dataset...")
    df_macro = build_macro_dataset()
    
    analyzer = MacroAnalyzer(df_macro)
    report = analyzer.generate_report()
    print(report)
