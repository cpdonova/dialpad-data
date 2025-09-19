import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for Dialpad API settings"""
    
    def __init__(self):
        self.bearer_token = os.getenv('DIALPAD_BEARER_TOKEN')
        self.api_base_url = os.getenv('DIALPAD_API_BASE_URL', 'https://dialpad.com/api/v2')
        self.company_id = os.getenv('COMPANY_ID')
        self.call_center_id = os.getenv('CALL_CENTER_ID')
        self.office_id = os.getenv('OFFICE_ID')
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Validate required settings
        if not self.bearer_token:
            raise ValueError("DIALPAD_BEARER_TOKEN is required. Please set it in your .env file.")
        
        # Set up logging
        log_level = logging.DEBUG if self.debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @property
    def headers(self) -> Dict[str, str]:
        """Return headers for API requests"""
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def get_api_url(self, endpoint: str) -> str:
        """Construct full API URL for an endpoint"""
        return f"{self.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"