# ETSU Computing Website Content Extractor

This project crawls the ETSU Computing department website, extracts content, and organizes it into a structured format that can be easily imported into LLMs for summarization or fact extraction. It's designed to help you prepare talking points for campus tours and keep track of the latest achievements, courses, student organizations, and other important information.

## Features

- **Smart Content Extraction**: Properly extracts content from complex web structures including accordion menus (`<details>` and `<summary>` elements), tables, and lists
- **Path Restriction**: Stays within the Computing department by only crawling URLs with the `/cbat/computing` prefix
- **Depth Control**: Limits crawling to specified levels deep from the starting page
- **Content Organization**: Automatically categorizes extracted content by topic
- **Key Facts Extraction**: Identifies potential talking points from the extracted content

## Project Structure

The project consists of three main Python scripts:

1. `web_crawler.py` - Crawls the ETSU Computing website and extracts content into a raw markdown file
2. `content_extractor.py` - Processes the raw content and organizes it into categories
3. `run.py` - Orchestrates the entire process with a simple command

## Requirements

- Python 3.7 or higher
- Required Python packages:
  - requests
  - beautifulsoup4
  - argparse

Install the required packages:

```bash
pip install requests beautifulsoup4
```

## Usage

### Quick Start

Run the entire process with default settings:

```bash
python run.py
```

This will:
1. Crawl the ETSU Computing website starting from https://www.etsu.edu/cbat/computing/
2. Extract content into a raw markdown file
3. Process and categorize the content
4. Generate organized markdown files by category and a key facts file

### Advanced Usage

Control crawling behavior:

```bash
python run.py --start-url https://www.etsu.edu/cbat/computing/ --max-pages 50 --delay 2.0 --max-depth 1 --path-prefix /cbat/computing
```

The `--max-depth` parameter controls how many "hops" from the starting URL the crawler will follow:
- `--max-depth 1` (default): Only crawls links found on the start page (main navigation links)
- `--max-depth 2`: Crawls the main navigation links and links found on those pages
- Higher values will crawl deeper into the site structure

The `--path-prefix` parameter (default: `/cbat/computing`) restricts the crawler to only visit URLs that start with the given path. This prevents the crawler from navigating to other departments or colleges.

Skip crawling and process existing content:

```bash
python run.py --skip-crawl
```

Specify output directory:

```bash
python run.py --output-dir my_etsu_data
```

### Running Individual Components

If you prefer to run each component separately:

1. Run the web crawler:
   ```bash
   python web_crawler.py --start-url https://www.etsu.edu/cbat/computing/ --output etsu_content.md
   ```

2. Process the extracted content:
   ```bash
   python content_extractor.py --input etsu_content.md --output-dir extracted_content
   ```

## Output Files

The script generates several output files in the specified directory:

- `etsu_computing_raw_[timestamp].md` - Raw content from all crawled pages
- `extracted_[timestamp]/` - Directory containing organized content:
  - `achievements.md` - Department achievements and awards
  - `courses.md` - Information about courses
  - `concentrations.md` - Degree programs and concentrations
  - `student_organizations.md` - Student clubs and organizations
  - `faculty.md` - Faculty information
  - `research.md` - Research activities
  - `events.md` - Events and activities
  - `facilities.md` - Information about facilities
  - `general_info.md` - General information
  - `key_facts.md` - Extracted key facts that can serve as talking points
  - `all_content.md` - All content organized by category

## Using the Output with LLMs

The generated markdown files can be imported into LLMs (like Claude) for summarization or to extract specific information. For example:

1. Import `key_facts.md` and ask the LLM to prepare a 5-minute tour script based on the highlights
2. Import `student_organizations.md` and ask the LLM to summarize all active student clubs
3. Import `courses.md` and ask the LLM to identify new courses or program changes

## Customization

### Modifying Category Keywords

To customize how content is categorized, edit the `category_keywords` dictionary in `content_extractor.py`. You can add new categories or modify the keywords for existing ones to better match the structure of your department's website.

### Adjusting Content Extraction

The content extraction logic in `web_crawler.py` can be customized to better target specific elements on the ETSU Computing website. Look for the `_extract_content` method to adjust the HTML selectors.

## Notes and Limitations

- The crawler respects robots.txt by default, which may limit what content it can access
- Very dynamic content (loaded via JavaScript) might not be captured
- PDF, DOC, and other non-HTML content is not processed
- Images and media content are not included in the extraction

## Maintenance

To keep your talking points up-to-date, run this tool periodically to capture new content and changes on the website
