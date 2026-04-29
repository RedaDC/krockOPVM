"""
Historical Data Accumulator for OPCVM
======================================
Accumulates daily ASFIM uploads to build historical time series.
Solves the problem of ASFIM files containing only 1 day of data.
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

log = logging.getLogger("historical_accumulator")

class HistoricalDataAccumulator:
    """
    Accumulates daily OPCVM data uploads to build historical time series.
    Each daily upload is stored and combined to create multi-day history.
    """
    
    def __init__(self, storage_dir="data/historical"):
        """
        Initialize the accumulator.
        
        Args:
            storage_dir: Directory to store historical daily files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "opcvm_historical_complete.csv"
        
    def add_daily_data(self, df_daily: pd.DataFrame, source_date: datetime = None) -> bool:
        """
        Add a day's OPCVM data to the historical database.
        
        Args:
            df_daily: DataFrame with columns ['date', 'nom_fonds', 'classification', 'vl_jour']
            source_date: Date of the data (if not in DataFrame)
            
        Returns:
            bool: True if successfully added
        """
        try:
            df = df_daily.copy()
            
            # Ensure date column exists
            if 'date' not in df.columns:
                if source_date:
                    df['date'] = source_date
                else:
                    df['date'] = datetime.now().normalize()
            
            # Ensure date is datetime
            df['date'] = pd.to_datetime(df['date']).dt.normalize()
            
            # Validate required columns
            required_cols = ['date', 'nom_fonds', 'vl_jour']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                log.error(f"Missing required columns: {missing}")
                return False
            
            # Load existing history
            if self.history_file.exists():
                df_history = pd.read_csv(self.history_file, parse_dates=['date'])
                
                # Remove duplicate entries for same date and fund
                df_history = df_history.drop_duplicates(subset=['date', 'nom_fonds'], keep='last')
                
                # Combine with new data
                df_combined = pd.concat([df_history, df], ignore_index=True)
                
                # Remove duplicates again (in case of re-upload)
                df_combined = df_combined.drop_duplicates(subset=['date', 'nom_fonds'], keep='last')
            else:
                df_combined = df
            
            # Sort by date and fund
            df_combined = df_combined.sort_values(['date', 'nom_fonds'])
            
            # Save to file
            df_combined.to_csv(self.history_file, index=False)
            
            # Also save daily snapshot
            date_str = df['date'].iloc[0].strftime('%Y%m%d')
            daily_file = self.storage_dir / f"opcvm_daily_{date_str}.csv"
            df.to_csv(daily_file, index=False)
            
            log.info(f"Added {len(df)} records for {df['date'].iloc[0].date()}")
            log.info(f"Total historical records: {len(df_combined)}")
            log.info(f"Date range: {df_combined['date'].min().date()} to {df_combined['date'].max().date()}")
            
            return True
            
        except Exception as e:
            log.error(f"Failed to add daily data: {e}")
            return False
    
    def get_historical_data(self, min_days: int = 5) -> pd.DataFrame:
        """
        Get accumulated historical data.
        
        Args:
            min_days: Minimum days of history required
            
        Returns:
            DataFrame with historical data (empty if insufficient)
        """
        if not self.history_file.exists():
            log.warning("No historical data file found")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(self.history_file, parse_dates=['date'])
            
            # Check if we have enough days
            unique_dates = df['date'].nunique()
            if unique_dates < min_days:
                log.warning(f"Insufficient history: {unique_dates} days (need {min_days})")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            log.error(f"Failed to load historical data: {e}")
            return pd.DataFrame()
    
    def get_fund_history(self, fund_name: str) -> pd.DataFrame:
        """
        Get historical data for a specific fund.
        
        Args:
            fund_name: Name of the fund
            
        Returns:
            DataFrame with fund's historical data
        """
        df_all = self.get_historical_data()
        if df_all.empty:
            return pd.DataFrame()
        
        return df_all[df_all['nom_fonds'] == fund_name].sort_values('date')
    
    def get_summary(self) -> dict:
        """
        Get summary statistics of historical data.
        
        Returns:
            Dictionary with summary info
        """
        if not self.history_file.exists():
            return {
                'total_records': 0,
                'total_days': 0,
                'total_funds': 0,
                'date_range': 'No data',
                'funds_with_enough_data': 0
            }
        
        df = pd.read_csv(self.history_file, parse_dates=['date'])
        
        # Count funds with at least 5 days of data
        fund_counts = df.groupby('nom_fonds')['date'].nunique()
        funds_with_5days = (fund_counts >= 5).sum()
        
        return {
            'total_records': len(df),
            'total_days': df['date'].nunique(),
            'total_funds': df['nom_fonds'].nunique(),
            'date_range': f"{df['date'].min().date()} to {df['date'].max().date()}",
            'funds_with_enough_data': funds_with_5days,
            'funds_with_40days': (fund_counts >= 40).sum()
        }
    
    def clear_history(self):
        """Clear all historical data"""
        if self.history_file.exists():
            self.history_file.unlink()
        
        # Remove daily files
        for file in self.storage_dir.glob("opcvm_daily_*.csv"):
            file.unlink()
        
        log.info("Historical data cleared")
    
    def migrate_existing_data(self, df_current: pd.DataFrame):
        """
        Migrate existing single-day data to historical format.
        Useful for first-time setup.
        
        Args:
            df_current: Current DataFrame with OPCVM data
        """
        if df_current.empty:
            return
        
        log.info(f"Migrating {len(df_current)} existing records to historical format")
        self.add_daily_data(df_current)


# Global instance for use across sessions
def get_accumulator() -> HistoricalDataAccumulator:
    """Get or create the global accumulator instance"""
    return HistoricalDataAccumulator()
