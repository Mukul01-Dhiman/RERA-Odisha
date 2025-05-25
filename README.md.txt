# Odisha RERA Projects Scraper

This Python project scrapes the first 6 projects listed under the "Projects Registered" section on the [Odisha RERA Project List](https://rera.odisha.gov.in/projects/project-list) website.  
For each project, it extracts the following details from the project's detail page:
- RERA Registration Number
- Project Name
- Promoter Name (Company Name under Promoter Details tab)
- Promoter Address (Registered Office Address under Promoter Details tab)
- GST Number

## Features
- Uses Selenium WebDriver in headless Chrome mode to automate browsing.
- Uses BeautifulSoup for parsing HTML content.
- Handles dynamic content and tab clicks to fetch promoter details.
- Extracts and prints project details in a readable format.

## Requirements

- Python 3.x
- Google Chrome browser installed (version should match with ChromeDriver)
- ChromeDriver executable (compatible with your Chrome browser version)
- Python packages:
  - selenium
  - beautifulsoup4

## Installation

1. Clone this repository or download the script.

2. Install required Python packages:

```bash
pip install selenium beautifulsoup4
