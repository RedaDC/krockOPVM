"""
ASFIM Performance Tables Scraper
=================================
Automatically downloads daily performance data from:
https://asfim.ma/publications/tableaux-des-performances/
"""

import os
import re
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from io import BytesIO

log = logging.getLogger("asfim_scraper")

ASFIM_PERFORMANCE_URL = "https://asfim.ma/publications/tableaux-des-performances/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

class ASFIMPerformanceScraper:
    """Scrapes daily OPCVM performance tables from ASFIM"""
    
    def __init__(self, output_dir="data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_latest_performance_file_url(self) -> str | None:
        """
        Scrapes ASFIM performance page to find the latest Excel file URL.
        
        Returns:
            URL of the latest performance Excel file or None
        """
        try:
            log.info(f"Scraping ASFIM performance page: {ASFIM_PERFORMANCE_URL}")
            response = requests.get(ASFIM_PERFORMANCE_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all Excel file links
            excel_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Look for Excel files with dates in the name
                if any(ext in href.lower() for ext in ['.xlsx', '.xls']):
                    # Extract date from filename or link text
                    link_text = link.get_text().strip()
                    date_match = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', link_text)
                    
                    file_date = None
                    if date_match:
                        day, month, year = date_match.groups()
                        file_date = f"{year}-{month}-{day}"
                    
                    excel_links.append({
                        'url': href if href.startswith('http') else f"https://asfim.ma{href}",
                        'text': link_text,
                        'date': file_date,
                        'filename': href.split('/')[-1]
                    })
            
            if not excel_links:
                log.warning("No Excel files found on ASFIM performance page")
                return None
            
            # Sort by date (most recent first)
            excel_links = [x for x in excel_links if x['date']]
            if excel_links:
                excel_links.sort(key=lambda x: x['date'], reverse=True)
                latest = excel_links[0]
                log.info(f"Latest performance file: {latest['filename']} ({latest['date']})")
                return latest['url']
            else:
                # If no dates found, return the first Excel link
                return excel_links[0]['url']
                
        except Exception as e:
            log.error(f"Failed to scrape ASFIM performance page: {e}")
            return None
    
    def download_performance_file(self, url: str = None, output_path: str = None) -> str | None:
        """
        Downloads the ASFIM performance Excel file.
        
        Args:
            url: Direct URL to Excel file (if None, will scrape to find it)
            output_path: Custom output path
            
        Returns:
            Path to downloaded file or None
        """
        try:
            # If no URL provided, scrape to find it
            if not url:
                url = self.get_latest_performance_file_url()
                if not url:
                    return None
            
            if not output_path:
                date_str = datetime.now().strftime('%Y%m%d')
                output_path = self.output_dir / f"asfim_performance_{date_str}.xlsx"
            
            log.info(f"Downloading ASFIM performance file: {url}")
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
            
            # Save file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            log.info(f"File saved: {output_path}")
            return str(output_path)
            
        except Exception as e:
            log.error(f"Failed to download performance file: {e}")
            return None
    
    def parse_performance_file(self, filepath: str) -> pd.DataFrame:
        """
        Parses the ASFIM performance Excel file.
        
        Args:
            filepath: Path to Excel file
            
        Returns:
            DataFrame with OPCVM performance data
        """
        try:
            log.info(f"Parsing performance file: {filepath}")
            
            # Read Excel file - try multiple sheets
            xls = pd.ExcelFile(filepath)
            log.info(f"Sheets found: {xls.sheet_names}")
            
            all_data = []
            
            for sheet_name in xls.sheet_names:
                # Read sheet with no header first to detect structure
                df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
                
                # Detect header row (look for keywords)
                header_row = self._detect_header_row(df_raw)
                
                # Read with detected header
                df = pd.read_excel(filepath, sheet_name=sheet_name, header=header_row)
                
                # Normalize columns
                df = self._normalize_columns(df)
                
                if not df.empty:
                    all_data.append(df)
            
            if not all_data:
                log.warning("No data parsed from performance file")
                return pd.DataFrame()
            
            # Combine all sheets
            df_combined = pd.concat(all_data, ignore_index=True)
            
            # Clean data
            df_combined = self._clean_data(df_combined)
            
            log.info(f"Parsed {len(df_combined)} rows from performance file")
            return df_combined
            
        except Exception as e:
            log.error(f"Failed to parse performance file: {e}")
            return pd.DataFrame()
    
    def _detect_header_row(self, df_raw: pd.DataFrame) -> int:
        """Detects the header row in raw DataFrame"""
        keywords = {'fonds', 'fund', 'vl', 'liquidative', 'performance', 'opcvm', 'isin', 'date', 'variation'}
        
        for i in range(min(20, len(df_raw))):
            row_text = ' '.join([str(v).lower() for v in df_raw.iloc[i].dropna()])
            matches = sum(1 for kw in keywords if kw in row_text)
            if matches >= 2:
                return i
        
        return 0
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizes column names to standard format"""
        col_map = {}
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            if any(k in col_lower for k in ['fonds', 'fund', 'nom', 'opcvm', 'désignation']):
                col_map[col] = 'nom_fonds'
            elif col_lower in ['vl', 'valeur liquidative', 'vl_jour', 'nav']:
                col_map[col] = 'vl'
            elif any(k in col_lower for k in ['performance', 'variation', 'rendement', 'return']):
                col_map[col] = 'performance'
            elif any(k in col_lower for k in ['classification', 'type', 'catégorie', 'categorie']):
                col_map[col] = 'classification'
            elif any(k in col_lower for k in ['isin', 'code isin']):
                col_map[col] = 'isin'
            elif any(k in col_lower for k in ['date', 'jour', 'date vl']):
                col_map[col] = 'date'
            elif any(k in col_lower for k in ['aum', 'encours', 'actif net']):
                col_map[col] = 'aum'
        
        df = df.rename(columns=col_map)
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans and validates parsed data"""
        # Remove rows where VL is not numeric
        if 'vl' in df.columns:
            df['vl'] = pd.to_numeric(df['vl'], errors='coerce')
            df = df.dropna(subset=['vl'])
        
        # Convert performance to numeric if exists
        if 'performance' in df.columns:
            df['performance'] = pd.to_numeric(df['performance'].astype(str).str.replace('%', ''), errors='coerce')
        
        # Add date if missing
        if 'date' not in df.columns:
            df['date'] = datetime.now().strftime('%Y-%m-%d')
        
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['nom_fonds', 'date'], keep='last')
        
        return df
    
    def get_latest_performance_data(self) -> pd.DataFrame:
        """
        Main method: Downloads and parses the latest performance data.
        
        Returns:
            DataFrame with latest OPCVM performance
        """
        # Step 1: Download file
        filepath = self.download_performance_file()
        
        if not filepath:
            log.error("Failed to download performance file")
            return pd.DataFrame()
        
        # Step 2: Parse file
        df = self.parse_performance_file(filepath)
        
        return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scraper = ASFIMPerformanceScraper()
    df = scraper.get_latest_performance_data()
    
    if not df.empty:
        print(f"\n✅ Successfully downloaded {len(df)} OPCVM records")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nSample data:")
        print(df.head(10))
    else:
        print("\n❌ Failed to download performance data")
