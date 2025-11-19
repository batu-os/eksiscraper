#!/usr/bin/env python3
"""
Ekşi Sözlük Scraper Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A robust and flexible scraper for Ekşi Sözlük entries.
Supports both CLI and programmatic usage.

Usage:
    CLI:
        python eksiscraper.py <url> [--delay <ms>] [--silent] [--output <filename>]
    
    Module:
        import eksiscraper
        scraper = eksiscraper.EksiScraper(delay_ms=2000, verbose=True)
        df = scraper.scrape("https://eksisozluk.com/baslik--123")
        scraper.save_to_csv(df)

Author: EksiScraper Module
License: MIT
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from curl_cffi import requests
import pandas as pd
from bs4 import BeautifulSoup


def setup_logger(verbose: bool = True) -> logging.Logger:
    """
    Set up and configure logger.
    
    Args:
        verbose: If True, show info logs. If False, only show warnings and errors.
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler - always log everything
    log_file = Path('eksiscraper.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler - respect verbose setting
    # Use utf-8 encoding for console to support emojis
    import io
    console_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
    console_handler.setLevel(logging.INFO if verbose else logging.WARNING)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


class EksiScraper:
    """
    Ekşi Sözlük scraper class for extracting entries from topics.
    """
    
    def __init__(self, delay_ms: int = 2000, verbose: bool = True):
        """
        Initialize the Ekşi Sözlük scraper.

        Args:
            delay_ms: Delay between requests in milliseconds (default: 2000ms)
            verbose: If True, show info logs. If False, only show warnings and errors.
        """
        self.delay_seconds = delay_ms / 1000.0
        self.verbose = verbose
        self.logger = setup_logger(verbose)

        # Headers for curl_cffi - mimics modern Chrome browser
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1'
        }

        # Storage for scraped data
        self.entries: List[Dict] = []
        self.errors: List[Dict] = []

        # Store topic info for filename generation
        self.topic_title: Optional[str] = None
        self.total_pages: int = 0

        self.logger.info(f"🚀 EksiScraper initialized (delay: {delay_ms}ms, verbose: {verbose})")
    
    def _clean_url(self, url: str) -> str:
        """
        Clean and validate URL.

        Args:
            url: Raw URL input

        Returns:
            Cleaned URL without query parameters
        """
        # Remove query parameters
        base_url = url.split('?')[0]

        # Ensure it's an Ekşi Sözlük URL
        if 'eksisozluk.com' not in base_url:
            raise ValueError(f"Invalid URL: {url}. Must be an eksisozluk.com URL.")

        return base_url

    def _extract_topic_title(self, url: str) -> str:
        """
        Extract topic title from URL for filename.

        Args:
            url: Topic URL (e.g., https://eksisozluk.com/baslik-ismi--123)

        Returns:
            Sanitized topic title safe for filename
        """
        try:
            # Extract the path part (e.g., "baslik-ismi--123")
            path = url.split('eksisozluk.com/')[-1].split('?')[0]

            # Remove the ID part (everything after and including --)
            if '--' in path:
                title = path.split('--')[0]
            else:
                title = path

            # Replace hyphens with spaces, then spaces with underscores
            title = title.replace('-', ' ').replace(' ', '_')

            # Remove invalid filename characters
            # Windows invalid chars: < > : " / \ | ? *
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                title = title.replace(char, '')

            # Remove any leading/trailing underscores or dots
            title = title.strip('_. ')

            # Limit length to 100 characters
            if len(title) > 100:
                title = title[:100]

            # If title is empty after sanitization, use a default
            if not title:
                title = 'topic'

            return title

        except Exception as e:
            self.logger.warning(f"⚠️  Could not extract topic title: {str(e)}")
            return 'topic'
    
    def _fetch_page(self, url: str, page_num: int, max_retries: int = 3) -> Optional[str]:
        """
        Fetch a single page with retry logic.
        
        Args:
            url: Page URL to fetch
            page_num: Page number (for logging)
            max_retries: Maximum number of retry attempts
            
        Returns:
            HTML content if successful, None otherwise
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting (except for first page on first attempt)
                if page_num > 1 or attempt > 0:
                    self.logger.info(f"⏳ Waiting {self.delay_seconds:.1f}s...")
                    time.sleep(self.delay_seconds)

                # Make request with curl_cffi (impersonate Chrome 120)
                response = requests.get(url, headers=self.headers, impersonate="chrome120", timeout=30)
                
                # Handle response status codes
                if response.status_code == 200:
                    self.logger.info(f"✅ Page {page_num} fetched successfully")
                    return response.text
                
                elif response.status_code == 429:
                    # Rate limit - exponential backoff
                    wait_time = (attempt + 1) * 10
                    self.logger.warning(
                        f"⚠️  Rate limit on page {page_num}! "
                        f"Waiting {wait_time}s... (Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                
                elif response.status_code == 403:
                    # Forbidden - wait and retry
                    wait_time = (attempt + 1) * 5
                    self.logger.warning(
                        f"⚠️  403 Forbidden on page {page_num}! "
                        f"Waiting {wait_time}s... (Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                
                elif response.status_code == 404:
                    # Not found - no point retrying
                    self.logger.error(f"❌ Page {page_num} not found (404)")
                    self.errors.append({
                        'page': page_num,
                        'error': '404 Not Found',
                        'url': url
                    })
                    return None
                
                else:
                    # Other HTTP errors
                    self.logger.error(f"❌ Page {page_num} - HTTP {response.status_code}")
                    self.errors.append({
                        'page': page_num,
                        'error': f'HTTP {response.status_code}',
                        'url': url
                    })
                    
            except Exception as e:
                self.logger.error(
                    f"❌ Error fetching page {page_num}: {str(e)} "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )
                if attempt == max_retries - 1:
                    self.errors.append({
                        'page': page_num,
                        'error': str(e),
                        'url': url
                    })
        
        return None
    
    def _parse_entries(self, html: str, page_num: int) -> List[Dict]:
        """
        Parse entries from HTML content.
        
        Args:
            html: HTML content to parse
            page_num: Page number (for reference)
            
        Returns:
            List of parsed entry dictionaries
        """
        entries = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find entry list container
            entry_list = soup.find('ul', {'id': 'entry-item-list'})
            if not entry_list:
                self.logger.warning(f"⚠️  No entry list found on page {page_num}")
                return entries
            
            # Find all entries
            entry_items = entry_list.find_all('li', {'id': 'entry-item'})
            self.logger.info(f"📝 Found {len(entry_items)} entries on page {page_num}")
            
            # Parse each entry
            for item in entry_items:
                try:
                    entry_data = {
                        'entry_id': item.get('data-id'),
                        'author': item.get('data-author'),
                        'author_id': item.get('data-author-id'),
                        'favorite_count': item.get('data-favorite-count', '0'),
                        'page_number': page_num,
                    }
                    
                    # Extract content
                    content_div = item.find('div', class_='content')
                    if content_div:
                        entry_data['content'] = content_div.get_text(strip=True)
                    
                    # Extract date
                    footer = item.find('footer')
                    if footer:
                        date_link = footer.find('a', class_='entry-date')
                        if date_link:
                            entry_data['date'] = date_link.get_text(strip=True)
                        else:
                            entry_data['date'] = None
                    else:
                        entry_data['date'] = None
                    
                    entries.append(entry_data)
                    
                except Exception as e:
                    self.logger.debug(f"Error parsing entry: {str(e)}")
                    continue
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing HTML on page {page_num}: {str(e)}")
            self.errors.append({
                'page': page_num,
                'error': f'Parse error: {str(e)}'
            })
        
        return entries
    
    def _get_total_pages(self, base_url: str) -> int:
        """
        Determine the total number of pages for a topic.
        
        Args:
            base_url: Base topic URL
            
        Returns:
            Total number of pages
        """
        try:
            url = f"{base_url}?p=1"
            response = requests.get(url, headers=self.headers, impersonate="chrome120", timeout=30)
            
            if response.status_code != 200:
                self.logger.warning(
                    f"⚠️  Could not determine page count (HTTP {response.status_code}). "
                    "Assuming single page..."
                )
                return 1
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for pager element
            pager = soup.find('div', class_='pager')
            if pager:
                page_count = pager.get('data-pagecount')
                if page_count:
                    total_pages = int(page_count)
                    self.logger.info(f"📚 Topic has {total_pages} page(s)")
                    return total_pages
            
            # No pager means single page
            self.logger.info("📄 Topic has 1 page")
            return 1
            
        except Exception as e:
            self.logger.error(f"❌ Error getting page count: {str(e)}")
            self.logger.info("📄 Assuming single page...")
            return 1
    
    def scrape(self, url: str) -> pd.DataFrame:
        """
        Main scraping method.
        
        Args:
            url: Ekşi Sözlük topic URL to scrape
            
        Returns:
            DataFrame containing scraped entries
        """
        # Reset state
        self.entries = []
        self.errors = []
        seen_entry_ids = set()  # Track unique entries
        
        # Clean and validate URL
        try:
            base_url = self._clean_url(url)
        except ValueError as e:
            self.logger.error(str(e))
            return pd.DataFrame()
        
        self.logger.info(f"🎯 Starting scrape: {base_url}")
        self.logger.info(f"⚙️  Settings: delay={self.delay_seconds:.1f}s, verbose={self.verbose}")

        # Extract topic title for filename
        self.topic_title = self._extract_topic_title(base_url)
        self.logger.debug(f"📝 Topic title: {self.topic_title}")

        # Get total pages
        total_pages = self._get_total_pages(base_url)
        self.total_pages = total_pages
        
        # Scrape each page
        duplicate_count = 0
        for page_num in range(1, total_pages + 1):
            page_url = f"{base_url}?p={page_num}"
            self.logger.info(f"\n📖 Processing page {page_num}/{total_pages}...")
            self.logger.debug(f"🔗 URL: {page_url}")
            
            # Fetch page
            html = self._fetch_page(page_url, page_num)
            if html:
                # Parse entries
                page_entries = self._parse_entries(html, page_num)
                
                # Filter out duplicates
                unique_entries = []
                for entry in page_entries:
                    if entry.get('entry_id') and entry['entry_id'] not in seen_entry_ids:
                        seen_entry_ids.add(entry['entry_id'])
                        unique_entries.append(entry)
                    else:
                        duplicate_count += 1
                
                if unique_entries:
                    self.logger.info(f"✅ Added {len(unique_entries)} unique entries from page {page_num}")
                else:
                    self.logger.warning(f"⚠️  No new entries on page {page_num} (all duplicates)")
                
                self.entries.extend(unique_entries)
            else:
                self.logger.warning(f"⚠️  Skipping page {page_num} (fetch failed)")
        
        # Summary
        self.logger.info(f"\n✨ Scraping completed!")
        self.logger.info(f"📊 Total unique entries: {len(self.entries)}")
        if duplicate_count > 0:
            self.logger.info(f"🔄 Duplicate entries filtered: {duplicate_count}")
        if self.errors:
            self.logger.info(f"⚠️  Errors encountered: {len(self.errors)}")
        
        # Create DataFrame
        if self.entries:
            df = pd.DataFrame(self.entries)
            return df
        else:
            self.logger.warning("⚠️  No entries found!")
            return pd.DataFrame()
    
    def save_to_csv(self, df: pd.DataFrame, filename: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Save DataFrame to CSV file with format: baslikismi_sayfasayisi_tarih.csv

        Args:
            df: DataFrame to save
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Tuple of (data_filename, error_filename or None)
        """
        if df.empty:
            self.logger.warning("⚠️  No data to save!")
            return ("", None)

        # Ensure data directory exists
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)

        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Try to create filename with topic title and page count
            try:
                if self.topic_title and self.total_pages > 0:
                    # Format: data/baslikismi_sayfasayisi_tarih.csv
                    filename = f'data/{self.topic_title}_{self.total_pages}sayfa_{timestamp}.csv'
                    self.logger.debug(f"📝 Generated filename: {filename}")
                else:
                    # Fallback to default format
                    filename = f'data/eksisozluk_entries_{timestamp}.csv'
                    self.logger.debug(f"📝 Using default filename: {filename}")

            except Exception as e:
                # If anything goes wrong, use error fallback filename
                self.logger.error(f"❌ Error generating filename: {str(e)}")
                filename = f'data/error_{timestamp}.csv'
                self.logger.warning(f"⚠️  Using error fallback filename: {filename}")

        # Save main data with error handling
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            self.logger.info(f"💾 Data saved to: {filename}")
        except Exception as e:
            # If saving fails, try with error fallback filename
            self.logger.error(f"❌ Error saving to {filename}: {str(e)}")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'data/error_{timestamp}.csv'
            try:
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                self.logger.info(f"💾 Data saved to fallback file: {filename}")
            except Exception as e2:
                self.logger.error(f"❌ Critical error: Could not save file: {str(e2)}")
                return ("", None)

        # Save errors if any
        error_filename = None
        if self.errors:
            try:
                error_filename = filename.replace('.csv', '_errors.csv')
                error_df = pd.DataFrame(self.errors)
                error_df.to_csv(error_filename, index=False, encoding='utf-8-sig')
                self.logger.info(f"📝 Errors saved to: {error_filename}")
            except Exception as e:
                self.logger.error(f"❌ Error saving error log: {str(e)}")
                error_filename = None

        return (filename, error_filename)
    
    def get_summary(self, df: pd.DataFrame) -> Dict:
        """
        Get summary statistics from scraped data.
        
        Args:
            df: DataFrame with scraped entries
            
        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {
                'total_entries': 0,
                'unique_authors': 0,
                'total_favorites': 0,
                'top_authors': []
            }
        
        return {
            'total_entries': len(df),
            'unique_authors': df['author'].nunique(),
            'total_favorites': df['favorite_count'].astype(int).sum(),
            'top_authors': df['author'].value_counts().head(5).to_dict()
        }


def main():
    """
    Main CLI entry point.
    """
    # Set UTF-8 encoding for stdout to support emojis on Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Ekşi Sözlük Entry Scraper',
        epilog='Example: python eksiscraper.py "https://eksisozluk.com/baslik--123" --delay 3000 --silent'
    )
    
    parser.add_argument(
        'url',
        nargs='?',
        help='Ekşi Sözlük topic URL to scrape'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=2000,
        help='Delay between requests in milliseconds (default: 2000ms)'
    )
    
    parser.add_argument(
        '--silent',
        action='store_true',
        help='Silent mode - suppress info logs'
    )
    
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Output CSV filename (auto-generated if not specified)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Get URL (from args or input)
    if args.url:
        url = args.url
    else:
        url = input("Enter Ekşi Sözlük topic URL: ").strip()
    
    if not url:
        print("❌ Error: No URL provided!")
        sys.exit(1)
    
    # Create scraper instance
    scraper = EksiScraper(
        delay_ms=args.delay,
        verbose=not args.silent
    )
    
    # Perform scraping
    print(f"\n🚀 Starting scraper...")
    df = scraper.scrape(url)
    
    # Save results
    if not df.empty:
        data_file, error_file = scraper.save_to_csv(df, args.output)
        
        # Display summary
        summary = scraper.get_summary(df)
        
        print("\n" + "=" * 60)
        print("📊 SCRAPING SUMMARY")
        print("=" * 60)
        print(f"Total entries: {summary['total_entries']}")
        print(f"Unique authors: {summary['unique_authors']}")
        print(f"Total favorites: {summary['total_favorites']}")
        
        if summary['top_authors']:
            print("\n🏆 Top 5 Authors:")
            for i, (author, count) in enumerate(summary['top_authors'].items(), 1):
                print(f"  {i}. {author}: {count} entries")
        
        print("\n✅ Scraping completed successfully!")
        print(f"📁 Data saved to: {data_file}")
        if error_file:
            print(f"⚠️  Errors saved to: {error_file}")
    else:
        print("\n❌ No data could be scraped!")
        print("💡 Please check the URL and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
