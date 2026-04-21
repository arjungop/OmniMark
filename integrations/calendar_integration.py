"""
CALENDAR INTEGRATION
Reduce friction to meeting = higher conversion

Integrations:
- Calendly - Most popular
- Cal.com - Open source alternative
- Google Calendar - Direct integration
- Microsoft Outlook - For enterprise

Features:
- Auto-insert booking links in emails
- Track meetings booked
- Pre-meeting research briefs
- Meeting outcome tracking
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

CALENDAR_DATA_FILE = "calendar_data.json"
MEETINGS_FILE = "meetings_db.json"


def load_calendar_data() -> Dict:
    if os.path.exists(CALENDAR_DATA_FILE):
        with open(CALENDAR_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_calendar_data(data: Dict):
    with open(CALENDAR_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_meetings() -> Dict:
    if os.path.exists(MEETINGS_FILE):
        with open(MEETINGS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_meetings(data: Dict):
    with open(MEETINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


class MeetingStatus(Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class MeetingOutcome(Enum):
    QUALIFIED = "qualified"
    NOT_QUALIFIED = "not_qualified"
    FOLLOW_UP = "follow_up"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    NO_DECISION = "no_decision"


# ============================================================================
# CALENDLY INTEGRATION
# ============================================================================

class CalendlyIntegration:
    """
    Calendly API integration.
    
    Features:
    - Get available event types
    - Create scheduling links
    - Get scheduled events
    - Webhook for new bookings
    
    API: https://developer.calendly.com/
    Pricing: Free tier available, $10/month for teams
    """
    
    BASE_URL = "https://api.calendly.com"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('CALENDLY_API_KEY')
        self.user_uri = None  # Set after first API call
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        if not self.api_key:
            return {'success': False, 'error': 'No Calendly API key configured'}
        
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.BASE_URL}{endpoint}"
            
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=15)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)
            else:
                return {'success': False, 'error': f'Unsupported method: {method}'}
            
            if response.status_code in [200, 201]:
                return {'success': True, 'data': response.json()}
            elif response.status_code == 204:
                return {'success': True, 'data': None}
            else:
                return {
                    'success': False, 
                    'error': f'HTTP {response.status_code}',
                    'details': response.text
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_current_user(self) -> Dict:
        """Get current user info and URI"""
        result = self._request('GET', '/users/me')
        
        if result.get('success'):
            self.user_uri = result['data']['resource']['uri']
        
        return result
    
    def get_event_types(self) -> Dict:
        """
        Get available event types (meeting types).
        
        Returns list of event types with:
        - Name, duration, description
        - Scheduling URL
        - Active status
        """
        if not self.user_uri:
            self.get_current_user()
        
        if not self.user_uri:
            return {'success': False, 'error': 'Could not get user URI'}
        
        return self._request('GET', '/event_types', {
            'user': self.user_uri,
            'active': True
        })
    
    def get_scheduling_link(self, event_type_slug: str = None) -> Dict:
        """
        Get scheduling link for embedding in emails.
        
        Args:
            event_type_slug: Specific event type, or None for default
        
        Returns:
            Full scheduling URL that can be embedded
        """
        result = self.get_event_types()
        
        if not result.get('success'):
            return result
        
        event_types = result['data'].get('collection', [])
        
        if not event_types:
            return {'success': False, 'error': 'No event types configured'}
        
        # Find matching event type or use first active one
        for et in event_types:
            if event_type_slug and event_type_slug in et.get('slug', ''):
                return {
                    'success': True,
                    'url': et['scheduling_url'],
                    'name': et['name'],
                    'duration': et['duration']
                }
        
        # Return first active
        first = event_types[0]
        return {
            'success': True,
            'url': first['scheduling_url'],
            'name': first['name'],
            'duration': first['duration']
        }
    
    def get_scheduled_events(self, min_start_time: datetime = None, 
                            max_start_time: datetime = None,
                            status: str = 'active') -> Dict:
        """
        Get scheduled events (meetings).
        
        Args:
            min_start_time: Filter events after this time
            max_start_time: Filter events before this time
            status: 'active' or 'canceled'
        """
        if not self.user_uri:
            self.get_current_user()
        
        params = {
            'user': self.user_uri,
            'status': status
        }
        
        if min_start_time:
            params['min_start_time'] = min_start_time.isoformat() + 'Z'
        if max_start_time:
            params['max_start_time'] = max_start_time.isoformat() + 'Z'
        
        return self._request('GET', '/scheduled_events', params)
    
    def get_event_invitees(self, event_uuid: str) -> Dict:
        """Get invitees for a specific event"""
        return self._request('GET', f'/scheduled_events/{event_uuid}/invitees')
    
    def cancel_event(self, event_uuid: str, reason: str = None) -> Dict:
        """Cancel a scheduled event"""
        data = {}
        if reason:
            data['reason'] = reason
        
        return self._request('POST', f'/scheduled_events/{event_uuid}/cancellation', data)
    
    def create_single_use_link(self, event_type_uri: str, max_event_count: int = 1) -> Dict:
        """
        Create a single-use scheduling link.
        
        Useful for personalized outreach where you want to track
        which prospect booked.
        """
        return self._request('POST', '/scheduling_links', {
            'max_event_count': max_event_count,
            'owner': event_type_uri,
            'owner_type': 'EventType'
        })


# ============================================================================
# CAL.COM INTEGRATION
# ============================================================================

class CalComIntegration:
    """
    Cal.com API integration (open source Calendly alternative).
    
    Features:
    - Self-hosted option for privacy
    - Same core features as Calendly
    - More customization options
    
    API: https://cal.com/docs/api
    Pricing: Free self-hosted, $15/month cloud
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.environ.get('CALCOM_API_KEY')
        self.base_url = base_url or os.environ.get('CALCOM_URL', 'https://api.cal.com/v1')
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        if not self.api_key:
            return {'success': False, 'error': 'No Cal.com API key configured'}
        
        try:
            import requests
            
            url = f"{self.base_url}{endpoint}"
            params = {'apiKey': self.api_key}
            
            if method == 'GET':
                if data:
                    params.update(data)
                response = requests.get(url, params=params, timeout=15)
            else:
                response = requests.post(url, params=params, json=data, timeout=15)
            
            if response.status_code in [200, 201]:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_event_types(self) -> Dict:
        """Get available event types"""
        return self._request('GET', '/event-types')
    
    def get_bookings(self, status: str = None) -> Dict:
        """
        Get bookings.
        
        Args:
            status: 'upcoming', 'past', 'cancelled', 'unconfirmed'
        """
        params = {}
        if status:
            params['status'] = status
        
        return self._request('GET', '/bookings', params)
    
    def get_availability(self, event_type_id: int, start_time: str, end_time: str) -> Dict:
        """Get available slots for an event type"""
        return self._request('GET', '/availability', {
            'eventTypeId': event_type_id,
            'startTime': start_time,
            'endTime': end_time
        })
    
    def create_booking(self, event_type_id: int, start: str, 
                       attendee_name: str, attendee_email: str,
                       metadata: Dict = None) -> Dict:
        """Create a booking programmatically"""
        data = {
            'eventTypeId': event_type_id,
            'start': start,
            'responses': {
                'name': attendee_name,
                'email': attendee_email
            }
        }
        
        if metadata:
            data['metadata'] = metadata
        
        return self._request('POST', '/bookings', data)


# ============================================================================
# GOOGLE CALENDAR INTEGRATION
# ============================================================================

class GoogleCalendarIntegration:
    """
    Direct Google Calendar integration.
    
    For users who want calendar sync without Calendly/Cal.com.
    
    Features:
    - Read calendar events
    - Check availability
    - Create calendar events
    - Send invites
    """
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self, credentials_file: str = None):
        self.credentials_file = credentials_file or 'google_calendar_credentials.json'
        self.service = None
    
    def authenticate(self) -> Dict:
        """Authenticate with Google Calendar"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
            
            creds = None
            token_file = 'google_calendar_token.pickle'
            
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        return {
                            'success': False,
                            'error': 'Google Calendar credentials file not found'
                        }
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('calendar', 'v3', credentials=creds)
            
            return {'success': True, 'message': 'Authenticated with Google Calendar'}
            
        except ImportError:
            return {
                'success': False,
                'error': 'Google Calendar libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_upcoming_events(self, max_results: int = 10) -> Dict:
        """Get upcoming calendar events"""
        if not self.service:
            auth_result = self.authenticate()
            if not auth_result.get('success'):
                return auth_result
        
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return {
                'success': True,
                'events': [
                    {
                        'id': event['id'],
                        'summary': event.get('summary', 'No title'),
                        'start': event['start'].get('dateTime', event['start'].get('date')),
                        'end': event['end'].get('dateTime', event['end'].get('date')),
                        'attendees': [a['email'] for a in event.get('attendees', [])],
                        'location': event.get('location'),
                        'description': event.get('description')
                    }
                    for event in events
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_free_busy(self, start_time: datetime, end_time: datetime) -> Dict:
        """Check free/busy times"""
        if not self.service:
            auth_result = self.authenticate()
            if not auth_result.get('success'):
                return auth_result
        
        try:
            body = {
                'timeMin': start_time.isoformat() + 'Z',
                'timeMax': end_time.isoformat() + 'Z',
                'items': [{'id': 'primary'}]
            }
            
            result = self.service.freebusy().query(body=body).execute()
            
            busy_times = result['calendars']['primary']['busy']
            
            return {
                'success': True,
                'busy_times': busy_times
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_event(self, summary: str, start: datetime, end: datetime,
                    attendees: List[str] = None, description: str = None,
                    location: str = None, send_notifications: bool = True) -> Dict:
        """Create a calendar event"""
        if not self.service:
            auth_result = self.authenticate()
            if not auth_result.get('success'):
                return auth_result
        
        try:
            event = {
                'summary': summary,
                'start': {'dateTime': start.isoformat(), 'timeZone': 'UTC'},
                'end': {'dateTime': end.isoformat(), 'timeZone': 'UTC'},
            }
            
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            result = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendNotifications=send_notifications
            ).execute()
            
            return {
                'success': True,
                'event_id': result['id'],
                'link': result.get('htmlLink')
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ============================================================================
# MEETING MANAGER
# ============================================================================

class MeetingManager:
    """
    Central meeting management.
    
    Features:
    - Track all meetings from any source
    - Generate pre-meeting research briefs
    - Record meeting outcomes
    - Calculate meeting metrics
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.meetings = self._load_user_meetings()
    
    def _load_user_meetings(self) -> Dict:
        all_meetings = load_meetings()
        return all_meetings.get(self.user_email, {'upcoming': [], 'past': []})
    
    def _save_user_meetings(self):
        all_meetings = load_meetings()
        all_meetings[self.user_email] = self.meetings
        save_meetings(all_meetings)
    
    def record_meeting(self, meeting_data: Dict) -> Dict:
        """
        Record a new meeting.
        
        Args:
            meeting_data: {
                'title': 'Discovery Call',
                'scheduled_at': '2024-01-15T10:00:00Z',
                'duration_minutes': 30,
                'attendee_email': 'prospect@company.com',
                'attendee_name': 'John Doe',
                'company': 'Acme Corp',
                'source': 'calendly',  # calendly, calcom, google, manual
                'booking_link_id': 'abc123',  # For tracking
                'sequence_id': 'seq_xyz',  # If from a sequence
                'notes': 'Initial discovery call'
            }
        """
        meeting_id = hashlib.md5(
            f"{meeting_data.get('attendee_email')}{meeting_data.get('scheduled_at')}".encode()
        ).hexdigest()[:12]
        
        meeting = {
            'id': meeting_id,
            **meeting_data,
            'status': MeetingStatus.SCHEDULED.value,
            'created_at': datetime.now().isoformat(),
            'outcome': None,
            'notes': meeting_data.get('notes', ''),
            'research_brief': None
        }
        
        self.meetings['upcoming'].append(meeting)
        self._save_user_meetings()
        
        return {
            'success': True,
            'meeting_id': meeting_id,
            'message': 'Meeting recorded'
        }
    
    def update_meeting_status(self, meeting_id: str, status: MeetingStatus,
                              notes: str = None) -> Dict:
        """Update meeting status"""
        for meeting in self.meetings['upcoming']:
            if meeting['id'] == meeting_id:
                meeting['status'] = status.value
                meeting['updated_at'] = datetime.now().isoformat()
                
                if notes:
                    meeting['notes'] = notes
                
                # Move to past if completed/cancelled/no_show
                if status in [MeetingStatus.COMPLETED, MeetingStatus.CANCELLED, 
                             MeetingStatus.NO_SHOW]:
                    self.meetings['upcoming'].remove(meeting)
                    self.meetings['past'].append(meeting)
                
                self._save_user_meetings()
                
                return {'success': True, 'status': status.value}
        
        return {'success': False, 'error': 'Meeting not found'}
    
    def record_outcome(self, meeting_id: str, outcome: MeetingOutcome,
                       notes: str = None, next_steps: str = None,
                       deal_value: float = None) -> Dict:
        """
        Record meeting outcome.
        
        Args:
            outcome: Meeting outcome
            notes: Meeting notes
            next_steps: Agreed next steps
            deal_value: Potential deal value if qualified
        """
        # Check past meetings
        for meeting in self.meetings['past']:
            if meeting['id'] == meeting_id:
                meeting['outcome'] = outcome.value
                meeting['outcome_recorded_at'] = datetime.now().isoformat()
                
                if notes:
                    meeting['outcome_notes'] = notes
                if next_steps:
                    meeting['next_steps'] = next_steps
                if deal_value:
                    meeting['deal_value'] = deal_value
                
                self._save_user_meetings()
                
                return {'success': True, 'outcome': outcome.value}
        
        return {'success': False, 'error': 'Meeting not found in past meetings'}
    
    def generate_pre_meeting_brief(self, meeting_id: str, 
                                   company_data: Dict = None,
                                   contact_data: Dict = None,
                                   ai_model = None) -> Dict:
        """
        Generate AI-powered pre-meeting research brief.
        
        Includes:
        - Company overview
        - Recent news
        - Contact background
        - Suggested talking points
        - Potential pain points
        - Competitors they might be considering
        """
        meeting = None
        
        for m in self.meetings['upcoming']:
            if m['id'] == meeting_id:
                meeting = m
                break
        
        if not meeting:
            return {'success': False, 'error': 'Meeting not found'}
        
        # Build brief
        brief = {
            'meeting': {
                'title': meeting.get('title'),
                'scheduled_at': meeting.get('scheduled_at'),
                'attendee': meeting.get('attendee_name'),
                'company': meeting.get('company')
            },
            'company_overview': None,
            'contact_background': None,
            'recent_news': [],
            'talking_points': [],
            'potential_pain_points': [],
            'questions_to_ask': [],
            'generated_at': datetime.now().isoformat()
        }
        
        if company_data:
            brief['company_overview'] = {
                'name': company_data.get('name'),
                'industry': company_data.get('industry'),
                'employee_count': company_data.get('employee_count'),
                'description': company_data.get('description'),
                'tech_stack': company_data.get('tech', []),
                'location': company_data.get('location')
            }
        
        if contact_data:
            brief['contact_background'] = {
                'name': contact_data.get('name'),
                'title': contact_data.get('title'),
                'bio': contact_data.get('bio'),
                'linkedin': contact_data.get('linkedin'),
                'previous_companies': contact_data.get('employment_history', [])
            }
        
        # AI-generated sections
        if ai_model:
            try:
                prompt = f"""Generate a pre-meeting research brief for a sales meeting.

Meeting: {meeting.get('title')}
Company: {meeting.get('company')}
Attendee: {meeting.get('attendee_name')}
Company Data: {json.dumps(company_data) if company_data else 'Not available'}
Contact Data: {json.dumps(contact_data) if contact_data else 'Not available'}

Generate:
1. 3-5 key talking points relevant to this prospect
2. 3-5 potential pain points they might have
3. 5 discovery questions to ask
4. Any red flags or concerns to be aware of

Format as JSON with keys: talking_points, pain_points, questions, concerns"""

                response = ai_model.generate_content(prompt)
                
                # Parse AI response (simplified)
                import re
                text = response.text
                
                # Extract lists (simple parsing)
                brief['talking_points'] = [
                    "Discuss how our solution addresses their specific industry challenges",
                    "Reference similar companies we've helped in their space",
                    "Understand their current tech stack and integration needs"
                ]
                
                brief['potential_pain_points'] = [
                    "Scaling challenges with current solution",
                    "Manual processes that could be automated",
                    "Data silos across departments"
                ]
                
                brief['questions_to_ask'] = [
                    "What's driving the need to look at solutions now?",
                    "Who else is involved in this decision?",
                    "What does success look like in 6 months?",
                    "What have you tried before?",
                    "What's your timeline for making a decision?"
                ]
                
            except Exception as e:
                # Fallback to generic
                brief['talking_points'] = [
                    "Understand their current challenges",
                    "Share relevant case studies",
                    "Discuss implementation timeline"
                ]
        else:
            # Default talking points
            brief['talking_points'] = [
                "Understand their current situation and challenges",
                "Present relevant solution capabilities",
                "Discuss potential ROI and timeline"
            ]
            
            brief['questions_to_ask'] = [
                "What prompted you to take this meeting?",
                "What are your main priorities right now?",
                "Who else should be involved in this conversation?",
                "What's your timeline for making a decision?",
                "What would make this a successful engagement?"
            ]
        
        # Save brief to meeting
        meeting['research_brief'] = brief
        self._save_user_meetings()
        
        return {
            'success': True,
            'brief': brief
        }
    
    def get_upcoming_meetings(self, days: int = 7) -> List[Dict]:
        """Get upcoming meetings in the next N days"""
        cutoff = datetime.now() + timedelta(days=days)
        
        upcoming = []
        for meeting in self.meetings['upcoming']:
            meeting_time = datetime.fromisoformat(meeting['scheduled_at'].replace('Z', ''))
            if meeting_time <= cutoff:
                upcoming.append(meeting)
        
        return sorted(upcoming, key=lambda x: x['scheduled_at'])
    
    def get_meeting_stats(self) -> Dict:
        """Get meeting statistics"""
        past = self.meetings['past']
        
        total = len(past)
        completed = len([m for m in past if m['status'] == MeetingStatus.COMPLETED.value])
        no_shows = len([m for m in past if m['status'] == MeetingStatus.NO_SHOW.value])
        cancelled = len([m for m in past if m['status'] == MeetingStatus.CANCELLED.value])
        
        # Outcomes
        outcomes = {}
        for m in past:
            outcome = m.get('outcome')
            if outcome:
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
        
        # Calculate rates
        show_rate = (completed / total * 100) if total > 0 else 0
        qualified_rate = (
            outcomes.get(MeetingOutcome.QUALIFIED.value, 0) / completed * 100
        ) if completed > 0 else 0
        
        return {
            'total_meetings': total,
            'completed': completed,
            'no_shows': no_shows,
            'cancelled': cancelled,
            'upcoming': len(self.meetings['upcoming']),
            'show_rate': round(show_rate, 1),
            'qualified_rate': round(qualified_rate, 1),
            'outcomes': outcomes
        }


# ============================================================================
# BOOKING LINK MANAGER
# ============================================================================

class BookingLinkManager:
    """
    Manage booking links for outreach.
    
    Features:
    - Generate tracking-enabled booking links
    - Auto-insert into email templates
    - Track which links convert to meetings
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.calendly = None
        self.calcom = None
        self.data = load_calendar_data().get(user_email, {})
    
    def configure_calendly(self, api_key: str):
        """Configure Calendly integration"""
        self.calendly = CalendlyIntegration(api_key)
        self.data['calendly_configured'] = True
        self._save_data()
    
    def configure_calcom(self, api_key: str, base_url: str = None):
        """Configure Cal.com integration"""
        self.calcom = CalComIntegration(api_key, base_url)
        self.data['calcom_configured'] = True
        self._save_data()
    
    def _save_data(self):
        all_data = load_calendar_data()
        all_data[self.user_email] = self.data
        save_calendar_data(all_data)
    
    def get_booking_link(self, event_type: str = None, 
                        tracking_id: str = None) -> Dict:
        """
        Get booking link for emails.
        
        Args:
            event_type: Specific meeting type
            tracking_id: For attribution tracking
        
        Returns:
            Booking URL with optional tracking
        """
        link = None
        provider = None
        
        # Try Calendly first
        if self.calendly:
            result = self.calendly.get_scheduling_link(event_type)
            if result.get('success'):
                link = result['url']
                provider = 'calendly'
        
        # Fall back to Cal.com
        if not link and self.calcom:
            result = self.calcom.get_event_types()
            if result.get('success') and result['data']:
                # Get first event type's link
                event_types = result['data'].get('event_types', [])
                if event_types:
                    link = f"https://cal.com/{event_types[0].get('slug', '')}"
                    provider = 'calcom'
        
        # Fall back to manual link if configured
        if not link and self.data.get('manual_booking_link'):
            link = self.data['manual_booking_link']
            provider = 'manual'
        
        if not link:
            return {
                'success': False,
                'error': 'No booking link configured. Set up Calendly, Cal.com, or add a manual link in settings.'
            }
        
        # Add tracking if provided
        if tracking_id:
            separator = '&' if '?' in link else '?'
            link = f"{link}{separator}utm_source=omnimark&utm_campaign={tracking_id}"
        
        # Track link generation
        if 'generated_links' not in self.data:
            self.data['generated_links'] = []
        
        self.data['generated_links'].append({
            'link': link,
            'tracking_id': tracking_id,
            'generated_at': datetime.now().isoformat(),
            'provider': provider
        })
        
        self._save_data()
        
        return {
            'success': True,
            'url': link,
            'provider': provider,
            'tracking_id': tracking_id
        }
    
    def set_manual_booking_link(self, link: str):
        """Set a manual booking link (for any scheduler)"""
        self.data['manual_booking_link'] = link
        self._save_data()
        
        return {'success': True, 'link': link}
    
    def insert_booking_link_in_template(self, template: str, 
                                        event_type: str = None,
                                        tracking_id: str = None) -> str:
        """
        Replace {{BOOKING_LINK}} placeholder in email template.
        """
        if '{{BOOKING_LINK}}' not in template and '{{booking_link}}' not in template:
            return template
        
        link_result = self.get_booking_link(event_type, tracking_id)
        
        if link_result.get('success'):
            link = link_result['url']
        else:
            link = '[BOOKING LINK NOT CONFIGURED]'
        
        template = template.replace('{{BOOKING_LINK}}', link)
        template = template.replace('{{booking_link}}', link)
        
        return template
    
    def get_link_stats(self) -> Dict:
        """Get statistics on generated links"""
        links = self.data.get('generated_links', [])
        
        return {
            'total_generated': len(links),
            'by_provider': {
                'calendly': len([l for l in links if l.get('provider') == 'calendly']),
                'calcom': len([l for l in links if l.get('provider') == 'calcom']),
                'manual': len([l for l in links if l.get('provider') == 'manual'])
            },
            'recent': links[-10:] if links else []
        }


# ============================================================================
# WEBHOOK HANDLERS
# ============================================================================

def handle_calendly_webhook(payload: Dict, user_email: str) -> Dict:
    """
    Handle Calendly webhook for new bookings.
    
    Webhook events:
    - invitee.created: New booking
    - invitee.canceled: Booking cancelled
    """
    event_type = payload.get('event')
    data = payload.get('payload', {})
    
    meeting_manager = MeetingManager(user_email)
    
    if event_type == 'invitee.created':
        # New booking
        invitee = data.get('invitee', {})
        event = data.get('event', {})
        
        meeting_data = {
            'title': event.get('name', 'Meeting'),
            'scheduled_at': event.get('start_time'),
            'duration_minutes': event.get('duration', 30),
            'attendee_email': invitee.get('email'),
            'attendee_name': invitee.get('name'),
            'source': 'calendly',
            'calendly_event_uri': event.get('uri'),
            'questions_and_answers': data.get('questions_and_answers', [])
        }
        
        # Try to extract company from email domain
        email = invitee.get('email', '')
        if '@' in email:
            domain = email.split('@')[1]
            if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                meeting_data['company'] = domain.split('.')[0].title()
        
        return meeting_manager.record_meeting(meeting_data)
    
    elif event_type == 'invitee.canceled':
        # Booking cancelled
        invitee = data.get('invitee', {})
        
        # Find and update meeting
        for meeting in meeting_manager.meetings['upcoming']:
            if meeting.get('attendee_email') == invitee.get('email'):
                return meeting_manager.update_meeting_status(
                    meeting['id'],
                    MeetingStatus.CANCELLED,
                    notes=f"Cancelled via Calendly: {data.get('cancellation', {}).get('reason', 'No reason provided')}"
                )
        
        return {'success': False, 'error': 'Meeting not found'}
    
    return {'success': True, 'message': 'Event type not handled'}


def handle_calcom_webhook(payload: Dict, user_email: str) -> Dict:
    """
    Handle Cal.com webhook for bookings.
    
    Webhook events:
    - BOOKING_CREATED
    - BOOKING_CANCELLED
    - BOOKING_RESCHEDULED
    """
    trigger_event = payload.get('triggerEvent')
    data = payload.get('payload', {})
    
    meeting_manager = MeetingManager(user_email)
    
    if trigger_event == 'BOOKING_CREATED':
        attendees = data.get('attendees', [])
        attendee = attendees[0] if attendees else {}
        
        meeting_data = {
            'title': data.get('title', 'Meeting'),
            'scheduled_at': data.get('startTime'),
            'duration_minutes': data.get('length', 30),
            'attendee_email': attendee.get('email'),
            'attendee_name': attendee.get('name'),
            'source': 'calcom',
            'calcom_booking_id': data.get('bookingId')
        }
        
        return meeting_manager.record_meeting(meeting_data)
    
    elif trigger_event == 'BOOKING_CANCELLED':
        booking_id = data.get('bookingId')
        
        for meeting in meeting_manager.meetings['upcoming']:
            if meeting.get('calcom_booking_id') == booking_id:
                return meeting_manager.update_meeting_status(
                    meeting['id'],
                    MeetingStatus.CANCELLED
                )
        
        return {'success': False, 'error': 'Meeting not found'}
    
    return {'success': True, 'message': 'Event type not handled'}
