import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Set
import tldextract
import time

class EmailScraper:
    def __init__(self, max_pages: int = 10, timeout: int = 10, delay: float = 1.0):
        self.max_pages = max_pages
        self.timeout = timeout
        self.delay = delay  # Delay between requests to avoid rate limiting
        self.visited_urls = set()
        self.emails_found = set()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def is_valid_url(self, url: str, base_domain: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        if parsed.scheme not in ('http', 'https'):
            return False
        if any(ext in url for ext in ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com']):
            return False
        
        try:
            extracted = tldextract.extract(url)
            base_extracted = tldextract.extract(base_domain)
            return f"{extracted.domain}.{extracted.suffix}" == f"{base_extracted.domain}.{base_extracted.suffix}"
        except:
            return False
    
    def extract_emails(self, text: str) -> Set[str]:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = set(re.findall(email_pattern, text, re.IGNORECASE))
        # Basic email validation
        return {email for email in emails if '.' in email.split('@')[-1] and len(email.split('@')[0]) > 0}
    
    def scrape_page(self, url: str, base_domain: str):
        try:
            time.sleep(self.delay)  # Respectful crawling
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            if 'text/html' not in response.headers.get('Content-Type', ''):
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            
            # Extract emails from page content
            new_emails = self.extract_emails(text)
            self.emails_found.update(new_emails)
            
            # Find all links on the page
            for link in soup.find_all('a', href=True):
                next_url = urljoin(url, link['href'])
                if (self.is_valid_url(next_url, base_domain) and 
                    next_url not in self.visited_urls and 
                    len(self.visited_urls) < self.max_pages):
                    self.visited_urls.add(next_url)
                    self.scrape_page(next_url, base_domain)
                    
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
    
    def scrape_website(self, start_url: str) -> List[str]:
        try:
            parsed = urlparse(start_url)
            if not parsed.scheme:
                start_url = 'http://' + start_url
            
            base_domain = parsed.netloc if parsed.netloc else start_url
            
            self.visited_urls.add(start_url)
            self.scrape_page(start_url, base_domain)
            
            return sorted(self.emails_found)
        except Exception as e:
            print(f"Scraping failed: {str(e)}")
            return []