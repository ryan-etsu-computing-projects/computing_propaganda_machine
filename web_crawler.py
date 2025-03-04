import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
import time
import argparse
from collections import deque

class WebsiteCrawler:
    def __init__(self, start_url, output_file, delay=1.0, max_pages=None, max_depth=None, respect_robots=True):
        """
        Initialize the crawler with the starting URL and configuration.
        
        Args:
            start_url (str): The URL to start crawling from
            output_file (str): Path to save the extracted content
            delay (float): Delay between requests in seconds
            max_pages (int, optional): Maximum number of pages to crawl
            max_depth (int, optional): Maximum depth to crawl (levels from start URL)
            respect_robots (bool): Whether to respect robots.txt
        """
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.output_file = output_file
        self.delay = delay
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.respect_robots = respect_robots
        
        # Sets to keep track of URLs
        self.visited_urls = set()
        self.urls_to_visit = deque([(start_url, 0)])  # (url, depth) pairs
        
        # Dictionary to store extracted content
        self.extracted_content = {}
        
        # Disallowed paths (from robots.txt)
        self.disallowed_paths = []
        if respect_robots:
            self._parse_robots_txt()
    
    def _parse_robots_txt(self):
        """Parse robots.txt to respect website crawling rules"""
        parsed_url = urlparse(self.start_url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        
        try:
            response = requests.get(robots_url)
            if response.status_code == 200:
                lines = response.text.split('\n')
                
                # Simple robots.txt parsing
                for line in lines:
                    if line.lower().startswith('disallow:'):
                        path = line.split(':', 1)[1].strip()
                        if path:
                            self.disallowed_paths.append(path)
                
                print(f"Found {len(self.disallowed_paths)} disallowed paths in robots.txt")
            else:
                print("No robots.txt found or couldn't be accessed")
        except Exception as e:
            print(f"Error parsing robots.txt: {e}")
    
    def _is_allowed(self, url):
        """Check if URL is allowed to be crawled based on robots.txt rules"""
        if not self.respect_robots:
            return True
        
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        for disallowed in self.disallowed_paths:
            if path.startswith(disallowed):
                return False
        
        return True
    
    def _is_valid_url(self, url):
        """Check if URL should be crawled (same domain, not visited, allowed by robots.txt)"""
        parsed_url = urlparse(url)
        
        # Check if URL is from the same domain
        if parsed_url.netloc != self.base_domain:
            return False
        
        # Check if URL has already been visited
        if url in self.visited_urls:
            return False
        
        # Check file extensions to avoid PDFs, images, etc.
        if parsed_url.path.lower().endswith(('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js')):
            return False
        
        # Check if URL is allowed by robots.txt
        if not self._is_allowed(url):
            return False
        
        return True
    
    def _extract_content(self, url, soup):
        """Extract relevant content from the page"""
        # Title of the page
        title = soup.title.string if soup.title else "No Title"
        
        # Get main content - adjust selectors according to the website's structure
        # These are common selectors, but you may need to customize them
        main_content_selectors = ['main', 'article', '.content', '#content', '.main-content']
        main_content = None
        
        for selector in main_content_selectors:
            content = soup.select(selector)
            if content:
                main_content = content[0]
                break
        
        # If no main content was found, use the body
        if not main_content:
            main_content = soup.body
        
        # Extract text, removing script and style elements
        for script in main_content.find_all(['script', 'style']):
            script.decompose()
        
        # Get all text and clean it
        text = main_content.get_text(separator="\n", strip=True)
        
        # Remove extra whitespace
        text = re.sub(r'\n+', '\n\n', text)
        
        return {
            'title': title,
            'url': url,
            'content': text
        }
    
    def _extract_links(self, soup, current_url):
        """Extract links from the page"""
        links = []
        
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)
            
            # Remove fragments and query parameters
            parsed_url = urlparse(absolute_url)
            clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            
            if self._is_valid_url(clean_url) and clean_url not in self.urls_to_visit:
                links.append(clean_url)
        
        return links
    
    def crawl(self):
        """Start crawling the website"""
        page_count = 0
        
        print(f"Starting crawl from {self.start_url}")
        print(f"Output will be saved to {self.output_file}")
        if self.max_depth is not None:
            print(f"Maximum crawl depth: {self.max_depth} levels from start URL")
        
        while self.urls_to_visit and (self.max_pages is None or page_count < self.max_pages):
            # Get the next URL and its depth to visit
            current_url, current_depth = self.urls_to_visit.popleft()
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue
            
            # Skip if we've reached max depth
            if self.max_depth is not None and current_depth > self.max_depth:
                continue

            try:
                # Make the request
                depth_indicator = '*' * current_depth
                print(f"Crawling [{current_depth}]: {depth_indicator} {current_url}")
                response = requests.get(current_url)
                
                # Mark as visited
                self.visited_urls.add(current_url)
                page_count += 1
                
                # Process only successful responses
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract content
                    content = self._extract_content(current_url, soup)
                    self.extracted_content[current_url] = content
                    
                    # Extract links if we haven't reached max depth
                    if self.max_depth is None or current_depth < self.max_depth:
                        links = self._extract_links(soup, current_url)
                        for link in links:
                            # Store URLs with their depth
                            url_entry = (link, current_depth + 1)
                            url_exists = any(link == u for u, _ in self.urls_to_visit)
                            if link not in self.visited_urls and not url_exists:
                                self.urls_to_visit.append(url_entry)
                else:
                    print(f"Failed to fetch {current_url}: HTTP {response.status_code}")
                
                # Respect the delay between requests
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"Error crawling {current_url}: {e}")
        
        # Save the extracted content
        self._save_content()
        
        print(f"Crawling complete. Visited {page_count} pages.")
        print(f"Content saved to {self.output_file}")
    
    def _save_content(self):
        """Save the extracted content to a Markdown file"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(f"# ETSU Computing Department Website Content\n\n")
            f.write(f"*Crawled on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(f"*Starting URL: {self.start_url}*\n\n")
            
            # Write content for each URL
            for url, data in self.extracted_content.items():
                f.write(f"## {data['title']}\n\n")
                f.write(f"**URL:** {url}\n\n")
                f.write(f"{data['content']}\n\n")
                f.write("---\n\n")


def main():
    parser = argparse.ArgumentParser(description='Crawl a website and extract content to Markdown')
    parser.add_argument('--start-url', type=str, default='https://www.etsu.edu/cbat/computing/',
                        help='URL to start crawling from')
    parser.add_argument('--output', type=str, default='etsu_computing_content.md',
                        help='Output Markdown file')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between requests in seconds')
    parser.add_argument('--max-pages', type=int, default=None,
                        help='Maximum number of pages to crawl')
    parser.add_argument('--max-depth', type=int, default=None,
                        help='Maximum depth to crawl (1 = only links on start page)')
    parser.add_argument('--no-robots', action='store_true',
                        help='Ignore robots.txt rules')
    
    args = parser.parse_args()
    
    crawler = WebsiteCrawler(
        start_url=args.start_url,
        output_file=args.output,
        delay=args.delay,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        respect_robots=not args.no_robots
    )
    
    crawler.crawl()


if __name__ == "__main__":
    main()
