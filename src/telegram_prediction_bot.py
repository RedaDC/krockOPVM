"""
Enhanced Telegram Bot with AI Predictions
==========================================
Sends professional prediction reports with:
- Stable prediction table summary
- Detailed AI justifications for each fund
- Technical analysis
- Macro factors
- Recommendations
- Risk assessment
"""

import pandas as pd
import requests
from datetime import datetime
from typing import Dict, List, Optional
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TELEGRAM

log = logging.getLogger("telegram_predictions")

class TelegramPredictionBot:
    """
    Enhanced Telegram bot for sending AI prediction reports
    with detailed justifications and professional analysis.
    """
    
    def __init__(self, token=None, chat_id=None):
        """Initialize the prediction bot"""
        self.token = token or TELEGRAM.get('token')
        self.chat_id = chat_id or TELEGRAM.get('chat_id')
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        
    def send_prediction_report(
        self,
        prediction_results: List[Dict],
        metadata: Dict = None,
        send_detailed: bool = True
    ) -> bool:
        """
        Send comprehensive prediction report to Telegram.
        
        Args:
            prediction_results: List of prediction dictionaries from session state
            metadata: Prediction metadata (timestamp, params)
            send_detailed: Whether to send detailed justifications
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Send summary first
            summary_msg = self._format_summary(prediction_results, metadata)
            self._send_message(summary_msg)
            
            # Send detailed justifications if requested
            if send_detailed:
                for result in prediction_results:
                    detail_msg = self._format_detail(result)
                    if detail_msg:
                        self._send_message(detail_msg)
            
            log.info(f"Prediction report sent: {len(prediction_results)} funds")
            return True
            
        except Exception as e:
            log.error(f"Failed to send prediction report: {e}")
            return False
    
    def _format_summary(
        self, 
        results: List[Dict], 
        metadata: Dict = None
    ) -> str:
        """
        Format prediction summary table for Telegram.
        Telegram has 4096 character limit per message.
        """
        # Header with metadata
        msg = "📊 *RAPPORT PREDICTIONS OPCVM*\n\n"
        
        if metadata:
            timestamp = metadata.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            bam_rate = metadata.get('macro_params', {}).get('taux_bam', 'N/A')
            msg += f"📅 Date: {timestamp}\n"
            msg += f"🏦 Taux BAM: {bam_rate}%\n"
        
        msg += f"📈 Fonds analysés: {len(results)}\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Summary statistics
        bullish = [r for r in results if 'BULLISH' in r.get('Signal', '')]
        bearish = [r for r in results if 'BEARISH' in r.get('Signal', '')]
        neutral = [r for r in results if 'NEUTRAL' in r.get('Signal', '')]
        
        msg += f"🟢 Signaux Haussiers: {len(bullish)}\n"
        msg += f"🔴 Signaux Baissiers: {len(bearish)}\n"
        msg += f"⚪ Signaux Neutres: {len(neutral)}\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Top 5 predictions (by absolute performance)
        sorted_results = sorted(
            results, 
            key=lambda x: abs(x.get('Performance Attendue (%)', 0)), 
            reverse=True
        )[:5]
        
        msg += "*TOP 5 PREDICTIONS:*\n\n"
        
        for i, result in enumerate(sorted_results, 1):
            fund = result.get('Produit', 'Unknown')[:30]
            perf = result.get('Performance Attendue (%)', 0)
            signal = result.get('Signal', 'NEUTRAL')
            conviction = result.get('Conviction', 'LOW')
            method = result.get('Methode', 'N/A')
            
            # Signal emoji
            if 'BULLISH' in signal:
                signal_emoji = "🟢"
            elif 'BEARISH' in signal:
                signal_emoji = "🔴"
            else:
                signal_emoji = "⚪"
            
            msg += f"*{i}. {signal_emoji} {fund}*\n"
            msg += f"   Performance: {perf:+.2f}%\n"
            msg += f"   Signal: {signal} ({conviction})\n"
            msg += f"   Méthode: {method}\n"
            msg += f"   VL: {result.get('VL Actuelle', 0):.2f} → {result.get('VL Cible (30j)', 0):.2f}\n"
            msg += f"   Confiance IA: {result.get('Confiance IA', 'N/A')}\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += "⚠️ _Disclaimer: Rapport généré automatiquement par IA. Consultez un conseiller financier avant toute décision._"
        
        return msg
    
    def _format_detail(self, result: Dict) -> Optional[str]:
        """
        Format detailed justification for a single fund.
        """
        ai_analysis = result.get('AI_Analysis')
        if not ai_analysis:
            return None
        
        fund = result.get('Produit', 'Unknown')
        signal = result.get('Signal', 'NEUTRAL')
        conviction = result.get('Conviction', 'LOW')
        perf = result.get('Performance Attendue (%)', 0)
        
        # Signal emoji
        if 'BULLISH' in signal:
            signal_emoji = "🟢"
        elif 'BEARISH' in signal:
            signal_emoji = "🔴"
        else:
            signal_emoji = "⚪"
        
        msg = f"{signal_emoji} *{fund}*\n"
        msg += f"*Signal:* {signal} ({conviction})\n"
        msg += f"*Performance 30j:* {perf:+.2f}%\n"
        msg += f"*VL Actuelle:* {result.get('VL Actuelle', 0):.2f} MAD\n"
        msg += f"*VL Cible:* {result.get('VL Cible (30j)', 0):.2f} MAD\n"
        msg += f"*Confiance IA:* {result.get('Confiance IA', 'N/A')}\n"
        msg += f"*Données:* {result.get('Data_Points', 0)} jours\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Justification from AI reasoning
        msg += "*📝 JUSTIFICATION:*\n\n"
        reasoning = ai_analysis.get('reasoning', 'Non disponible')
        if not reasoning or reasoning == 'Non disponible':
            # Fallback to old field name
            reasoning = result.get('Prediction_Justification', 'Non disponible')
        # Truncate if too long (Telegram limit)
        if len(reasoning) > 800:
            reasoning = reasoning[:800] + "..."
        msg += f"{reasoning}\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Technical Analysis (from AI reasoning engine)
        if 'technical_summary' in ai_analysis:
            msg += "*📊 ANALYSE TECHNIQUE:*\n"
            msg += f"{ai_analysis.get('technical_summary', 'N/A')}\n\n"
        
        # Macro Analysis (from AI reasoning engine)
        if 'macro_summary' in ai_analysis:
            msg += "*🏦 FACTEURS MACRO:*\n"
            msg += f"{ai_analysis.get('macro_summary', 'N/A')}\n\n"
        
        # Sentiment
        sentiment = ai_analysis.get('sentiment_analysis', {})
        if sentiment:
            msg += "*📰 SENTIMENT ACTUALITÉS:*\n"
            msg += f"• Sentiment: {sentiment.get('overall_sentiment', 'N/A')}\n"
            msg += f"• Score: {sentiment.get('sentiment_score', 0):+.3f}\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Recommendation (from AI reasoning engine)
        if 'recommendation' in ai_analysis:
            msg += "*💡 RECOMMANDATION:*\n"
            rec_action = ai_analysis.get('recommendation', 'N/A')
            msg += f"*Action:* {rec_action}\n\n"
            
            if 'risk_assessment' in ai_analysis:
                msg += f"*Risque:* {ai_analysis.get('risk_assessment', 'N/A')}\n\n"
        
        msg += "\n━━━━━━━━━━━━━━━━━━━━\n"
        msg += "⚠️ _Ce rapport est généré automatiquement. Ne constitue pas un conseil financier._"
        
        return msg
    
    def _send_message(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """
        Send message to Telegram with error handling.
        Handles 4096 character limit.
        """
        try:
            # Check message length
            if len(message) > 4096:
                # Split message
                chunks = self._split_message(message, max_length=4000)
                for chunk in chunks:
                    self._send_chunk(chunk, parse_mode)
            else:
                self._send_chunk(message, parse_mode)
            
            return True
            
        except Exception as e:
            log.error(f"Failed to send Telegram message: {e}")
            return False
    
    def _send_chunk(self, message: str, parse_mode: str) -> bool:
        """Send a single message chunk to Telegram"""
        url = f"{self.api_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        log.info(f"Message sent successfully ({len(message)} chars)")
        return True
    
    def _split_message(self, message: str, max_length: int = 4000) -> List[str]:
        """Split long message into chunks at natural breakpoints"""
        chunks = []
        
        # Try to split at section dividers first
        sections = message.split('\n\n━━━━━━━━━━━━━━━━━━━━\n\n')
        
        current_chunk = ""
        for section in sections:
            if len(current_chunk) + len(section) + 50 < max_length:
                current_chunk += section + '\n\n━━━━━━━━━━━━━━━━━━━━\n\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = section + '\n\n━━━━━━━━━━━━━━━━━━━━\n\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If any chunk is still too long, do hard split
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > 4096:
                # Hard split at max_length
                for i in range(0, len(chunk), max_length):
                    final_chunks.append(chunk[i:i+max_length])
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def send_test_message(self) -> bool:
        """Send a test message to verify bot configuration"""
        test_msg = "✅ *Test Bot OPCVM*\n\n"
        test_msg += "Le bot de predictions est correctement configuré.\n\n"
        test_msg += f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        test_msg += "Vous recevrez désormais les rapports de predictions détaillés avec justifications IA."
        
        return self._send_message(test_msg)


def send_predictions_to_telegram(
    prediction_results: List[Dict],
    metadata: Dict = None,
    token: str = None,
    chat_id: str = None,
    send_detailed: bool = True
) -> bool:
    """
    Convenience function to send predictions to Telegram.
    
    Args:
        prediction_results: List of prediction results
        metadata: Prediction metadata
        token: Telegram bot token (optional)
        chat_id: Telegram chat ID (optional)
        send_detailed: Whether to send detailed justifications
        
    Returns:
        bool: True if sent successfully
    """
    bot = TelegramPredictionBot(token=token, chat_id=chat_id)
    return bot.send_prediction_report(prediction_results, metadata, send_detailed)
