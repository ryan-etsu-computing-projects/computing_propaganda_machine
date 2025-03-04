import os
import re
import json
import argparse
from collections import defaultdict

class ContentExtractor:
    def __init__(self, input_file, output_dir="extracted_content"):
        """
        Initialize the content extractor with input and output locations.

        Args:
            input_file (str): Path to the markdown file with crawled content
            output_dir (str): Directory to save organized content files
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.content_sections = []

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Categorized content storage
        self.categories = {
            "achievements": [],
            "courses": [],
            "concentrations": [],
            "student_organizations": [],
            "faculty": [],
            "research": [],
            "events": [],
            "facilities": [],
            "general_info": []
        }

        # Keywords for categorization
        self.category_keywords = {
            "achievements": ["achievement", "award", "recognition", "honor", "success", "won", "ranked", "accomplishment"],
            "courses": ["course", "class", "curriculum", "syllabus", "credit hour", "prerequisite", "corequisite", "CSCI", "ITIS"],
            "concentrations": ["concentration", "major", "minor", "specialization", "track", "degree", "program", "BS in", "MS in"],
            "student_organizations": ["club", "organization", "society", "association", "student group", "ACM", "student chapter"],
            "faculty": ["faculty", "professor", "instructor", "dean", "chair", "director", "Dr.", "Ph.D"],
            "research": ["research", "thesis", "dissertation", "publication", "journal", "conference", "study", "investigation", "project", "honors college", "graduate studies", "independent studies", "library resources", "thesis preparation", "research honors"],
            "events": ["event", "seminar", "workshop", "conference", "hackathon", "competition", "meeting", "ceremony"],
            "facilities": ["lab", "laboratory", "classroom", "center", "building", "brinkley", "facility", "equipment"],
            "general_info": ["about", "mission", "vision", "contact", "location", "schedule", "deadline", "application"]
        }
    
    def _parse_markdown(self):
        """Parse the markdown file into sections"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split the content by the separator
        sections = content.split("---")

        # Process each section
        for section in sections:
            if not section.strip():
                continue

            # Extract title and URL if available
            title_match = re.search(r'##\s+(.*?)\n', section)
            url_match = re.search(r'\*\*URL:\*\*\s+(.*?)\n', section)

            if title_match:
                title = title_match.group(1).strip()
                url = url_match.group(1).strip() if url_match else "No URL"

                # Remove the title and URL lines to get just the content
                content_text = section
                content_text = re.sub(r'##\s+.*?\n', '', content_text)
                content_text = re.sub(r'\*\*URL:\*\*\s+.*?\n', '', content_text)

                self.content_sections.append({
                    "title": title,
                    "url": url,
                    "content": content_text.strip()
                })
    
    def _categorize_content(self):
        """Categorize content based on keywords and URL patterns"""
        for section in self.content_sections:
            categorized = False
            combined_text = f"{section['title']} {section['content']}".lower()
            url = section['url'].lower()

            # First check URL patterns which are more reliable indicators
            url_patterns = {
                "research": ["/research/", "honors-in-discipline", "gradschool/etd", "thesis"],
                "courses": ["/courses/", "/curriculum/", "/syllabus/"],
                "faculty": ["/faculty/", "/staff/", "/people/", "/directory/"],
                "student_organizations": ["/student-organizations/", "/clubs/", "/societies/"],
                "achievements": ["/news/", "/achievements/", "/awards/"],
                "concentrations": ["/programs/", "/degrees/", "/majors/", "/concentrations/"],
                "events": ["/events/", "/calendar/", "/schedule/"],
                "facilities": ["/facilities/", "/labs/", "/resources/"]
            }

            # Check URL patterns first
            for category, patterns in url_patterns.items():
                for pattern in patterns:
                    if pattern in url:
                        self.categories[category].append(section)
                        categorized = True
                        break
                if categorized:
                    break

            # If not categorized by URL, check keywords
            if not categorized:
                for category, keywords in self.category_keywords.items():
                    for keyword in keywords:
                        if keyword.lower() in combined_text:
                            self.categories[category].append(section)
                            categorized = True
                            break

                    if categorized:
                        break

            # If still not categorized, add to general info
            if not categorized:
                self.categories["general_info"].append(section)
    
    def _extract_key_facts(self, section):
        """Extract potential key facts based on patterns"""
        content = section["content"]
        facts = []

        # Patterns for potential facts
        patterns = [
            # Lists
            r'• (.*?)(?=\n• |\n\n|$)',  # Bullet points
            r'\d+\.\s+(.*?)(?=\n\d+\. |\n\n|$)',  # Numbered lists

            # Sentences with significant markers
            r'(.*?students.*?\.)',
            r'(.*?faculty.*?\.)',
            r'(.*?program.*?\.)',
            r'(.*?course.*?\.)',
            r'(.*?award.*?\.)',
            r'(.*?research.*?\.)',
            r'(.*?new.*?\.)',
            r'(.*?first.*?\.)',
            r'(.*?best.*?\.)',
            r'(.*?only.*?\.)',
            r'(.*?largest.*?\.)',
            r'(.*?highest.*?\.)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Clean up the fact and add if it's not too short
                fact = match.strip()
                if len(fact) > 15 and fact not in facts:
                    facts.append(fact)

        return facts
    
    def process(self):
        """Process the content file and generate organized output"""
        print(f"Processing content from {self.input_file}")

        # Parse the markdown file
        self._parse_markdown()
        print(f"Found {len(self.content_sections)} content sections")

        # Categorize the content
        self._categorize_content()

        # Generate category files
        for category, sections in self.categories.items():
            if sections:
                self._generate_category_file(category, sections)

        # Generate a key facts file
        self._generate_key_facts_file()

        # Generate a combined markdown file
        self._generate_combined_file()

        print(f"Processing complete. Results saved to {self.output_dir}/")
    
    def _generate_category_file(self, category, sections):
        """Generate a markdown file for a specific category"""
        output_file = os.path.join(self.output_dir, f"{category}.md")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# ETSU Computing: {category.replace('_', ' ').title()}\n\n")

            for section in sections:
                f.write(f"## {section['title']}\n\n")
                f.write(f"**Source:** {section['url']}\n\n")
                f.write(f"{section['content']}\n\n")
                f.write("---\n\n")
    
    def _generate_key_facts_file(self):
        """Generate a file with potential key facts"""
        output_file = os.path.join(self.output_dir, "key_facts.md")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# ETSU Computing: Key Facts\n\n")
            f.write("*These are potential talking points extracted from the website content*\n\n")

            for category, sections in self.categories.items():
                if sections:
                    f.write(f"## {category.replace('_', ' ').title()}\n\n")

                    for section in sections:
                        facts = self._extract_key_facts(section)
                        if facts:
                            f.write(f"### From: {section['title']}\n\n")
                            for fact in facts:
                                f.write(f"- {fact}\n")
                            f.write("\n")

            f.write("\n*Note: These facts were automatically extracted and may need review.*\n")
    
    def _generate_combined_file(self):
        """Generate a single combined file with all content organized by category"""
        output_file = os.path.join(self.output_dir, "all_content.md")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# ETSU Computing Department: Complete Extracted Content\n\n")
            f.write("*This file contains all extracted content organized by category*\n\n")

            # Table of contents
            f.write("## Table of Contents\n\n")
            for category in self.categories.keys():
                if self.categories[category]:
                    f.write(f"- [{category.replace('_', ' ').title()}](#{category})\n")
            f.write("\n")

            # Category content
            for category, sections in self.categories.items():
                if sections:
                    f.write(f"<a id='{category}'></a>\n")
                    f.write(f"## {category.replace('_', ' ').title()}\n\n")

                    for section in sections:
                        f.write(f"### {section['title']}\n\n")
                        f.write(f"**Source:** {section['url']}\n\n")
                        f.write(f"{section['content']}\n\n")
                        f.write("---\n\n")


def main():
    parser = argparse.ArgumentParser(description='Extract and organize content from crawled website data')
    parser.add_argument('--input', type=str, default='etsu_computing_content.md',
                        help='Input markdown file with crawled content')
    parser.add_argument('--output-dir', type=str, default='extracted_content',
                        help='Directory to save organized content files')
    
    args = parser.parse_args()

    extractor = ContentExtractor(
        input_file=args.input,
        output_dir=args.output_dir
    )
    
    extractor.process()


if __name__ == "__main__":
    main()