"""
REAL-TIME EVENT TRACKING & WEBHOOKS
Event-driven architecture for instant updates and triggers.

Features:
- Email event tracking (opens, clicks, replies)
- LinkedIn event tracking (connections, messages, replies)
- Webhook handlers for external integrations
- Real-time notifications
- Automatic sequence control (stop on reply, etc.)
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Callable
from flask import request, jsonify


# ============================================================================
# EVENT STORAGE
# ============================================================================

EVENTS_DB = "events_db.json"

def load_events() -> Dict:
    if os.path.exists(EVENTS_DB):
        with open(EVENTS_DB, 'r') as f:
            return json.load(f)
    return {'events': [], 'handlers': {}}

def save_events(data: Dict):
    with open(EVENTS_DB, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# EVENT TRACKER
# ============================================================================

class EventTracker:
    """
    Central event tracking and webhook system.
    All events flow through here.
    """
    
    EVENT_TYPES = {
        # Email events
        'email.sent': 'Email was sent',
        'email.delivered': 'Email was delivered',
        'email.opened': 'Email was opened',
        'email.clicked': 'Link in email was clicked',
        'email.replied': 'Recipient replied to email',
        'email.bounced': 'Email bounced',
        'email.unsubscribed': 'Recipient unsubscribed',
        
        # LinkedIn events
        'linkedin.profile_viewed': 'Profile was viewed',
        'linkedin.connection_sent': 'Connection request sent',
        'linkedin.connection_accepted': 'Connection request accepted',
        'linkedin.connection_declined': 'Connection request declined',
        'linkedin.message_sent': 'LinkedIn message sent',
        'linkedin.message_replied': 'Recipient replied on LinkedIn',
        
        # Meeting events
        'meeting.scheduled': 'Meeting was scheduled',
        'meeting.completed': 'Meeting was completed',
        'meeting.cancelled': 'Meeting was cancelled',
        'meeting.no_show': 'No-show for meeting',
        
        # Deal events
        'deal.created': 'Deal/opportunity created',
        'deal.stage_changed': 'Deal stage changed',
        'deal.won': 'Deal was won',
        'deal.lost': 'Deal was lost',
    }
    
    def __init__(self):
        self.data = load_events()
        self.handlers = {}  # In-memory event handlers
    
    def track_event(self,
                   event_type: str,
                   data: Dict,
                   user_email: str = None) -> str:
        """
        Track an event and trigger handlers.
        
        Args:
            event_type: Type of event (e.g., 'email.opened')
            data: Event data (varies by type)
            user_email: User associated with event
        
        Returns:
            event_id
        """
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")
        
        event_id = hashlib.md5(
            f"{event_type}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        event = {
            'id': event_id,
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'user_email': user_email,
            'data': data,
            'processed': False
        }
        
        self.data['events'].append(event)
        save_events(self.data)
        
        # Trigger handlers
        self._trigger_handlers(event)
        
        return event_id
    
    def _trigger_handlers(self, event: Dict):
        """Trigger registered handlers for this event type"""
        event_type = event['type']
        
        # Built-in handlers
        if event_type == 'email.replied':
            self._handle_email_reply(event)
        elif event_type == 'email.clicked':
            self._handle_email_click(event)
        elif event_type == 'email.opened':
            self._handle_email_open(event)
        elif event_type == 'linkedin.connection_accepted':
            self._handle_connection_accepted(event)
        elif event_type == 'linkedin.message_replied':
            self._handle_linkedin_reply(event)
        elif event_type == 'meeting.scheduled':
            self._handle_meeting_scheduled(event)
        
        # Custom handlers
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Handler error: {e}")
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register a custom event handler"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    # ========================================================================
    # BUILT-IN EVENT HANDLERS
    # ========================================================================
    
    def _handle_email_reply(self, event: Dict):
        """Handle email reply - stop sequence, update intelligence"""
        data = event['data']
        tracking_id = data.get('tracking_id')
        
        if tracking_id:
            # Stop email sequence
            try:
                from integrations.email_sender import EmailSequenceManager
                # This would need sender instance - placeholder
                print(f"Stop sequence for tracking_id: {tracking_id}")
            except Exception as e:
                print(f"Error stopping sequence: {e}")
        
        # Update account score (high value signal)
        self._update_account_score(
            email=data.get('from'),
            signal_type='email_reply',
            signal_value=30  # High positive signal
        )
        
        # Create notification
        self._create_notification(
            user_email=event.get('user_email'),
            type='reply_received',
            message=f"Reply received from {data.get('from')}",
            priority='high'
        )
    
    def _handle_email_click(self, event: Dict):
        """Handle email link click - strong intent signal"""
        data = event['data']
        
        # Update account score (strong intent)
        self._update_account_score(
            email=data.get('recipient'),
            signal_type='email_click',
            signal_value=15
        )
        
        # Track which links are clicked
        self._track_link_performance(
            url=data.get('url'),
            tracking_id=data.get('tracking_id')
        )
    
    def _handle_email_open(self, event: Dict):
        """Handle email open - engagement signal"""
        data = event['data']
        
        # Update account score (basic engagement)
        self._update_account_score(
            email=data.get('recipient'),
            signal_type='email_open',
            signal_value=5
        )
    
    def _handle_connection_accepted(self, event: Dict):
        """Handle LinkedIn connection accepted"""
        data = event['data']
        
        # Update sequence manager
        try:
            from integrations.linkedin_automation import LinkedInSequenceManager
            manager = LinkedInSequenceManager()
            manager.record_event(
                prospect_linkedin_url=data.get('linkedin_url'),
                event_type='connection_accepted',
                metadata=data
            )
        except Exception as e:
            print(f"Error updating LinkedIn sequence: {e}")
        
        # Update account score
        self._update_account_score(
            email=data.get('email'),
            signal_type='linkedin_connection',
            signal_value=10
        )
        
        # Create notification
        self._create_notification(
            user_email=event.get('user_email'),
            type='connection_accepted',
            message=f"{data.get('name')} accepted your connection",
            priority='medium'
        )
    
    def _handle_linkedin_reply(self, event: Dict):
        """Handle LinkedIn message reply"""
        data = event['data']
        
        # Stop LinkedIn sequence
        try:
            from integrations.linkedin_automation import LinkedInSequenceManager
            manager = LinkedInSequenceManager()
            manager.record_event(
                prospect_linkedin_url=data.get('linkedin_url'),
                event_type='message_replied',
                metadata=data
            )
        except Exception as e:
            print(f"Error updating LinkedIn sequence: {e}")
        
        # Update account score (very high value)
        self._update_account_score(
            email=data.get('email'),
            signal_type='linkedin_reply',
            signal_value=35
        )
        
        # Create notification
        self._create_notification(
            user_email=event.get('user_email'),
            type='linkedin_reply',
            message=f"LinkedIn reply from {data.get('name')}",
            priority='high'
        )
    
    def _handle_meeting_scheduled(self, event: Dict):
        """Handle meeting scheduled - highest value signal"""
        data = event['data']
        
        # Update account score (highest value)
        self._update_account_score(
            email=data.get('attendee_email'),
            signal_type='meeting_scheduled',
            signal_value=50
        )
        
        # Generate meeting prep brief
        self._generate_meeting_prep(data)
        
        # Create notification
        self._create_notification(
            user_email=event.get('user_email'),
            type='meeting_scheduled',
            message=f"Meeting scheduled with {data.get('attendee_name')}",
            priority='high'
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _update_account_score(self, email: str, signal_type: str, signal_value: int):
        """Update account intelligence score"""
        # This would integrate with intelligence/ai_brain.py
        print(f"Update score for {email}: {signal_type} = +{signal_value}")
        
        # Store the signal
        from intelligence.ai_brain import AccountScoringEngine
        # Implementation would update the actual scoring
    
    def _create_notification(self, user_email: str, type: str, message: str, priority: str):
        """Create user notification"""
        notification = {
            'id': hashlib.md5(f"{user_email}{message}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            'user_email': user_email,
            'type': type,
            'message': message,
            'priority': priority,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        # Store notification
        notifications_file = "notifications.json"
        if os.path.exists(notifications_file):
            with open(notifications_file, 'r') as f:
                notifications = json.load(f)
        else:
            notifications = {'notifications': []}
        
        notifications['notifications'].append(notification)
        
        with open(notifications_file, 'w') as f:
            json.dump(notifications, f, indent=2)
    
    def _track_link_performance(self, url: str, tracking_id: str):
        """Track which links get clicked"""
        link_tracking_file = "link_tracking.json"
        
        if os.path.exists(link_tracking_file):
            with open(link_tracking_file, 'r') as f:
                link_data = json.load(f)
        else:
            link_data = {'links': {}}
        
        if url not in link_data['links']:
            link_data['links'][url] = {'clicks': 0, 'unique_clicks': []}
        
        link_data['links'][url]['clicks'] += 1
        if tracking_id not in link_data['links'][url]['unique_clicks']:
            link_data['links'][url]['unique_clicks'].append(tracking_id)
        
        with open(link_tracking_file, 'w') as f:
            json.dump(link_data, f, indent=2)
    
    def _generate_meeting_prep(self, meeting_data: Dict):
        """Generate AI-powered meeting prep brief"""
        # This would use Gemini to generate prep brief
        print(f"Generate meeting prep for: {meeting_data.get('attendee_name')}")
    
    def get_events(self,
                  event_type: str = None,
                  user_email: str = None,
                  since: str = None,
                  limit: int = 100) -> List[Dict]:
        """
        Query events.
        
        Args:
            event_type: Filter by event type
            user_email: Filter by user
            since: ISO timestamp to get events after
            limit: Max number of events to return
        
        Returns:
            List of events
        """
        events = self.data['events']
        
        # Apply filters
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        
        if user_email:
            events = [e for e in events if e.get('user_email') == user_email]
        
        if since:
            events = [e for e in events if e['timestamp'] > since]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return events[:limit]


# ============================================================================
# FLASK WEBHOOK ROUTES
# ============================================================================

def setup_webhooks(app):
    """
    Setup webhook routes for Flask app.
    Call this from app.py: setup_webhooks(app)
    """
    
    tracker = EventTracker()
    
    @app.route('/track/<tracking_id>/open.gif', methods=['GET'])
    def track_email_open(tracking_id):
        """Email open tracking pixel"""
        # Extract metadata from request
        metadata = {
            'user_agent': request.headers.get('User-Agent'),
            'ip': request.remote_addr,
            'timestamp': datetime.now().isoformat()
        }
        
        # Track the event
        tracker.track_event(
            event_type='email.opened',
            data={
                'tracking_id': tracking_id,
                'metadata': metadata
            }
        )
        
        # Return 1x1 transparent gif
        from flask import send_file
        import io
        
        # 1x1 transparent GIF
        gif_data = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        
        return send_file(
            io.BytesIO(gif_data),
            mimetype='image/gif'
        )
    
    @app.route('/track/<tracking_id>/click', methods=['GET'])
    def track_email_click(tracking_id):
        """Email link click tracking"""
        url = request.args.get('url', '')
        
        # Track the event
        tracker.track_event(
            event_type='email.clicked',
            data={
                'tracking_id': tracking_id,
                'url': url,
                'ip': request.remote_addr
            }
        )
        
        # Redirect to actual URL
        from flask import redirect
        return redirect(url)
    
    @app.route('/webhook/email/reply', methods=['POST'])
    def webhook_email_reply():
        """Webhook for email reply (from SendGrid, Mailgun, etc.)"""
        data = request.get_json()
        
        # Track the event
        tracker.track_event(
            event_type='email.replied',
            data=data
        )
        
        return jsonify({'status': 'ok'})
    
    @app.route('/webhook/linkedin/event', methods=['POST'])
    def webhook_linkedin_event():
        """Webhook for LinkedIn events (from PhantomBuster, Waalaxy)"""
        data = request.get_json()
        event_type = data.get('event_type')
        
        # Map to our event types
        event_map = {
            'connection_accepted': 'linkedin.connection_accepted',
            'connection_declined': 'linkedin.connection_declined',
            'message_replied': 'linkedin.message_replied'
        }
        
        if event_type in event_map:
            tracker.track_event(
                event_type=event_map[event_type],
                data=data
            )
        
        return jsonify({'status': 'ok'})
    
    @app.route('/webhook/calendar/meeting', methods=['POST'])
    def webhook_meeting_scheduled():
        """Webhook for meeting scheduled (from Calendly, Google Calendar)"""
        data = request.get_json()
        
        tracker.track_event(
            event_type='meeting.scheduled',
            data=data
        )
        
        return jsonify({'status': 'ok'})
    
    @app.route('/api/events', methods=['GET'])
    def api_get_events():
        """API to query events"""
        event_type = request.args.get('type')
        user_email = request.args.get('user')
        since = request.args.get('since')
        limit = int(request.args.get('limit', 100))
        
        events = tracker.get_events(
            event_type=event_type,
            user_email=user_email,
            since=since,
            limit=limit
        )
        
        return jsonify({
            'events': events,
            'count': len(events)
        })
    
    @app.route('/api/notifications/<user_email>', methods=['GET'])
    def api_get_notifications(user_email):
        """Get notifications for a user"""
        notifications_file = "notifications.json"
        
        if not os.path.exists(notifications_file):
            return jsonify({'notifications': []})
        
        with open(notifications_file, 'r') as f:
            data = json.load(f)
        
        user_notifications = [
            n for n in data['notifications']
            if n.get('user_email') == user_email
        ]
        
        # Sort by timestamp (newest first)
        user_notifications.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'notifications': user_notifications[:50],  # Last 50
            'unread_count': len([n for n in user_notifications if not n.get('read', False)])
        })


# ============================================================================
# TESTING
# ============================================================================

if __name__ == '__main__':
    # Test event tracking
    tracker = EventTracker()
    
    # Simulate email open
    event_id = tracker.track_event(
        event_type='email.opened',
        data={
            'tracking_id': 'test123',
            'recipient': 'prospect@company.com'
        },
        user_email='user@example.com'
    )
    
    print(f"Tracked event: {event_id}")
    
    # Query events
    events = tracker.get_events(event_type='email.opened')
    print(f"Found {len(events)} email open events")
