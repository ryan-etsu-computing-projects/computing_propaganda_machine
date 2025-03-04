import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
import time
import argparse
from collections import deque

class WebsiteCrawler:
    def __init__(self, start_url, output_file, delay=1.0, max_pages=None, max_depth=None, path_prefix=None, respect_robots=True):
        """
        Initialize the crawler with the starting URL and configuration.
        
        Args:
            start_url (str): The URL to start crawling from
            output_file (str): Path to save the extracted content
            delay (float): Delay between requests in seconds
            max_pages (int, optional): Maximum number of pages to crawl
            max_depth (int, optional): Maximum depth to crawl (levels from start URL)
            path_prefix (str, optional): Only crawl URLs with this path prefix
            respect_robots (bool): Whether to respect robots.txt
        """
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.output_file = output_file
        self.delay = delay
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.path_prefix = path_prefix
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
        
        # Check if URL path starts with the required prefix
        if self.path_prefix and not parsed_url.path.startswith(self.path_prefix):
            return False

        # Check file extensions to avoid PDFs, images, etc.
        if parsed_url.path.lower().endswith(('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js')):
            return False
        
        # Check if URL is allowed by robots.txt
        if not self._is_allowed(url):
            return False
        
        return True
    
    def _process_text_node(self, element):
        """Process a text node, removing extra whitespace"""
        if element.string:
            return element.string.strip()
        return ""

    def _process_element(self, element, indent=0):
        """Process an HTML element and its children recursively to extract structured content"""
        if element.name is None:
            # This is a text node
            text = self._process_text_node(element)
            if text:
                return text
            return ""

        # Skip script, style, and other non-content elements
        if element.name in ['script', 'style', 'meta', 'link', 'noscript']:
            return ""

        # Skip site navigation and header elements
        skip_classes = ['nav__global', 'nav__page', 'site-search-wrap', 'flyout-menu', 'header-primary', 'leftSidebar']
        for cls in skip_classes:
            if element.get('class') and cls in element.get('class'):
                return ""

        # Handle various HTML elements differently
        if element.name == 'h1':
            return f"\n# {element.get_text(strip=True)}\n\n"
        elif element.name == 'h2':
            return f"\n## {element.get_text(strip=True)}\n\n"
        elif element.name == 'h3':
            return f"\n### {element.get_text(strip=True)}\n\n"
        elif element.name == 'h4':
            return f"\n#### {element.get_text(strip=True)}\n\n"
        elif element.name == 'h5':
            return f"\n##### {element.get_text(strip=True)}\n\n"
        elif element.name == 'h6':
            return f"\n###### {element.get_text(strip=True)}\n\n"
        elif element.name == 'p':
            return f"{element.get_text(separator=' ', strip=True)}\n\n"
        elif element.name == 'br':
            return "\n"
        elif element.name == 'hr':
            return "\n---\n\n"
        elif element.name == 'a' and element.has_attr('href'):
            text = element.get_text(strip=True)
            href = element['href']
            if text:
                return f"[{text}]({href})"
            return ""
        elif element.name in ['ul', 'ol']:
            result = "\n"
            for i, li in enumerate(element.find_all('li', recursive=False)):
                li_text = ""
                for child in li.children:
                    li_text += self._process_element(child, indent)

                if element.name == 'ol':
                    result += f"{i+1}. {li_text.strip()}\n"
                else:
                    result += f"* {li_text.strip()}\n"
            return result + "\n"
        elif element.name == 'details':
            # Special handling for accordion elements
            summary = element.find('summary')
            summary_text = summary.get_text(strip=True) if summary else "Accordion Item"

            # Process all content inside the details tag, excluding the summary
            content = ""
            for child in element.children:
                if child != summary:
                    content += self._process_element(child, indent)

            return f"\n### {summary_text}\n{content}\n"
        elif element.name == 'summary':
            # Skip summary elements as they're handled by the details processing
            return ""
        elif element.name == 'table':
            # Enhanced table handling
            result = "\n"

            # First, handle table headers
            headers = []
            header_row = element.find('thead')
            if header_row:
                th_cells = header_row.find_all('th')
                if th_cells:
                    headers = [th.get_text(strip=True) for th in th_cells]

            if not headers:
                # Try to get headers from the first row
                first_row = element.find('tr')
                if first_row:
                    th_cells = first_row.find_all('th')
                    if th_cells:
                        headers = [th.get_text(strip=True) for th in th_cells]

            # If we found headers, add them to the table
            if headers:
                result += "| " + " | ".join(headers) + " |\n"
                result += "| " + " | ".join(['---'] * len(headers)) + " |\n"

            # Process rows
            rows = element.find_all('tr')
            for row in rows:
                # Skip the header row if we already processed it
                if row == element.find('tr') and headers and row.find('th'):
                    continue

                cells = row.find_all(['td', 'th'])
                if cells:
                    result += "| " + " | ".join(cell.get_text(strip=True) for cell in cells) + " |\n"

            return result + "\n"
        elif element.name == 'div':
            # Process div content
            result = ""
            for child in element.children:
                result += self._process_element(child, indent)
            return result

        # For other elements, process their children
        result = ""
        for child in element.children:
            result += self._process_element(child, indent + 1)

        return result

    def _extract_content(self, url, soup):
        """Extract relevant content from the page using a structured approach"""
        # Title of the page
        title = soup.title.string if soup.title else "No Title"
        
        # Get main content
        main_content = None
        
        # Try to find the main content area with various selectors, prioritizing more specific IDs/classes
        content_selectors = [
            '#main',  # Main content div on ETSU pages
            'section[role="main"]',  # Main section with role=main
            '#content',  # Content ID
            '.content-grid',  # Content grid class
            'main',  # HTML5 main tag
            'article',  # Article tag
            '.page-content',  # Page content class
            '.main-content'  # Main content class
        ]

        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                main_content = elements[0]
                break
        
        # If no main content was found, use the body
        if not main_content:
            main_content = soup.body
        
        # Remove navigation and sidebar elements that might be inside the main content
        for nav in main_content.find_all(['nav', 'header', 'footer']):
            nav.decompose()
        
        # Check if there's an accordion list specifically (common on ETSU research pages)
        accordion_lists = main_content.select('.list__accordions')

        # Special handling if we found accordion lists
        if accordion_lists:
            structured_content = "# " + title + "\n\n"

            for accordion_list in accordion_lists:
                for details in accordion_list.find_all('details'):
                    summary = details.find('summary')
                    if summary:
                        summary_text = summary.get_text(strip=True)
                        structured_content += f"## {summary_text}\n\n"

                        # Extract content from the div inside details
                        content_div = details.find('div')
                        if content_div:
                            # Process paragraphs
                            for p in content_div.find_all('p'):
                                structured_content += f"{p.get_text(strip=True)}\n\n"

                            # Process lists
                            for ul in content_div.find_all('ul'):
                                for li in ul.find_all('li'):
                                    # Handle links in list items
                                    if li.find('a'):
                                        for a in li.find_all('a'):
                                            href = a.get('href', '')
                                            link_text = a.get_text(strip=True)
                                            structured_content += f"* [{link_text}]({href})\n"
                                    else:
                                        structured_content += f"* {li.get_text(strip=True)}\n"
                                structured_content += "\n"
        else:
            # Process the main content to extract structured text
            structured_content = self._process_element(main_content)

        # Clean up any excessive whitespace
        structured_content = re.sub(r'\n{3,}', '\n\n', structured_content)
        
        return {
            'title': title,
            'url': url,
            'content': structured_content
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
        if self.path_prefix:
            print(f"Only crawling URLs with path prefix: {self.path_prefix}")
        
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
    parser.add_argument('--path-prefix', type=str, default='/cbat/computing',
                        help='Only crawl URLs with this path prefix')
    parser.add_argument('--no-robots', action='store_true',
                        help='Ignore robots.txt rules')
    
    args = parser.parse_args()
    
    crawler = WebsiteCrawler(
        start_url=args.start_url,
        output_file=args.output,
        delay=args.delay,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        path_prefix=args.path_prefix,
        respect_robots=not args.no_robots
    )
    
    crawler.crawl()


if __name__ == "__main__":
    main()