"""
SheetDB CRM Integration
Store contacts, campaigns, and analytics in Google Sheets via SheetDB API
100% FREE - Unlimited requests
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

class SheetDBCRM:
    """
    SheetDB CRM for storing marketing data in Google Sheets
    
    API Docs: https://docs.sheetdb.io/
    
    Features:
    - Store contacts with enrichment data
    - Track email campaigns and sequences
    - Log events (opens, clicks, replies)
    - Analytics and reporting
    """
    
    def __init__(self, api_url: str):
        """
        Initialize SheetDB CRM
        
        Args:
            api_url: SheetDB API endpoint (e.g., https://sheetdb.io/api/v1/YOUR_SHEET_ID)
        """
        self.api_url = api_url.rstrip('/')
        self.headers = {'Content-Type': 'application/json'}
    
    # ========================================================================
    # CONTACTS MANAGEMENT
    # ========================================================================
    
    def add_contact(self, contact_data: Dict[str, Any]) -> Dict:
        """
        Add a new contact to the CRM
        
        Args:
            contact_data: {
                'email': 'john@company.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'company': 'Company Inc',
                'title': 'CEO',
                'linkedin': 'linkedin.com/in/johndoe',
                'phone': '+1234567890',
                'source': 'apollo|manual|import',
                'tags': 'enterprise,decision-maker',
                'status': 'new|contacted|qualified|customer',
                'account_score': 85
            }
        
        Returns:
            Response from SheetDB API
        """
        # Add metadata
        contact_data['created_at'] = datetime.now().isoformat()
        contact_data['updated_at'] = datetime.now().isoformat()
        
        # Default values
        contact_data.setdefault('status', 'new')
        contact_data.setdefault('account_score', 0)
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={'data': [contact_data]}
            )
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_contact(self, email: str) -> Optional[Dict]:
        """
        Get contact by email
        
        Args:
            email: Contact email address
        
        Returns:
            Contact data or None
        """
        try:
            response = requests.get(
                f"{self.api_url}/search",
                params={'email': email}
            )
            response.raise_for_status()
            results = response.json()
            return results[0] if results else None
        except Exception as e:
            print(f"Error getting contact: {e}")
            return None
    
    def update_contact(self, email: str, updates: Dict) -> Dict:
        """
        Update contact information
        
        Args:
            email: Contact email
            updates: Fields to update
        
        Returns:
            API response
        """
        updates['updated_at'] = datetime.now().isoformat()
        
        try:
            response = requests.patch(
                f"{self.api_url}/email/{email}",
                headers=self.headers,
                json={'data': updates}
            )
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_contacts(self, limit: int = 1000) -> List[Dict]:
        """
        Get all contacts
        
        Args:
            limit: Maximum number of contacts to return
        
        Returns:
            List of contacts
        """
        try:
            response = requests.get(
                self.api_url,
                params={'limit': limit}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting contacts: {e}")
            return []
    
    def search_contacts(self, filters: Dict) -> List[Dict]:
        """
        Search contacts by criteria
        
        Args:
            filters: Search criteria (e.g., {'status': 'qualified', 'company': 'Acme'})
        
        Returns:
            Matching contacts
        """
        try:
            response = requests.get(
                f"{self.api_url}/search",
                params=filters
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error searching contacts: {e}")
            return []
    
    # ========================================================================
    # CAMPAIGN TRACKING
    # ========================================================================
    
    def log_campaign(self, campaign_data: Dict) -> Dict:
        """
        Log email/LinkedIn campaign
        
        Args:
            campaign_data: {
                'campaign_id': 'camp_123',
                'type': 'email|linkedin',
                'contact_email': 'john@company.com',
                'subject': 'Email subject',
                'sent_at': '2025-01-01T10:00:00',
                'status': 'sent|opened|clicked|replied'
            }
        
        Returns:
            API response
        """
        campaign_data['created_at'] = datetime.now().isoformat()
        
        try:
            # Use a separate sheet for campaigns (append /campaigns to URL)
            response = requests.post(
                f"{self.api_url}?sheet=campaigns",
                headers=self.headers,
                json={'data': [campaign_data]}
            )
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_campaigns(self, contact_email: str = None) -> List[Dict]:
        """
        Get campaigns (optionally filtered by contact)
        
        Args:
            contact_email: Filter by contact email
        
        Returns:
            List of campaigns
        """
        try:
            url = f"{self.api_url}?sheet=campaigns"
            if contact_email:
                url += f"&contact_email={contact_email}"
            
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting campaigns: {e}")
            return []
    
    # ========================================================================
    # EVENT TRACKING
    # ========================================================================
    
    def log_event(self, event_data: Dict) -> Dict:
        """
        Log engagement event (open, click, reply, etc.)
        
        Args:
            event_data: {
                'event_type': 'email_open|email_click|email_reply|linkedin_view|linkedin_connect',
                'contact_email': 'john@company.com',
                'campaign_id': 'camp_123',
                'timestamp': '2025-01-01T10:30:00',
                'metadata': {'link_url': 'https://example.com'}
            }
        
        Returns:
            API response
        """
        event_data['created_at'] = datetime.now().isoformat()
        
        try:
            response = requests.post(
                f"{self.api_url}?sheet=events",
                headers=self.headers,
                json={'data': [event_data]}
            )
            response.raise_for_status()
            
            # Update contact's last_activity
            if 'contact_email' in event_data:
                self.update_contact(
                    event_data['contact_email'],
                    {'last_activity': event_data['created_at']}
                )
            
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_events(self, contact_email: str = None, event_type: str = None) -> List[Dict]:
        """
        Get events (optionally filtered)
        
        Args:
            contact_email: Filter by contact
            event_type: Filter by event type
        
        Returns:
            List of events
        """
        try:
            url = f"{self.api_url}?sheet=events"
            params = {}
            if contact_email:
                params['contact_email'] = contact_email
            if event_type:
                params['event_type'] = event_type
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting events: {e}")
            return []
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    
    def get_analytics_summary(self) -> Dict:
        """
        Get CRM analytics summary
        
        Returns:
            Analytics data with counts and metrics
        """
        try:
            contacts = self.get_all_contacts()
            campaigns = self.get_campaigns()
            events = self.get_events()
            
            # Calculate metrics
            total_contacts = len(contacts)
            status_breakdown = {}
            for contact in contacts:
                status = contact.get('status', 'unknown')
                status_breakdown[status] = status_breakdown.get(status, 0) + 1
            
            total_campaigns = len(campaigns)
            campaign_types = {}
            for campaign in campaigns:
                ctype = campaign.get('type', 'unknown')
                campaign_types[ctype] = campaign_types.get(ctype, 0) + 1
            
            total_events = len(events)
            event_breakdown = {}
            for event in events:
                etype = event.get('event_type', 'unknown')
                event_breakdown[etype] = event_breakdown.get(etype, 0) + 1
            
            # Calculate engagement rates
            email_sent = campaign_types.get('email', 0)
            email_opens = event_breakdown.get('email_open', 0)
            email_clicks = event_breakdown.get('email_click', 0)
            email_replies = event_breakdown.get('email_reply', 0)
            
            open_rate = (email_opens / email_sent * 100) if email_sent > 0 else 0
            click_rate = (email_clicks / email_sent * 100) if email_sent > 0 else 0
            reply_rate = (email_replies / email_sent * 100) if email_sent > 0 else 0
            
            return {
                'contacts': {
                    'total': total_contacts,
                    'by_status': status_breakdown
                },
                'campaigns': {
                    'total': total_campaigns,
                    'by_type': campaign_types
                },
                'events': {
                    'total': total_events,
                    'by_type': event_breakdown
                },
                'engagement': {
                    'email_sent': email_sent,
                    'open_rate': round(open_rate, 2),
                    'click_rate': round(click_rate, 2),
                    'reply_rate': round(reply_rate, 2)
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================
    
    def bulk_add_contacts(self, contacts: List[Dict]) -> Dict:
        """
        Add multiple contacts at once
        
        Args:
            contacts: List of contact dictionaries
        
        Returns:
            API response
        """
        # Add timestamps
        for contact in contacts:
            contact['created_at'] = datetime.now().isoformat()
            contact['updated_at'] = datetime.now().isoformat()
            contact.setdefault('status', 'new')
            contact.setdefault('account_score', 0)
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={'data': contacts}
            )
            response.raise_for_status()
            return {'success': True, 'data': response.json(), 'count': len(contacts)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_to_csv(self, sheet: str = 'default') -> str:
        """
        Export sheet data as CSV
        
        Args:
            sheet: Sheet name (default|campaigns|events)
        
        Returns:
            CSV data as string
        """
        try:
            url = self.api_url
            if sheet != 'default':
                url += f"?sheet={sheet}"
            
            response = requests.get(url, headers={'Accept': 'text/csv'})
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f"Error: {e}"
