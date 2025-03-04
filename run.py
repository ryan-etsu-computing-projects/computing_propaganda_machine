#!/usr/bin/env python3
"""
ETSU Computing Website Content Extractor

This script automates the process of crawling the ETSU Computing department website,
extracting content, and organizing it into categories for easy reference.
"""

import os
import argparse
import subprocess
import time
from datetime import datetime

def run_command(command, description):
    """Run a shell command and print status"""
    print(f"\n{'-' * 80}")
    print(f"{description}...")
    print(f"{'-' * 80}")
    print(f"Running: {' '.join(command)}")
    
    start_time = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    end_time = time.time()
    
    if result.returncode == 0:
        print(f"✅ Command completed successfully in {end_time - start_time:.2f} seconds")
    else:
        print(f"❌ Command failed with error code {result.returncode}")
        print(f"Error output: {result.stderr}")
    
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description='Crawl ETSU Computing website and extract content')
    parser.add_argument('--start-url', type=str, default='https://www.etsu.edu/cbat/computing/',
                        help='URL to start crawling from')
    parser.add_argument('--output-dir', type=str, default='etsu_computing_data',
                        help='Directory to save all output')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between requests in seconds')
    parser.add_argument('--max-pages', type=int, default=100,
                        help='Maximum number of pages to crawl')
    parser.add_argument('--max-depth', type=int, default=1,
                        help='Maximum depth to crawl (1 = only links on start page)')
    parser.add_argument('--path-prefix', type=str, default='/cbat/computing',
                        help='Only crawl URLs with this path prefix')
    parser.add_argument('--skip-crawl', action='store_true',
                        help='Skip crawling and use existing raw content file')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set output file paths
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    raw_content_file = os.path.join(args.output_dir, f"etsu_computing_raw_{timestamp}.md")
    extracted_dir = os.path.join(args.output_dir, f"extracted_{timestamp}")
    
    # Step 1: Run the web crawler
    if not args.skip_crawl:
        success = run_command(
            [
                "python", "web_crawler.py",
                "--start-url", args.start_url,
                "--output", raw_content_file,
                "--delay", str(args.delay),
                "--max-pages", str(args.max_pages),
                "--max-depth", str(args.max_depth),
                "--path-prefix", args.path_prefix
            ],
            "Crawling website content"
        )
        
        if not success:
            print("❌ Website crawling failed. Exiting.")
            return
    else:
        print("⏩ Skipping website crawling as requested.")
        # Use the most recent raw content file
        existing_files = [f for f in os.listdir(args.output_dir) if f.startswith("etsu_computing_raw_") and f.endswith(".md")]
        if existing_files:
            existing_files.sort(reverse=True)
            raw_content_file = os.path.join(args.output_dir, existing_files[0])
            print(f"📝 Using existing content file: {raw_content_file}")
        else:
            print("❌ No existing content files found. Please run without --skip-crawl first.")
            return
    
    # Step 2: Run the content extractor
    success = run_command(
        [
            "python", "content_extractor.py",
            "--input", raw_content_file,
            "--output-dir", extracted_dir
        ],
        "Extracting and categorizing content"
    )
    
    if not success:
        print("❌ Content extraction failed. Exiting.")
        return
    
    # Create a symlink to the latest extraction
    latest_link = os.path.join(args.output_dir, "latest")
    if os.path.exists(latest_link) and os.path.islink(latest_link):
        os.unlink(latest_link)
    elif os.path.exists(latest_link):
        os.rename(latest_link, f"{latest_link}_backup_{timestamp}")
    
    try:
        os.symlink(extracted_dir, latest_link, target_is_directory=True)
        print(f"🔗 Created symlink: {latest_link} -> {extracted_dir}")
    except:
        print(f"⚠️ Could not create symlink. You can find the latest extraction at: {extracted_dir}")
    
    print(f"\n{'=' * 80}")
    print(f"✅ Process completed successfully!")
    print(f"📁 Raw content saved to: {raw_content_file}")
    print(f"📁 Extracted content saved to: {extracted_dir}")
    print(f"📄 Key facts for your tour: {os.path.join(extracted_dir, 'key_facts.md')}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
