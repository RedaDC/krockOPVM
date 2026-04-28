"""
ASFIM/Maroc Public Data Scraper
Attempts to collect OPCVM data from publicly available sources
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from datetime import datetime

# Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PublicDataScraper:
    """Scrape public OPCVM data from Moroccan financial websites"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        
    def scrape_ammc(self):
        """
        Try AMMC (Market Regulator) for fund statistics
        Source: ammc.ma
        """
        logger.info("Attempting AMMC data collection...")
        
        urls = [
            'https://www.ammc.ma/fr/publications/statistiques',
            'https://www.ammc.ma/fr/opcvm',
        ]
        
        for url in urls:
            try:
                logger.info(f"Trying: {url}")
                response = self.session.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for tables
                tables = soup.find_all('table')
                if tables:
                    logger.info(f"Found {len(tables)} tables at {url}")
                    for i, table in enumerate(tables):
                        df = pd.read_html(str(table))[0]
                        logger.info(f"Table {i}: {df.shape[0]} rows x {df.shape[1]} cols")
                        logger.info(f"Columns: {list(df.columns)}")
                        
                        # Save for inspection
                        df.to_csv(f'data/raw/ammc_table_{i}.csv', index=False)
                        logger.info(f"Saved to data/raw/ammc_table_{i}.csv")
                
                # Look for downloadable files
                links = soup.find_all('a', href=True)
                pdf_links = [link['href'] for link in links if '.pdf' in link['href'].lower() or '.xls' in link['href'].lower()]
                
                if pdf_links:
                    logger.info(f"Found {len(pdf_links)} downloadable files")
                    for link in pdf_links[:5]:  # First 5
                        logger.info(f"  - {link}")
                
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                continue
        
        return None
    
    def scrape_casablanca_bourse(self):
        """
        Try Casablanca Stock Exchange for fund data
        Source: casablanca-bourse.com
        """
        logger.info("Attempting Casablanca Bourse data collection...")
        
        urls = [
            'https://www.casablanca-bourse.com/bourseweb/en/nav-historical.aspx',
            'https://www.casablanca-bourse.com/bourseweb/en/Funds.aspx',
        ]
        
        for url in urls:
            try:
                logger.info(f"Trying: {url}")
                response = self.session.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for fund tables
                tables = soup.find_all('table')
                if tables:
                    logger.info(f"Found {len(tables)} tables")
                    for i, table in enumerate(tables):
                        try:
                            df = pd.read_html(str(table))[0]
                            logger.info(f"Table {i}: {df.shape}")
                            df.to_csv(f'data/raw/casablanca_table_{i}.csv', index=False)
                        except:
                            continue
                
                # Look for fund lists
                fund_links = soup.find_all('a', string=lambda text: text and ('opcvm' in text.lower() or 'fund' in text.lower()))
                if fund_links:
                    logger.info(f"Found {len(fund_links)} fund-related links")
                    for link in fund_links[:10]:
                        logger.info(f"  - {link.get('href', 'no href')}")
                
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                continue
        
        return None
    
    def scrape_asfim_public(self):
        """
        Try ASFIM public pages
        Source: asfim.ma
        """
        logger.info("Attempting ASFIM public data collection...")
        
        urls = [
            'https://asfim.ma/la-gestion-dactifs-au-maroc/opcvm/',
            'https://asfim.ma/',
        ]
        
        for url in urls:
            try:
                logger.info(f"Trying: {url}")
                response = self.session.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for data tables
                tables = soup.find_all('table')
                logger.info(f"Found {len(tables)} tables")
                
                # Look for download links
                links = soup.find_all('a', href=True)
                download_links = []
                
                for link in links:
                    href = link['href'].lower()
                    if any(ext in href for ext in ['.pdf', '.xls', '.xlsx', '.csv', 'download', 'export']):
                        download_links.append({
                            'text': link.get_text(strip=True),
                            'url': link['href']
                        })
                
                if download_links:
                    logger.info(f"Found {len(download_links)} download links:")
                    for dl in download_links[:10]:
                        logger.info(f"  - {dl['text']}: {dl['url']}")
                
                # Save page structure for analysis
                with open(f'data/raw/asfim_page_structure.txt', 'w', encoding='utf-8') as f:
                    f.write(soup.get_text()[:5000])  # First 5000 chars
                    logger.info("Saved page structure to data/raw/asfim_page_structure.txt")
                
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                continue
        
        return None
    
    def run_all_scrapers(self):
        """Run all public data scrapers"""
        logger.info("="*70)
        logger.info("PUBLIC DATA COLLECTION - MOROCCAN OPCVM SOURCES")
        logger.info("="*70)
        
        # Ensure directory exists
        import os
        os.makedirs('data/raw', exist_ok=True)
        
        results = {}
        
        # Try each source
        logger.info("\n1. AMMC (Regulator)")
        results['ammc'] = self.scrape_ammc()
        
        logger.info("\n2. Casablanca Bourse")
        results['casablanca'] = self.scrape_casablanca_bourse()
        
        logger.info("\n3. ASFIM Public")
        results['asfim'] = self.scrape_asfim_public()
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("COLLECTION SUMMARY")
        logger.info("="*70)
        
        # List all files created
        import glob
        files = glob.glob('data/raw/*.csv') + glob.glob('data/raw/*.txt')
        
        if files:
            logger.info(f"\nFiles collected ({len(files)}):")
            for f in files:
                size = os.path.getsize(f)
                logger.info(f"  - {f} ({size:,} bytes)")
            
            logger.info("\nNext steps:")
            logger.info("  1. Review the CSV files in data/raw/")
            logger.info("  2. Check if any contain usable OPCVM data")
            logger.info("  3. If yes, I'll build proper parsers")
        else:
            logger.warning("\nNo data files collected.")
            logger.warning("Possible reasons:")
            logger.warning("  - Websites require JavaScript rendering")
            logger.warning("  - Data is behind login/authentication")
            logger.warning("  - URLs have changed")
            logger.warning("\nRecommendation:")
            logger.warning("  - Try accessing these sites manually in browser")
            logger.warning("  - Share screenshots of data tables you find")
            logger.warning("  - I'll build custom scrapers based on actual structure")
        
        return results


if __name__ == "__main__":
    scraper = PublicDataScraper()
    scraper.run_all_scrapers()
