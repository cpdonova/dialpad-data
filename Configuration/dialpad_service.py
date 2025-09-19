import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class DialpadAPI:
    """Dialpad API client for fetching employee status information"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.headers)
    
    def get_company_info(self) -> Optional[Dict[str, Any]]:
        """Get company information"""
        try:
            url = self.config.get_api_url('company/')
            logger.debug(f"Fetching company info from: {url}")
            
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching company info: {e}")
            return None
    
    def get_users(self, email_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all users in the company, optionally filtered by email
        
        Note: The Dialpad API only supports email filtering, not office_id or call_center_id
        """
        try:
            if email_filter:
                url = self.config.get_api_url(f'users/?email={email_filter}')
                logger.debug(f"Fetching users with email filter: {url}")
            else:
                url = self.config.get_api_url('users/')
                logger.debug(f"Fetching all users from: {url}")
            
            # Get all users with pagination
            all_users = []
            cursor = None
            
            while True:
                if cursor:
                    paginated_url = f"{url}{'&' if '?' in url else '?'}cursor={cursor}"
                else:
                    paginated_url = url
                
                response = self.session.get(paginated_url, timeout=self.config.request_timeout)
                response.raise_for_status()
                
                data = response.json()
                users = data.get('items', data.get('results', []))
                all_users.extend(users)
                
                logger.debug(f"Fetched {len(users)} users (total: {len(all_users)})")
                
                # Check for next page
                cursor = data.get('cursor')
                if not cursor or not users:
                    break
                    
                # Safety limit to prevent infinite loops
                if len(all_users) > 1000:
                    logger.warning(f"Reached safety limit of 1000 users")
                    break
            
            logger.info(f"Total users fetched: {len(all_users)}")
            return all_users
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching users: {e}")
            return []
    
    def filter_users_by_office(self, users: List[Dict[str, Any]], office_id: str) -> List[Dict[str, Any]]:
        """Filter users by office_id (client-side filtering since API doesn't support it)"""
        filtered_users = []
        for user in users:
            if user.get('office_id') == office_id:
                filtered_users.append(user)
        return filtered_users
    
    def get_call_center_users(self, call_center_id: str) -> List[Dict[str, Any]]:
        """Get users specifically from a call center"""
        try:
            url = self.config.get_api_url(f'callcenters/{call_center_id}/users/')
            logger.debug(f"Fetching call center users from: {url}")
            
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching call center users: {e}")
            # Try alternative endpoint
            return self.get_users(call_center_id)
    
    def get_user_devices(self, user_id: int) -> List[Dict[str, Any]]:
        """Get devices for a specific user"""
        try:
            url = self.config.get_api_url(f'userdevices/?user_id={user_id}')
            logger.debug(f"Fetching devices for user {user_id} from: {url}")
            
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching devices for user {user_id}: {e}")
            return []
    
    def get_contacts(self, office_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get contacts from the company, optionally filtered by office"""
        try:
            if office_id:
                url = self.config.get_api_url(f'contacts/?office_id={office_id}')
                logger.debug(f"Fetching contacts from office {office_id}: {url}")
            else:
                url = self.config.get_api_url('contacts/')
                logger.debug(f"Fetching contacts from: {url}")
            
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('items', [])  # Contacts use 'items' not 'results'
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching contacts: {e}")
            return []
    
    def get_offices(self) -> List[Dict[str, Any]]:
        """Get offices from the company"""
        try:
            url = self.config.get_api_url('offices/')
            logger.debug(f"Fetching offices from: {url}")
            
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('items', [])  # Offices use 'items' not 'results'
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching offices: {e}")
            return []

    def get_call_centers(self) -> List[Dict[str, Any]]:
        """Get call centers information"""
        try:
            url = self.config.get_api_url('callcenters/')
            logger.debug(f"Fetching call centers from: {url}")
            
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching call centers: {e}")
            return []

class EmployeeStatusService:
    """Service for gathering and formatting employee status information"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api = DialpadAPI(config)
    
    def get_employee_status(self) -> Dict[str, Any]:
        """Get comprehensive employee status information"""
        logger.info("Gathering employee status information...")
        
        # Get company info
        company_info = self.api.get_company_info()
        
        # Get all users and filter manually by office
        logger.info("Fetching all users...")
        all_users = self.api.get_users()
        
        if self.config.office_id:
            logger.info(f"Filtering users by office ID: {self.config.office_id}")
            users = self.api.filter_users_by_office(all_users, self.config.office_id)
        else:
            users = all_users
        
        logger.info(f"Found {len(users)} users in target office")
        
        # Get call centers, contacts, and offices
        call_centers = self.api.get_call_centers()
        
        # Get contacts - filter by office if specified
        if self.config.office_id:
            logger.info(f"Fetching contacts from office ID: {self.config.office_id}")
            contacts = self.api.get_contacts(office_id=self.config.office_id)
        else:
            contacts = self.api.get_contacts()
            
        offices = self.api.get_offices()
        
        logger.info(f"Found {len(contacts)} contacts and {len(offices)} offices")
        
        # Process user information
        employee_details = []
        
        # Process regular users if any
        for user in users:
            user_id = user.get('id')
            if user_id:
                # Get devices for this user
                devices = self.api.get_user_devices(user_id)
                
                employee_info = {
                    'id': user_id,
                    'name': user.get('display_name', 'Unknown'),
                    'email': user.get('email', 'N/A'),
                    'phone': user.get('phone_number', 'N/A'),
                    'department': user.get('department', {}).get('name', 'N/A'),
                    'role': user.get('role', 'N/A'),
                    'state': user.get('state', 'unknown'),
                    'devices': devices,
                    'device_count': len(devices),
                    'online_devices': len([d for d in devices if d.get('is_online', False)]),
                    'last_activity': user.get('last_activity'),
                    'timezone': user.get('timezone', 'N/A'),
                    'type': 'user'
                }
                employee_details.append(employee_info)
        
        # Process contacts as potential employees
        for contact in contacts:
            contact_info = {
                'id': contact.get('id', 'unknown'),
                'name': contact.get('display_name', contact.get('first_name', 'Unknown')),
                'email': contact.get('primary_email', 'N/A'),
                'phone': contact.get('primary_phone', 'N/A'),
                'department': contact.get('company_name', 'N/A'),
                'role': contact.get('job_title', 'Contact'),
                'state': 'unknown',
                'devices': [],
                'device_count': 0,
                'online_devices': 0,
                'last_activity': contact.get('updated_at'),
                'timezone': 'N/A',
                'type': 'contact',
                'contact_type': contact.get('type', 'unknown')
            }
            employee_details.append(contact_info)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'company': company_info,
            'total_employees': len(employee_details),
            'employees': employee_details,
            'call_centers': call_centers,
            'contacts': contacts,
            'offices': offices,
            'summary': self._generate_summary(employee_details)
        }
    
    def _generate_summary(self, employees: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of employee status"""
        total = len(employees)
        
        # Count by state
        states = {}
        departments = {}
        online_count = 0
        
        for emp in employees:
            state = emp.get('state', 'unknown')
            states[state] = states.get(state, 0) + 1
            
            dept = emp.get('department', 'N/A')
            departments[dept] = departments.get(dept, 0) + 1
            
            if emp.get('online_devices', 0) > 0:
                online_count += 1
        
        return {
            'total_employees': total,
            'online_employees': online_count,
            'offline_employees': total - online_count,
            'states_breakdown': states,
            'departments_breakdown': departments
        }