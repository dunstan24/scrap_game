"""
AI Analyzer for job postings using Google Gemini (New SDK)
Extracts contact information and analyzes sponsorship signals
"""
import json
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from utils import logger


class GeminiAnalyzer:
    """
    Analyzes job postings using Google Gemini AI (New SDK)
    Features:
    - Multi-key rotation for reliability
    - Rate limiting for free tier compliance
    - Sponsorship signal detection
    - Contact information extraction
    """
    
    def __init__(self, api_keys: List[str], model_name: str = 'gemini-2.0-flash-exp', rate_limit_rpm: int = 15):
        """
        Initialize the Gemini analyzer
        
        Args:
            api_keys: List of Gemini API keys for rotation
            model_name: Gemini model to use
            rate_limit_rpm: Rate limit in requests per minute
        """
        self.api_keys = api_keys
        self.current_key_index = 0
        self.model_name = model_name
        self.rate_limit_rpm = rate_limit_rpm
        self.requests_this_minute = 0
        self.minute_start_time = time.time()
        
        # Initialize with first key
        self._configure_api(self.api_keys[self.current_key_index])
        
        logger.info(f"GeminiAnalyzer initialized with {len(api_keys)} API keys")
        logger.info(f"Using model: {model_name}")
        logger.info(f"Rate limit: {rate_limit_rpm} requests/minute")
    
    def _configure_api(self, api_key: str):
        """Configure Gemini API with given key"""
        try:
            self.client = genai.Client(api_key=api_key)
            logger.info(f"Configured API with key index: {self.current_key_index}")
        except Exception as e:
            logger.error(f"Error configuring API: {str(e)}")
            raise
    
    def _rotate_api_key(self):
        """Rotate to next API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.warning(f"Rotating to API key index: {self.current_key_index}")
        self._configure_api(self.api_keys[self.current_key_index])
    
    def _handle_rate_limit(self):
        """Handle rate limiting for free tier"""
        current_time = time.time()
        elapsed = current_time - self.minute_start_time
        
        # Reset counter every minute
        if elapsed >= 60:
            self.requests_this_minute = 0
            self.minute_start_time = current_time
            return
        
        # Check if we've hit the rate limit
        if self.requests_this_minute >= self.rate_limit_rpm:
            sleep_time = 60 - elapsed + 1  # Wait until next minute + 1 second buffer
            logger.info(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
            self.requests_this_minute = 0
            self.minute_start_time = time.time()
    
    def _extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract contact information using regex patterns
        This is a fallback/supplement to AI extraction
        """
        contact_info = {
            'phone_number': None,
            'company_email': None
        }
        
        # Phone number patterns (Australian formats)
        phone_patterns = [
            r'\+61\s?\d{1}\s?\d{4}\s?\d{4}',  # +61 X XXXX XXXX
            r'0\d{1}\s?\d{4}\s?\d{4}',         # 0X XXXX XXXX
            r'\(\d{2}\)\s?\d{4}\s?\d{4}',      # (XX) XXXX XXXX
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                contact_info['phone_number'] = match.group(0)
                break
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            contact_info['company_email'] = email_match.group(0)
        
        return contact_info
    
    def analyze_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a job posting for sponsorship signals and extract contact information
        
        Args:
            job_data: Dictionary containing job information
            
        Returns:
            Dictionary with AI-extracted fields
        """
        # Handle rate limiting
        self._handle_rate_limit()
        
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(job_data)
        
        # Try to get AI response with key rotation fallback
        max_retries = len(self.api_keys)
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    )
                )
                
                # Parse response
                result = json.loads(response.text)
                
                # Increment request counter
                self.requests_this_minute += 1
                
                # Supplement with regex extraction if AI didn't find contact info
                regex_contacts = self._extract_contact_info(job_data.get('description', ''))
                if not result.get('phone_number') and regex_contacts['phone_number']:
                    result['phone_number'] = regex_contacts['phone_number']
                if not result.get('company_email') and regex_contacts['company_email']:
                    result['company_email'] = regex_contacts['company_email']
                
                logger.info(f"AI analysis completed for: {job_data.get('job_title', 'Unknown')}")
                return result
                
            except Exception as e:
                logger.error(f"Error with API key {self.current_key_index}: {str(e)}")
                
                if attempt < max_retries - 1:
                    self._rotate_api_key()
                    time.sleep(2)  # Brief pause before retry
                else:
                    logger.error("All API keys failed. Returning default values.")
                    return self._get_default_analysis()
        
        return self._get_default_analysis()
    
    def _build_analysis_prompt(self, job_data: Dict[str, Any]) -> str:
        """Build the AI analysis prompt"""
        job_title = job_data.get('job_title', 'N/A')
        company_name = job_data.get('company_name', 'N/A')
        location = job_data.get('location', 'N/A')
        description = job_data.get('description', 'N/A')
        
        prompt = f"""Analyze this Australian job posting and extract information in JSON format.

Job Details:
- Title: {job_title}
- Company: {company_name}
- Location: {location}
- Description: {description[:50000]}  

Extract and analyze the following:

1. **Contact Information** (from description):
   - contact_name: Full name of contact person (or null)
   - phone_number: Phone number in any format (or null)
   - company_email: Email address (or null)

2. **Sponsorship Signal Classification**:
   Classify as one of: "yes", "maybe", "unknown"
   
   **IMPORTANT CLASSIFICATION RULES:**
   
   A. **"yes"** - EXPLICIT SPONSORSHIP MENTIONED:
      - Job description explicitly states: "visa sponsorship available", "will sponsor", "sponsorship offered"
      - Mentions specific visa types: 482, 186, TSS, ENS, RSMS
      - States "international candidates welcome with sponsorship"
      - Any clear statement about providing visa sponsorship
   
   B. **"maybe"** - STRONG INDICATORS (High Probability):
      
      **Government/Public Sector Employers** (VERY IMPORTANT):
      - Company name contains: "Department of", "Ministry of", "State Government", "Federal Government"
      - Examples: "Department of Health Tasmania", "NSW Health", "Queensland Government"
      - Public hospitals, universities, government agencies
      - These employers commonly sponsor skilled workers
      
      **High-Demand Healthcare Occupations**:
      - Registered Nurse, Clinical Nurse, Nurse Practitioner
      - Medical practitioners, specialists, allied health
      - These roles are on skilled occupation lists
      
      **High-Demand Other Occupations**:
      - Engineers (civil, mechanical, mining, software)
      - IT professionals (developers, analysts, architects)
      - Tradespeople in mining/construction
      
      **Large Organizations**:
      - Multinational companies
      - Major Australian corporations
      - Mining companies (Rio Tinto, BHP, etc.)
      - Major healthcare networks
      
      **Inclusive Language**:
      - "Open to all applicants"
      - "Diverse backgrounds encouraged"
      - "International candidates welcome"
      - "Relocation assistance available"
      
      **SPECIAL RULE FOR GOVERNMENT + HEALTHCARE:**
      If company is government (Department of Health, NSW Health, etc.) AND role is healthcare (Nurse, Doctor, Allied Health):
      → MUST classify as "maybe" with confidence ≥ 0.75
      → Reasoning should mention: "Government healthcare employer with high demand occupation"
   
   C. **"unknown"** - No Clear Indicators:
      - No government affiliation
      - Not a high-demand occupation
      - No sponsorship mentions
      - Small private companies with no history
      - Retail, hospitality (unless large chain)

3. **Confidence & Reasoning**:
   - sponsorship_confidence: Float 0.0-1.0 indicating confidence
     * 0.9-1.0: Explicit sponsorship mentioned
     * 0.7-0.9: Government + healthcare, or strong indicators
     * 0.5-0.7: Some indicators present
     * 0.3-0.5: Weak indicators
     * 0.0-0.3: No indicators
   
   - sponsorship_reasoning: Brief explanation (max 150 words)
     * For government employers: MUST mention "government employer"
     * For healthcare: MUST mention "high-demand occupation"
     * Explain the key factors for classification

**EXAMPLES:**

Example 1:
Company: "Department of Health Tasmania"
Title: "Registered Nurse"
→ Classification: "maybe"
→ Confidence: 0.80
→ Reasoning: "Government healthcare employer (Department of Health Tasmania) hiring for a high-demand occupation (Registered Nurse). Government health departments in Australia commonly sponsor skilled healthcare workers due to workforce shortages."

Example 2:
Company: "NSW Health"
Title: "Clinical Nurse Specialist"
→ Classification: "maybe"
→ Confidence: 0.85
→ Reasoning: "State government health employer with critical nursing role. NSW Health regularly sponsors international nurses for skilled positions."

Example 3:
Description mentions: "482 visa sponsorship available"
→ Classification: "yes"
→ Confidence: 0.95
→ Reasoning: "Explicitly states 482 visa sponsorship is available."

Return ONLY valid JSON in this exact format:
{{
    "contact_name": "string or null",
    "phone_number": "string or null",
    "company_email": "string or null",
    "sponsorship_signal": "yes|maybe|unknown",
    "sponsorship_confidence": 0.0-1.0,
    "sponsorship_reasoning": "brief explanation"
}}"""
        
        return prompt
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when AI fails"""
        return {
            'contact_name': None,
            'phone_number': None,
            'company_email': None,
            'sponsorship_signal': 'unknown',
            'sponsorship_confidence': 0.0,
            'sponsorship_reasoning': 'AI analysis unavailable'
        }
    
    def analyze_batch(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze multiple jobs in batch
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            List of job dictionaries with AI analysis added
        """
        logger.info(f"Starting batch analysis of {len(jobs)} jobs...")
        
        analyzed_jobs = []
        for idx, job in enumerate(jobs, 1):
            try:
                # Get AI analysis
                ai_result = self.analyze_job(job)
                
                # Merge AI results with original job data
                job.update(ai_result)
                analyzed_jobs.append(job)
                
                # Progress logging
                if idx % 10 == 0:
                    logger.info(f"Analyzed {idx}/{len(jobs)} jobs")
                    
            except Exception as e:
                logger.error(f"Error analyzing job {idx}: {str(e)}")
                # Add default values and continue
                job.update(self._get_default_analysis())
                analyzed_jobs.append(job)
        
        logger.info(f"Batch analysis completed: {len(analyzed_jobs)}/{len(jobs)} jobs")
        return analyzed_jobs


def test_analyzer():
    """Test function for the analyzer"""
    from config import GEMINI_API_KEYS, GEMINI_MODEL
    
    # Sample job data
    test_job = {
        'job_title': 'Registered Nurse',
        'company_name': 'Sydney Hospital',
        'location': 'Sydney, NSW',
        'description': '''We are seeking an experienced Registered Nurse to join our team.
        
        Requirements:
        - Current AHPRA registration
        - Minimum 2 years experience
        - Sponsorship available for the right candidate
        
        Contact: Sarah Johnson
        Email: recruitment@sydneyhospital.com.au
        Phone: (02) 9876 5432
        '''
    }
    
    analyzer = GeminiAnalyzer(GEMINI_API_KEYS, GEMINI_MODEL)
    result = analyzer.analyze_job(test_job)
    
    print("\n" + "="*60)
    print("AI ANALYSIS RESULT")
    print("="*60)
    print(json.dumps(result, indent=2))
    print("="*60 + "\n")


if __name__ == "__main__":
    test_analyzer()
