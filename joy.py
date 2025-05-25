from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import time
import logging
import json
import os
import re

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def enhanced_get_table_value(soup, key_text, default="N/A"):
    """
    Enhanced function to extract table values with multiple strategies
    """
    try:
        # Strategy 1: Look for table rows with th/td pairs
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key_text.lower() in label.lower():
                        logger.info(f"Found {key_text}: {value}")
                        return value
        
        # Strategy 2: Look for div-based layouts with labels
        divs = soup.find_all('div')
        for div in divs:
            text = div.get_text(strip=True)
            if key_text.lower() in text.lower():
                # Try to find the value in next sibling or within the same div
                next_sibling = div.find_next_sibling()
                if next_sibling:
                    value = next_sibling.get_text(strip=True)
                    if value and value != text:
                        logger.info(f"Found {key_text} (div method): {value}")
                        return value
        
        # Strategy 3: Look for span/label combinations
        labels = soup.find_all(['label', 'span'], string=re.compile(key_text, re.IGNORECASE))
        for label in labels:
            # Check parent or next elements
            parent = label.parent
            if parent:
                value_elem = parent.find_next(['span', 'div', 'td'])
                if value_elem:
                    value = value_elem.get_text(strip=True)
                    if value and value != label.get_text(strip=True):
                        logger.info(f"Found {key_text} (label method): {value}")
                        return value
        
        logger.warning(f"Could not find value for '{key_text}' using any strategy")
        return default
        
    except Exception as e:
        logger.warning(f"Error getting {key_text} from table: {e}")
        return default

def wait_for_page_load(driver, timeout=15):
    """Wait for page to fully load"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)  # Additional wait for dynamic content
    except TimeoutException:
        logger.warning("Page load timeout, continuing anyway")

def debug_page_content(driver, project_num):
    """Debug function to log page content for analysis"""
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Log all table content
        tables = soup.find_all('table')
        logger.info(f"Project {project_num}: Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            logger.info(f"Table {i+1} content preview:")
            rows = table.find_all('tr')[:3]  # First 3 rows only
            for j, row in enumerate(rows):
                cells = row.find_all(['th', 'td'])
                cell_texts = [cell.get_text(strip=True)[:50] for cell in cells]
                logger.info(f"  Row {j+1}: {cell_texts}")
        
        # Log all text content with specific keywords
        page_text = soup.get_text()
        keywords = ['rera', 'project', 'promoter', 'gst', 'address', 'company']
        for keyword in keywords:
            if keyword.lower() in page_text.lower():
                # Find context around keyword
                lines = page_text.split('\n')
                for line in lines:
                    if keyword.lower() in line.lower() and line.strip():
                        logger.info(f"Found '{keyword}' context: {line.strip()[:100]}")
                        break
                        
    except Exception as e:
        logger.error(f"Error in debug_page_content: {e}")

def get_project_details_by_click(driver, button_index):
    logger.info(f"Processing project {button_index + 1}")
    
    try:
        # Navigate back to main page
        driver.get('https://rera.odisha.gov.in/projects/project-list')
        wait_for_page_load(driver)
        
        # Wait for view details buttons
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.XPATH, "//a[text()='View Details']")))
        time.sleep(3)

        # Get all view details buttons
        view_buttons = driver.find_elements(By.XPATH, "//a[text()='View Details']")
        if button_index >= len(view_buttons):
            logger.error(f"Button index {button_index} out of range. Available buttons: {len(view_buttons)}")
            return None

        # Click the specific button
        button = view_buttons[button_index]
        logger.info(f"Clicking View Details button {button_index + 1}")
        
        # Scroll to button and click
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
        time.sleep(2)
        
        # Try different click methods
        try:
            button.click()
        except:
            logger.info("Normal click failed, trying JavaScript click")
            driver.execute_script("arguments[0].click();", button)
        
        # Wait for page to load
        wait_for_page_load(driver, 20)
        
        # Debug: Log current URL and page content
        logger.info(f"Current URL: {driver.current_url}")
        debug_page_content(driver, button_index + 1)
        
        # Parse page content
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract basic project information with multiple strategies
        rera_no = enhanced_get_table_value(soup, 'RERA')
        if rera_no == "N/A":
            rera_no = enhanced_get_table_value(soup, 'Registration')
        if rera_no == "N/A":
            rera_no = enhanced_get_table_value(soup, 'Regd')
            
        project_name = enhanced_get_table_value(soup, 'Project Name')
        if project_name == "N/A":
            project_name = enhanced_get_table_value(soup, 'Name')

        logger.info(f"✓ Found project: {project_name} ({rera_no})")

        # Initialize promoter details
        promoter_name = promoter_address = gst_no = "N/A"

        # Try to find and click promoter details tab
        try:
            # Multiple selectors for promoter tab
            promoter_selectors = [
                "//a[contains(text(), 'Promoter')]",
                "//a[contains(text(), 'promoter')]",
                "//*[contains(text(), 'Promoter Details')]",
                "//button[contains(text(), 'Promoter')]",
                "//tab[contains(text(), 'Promoter')]",
                "//li[contains(text(), 'Promoter')]"
            ]
            
            promoter_element = None
            for selector in promoter_selectors:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    promoter_element = elements[0]
                    logger.info(f"Found promoter tab with selector: {selector}")
                    break
            
            if promoter_element:
                logger.info("Clicking Promoter Details tab...")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", promoter_element)
                time.sleep(2)
                
                try:
                    promoter_element.click()
                except:
                    driver.execute_script("arguments[0].click();", promoter_element)
                
                wait_for_page_load(driver, 25)
                
                # Parse promoter details
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                promoter_name = enhanced_get_table_value(soup, 'Company Name')
                if promoter_name == "N/A":
                    promoter_name = enhanced_get_table_value(soup, 'Promoter Name')
                if promoter_name == "N/A":
                    promoter_name = enhanced_get_table_value(soup, 'Name')
                
                promoter_address = enhanced_get_table_value(soup, 'Address')
                if promoter_address == "N/A":
                    promoter_address = enhanced_get_table_value(soup, 'Registered Office')
                if promoter_address == "N/A":
                    promoter_address = enhanced_get_table_value(soup, 'Office Address')
                
                gst_no = enhanced_get_table_value(soup, 'GST')
                if gst_no == "N/A":
                    gst_no = enhanced_get_table_value(soup, 'GST No')
                if gst_no == "N/A":
                    gst_no = enhanced_get_table_value(soup, 'GSTIN')

                logger.info("✓ Extracted promoter details")
            else:
                logger.warning("No Promoter Details tab found with any selector")

        except Exception as e:
            logger.error(f"Error accessing promoter details: {e}")

        result = {
            'Project No': button_index + 1,
            'RERA Regd. No': rera_no,
            'Project Name': project_name,
            'Promoter Name': promoter_name,
            'Promoter Address': promoter_address,
            'GST No': gst_no
        }
        
        logger.info(f"Final extracted data: {result}")
        return result

    except Exception as e:
        logger.error(f"Error processing project {button_index + 1}: {e}")
        return {
            'Project No': button_index + 1,
            'RERA Regd. No': 'Error',
            'Project Name': 'Error',
            'Promoter Name': 'Error',
            'Promoter Address': 'Error',
            'GST No': 'Error'
        }

def main():
    print("\n" + "="*60)
    print("ENHANCED RERA SCRAPER - IMPROVED DATA EXTRACTION")
    print("="*60)

    # Enhanced Chrome options
    options = webdriver.ChromeOptions()
    # Comment out headless for debugging
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        # Additional anti-detection measures
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")

        logger.info("Navigating to RERA project list...")
        driver.get('https://rera.odisha.gov.in/projects/project-list')
        wait_for_page_load(driver, 30)

        # Check if page loaded correctly
        if "rera" not in driver.current_url.lower():
            logger.error("Failed to load RERA website correctly")
            return

        view_buttons = driver.find_elements(By.XPATH, "//a[text()='View Details']")
        total_projects = len(view_buttons)
        logger.info(f"Found {total_projects} projects available")

        if total_projects == 0:
            logger.error("No 'View Details' buttons found. Page might not have loaded correctly.")
            # Save page source for debugging
            with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info("Page source saved to debug_page_source.html for analysis")
            return

        # Process projects (start with just 3 for testing)
        num_to_process = min(6
                             , total_projects)
        results = []

        for i in range(num_to_process):
            logger.info(f"\n--- Processing Project {i + 1}/{num_to_process} ---")
            details = get_project_details_by_click(driver, i)
            if details:
                results.append(details)
            time.sleep(5)  # Longer delay between requests

        print("\n" + "="*60)
        print("SCRAPING RESULTS")
        print("="*60)

        if results:
            for project in results:
                print(f"\n--- Project {project['Project No']} ---")
                for key, value in project.items():
                    if key != 'Project No':
                        print(f"{key}: {value}")
                print("-" * 40)
        else:
            print("No projects were successfully processed.")

        logger.info(f"Successfully processed {len(results)} out of {num_to_process} projects")

        # Save results to JSON
        json_file = 'rera_projects_enhanced.json'
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            logger.info(f"Results saved to {json_file}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")

    except Exception as e:
        logger.error(f"Main execution error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            input("Press Enter to close browser (for debugging)...")  # Remove this line for automated runs
            driver.quit()
            logger.info("Browser closed")

# if _name_ == '_main_':
#     main()
if __name__ == "__main__":
    main()
