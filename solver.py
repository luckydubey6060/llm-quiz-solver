import os
import time
import base64
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from anthropic import Anthropic
import json
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuizSolver:
    """
    Main class that handles quiz solving logic
    """
    
    def __init__(self, email, secret):
        """
        Initialize the quiz solver
        
        Args:
            email: User's email
            secret: User's secret for authentication
        """
        self.email = email
        self.secret = secret
        
        # Initialize Claude API client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.client = Anthropic(api_key=api_key)
        self.start_time = None
        
        logger.info("QuizSolver initialized")
    
    def get_page_content(self, url):
        """
        Fetch and render JavaScript-heavy pages using Selenium
        
        Args:
            url: The URL to fetch
            
        Returns:
            tuple: (html_content, body_text)
        """
        logger.info(f"Fetching page content from: {url}")
        
        # Setup Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run without GUI
        chrome_options.add_argument('--no-sandbox')  # Required for some environments
        chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        chrome_options.add_argument('--disable-gpu')  # Disable GPU acceleration
        chrome_options.add_argument('--window-size=1920,1080')  # Set window size
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = None
        try:
            # Initialize Chrome driver
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            # Load the page
            driver.get(url)
            
            # Wait for page to load (adjust timeout as needed)
            time.sleep(5)  # Simple wait for JavaScript execution
            
            # Try to wait for body element
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                logger.warning("Timeout waiting for body element")
            
            # Get page source (HTML)
            html_content = driver.page_source
            
            # Get visible text from body
            try:
                body_element = driver.find_element(By.TAG_NAME, "body")
                body_text = body_element.text
            except:
                body_text = driver.find_element(By.TAG_NAME, "html").text
            
            logger.info(f"Page loaded successfully. Content length: {len(html_content)}")
            
            return html_content, body_text
            
        except Exception as e:
            logger.error(f"Error fetching page content: {str(e)}")
            raise
        finally:
            if driver:
                driver.quit()
    
    def extract_urls_from_text(self, text):
        """
        Extract URLs from text using regex
        
        Args:
            text: Text to search for URLs
            
        Returns:
            list: List of found URLs
        """
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls
    
    def parse_quiz_page(self, html_content, body_text):
        """
        Parse quiz page to extract question, submit URL, and any file URLs
        
        Args:
            html_content: Full HTML of the page
            body_text: Visible text from the page
            
        Returns:
            dict: Parsed information including submit_url, question, file_urls
        """
        logger.info("Parsing quiz page...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find submit URL
        submit_url = None
        
        # Method 1: Look for links with 'submit' in href
        for link in soup.find_all('a', href=True):
            if 'submit' in link['href'].lower():
                submit_url = link['href']
                break
        
        # Method 2: Search in body text
        if not submit_url:
            urls = self.extract_urls_from_text(body_text)
            for url in urls:
                if 'submit' in url.lower():
                    submit_url = url
                    break
        
        # Find file URLs (PDFs, CSVs, etc.)
        file_urls = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(ext in href.lower() for ext in ['.pdf', '.csv', '.xlsx', '.txt', '.json']):
                file_urls.append(href)
        
        # Extract question/instructions
        question = body_text
        
        logger.info(f"Found submit URL: {submit_url}")
        logger.info(f"Found {len(file_urls)} file URLs")
        
        return {
            'submit_url': submit_url,
            'question': question,
            'file_urls': file_urls,
            'html': html_content[:5000]  # First 5000 chars for context
        }
    
    def download_file(self, url):
        """
        Download a file from URL
        
        Args:
            url: URL to download from
            
        Returns:
            bytes: File content
        """
        logger.info(f"Downloading file from: {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            logger.info(f"File downloaded. Size: {len(response.content)} bytes")
            return response.content
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return None
    
    def ask_claude(self, question, context="", files_info=""):
        """
        Ask Claude to solve the quiz question
        
        Args:
            question: The quiz question
            context: Additional context (HTML snippets, etc.)
            files_info: Information about any files
            
        Returns:
            str: Claude's answer
        """
        logger.info("Asking Claude for answer...")
        
        prompt = f"""You are a data analysis expert solving a quiz question.

QUESTION:
{question}

CONTEXT:
{context}

FILES INFORMATION:
{files_info}

INSTRUCTIONS:
1. Read the question carefully
2. If there are file URLs mentioned, note them
3. Provide the precise answer in the exact format requested
4. If it's a number, return ONLY the number (no units, no extra text)
5. If it's text, return ONLY the exact text needed
6. If it's a boolean, return true or false
7. If it's JSON, return valid JSON

Your answer should be precise and in the exact format requested. Do not include any explanation unless asked.

ANSWER:"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            answer = message.content[0].text.strip()
            logger.info(f"Claude's answer: {answer}")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error asking Claude: {str(e)}")
            raise
    
    def process_answer(self, answer_text):
        """
        Process Claude's answer into the correct format
        
        Args:
            answer_text: Raw answer from Claude
            
        Returns:
            Processed answer (int, float, str, bool, dict, or list)
        """
        answer_text = answer_text.strip()
        
        # Try to parse as JSON
        try:
            return json.loads(answer_text)
        except:
            pass
        
        # Try to parse as number
        try:
            if '.' in answer_text:
                return float(answer_text)
            else:
                return int(answer_text)
        except:
            pass
        
        # Try to parse as boolean
        if answer_text.lower() in ['true', 'yes']:
            return True
        if answer_text.lower() in ['false', 'no']:
            return False
        
        # Return as string
        return answer_text
    
    def submit_answer(self, submit_url, quiz_url, answer):
        """
        Submit answer to the quiz endpoint
        
        Args:
            submit_url: URL to submit to
            quiz_url: Original quiz URL
            answer: The answer to submit
            
        Returns:
            dict: Response from server
        """
        logger.info(f"Submitting answer to: {submit_url}")
        
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            "answer": answer
        }
        
        try:
            response = requests.post(
                submit_url,
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            logger.info(f"Submit response status: {response.status_code}")
            
            result = response.json()
            logger.info(f"Submit result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error submitting answer: {str(e)}")
            return {"correct": False, "error": str(e)}
    
    def solve_single_quiz(self, url):
        """
        Solve a single quiz question
        
        Args:
            url: Quiz URL
            
        Returns:
            dict: Result from submission
        """
        logger.info(f"=" * 50)
        logger.info(f"SOLVING QUIZ: {url}")
        logger.info(f"=" * 50)
        
        try:
            # Step 1: Fetch page content
            html_content, body_text = self.get_page_content(url)
            
            # Step 2: Parse the page
            parsed = self.parse_quiz_page(html_content, body_text)
            
            if not parsed['submit_url']:
                logger.error("Could not find submit URL!")
                return {"correct": False, "error": "No submit URL found"}
            
            # Step 3: Download any files if needed
            files_info = ""
            if parsed['file_urls']:
                files_info = f"File URLs found: {', '.join(parsed['file_urls'])}\n"
                # You can add logic here to actually download and process files
            
            # Step 4: Ask Claude for answer
            answer_text = self.ask_claude(
                question=parsed['question'],
                context=parsed['html'],
                files_info=files_info
            )
            
            # Step 5: Process answer into correct format
            answer = self.process_answer(answer_text)
            
            logger.info(f"Processed answer: {answer} (type: {type(answer).__name__})")
            
            # Step 6: Submit answer
            result = self.submit_answer(parsed['submit_url'], url, answer)
            
            return result
            
        except Exception as e:
            logger.error(f"Error solving quiz: {str(e)}")
            return {"correct": False, "error": str(e)}
    
    def solve_quiz_chain(self, initial_url):
        """
        Solve entire quiz chain (multiple questions in sequence)
        
        Args:
            initial_url: Starting quiz URL
        """
        self.start_time = time.time()
        current_url = initial_url
        max_time = 180  # 3 minutes = 180 seconds
        question_count = 0
        
        logger.info("Starting quiz chain solver...")
        
        while current_url:
            # Check time limit
            elapsed = time.time() - self.start_time
            if elapsed > max_time:
                logger.error(f"TIME LIMIT EXCEEDED! ({elapsed:.1f}s)")
                break
            
            question_count += 1
            logger.info(f"Question {question_count} | Time elapsed: {elapsed:.1f}s")
            
            try:
                # Solve current question
                result = self.solve_single_quiz(current_url)
                
                # Check if answer was correct
                if result.get('correct'):
                    logger.info("✓ CORRECT ANSWER!")
                    
                    # Check for next URL
                    if result.get('url'):
                        current_url = result['url']
                        logger.info(f"Moving to next question: {current_url}")
                    else:
                        logger.info("✓ QUIZ COMPLETED! No more questions.")
                        break
                        
                else:
                    logger.warning("✗ WRONG ANSWER!")
                    reason = result.get('reason', 'No reason provided')
                    logger.warning(f"Reason: {reason}")
                    
                    # Check if we can retry or skip
                    if result.get('url'):
                        logger.info(f"Got next URL despite wrong answer: {result['url']}")
                        current_url = result['url']
                    else:
                        logger.error("No next URL provided. Ending quiz.")
                        break
                
            except Exception as e:
                logger.error(f"EXCEPTION while solving quiz: {str(e)}")
                break
        
        total_time = time.time() - self.start_time
        logger.info(f"=" * 50)
        logger.info(f"QUIZ SESSION ENDED")
        logger.info(f"Total questions attempted: {question_count}")
        logger.info(f"Total time: {total_time:.1f}s")
        logger.info(f"=" * 50)