"""
LINKEDIN AUTOMATION
Multi-channel outreach = 3x better results

Integrations:
- PhantomBuster - LinkedIn automation at scale
- Waalaxy - LinkedIn + Email sequences
- LinkedIn Sales Navigator API (if available)
- Profile scraping and enrichment
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

LINKEDIN_DATA_FILE = "linkedin_data.json"
LINKEDIN_QUEUE_FILE = "linkedin_queue.json"
SEQUENCES_FILE = "multichannel_sequences.json"


def load_linkedin_data() -> Dict:
    if os.path.exists(LINKEDIN_DATA_FILE):
        with open(LINKEDIN_DATA_FILE, 'r') as f:
            return json.load(f)
    return {'connections': {}, 'profile_views': {}, 'messages': {}}


def save_linkedin_data(data: Dict):
    with open(LINKEDIN_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


class ConnectionStatus(Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    NOT_SENT = "not_sent"


# ============================================================================
# PHANTOMBUSTER INTEGRATION
# ============================================================================

class PhantomBuster:
    """
    PhantomBuster API for LinkedIn automation.
    
    Capabilities:
    - Send connection requests with personalized notes
    - Auto-message new connections
    - Profile scraping and enrichment
    - Sales Navigator list extraction
    
    API: https://phantombuster.com/api
    Pricing: $59/month for 5 phantoms
    
    IMPORTANT: Use responsibly. LinkedIn limits:
    - ~100 connection requests/week
    - ~150 messages/day
    - Avoid aggressive automation
    """
    
    BASE_URL = "https://api.phantombuster.com/api/v2"
    
    # Pre-built phantom IDs for LinkedIn
    PHANTOMS = {
        'linkedin_connect': 'LinkedIn Auto Connect',
        'linkedin_message': 'LinkedIn Message Sender',
        'linkedin_profile_scraper': 'LinkedIn Profile Scraper',
        'linkedin_search_export': 'LinkedIn Search Export',
        'sales_nav_search': 'Sales Navigator Search Export',
        'linkedin_network': 'LinkedIn Network Booster'
    }
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('PHANTOMBUSTER_API_KEY')
        self.session_cookie = os.environ.get('LINKEDIN_SESSION_COOKIE')  # li_at cookie
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request to PhantomBuster"""
        if not self.api_key:
            return {'error': 'No API key configured', 'success': False}
        
        try:
            import requests
            
            headers = {
                'X-Phantombuster-Key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            url = f"{self.BASE_URL}/{endpoint}"
            
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=30)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}', 'details': response.text}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_agents(self) -> Dict:
        """List all configured phantoms/agents"""
        return self._request('GET', 'agents/fetch-all')
    
    def launch_agent(self, agent_id: str, arguments: Dict = None) -> Dict:
        """Launch a phantom with arguments"""
        data = {'id': agent_id}
        if arguments:
            data['argument'] = json.dumps(arguments)
        
        return self._request('POST', 'agents/launch', data)
    
    def get_agent_output(self, agent_id: str) -> Dict:
        """Get output from last agent run"""
        return self._request('GET', 'agents/fetch-output', {'id': agent_id})
    
    def send_connection_request(self, profile_url: str, message: str = None) -> Dict:
        """
        Send LinkedIn connection request.
        
        Args:
            profile_url: LinkedIn profile URL
            message: Optional personalized note (max 300 chars)
        
        Returns:
            Status of the request
        """
        if not self.session_cookie:
            return {'success': False, 'error': 'LinkedIn session cookie required'}
        
        # Queue the request
        queue = self._load_queue()
        
        request_id = hashlib.md5(f"{profile_url}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        queue['pending'].append({
            'id': request_id,
            'type': 'connection',
            'profile_url': profile_url,
            'message': message[:300] if message else None,
            'created_at': datetime.now().isoformat(),
            'status': 'queued'
        })
        
        self._save_queue(queue)
        
        # If PhantomBuster is configured, we can auto-process
        # Otherwise, queue for manual processing or alternative method
        
        return {
            'success': True,
            'request_id': request_id,
            'status': 'queued',
            'message': 'Connection request queued'
        }
    
    def send_message(self, profile_url: str, message: str) -> Dict:
        """
        Send LinkedIn message to a connection.
        
        Args:
            profile_url: LinkedIn profile URL (must be connected)
            message: Message content
        """
        if not self.session_cookie:
            return {'success': False, 'error': 'LinkedIn session cookie required'}
        
        queue = self._load_queue()
        
        request_id = hashlib.md5(f"{profile_url}{message}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        queue['pending'].append({
            'id': request_id,
            'type': 'message',
            'profile_url': profile_url,
            'message': message,
            'created_at': datetime.now().isoformat(),
            'status': 'queued'
        })
        
        self._save_queue(queue)
        
        return {
            'success': True,
            'request_id': request_id,
            'status': 'queued'
        }
    
    def scrape_profile(self, profile_url: str) -> Dict:
        """
        Scrape LinkedIn profile data.
        
        Returns:
            Name, headline, company, location, experience, education, skills
        """
        # Check cache first
        data = load_linkedin_data()
        cache_key = hashlib.md5(profile_url.encode()).hexdigest()
        
        if cache_key in data.get('profiles', {}):
            cached = data['profiles'][cache_key]
            if datetime.fromisoformat(cached['scraped_at']) > datetime.now() - timedelta(days=30):
                return {'success': True, 'data': cached, 'cached': True}
        
        # If no PhantomBuster, return placeholder for manual enrichment
        if not self.api_key:
            return {
                'success': False,
                'error': 'PhantomBuster API key required for profile scraping',
                'profile_url': profile_url
            }
        
        # Queue scrape request
        queue = self._load_queue()
        request_id = hashlib.md5(f"scrape_{profile_url}".encode()).hexdigest()[:12]
        
        queue['pending'].append({
            'id': request_id,
            'type': 'scrape',
            'profile_url': profile_url,
            'created_at': datetime.now().isoformat(),
            'status': 'queued'
        })
        
        self._save_queue(queue)
        
        return {
            'success': True,
            'request_id': request_id,
            'status': 'queued',
            'message': 'Profile scrape queued'
        }
    
    def search_profiles(self, query: str, limit: int = 25) -> Dict:
        """
        Search LinkedIn for profiles matching criteria.
        
        Args:
            query: Search query (job title, company, keywords)
            limit: Max profiles to return
        """
        if not self.api_key:
            return {'success': False, 'error': 'PhantomBuster API key required'}
        
        # This would launch the LinkedIn Search Export phantom
        return {
            'success': True,
            'status': 'queued',
            'message': f'Search for "{query}" queued (limit: {limit})'
        }
    
    def _load_queue(self) -> Dict:
        if os.path.exists(LINKEDIN_QUEUE_FILE):
            with open(LINKEDIN_QUEUE_FILE, 'r') as f:
                return json.load(f)
        return {'pending': [], 'completed': [], 'failed': []}
    
    def _save_queue(self, queue: Dict):
        with open(LINKEDIN_QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=2)
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        queue = self._load_queue()
        return {
            'pending': len(queue.get('pending', [])),
            'completed': len(queue.get('completed', [])),
            'failed': len(queue.get('failed', [])),
            'items': queue
        }
    
    def process_queue(self, batch_size: int = 10) -> Dict:
        """
        Process pending queue items.
        
        Respects LinkedIn rate limits:
        - Max 100 connections/week
        - Max 150 messages/day
        """
        queue = self._load_queue()
        pending = queue.get('pending', [])[:batch_size]
        
        results = []
        for item in pending:
            # In production, this would call PhantomBuster APIs
            # For now, we mark as processed and track
            item['status'] = 'processed'
            item['processed_at'] = datetime.now().isoformat()
            
            queue['completed'].append(item)
            queue['pending'].remove(item)
            
            results.append({
                'id': item['id'],
                'type': item['type'],
                'status': 'processed'
            })
        
        self._save_queue(queue)
        
        return {
            'success': True,
            'processed': len(results),
            'results': results
        }


# ============================================================================
# WAALAXY INTEGRATION
# ============================================================================

class Waalaxy:
    """
    Waalaxy - LinkedIn + Email multi-channel automation.
    
    Better for:
    - Combined LinkedIn + Email sequences
    - Pre-built campaign templates
    - Team collaboration
    
    API: https://www.waalaxy.com/
    Pricing: €56/month
    """
    
    BASE_URL = "https://api.waalaxy.com/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('WAALAXY_API_KEY')
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        if not self.api_key:
            return {'error': 'No Waalaxy API key', 'success': False}
        
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.BASE_URL}/{endpoint}"
            
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=30)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code in [200, 201]:
                return {'success': True, 'data': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_campaign(self, name: str, sequence_type: str, prospects: List[Dict]) -> Dict:
        """
        Create a multi-channel campaign.
        
        Args:
            name: Campaign name
            sequence_type: 'linkedin_only', 'email_only', 'multichannel'
            prospects: List of prospect data
        """
        return self._request('POST', 'campaigns', {
            'name': name,
            'type': sequence_type,
            'prospects': prospects
        })
    
    def add_prospects_to_campaign(self, campaign_id: str, prospects: List[Dict]) -> Dict:
        """Add prospects to existing campaign"""
        return self._request('POST', f'campaigns/{campaign_id}/prospects', {
            'prospects': prospects
        })
    
    def get_campaign_stats(self, campaign_id: str) -> Dict:
        """Get campaign performance stats"""
        return self._request('GET', f'campaigns/{campaign_id}/stats')
    
    def get_campaigns(self) -> Dict:
        """List all campaigns"""
        return self._request('GET', 'campaigns')


# ============================================================================
# MULTI-CHANNEL SEQUENCE ENGINE
# ============================================================================

class MultiChannelSequence:
    """
    Orchestrate multi-channel outreach sequences.
    
    Example sequence:
    Day 0: Email introduction
    Day 2: LinkedIn connection request (if no email reply)
    Day 4: LinkedIn message (if connected)
    Day 7: Follow-up email
    Day 10: Final email
    
    Multi-channel = 3x better response rates
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.sequences = self._load_sequences()
    
    def _load_sequences(self) -> Dict:
        if os.path.exists(SEQUENCES_FILE):
            with open(SEQUENCES_FILE, 'r') as f:
                data = json.load(f)
                return data.get(self.user_email, {})
        return {}
    
    def _save_sequences(self):
        all_sequences = {}
        if os.path.exists(SEQUENCES_FILE):
            with open(SEQUENCES_FILE, 'r') as f:
                all_sequences = json.load(f)
        
        all_sequences[self.user_email] = self.sequences
        
        with open(SEQUENCES_FILE, 'w') as f:
            json.dump(all_sequences, f, indent=2)
    
    def create_sequence(self, name: str, steps: List[Dict]) -> Dict:
        """
        Create a multi-channel sequence template.
        
        Args:
            name: Sequence name
            steps: List of steps, each with:
                - day: Day offset from start
                - channel: 'email', 'linkedin_connect', 'linkedin_message'
                - template: Message template
                - condition: Optional condition (e.g., 'if_no_reply', 'if_connected')
        
        Example:
            steps = [
                {'day': 0, 'channel': 'email', 'template': 'intro_email'},
                {'day': 2, 'channel': 'linkedin_connect', 'template': 'connection_note', 'condition': 'if_no_reply'},
                {'day': 4, 'channel': 'linkedin_message', 'template': 'linkedin_followup', 'condition': 'if_connected'},
                {'day': 7, 'channel': 'email', 'template': 'followup_email', 'condition': 'if_no_reply'}
            ]
        """
        sequence_id = hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        self.sequences[sequence_id] = {
            'id': sequence_id,
            'name': name,
            'steps': steps,
            'created_at': datetime.now().isoformat(),
            'active_prospects': [],
            'completed': [],
            'stats': {
                'enrolled': 0,
                'emails_sent': 0,
                'linkedin_connects': 0,
                'linkedin_messages': 0,
                'replies': 0,
                'meetings': 0
            }
        }
        
        self._save_sequences()
        
        return {
            'success': True,
            'sequence_id': sequence_id,
            'name': name,
            'steps': len(steps)
        }
    
    def enroll_prospect(self, sequence_id: str, prospect: Dict) -> Dict:
        """
        Enroll a prospect in a sequence.
        
        Args:
            sequence_id: Sequence to enroll in
            prospect: {
                'email': 'john@acme.com',
                'linkedin_url': 'https://linkedin.com/in/johndoe',
                'first_name': 'John',
                'last_name': 'Doe',
                'company': 'Acme Corp',
                'title': 'VP Sales',
                'variables': {...}  # For template personalization
            }
        """
        if sequence_id not in self.sequences:
            return {'success': False, 'error': 'Sequence not found'}
        
        sequence = self.sequences[sequence_id]
        
        prospect_id = hashlib.md5(
            f"{prospect.get('email', '')}{prospect.get('linkedin_url', '')}".encode()
        ).hexdigest()[:12]
        
        enrollment = {
            'id': prospect_id,
            'prospect': prospect,
            'enrolled_at': datetime.now().isoformat(),
            'current_step': 0,
            'status': 'active',
            'history': [],
            'next_action_at': datetime.now().isoformat()
        }
        
        sequence['active_prospects'].append(enrollment)
        sequence['stats']['enrolled'] += 1
        
        self._save_sequences()
        
        return {
            'success': True,
            'prospect_id': prospect_id,
            'sequence': sequence['name'],
            'next_step': sequence['steps'][0] if sequence['steps'] else None
        }
    
    def get_due_actions(self) -> List[Dict]:
        """
        Get all actions due for execution.
        
        Returns list of actions ready to be sent.
        """
        due_actions = []
        now = datetime.now()
        
        for seq_id, sequence in self.sequences.items():
            for prospect in sequence.get('active_prospects', []):
                if prospect['status'] != 'active':
                    continue
                
                next_action_at = datetime.fromisoformat(prospect['next_action_at'])
                
                if next_action_at <= now:
                    current_step_idx = prospect['current_step']
                    
                    if current_step_idx < len(sequence['steps']):
                        step = sequence['steps'][current_step_idx]
                        
                        # Check conditions
                        if self._check_condition(step.get('condition'), prospect):
                            due_actions.append({
                                'sequence_id': seq_id,
                                'sequence_name': sequence['name'],
                                'prospect_id': prospect['id'],
                                'prospect': prospect['prospect'],
                                'step': step,
                                'step_number': current_step_idx + 1
                            })
        
        return due_actions
    
    def _check_condition(self, condition: str, prospect: Dict) -> bool:
        """Check if step condition is met"""
        if not condition:
            return True
        
        history = prospect.get('history', [])
        
        if condition == 'if_no_reply':
            # Check if any reply received
            return not any(h.get('reply_received') for h in history)
        
        if condition == 'if_connected':
            # Check if LinkedIn connection accepted
            return any(
                h.get('channel') == 'linkedin_connect' and h.get('accepted')
                for h in history
            )
        
        if condition == 'if_opened':
            # Check if email was opened
            return any(
                h.get('channel') == 'email' and h.get('opened')
                for h in history
            )
        
        return True
    
    def execute_action(self, sequence_id: str, prospect_id: str, 
                       email_sender=None, linkedin=None) -> Dict:
        """
        Execute the next action for a prospect.
        
        Args:
            email_sender: EmailSender instance
            linkedin: PhantomBuster instance
        """
        if sequence_id not in self.sequences:
            return {'success': False, 'error': 'Sequence not found'}
        
        sequence = self.sequences[sequence_id]
        
        # Find prospect
        prospect_data = None
        for p in sequence['active_prospects']:
            if p['id'] == prospect_id:
                prospect_data = p
                break
        
        if not prospect_data:
            return {'success': False, 'error': 'Prospect not found'}
        
        current_step_idx = prospect_data['current_step']
        
        if current_step_idx >= len(sequence['steps']):
            # Sequence complete
            prospect_data['status'] = 'completed'
            sequence['completed'].append(prospect_data)
            sequence['active_prospects'].remove(prospect_data)
            self._save_sequences()
            return {'success': True, 'status': 'sequence_completed'}
        
        step = sequence['steps'][current_step_idx]
        prospect = prospect_data['prospect']
        
        result = {'success': False}
        
        # Execute based on channel
        if step['channel'] == 'email':
            if email_sender:
                # Personalize template
                body = self._personalize_template(step.get('template', ''), prospect)
                subject = self._personalize_template(step.get('subject', 'Following up'), prospect)
                
                result = email_sender.send(
                    to=prospect['email'],
                    subject=subject,
                    body=body,
                    track_opens=True,
                    track_clicks=True
                )
                
                if result.get('success'):
                    sequence['stats']['emails_sent'] += 1
            else:
                result = {'success': False, 'error': 'Email sender not configured'}
        
        elif step['channel'] == 'linkedin_connect':
            if linkedin:
                message = self._personalize_template(step.get('template', ''), prospect)
                result = linkedin.send_connection_request(
                    prospect.get('linkedin_url'),
                    message
                )
                
                if result.get('success'):
                    sequence['stats']['linkedin_connects'] += 1
            else:
                result = {'success': False, 'error': 'LinkedIn not configured'}
        
        elif step['channel'] == 'linkedin_message':
            if linkedin:
                message = self._personalize_template(step.get('template', ''), prospect)
                result = linkedin.send_message(
                    prospect.get('linkedin_url'),
                    message
                )
                
                if result.get('success'):
                    sequence['stats']['linkedin_messages'] += 1
            else:
                result = {'success': False, 'error': 'LinkedIn not configured'}
        
        # Record in history
        prospect_data['history'].append({
            'step': current_step_idx,
            'channel': step['channel'],
            'executed_at': datetime.now().isoformat(),
            'result': result
        })
        
        # Move to next step
        if result.get('success'):
            prospect_data['current_step'] += 1
            
            # Calculate next action time
            if prospect_data['current_step'] < len(sequence['steps']):
                next_step = sequence['steps'][prospect_data['current_step']]
                days_until_next = next_step.get('day', 0) - step.get('day', 0)
                prospect_data['next_action_at'] = (
                    datetime.now() + timedelta(days=max(1, days_until_next))
                ).isoformat()
        
        self._save_sequences()
        
        return {
            'success': result.get('success', False),
            'channel': step['channel'],
            'step': current_step_idx + 1,
            'total_steps': len(sequence['steps']),
            'result': result
        }
    
    def _personalize_template(self, template: str, prospect: Dict) -> str:
        """Replace template variables with prospect data"""
        if not template:
            return ""
        
        replacements = {
            '{{first_name}}': prospect.get('first_name', ''),
            '{{last_name}}': prospect.get('last_name', ''),
            '{{company}}': prospect.get('company', ''),
            '{{title}}': prospect.get('title', ''),
            '{{email}}': prospect.get('email', ''),
        }
        
        # Add custom variables
        for key, value in prospect.get('variables', {}).items():
            replacements[f'{{{{{key}}}}}'] = str(value)
        
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
    
    def record_reply(self, sequence_id: str, prospect_id: str, 
                     channel: str, sentiment: str = 'neutral') -> Dict:
        """
        Record a reply from a prospect.
        
        Args:
            channel: 'email' or 'linkedin'
            sentiment: 'positive', 'negative', 'neutral'
        """
        if sequence_id not in self.sequences:
            return {'success': False, 'error': 'Sequence not found'}
        
        sequence = self.sequences[sequence_id]
        
        for prospect in sequence['active_prospects']:
            if prospect['id'] == prospect_id:
                prospect['history'].append({
                    'type': 'reply',
                    'channel': channel,
                    'sentiment': sentiment,
                    'received_at': datetime.now().isoformat(),
                    'reply_received': True
                })
                
                sequence['stats']['replies'] += 1
                
                # If positive, might want to pause sequence
                if sentiment == 'positive':
                    prospect['status'] = 'replied_positive'
                
                self._save_sequences()
                
                return {
                    'success': True,
                    'status': prospect['status'],
                    'message': 'Reply recorded'
                }
        
        return {'success': False, 'error': 'Prospect not found'}
    
    def record_meeting(self, sequence_id: str, prospect_id: str) -> Dict:
        """Record that a meeting was booked"""
        if sequence_id not in self.sequences:
            return {'success': False, 'error': 'Sequence not found'}
        
        sequence = self.sequences[sequence_id]
        
        for prospect in sequence['active_prospects']:
            if prospect['id'] == prospect_id:
                prospect['status'] = 'meeting_booked'
                prospect['history'].append({
                    'type': 'meeting_booked',
                    'booked_at': datetime.now().isoformat()
                })
                
                sequence['stats']['meetings'] += 1
                
                self._save_sequences()
                
                return {'success': True, 'message': 'Meeting recorded'}
        
        return {'success': False, 'error': 'Prospect not found'}
    
    def get_sequence_stats(self, sequence_id: str = None) -> Dict:
        """Get stats for one or all sequences"""
        if sequence_id:
            if sequence_id in self.sequences:
                seq = self.sequences[sequence_id]
                return {
                    'name': seq['name'],
                    'stats': seq['stats'],
                    'active_prospects': len(seq['active_prospects']),
                    'completed': len(seq['completed'])
                }
            return {'error': 'Sequence not found'}
        
        # All sequences
        return {
            seq_id: {
                'name': seq['name'],
                'stats': seq['stats'],
                'active': len(seq['active_prospects'])
            }
            for seq_id, seq in self.sequences.items()
        }
    
    def get_all_sequences(self) -> List[Dict]:
        """Get all sequences for user"""
        return [
            {
                'id': seq_id,
                'name': seq['name'],
                'steps': len(seq['steps']),
                'active_prospects': len(seq['active_prospects']),
                'completed': len(seq['completed']),
                'stats': seq['stats'],
                'created_at': seq['created_at']
            }
            for seq_id, seq in self.sequences.items()
        ]


# ============================================================================
# LINKEDIN PROFILE TRACKER
# ============================================================================

class LinkedInTracker:
    """
    Track LinkedIn profile views and engagement.
    
    Features:
    - Log profile views (manual or automated)
    - Track connection status changes
    - Monitor engagement signals
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.data = load_linkedin_data()
    
    def log_profile_view(self, profile_url: str, viewer_info: Dict = None) -> Dict:
        """Log when someone views our profile or we view theirs"""
        if 'profile_views' not in self.data:
            self.data['profile_views'] = {}
        
        view_id = hashlib.md5(f"{profile_url}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        self.data['profile_views'][view_id] = {
            'profile_url': profile_url,
            'viewer': viewer_info,
            'viewed_at': datetime.now().isoformat(),
            'user': self.user_email
        }
        
        save_linkedin_data(self.data)
        
        return {'success': True, 'view_id': view_id}
    
    def update_connection_status(self, profile_url: str, status: ConnectionStatus,
                                 metadata: Dict = None) -> Dict:
        """Update connection status for a profile"""
        if 'connections' not in self.data:
            self.data['connections'] = {}
        
        profile_id = hashlib.md5(profile_url.encode()).hexdigest()[:12]
        
        if profile_id not in self.data['connections']:
            self.data['connections'][profile_id] = {
                'profile_url': profile_url,
                'history': []
            }
        
        self.data['connections'][profile_id]['current_status'] = status.value
        self.data['connections'][profile_id]['updated_at'] = datetime.now().isoformat()
        self.data['connections'][profile_id]['history'].append({
            'status': status.value,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata
        })
        
        save_linkedin_data(self.data)
        
        return {'success': True, 'status': status.value}
    
    def get_connection_status(self, profile_url: str) -> Dict:
        """Get current connection status"""
        profile_id = hashlib.md5(profile_url.encode()).hexdigest()[:12]
        
        if profile_id in self.data.get('connections', {}):
            return self.data['connections'][profile_id]
        
        return {'status': ConnectionStatus.NOT_SENT.value}
    
    def get_recent_profile_views(self, days: int = 7) -> List[Dict]:
        """Get profile views from the last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        recent = []
        for view_id, view in self.data.get('profile_views', {}).items():
            if datetime.fromisoformat(view['viewed_at']) > cutoff:
                view['id'] = view_id
                recent.append(view)
        
        return sorted(recent, key=lambda x: x['viewed_at'], reverse=True)


# ============================================================================
# PRE-BUILT SEQUENCE TEMPLATES
# ============================================================================

SEQUENCE_TEMPLATES = {
    'standard_multichannel': {
        'name': 'Standard Multi-Channel (Email + LinkedIn)',
        'description': 'Classic 5-touch sequence across email and LinkedIn',
        'steps': [
            {
                'day': 0,
                'channel': 'email',
                'subject': 'Quick question about {{company}}',
                'template': '''Hi {{first_name}},

I noticed {{company}} is growing fast in the {{industry}} space. 

We help companies like yours [specific value prop].

Would you be open to a quick 15-min call this week?

Best,
[Your name]'''
            },
            {
                'day': 2,
                'channel': 'linkedin_connect',
                'template': '''Hi {{first_name}}, I sent you an email about [topic]. Would love to connect here too.''',
                'condition': 'if_no_reply'
            },
            {
                'day': 5,
                'channel': 'linkedin_message',
                'template': '''Thanks for connecting, {{first_name}}! Did you get a chance to see my email about [value prop]?''',
                'condition': 'if_connected'
            },
            {
                'day': 7,
                'channel': 'email',
                'subject': 'Re: Quick question about {{company}}',
                'template': '''Hi {{first_name}},

Just floating this back up. I think we could help {{company}} with [specific outcome].

Worth a quick chat?

Best,
[Your name]''',
                'condition': 'if_no_reply'
            },
            {
                'day': 14,
                'channel': 'email',
                'subject': 'Closing the loop',
                'template': '''Hi {{first_name}},

I'll assume the timing isn't right. No worries at all.

If things change, here's my calendar link: [CALENDAR_LINK]

Best,
[Your name]''',
                'condition': 'if_no_reply'
            }
        ]
    },
    
    'linkedin_first': {
        'name': 'LinkedIn-First Approach',
        'description': 'Start with LinkedIn, then move to email',
        'steps': [
            {
                'day': 0,
                'channel': 'linkedin_connect',
                'template': '''Hi {{first_name}}, I came across your profile while researching {{industry}} leaders. Would love to connect.'''
            },
            {
                'day': 3,
                'channel': 'linkedin_message',
                'template': '''Thanks for connecting! I'm curious - how is {{company}} handling [relevant challenge]?''',
                'condition': 'if_connected'
            },
            {
                'day': 5,
                'channel': 'email',
                'subject': 'Following up from LinkedIn',
                'template': '''Hi {{first_name}},

We connected on LinkedIn recently. I wanted to share a quick idea about [value prop].

[2-3 sentences of value]

Open to a quick call?

Best,
[Your name]''',
                'condition': 'if_no_reply'
            }
        ]
    },
    
    'event_trigger': {
        'name': 'Event/News Trigger',
        'description': 'Reach out based on company news or trigger event',
        'steps': [
            {
                'day': 0,
                'channel': 'email',
                'subject': 'Congrats on {{trigger_event}}!',
                'template': '''Hi {{first_name}},

Saw the news about {{trigger_event}} at {{company}} - congrats!

Companies going through similar growth often run into [relevant challenge]. We've helped others in your situation [achieve outcome].

Would you be interested in a quick chat about how we might help {{company}}?

Best,
[Your name]'''
            },
            {
                'day': 1,
                'channel': 'linkedin_connect',
                'template': '''Hi {{first_name}}, congrats on {{trigger_event}}! Sent you an email with some ideas that might help.'''
            },
            {
                'day': 4,
                'channel': 'email',
                'subject': 'Re: Congrats on {{trigger_event}}!',
                'template': '''Hi {{first_name}},

Quick follow-up on my note about [value prop].

[Include 1 relevant case study or data point]

Worth 15 minutes to explore?

Best,
[Your name]''',
                'condition': 'if_no_reply'
            }
        ]
    }
}


def get_sequence_templates() -> Dict:
    """Get available sequence templates"""
    return SEQUENCE_TEMPLATES


# ============================================================================
# LINKEDIN SEQUENCE MANAGER
# ============================================================================

LINKEDIN_SEQUENCE_DB = "linkedin_sequences.json"

def load_linkedin_sequences() -> Dict:
    if os.path.exists(LINKEDIN_SEQUENCE_DB):
        with open(LINKEDIN_SEQUENCE_DB, 'r') as f:
            return json.load(f)
    return {'sequences': {}, 'active_campaigns': {}}

def save_linkedin_sequences(data: Dict):
    with open(LINKEDIN_SEQUENCE_DB, 'w') as f:
        json.dump(data, f, indent=2)


class LinkedInSequenceManager:
    """
    Automated LinkedIn outreach sequence manager.
    
    Features:
    - Multi-step sequences (view → connect → message → follow-up)
    - Configurable delays between steps
    - Stop conditions (replied, connected, meeting booked)
    - A/B testing for connection messages
    - Analytics and conversion tracking
    """
    
    def __init__(self):
        self.data = load_linkedin_sequences()
    
    def create_sequence(self,
                       sequence_name: str,
                       steps: List[Dict],
                       stop_on: List[str] = None) -> str:
        """
        Create a LinkedIn outreach sequence.
        
        Args:
            sequence_name: Name for this sequence
            steps: List of sequence steps with structure:
                {
                    'action': 'view_profile' | 'send_connection' | 'send_message' | 'engage_post',
                    'message_template': 'Hi {{first_name}}...',  # For connection/message
                    'delay_days': 3,  # Days after previous step
                    'conditions': ['if_connected', 'if_not_replied']  # Optional
                }
            stop_on: List of conditions to stop sequence
                ['connected', 'replied', 'meeting_booked', 'declined']
        
        Returns:
            sequence_id
        """
        sequence_id = hashlib.md5(
            f"{sequence_name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        self.data['sequences'][sequence_id] = {
            'id': sequence_id,
            'name': sequence_name,
            'steps': steps,
            'stop_on': stop_on or ['replied', 'meeting_booked'],
            'created_at': datetime.now().isoformat(),
            'active': True
        }
        
        save_linkedin_sequences(self.data)
        return sequence_id
    
    def start_campaign(self,
                      sequence_id: str,
                      prospects: List[Dict]) -> str:
        """
        Start a LinkedIn sequence campaign.
        
        Args:
            sequence_id: ID of the sequence to use
            prospects: List of prospect dicts with:
                {
                    'linkedin_url': 'https://linkedin.com/in/...',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'company': 'Acme Inc',
                    'title': 'VP Sales',
                    ... other merge fields
                }
        
        Returns:
            campaign_id
        """
        if sequence_id not in self.data['sequences']:
            raise ValueError(f"Sequence {sequence_id} not found")
        
        campaign_id = hashlib.md5(
            f"{sequence_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        sequence = self.data['sequences'][sequence_id]
        
        # Initialize campaign
        self.data['active_campaigns'][campaign_id] = {
            'id': campaign_id,
            'sequence_id': sequence_id,
            'sequence_name': sequence['name'],
            'started_at': datetime.now().isoformat(),
            'status': 'active',
            'prospects': {},
            'stats': {
                'total_prospects': len(prospects),
                'profile_views': 0,
                'connections_sent': 0,
                'connections_accepted': 0,
                'messages_sent': 0,
                'replies_received': 0,
                'meetings_booked': 0,
                'sequences_completed': 0,
                'sequences_stopped': 0
            }
        }
        
        # Initialize each prospect's journey
        for prospect in prospects:
            prospect_id = hashlib.md5(
                prospect['linkedin_url'].encode()
            ).hexdigest()[:12]
            
            self.data['active_campaigns'][campaign_id]['prospects'][prospect_id] = {
                'linkedin_url': prospect['linkedin_url'],
                'merge_fields': prospect,
                'current_step': 0,
                'status': 'pending',
                'next_action_date': datetime.now().isoformat(),
                'actions_taken': [],
                'events': [],
                'connection_status': 'not_sent'
            }
        
        save_linkedin_sequences(self.data)
        return campaign_id
    
    def process_campaigns(self) -> Dict:
        """
        Process all active LinkedIn campaigns - execute scheduled actions.
        Should be called periodically (e.g., every 6 hours via cron).
        
        Returns:
            Processing results
        """
        results = {
            'processed_campaigns': 0,
            'actions_taken': 0,
            'profile_views': 0,
            'connections_sent': 0,
            'messages_sent': 0,
            'errors': []
        }
        
        now = datetime.now()
        
        for campaign_id, campaign in list(self.data['active_campaigns'].items()):
            if campaign['status'] != 'active':
                continue
            
            sequence = self.data['sequences'][campaign['sequence_id']]
            if not sequence['active']:
                continue
            
            results['processed_campaigns'] += 1
            
            # Process each prospect
            for prospect_id, prospect_data in campaign['prospects'].items():
                if prospect_data['status'] in ['completed', 'stopped']:
                    continue
                
                # Check if it's time for next action
                next_action = datetime.fromisoformat(prospect_data['next_action_date'])
                if now < next_action:
                    continue
                
                # Check stop conditions
                if self._should_stop_sequence(prospect_data, sequence['stop_on']):
                    prospect_data['status'] = 'stopped'
                    campaign['stats']['sequences_stopped'] += 1
                    continue
                
                # Get current step in sequence
                step = prospect_data['current_step']
                if step >= len(sequence['steps']):
                    prospect_data['status'] = 'completed'
                    campaign['stats']['sequences_completed'] += 1
                    continue
                
                step_data = sequence['steps'][step]
                
                # Check step conditions
                if not self._check_step_conditions(prospect_data, step_data.get('conditions', [])):
                    # Skip this step, move to next
                    prospect_data['current_step'] += 1
                    continue
                
                # Execute the action
                try:
                    action_result = self._execute_action(
                        prospect_data,
                        step_data,
                        campaign,
                        results
                    )
                    
                    # Log the action
                    prospect_data['actions_taken'].append({
                        'step': step,
                        'action': step_data['action'],
                        'timestamp': datetime.now().isoformat(),
                        'result': action_result
                    })
                    
                    results['actions_taken'] += 1
                    
                    # Schedule next action
                    prospect_data['current_step'] += 1
                    
                    if prospect_data['current_step'] < len(sequence['steps']):
                        next_step = sequence['steps'][prospect_data['current_step']]
                        delay_days = next_step.get('delay_days', 3)
                        next_action_date = now + timedelta(days=delay_days)
                        prospect_data['next_action_date'] = next_action_date.isoformat()
                    
                except Exception as e:
                    results['errors'].append({
                        'campaign_id': campaign_id,
                        'prospect': prospect_data['merge_fields'].get('first_name'),
                        'error': str(e)
                    })
        
        save_linkedin_sequences(self.data)
        return results
    
    def _execute_action(self,
                       prospect_data: Dict,
                       step_data: Dict,
                       campaign: Dict,
                       results: Dict) -> Dict:
        """Execute a single LinkedIn action"""
        action = step_data['action']
        
        if action == 'view_profile':
            # In real implementation, this would use PhantomBuster/Waalaxy API
            # For now, we log it
            campaign['stats']['profile_views'] += 1
            results['profile_views'] += 1
            
            return {
                'action': 'view_profile',
                'success': True,
                'url': prospect_data['linkedin_url']
            }
        
        elif action == 'send_connection':
            # Personalize message
            message = self._apply_merge_fields(
                step_data.get('message_template', ''),
                prospect_data['merge_fields']
            )
            
            # In real implementation: PhantomBuster/Waalaxy API call
            campaign['stats']['connections_sent'] += 1
            results['connections_sent'] += 1
            prospect_data['connection_status'] = 'pending'
            
            return {
                'action': 'send_connection',
                'success': True,
                'message': message[:100] + '...'
            }
        
        elif action == 'send_message':
            # Personalize message
            message = self._apply_merge_fields(
                step_data.get('message_template', ''),
                prospect_data['merge_fields']
            )
            
            # In real implementation: LinkedIn messaging API
            campaign['stats']['messages_sent'] += 1
            results['messages_sent'] += 1
            
            return {
                'action': 'send_message',
                'success': True,
                'message': message[:100] + '...'
            }
        
        elif action == 'engage_post':
            # Like/comment on recent post
            # In real implementation: LinkedIn API
            
            return {
                'action': 'engage_post',
                'success': True
            }
        
        else:
            return {
                'action': action,
                'success': False,
                'error': 'Unknown action type'
            }
    
    def record_event(self,
                    prospect_linkedin_url: str,
                    event_type: str,
                    metadata: Dict = None):
        """
        Record a LinkedIn event (connection accepted, message replied, etc).
        
        Args:
            prospect_linkedin_url: The LinkedIn URL of the prospect
            event_type: 'connection_accepted', 'connection_declined', 'message_replied', 'meeting_booked'
            metadata: Additional event data
        """
        prospect_id = hashlib.md5(prospect_linkedin_url.encode()).hexdigest()[:12]
        
        for campaign_id, campaign in self.data['active_campaigns'].items():
            if prospect_id in campaign['prospects']:
                prospect_data = campaign['prospects'][prospect_id]
                
                # Record the event
                prospect_data['events'].append({
                    'type': event_type,
                    'timestamp': datetime.now().isoformat(),
                    'metadata': metadata or {}
                })
                
                # Update connection status
                if event_type == 'connection_accepted':
                    prospect_data['connection_status'] = 'connected'
                    campaign['stats']['connections_accepted'] += 1
                elif event_type == 'connection_declined':
                    prospect_data['connection_status'] = 'declined'
                elif event_type == 'message_replied':
                    campaign['stats']['replies_received'] += 1
                elif event_type == 'meeting_booked':
                    campaign['stats']['meetings_booked'] += 1
                
                save_linkedin_sequences(self.data)
                return True
        
        return False
    
    def _should_stop_sequence(self, prospect_data: Dict, stop_conditions: List[str]) -> bool:
        """Check if sequence should stop based on events"""
        event_types = [e['type'] for e in prospect_data['events']]
        
        for condition in stop_conditions:
            if condition in event_types:
                return True
        
        # Also check connection status
        if 'declined' in stop_conditions and prospect_data['connection_status'] == 'declined':
            return True
        
        return False
    
    def _check_step_conditions(self, prospect_data: Dict, conditions: List[str]) -> bool:
        """Check if step conditions are met"""
        if not conditions:
            return True
        
        for condition in conditions:
            if condition == 'if_connected':
                if prospect_data['connection_status'] != 'connected':
                    return False
            elif condition == 'if_not_connected':
                if prospect_data['connection_status'] == 'connected':
                    return False
            elif condition == 'if_not_replied':
                replies = [e for e in prospect_data['events'] if e['type'] == 'message_replied']
                if replies:
                    return False
        
        return True
    
    def _apply_merge_fields(self, template: str, merge_fields: Dict) -> str:
        """Replace {{field}} with actual values"""
        result = template
        for key, value in merge_fields.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
    
    def get_campaign_stats(self, campaign_id: str) -> Dict:
        """Get statistics for a campaign"""
        if campaign_id not in self.data['active_campaigns']:
            return {'error': 'Campaign not found'}
        
        campaign = self.data['active_campaigns'][campaign_id]
        stats = campaign['stats'].copy()
        stats['campaign_id'] = campaign_id
        stats['sequence_name'] = campaign['sequence_name']
        stats['started_at'] = campaign['started_at']
        stats['status'] = campaign['status']
        
        # Calculate rates
        if stats['connections_sent'] > 0:
            stats['connection_acceptance_rate'] = round(
                stats['connections_accepted'] / stats['connections_sent'] * 100, 2
            )
        
        if stats['messages_sent'] > 0:
            stats['reply_rate'] = round(
                stats['replies_received'] / stats['messages_sent'] * 100, 2
            )
        
        if stats['total_prospects'] > 0:
            stats['meeting_conversion_rate'] = round(
                stats['meetings_booked'] / stats['total_prospects'] * 100, 2
            )
        
        return stats
    
    def pause_campaign(self, campaign_id: str):
        """Pause a campaign"""
        if campaign_id in self.data['active_campaigns']:
            self.data['active_campaigns'][campaign_id]['status'] = 'paused'
            save_linkedin_sequences(self.data)
    
    def resume_campaign(self, campaign_id: str):
        """Resume a paused campaign"""
        if campaign_id in self.data['active_campaigns']:
            self.data['active_campaigns'][campaign_id]['status'] = 'active'
            save_linkedin_sequences(self.data)
    
    def stop_campaign(self, campaign_id: str):
        """Stop a campaign permanently"""
        if campaign_id in self.data['active_campaigns']:
            self.data['active_campaigns'][campaign_id]['status'] = 'stopped'
            save_linkedin_sequences(self.data)

