"""
EMAIL REPLY DETECTION
Monitor inbox for replies to our outreach.
Close the loop for the learning system.
"""

import os
import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from email import message_from_bytes
import base64

REPLY_LOG_FILE = "reply_log.json"
EMAIL_LOG_FILE = "email_log.json"

def load_reply_log() -> Dict:
    if os.path.exists(REPLY_LOG_FILE):
        with open(REPLY_LOG_FILE, 'r') as f:
            return json.load(f)
    return {'replies': [], 'last_check': None}

def save_reply_log(log: Dict):
    with open(REPLY_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)

def load_email_log() -> Dict:
    if os.path.exists(EMAIL_LOG_FILE):
        with open(EMAIL_LOG_FILE, 'r') as f:
            return json.load(f)
    return {'emails': []}

def save_email_log(log: Dict):
    with open(EMAIL_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)


# ============================================================================
# EMAIL TRACKER - Track opens/clicks from our tracking system
# ============================================================================

class EmailTracker:
    """
    Track email opens and clicks from our tracking pixels/links.
    Called by the Flask tracking endpoints.
    """
    
    def __init__(self):
        self.email_log = load_email_log()
    
    def track_open(self, tracking_id: str) -> bool:
        """Record an email open"""
        email_log = load_email_log()
        
        for email in email_log['emails']:
            if email.get('tracking_id') == tracking_id:
                if not email.get('opened'):  # Only count first open
                    email['opened'] = True
                    email['opened_at'] = datetime.now().isoformat()
                    email['open_count'] = email.get('open_count', 0) + 1
                    save_email_log(email_log)
                    
                    # Trigger learning event
                    self._trigger_learning_event(tracking_id, 'email_opened')
                    return True
                else:
                    email['open_count'] = email.get('open_count', 0) + 1
                    save_email_log(email_log)
                return True
        
        return False
    
    def track_click(self, tracking_id: str, url: str) -> bool:
        """Record a link click"""
        email_log = load_email_log()
        
        for email in email_log['emails']:
            if email.get('tracking_id') == tracking_id:
                if not email.get('clicked'):  # Only count first click
                    email['clicked'] = True
                    email['clicked_at'] = datetime.now().isoformat()
                    self._trigger_learning_event(tracking_id, 'email_clicked')
                
                email['click_count'] = email.get('click_count', 0) + 1
                
                if 'clicked_urls' not in email:
                    email['clicked_urls'] = []
                if url not in email['clicked_urls']:
                    email['clicked_urls'].append(url)
                
                save_email_log(email_log)
                return True
        
        return False
    
    def get_email_stats(self, tracking_id: str) -> Optional[Dict]:
        """Get stats for a specific email"""
        email_log = load_email_log()
        
        for email in email_log['emails']:
            if email.get('tracking_id') == tracking_id:
                return {
                    'tracking_id': tracking_id,
                    'to': email.get('to'),
                    'subject': email.get('subject'),
                    'sent_at': email.get('sent_at'),
                    'status': email.get('status'),
                    'opened': email.get('opened', False),
                    'opened_at': email.get('opened_at'),
                    'open_count': email.get('open_count', 0),
                    'clicked': email.get('clicked', False),
                    'clicked_at': email.get('clicked_at'),
                    'click_count': email.get('click_count', 0),
                    'clicked_urls': email.get('clicked_urls', []),
                    'replied': email.get('replied', False),
                    'replied_at': email.get('replied_at'),
                    'bounced': email.get('bounced', False)
                }
        
        return None
    
    def get_campaign_stats(self, tracking_ids: List[str]) -> Dict:
        """Get aggregate stats for a campaign (multiple emails)"""
        email_log = load_email_log()
        
        stats = {
            'total': 0,
            'sent': 0,
            'delivered': 0,
            'opened': 0,
            'clicked': 0,
            'replied': 0,
            'bounced': 0,
            'open_rate': 0,
            'click_rate': 0,
            'reply_rate': 0
        }
        
        for email in email_log['emails']:
            if email.get('tracking_id') in tracking_ids:
                stats['total'] += 1
                
                if email.get('status') == 'sent':
                    stats['sent'] += 1
                    if not email.get('bounced'):
                        stats['delivered'] += 1
                
                if email.get('opened'):
                    stats['opened'] += 1
                if email.get('clicked'):
                    stats['clicked'] += 1
                if email.get('replied'):
                    stats['replied'] += 1
                if email.get('bounced'):
                    stats['bounced'] += 1
        
        if stats['delivered'] > 0:
            stats['open_rate'] = round(stats['opened'] / stats['delivered'] * 100, 1)
            stats['click_rate'] = round(stats['clicked'] / stats['delivered'] * 100, 1)
            stats['reply_rate'] = round(stats['replied'] / stats['delivered'] * 100, 1)
        
        return stats
    
    def _trigger_learning_event(self, tracking_id: str, event_type: str):
        """Notify the learning system of an event"""
        # This would integrate with the LearningSystem
        # For now, just log it
        email_log = load_email_log()
        
        for email in email_log['emails']:
            if email.get('tracking_id') == tracking_id:
                if 'learning_events' not in email:
                    email['learning_events'] = []
                
                email['learning_events'].append({
                    'event': event_type,
                    'timestamp': datetime.now().isoformat()
                })
                
                save_email_log(email_log)
                break


# ============================================================================
# REPLY DETECTOR - Monitor inbox for responses
# ============================================================================

class ReplyDetector:
    """
    Monitor inbox for replies to our outreach emails.
    Supports Gmail API and IMAP.
    """
    
    def __init__(self, user_email: str, provider: str = 'gmail'):
        self.user_email = user_email
        self.provider = provider
        self.reply_log = load_reply_log()
    
    def check_for_replies_gmail(self, credentials_file: str = 'gmail_credentials.json') -> List[Dict]:
        """
        Check Gmail for new replies to our outreach.
        
        Returns list of detected replies with sentiment analysis.
        """
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
        except ImportError:
            return []
        
        token_file = f'gmail_token_{self.user_email.replace("@", "_").replace(".", "_")}.json'
        
        creds = None
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_file):
                    return []
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, 
                    ['https://www.googleapis.com/auth/gmail.readonly']
                )
                creds = flow.run_local_server(port=0)
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
        
        service = build('gmail', 'v1', credentials=creds)
        
        # Get emails from last 7 days
        since = (datetime.now() - timedelta(days=7)).strftime('%Y/%m/%d')
        query = f'after:{since} in:inbox'
        
        results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
        messages = results.get('messages', [])
        
        detected_replies = []
        email_log = load_email_log()
        sent_emails = {e['to']: e for e in email_log['emails']}
        
        for msg in messages:
            full_msg = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            
            # Get headers
            headers = {h['name']: h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
            from_email = headers.get('From', '')
            subject = headers.get('Subject', '')
            
            # Extract email address from "Name <email@domain.com>" format
            from_match = re.search(r'<([^>]+)>', from_email)
            from_addr = from_match.group(1) if from_match else from_email
            
            # Check if this is a reply to one of our emails
            if from_addr in sent_emails:
                original = sent_emails[from_addr]
                
                # Check if we already logged this reply
                reply_id = f"{from_addr}_{msg['id']}"
                if any(r.get('reply_id') == reply_id for r in self.reply_log.get('replies', [])):
                    continue
                
                # Get message body
                body = self._extract_body(full_msg)
                
                # Analyze sentiment
                sentiment = self._analyze_sentiment(body)
                
                reply = {
                    'reply_id': reply_id,
                    'from': from_addr,
                    'subject': subject,
                    'body_preview': body[:500] if body else '',
                    'original_tracking_id': original.get('tracking_id'),
                    'sentiment': sentiment,
                    'detected_at': datetime.now().isoformat(),
                    'gmail_id': msg['id'],
                    'thread_id': full_msg.get('threadId')
                }
                
                detected_replies.append(reply)
                
                # Update email log
                original['replied'] = True
                original['replied_at'] = datetime.now().isoformat()
                original['reply_sentiment'] = sentiment
        
        # Save updates
        if detected_replies:
            self.reply_log['replies'].extend(detected_replies)
            self.reply_log['last_check'] = datetime.now().isoformat()
            save_reply_log(self.reply_log)
            save_email_log(email_log)
            
            # Trigger learning events
            for reply in detected_replies:
                event_type = 'email_replied_positive' if reply['sentiment']['is_positive'] else 'email_replied'
                if reply['sentiment']['is_negative']:
                    event_type = 'email_replied_negative'
                
                self._trigger_learning_event(reply['original_tracking_id'], event_type, reply)
        
        return detected_replies
    
    def check_for_replies_imap(self, imap_host: str, imap_user: str, imap_password: str,
                                imap_port: int = 993) -> List[Dict]:
        """
        Check IMAP server for new replies.
        Works with any email provider.
        """
        import imaplib
        
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            mail.login(imap_user, imap_password)
            mail.select('INBOX')
            
            # Search for recent emails
            since = (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
            _, message_ids = mail.search(None, f'(SINCE {since})')
            
            detected_replies = []
            email_log = load_email_log()
            sent_emails = {e['to']: e for e in email_log['emails']}
            
            for msg_id in message_ids[0].split()[-100:]:  # Last 100
                _, msg_data = mail.fetch(msg_id, '(RFC822)')
                email_body = msg_data[0][1]
                msg = message_from_bytes(email_body)
                
                from_email = msg.get('From', '')
                from_match = re.search(r'<([^>]+)>', from_email)
                from_addr = from_match.group(1) if from_match else from_email
                
                if from_addr in sent_emails:
                    original = sent_emails[from_addr]
                    
                    reply_id = f"{from_addr}_{msg_id.decode()}"
                    if any(r.get('reply_id') == reply_id for r in self.reply_log.get('replies', [])):
                        continue
                    
                    body = self._extract_body_from_message(msg)
                    sentiment = self._analyze_sentiment(body)
                    
                    reply = {
                        'reply_id': reply_id,
                        'from': from_addr,
                        'subject': msg.get('Subject', ''),
                        'body_preview': body[:500] if body else '',
                        'original_tracking_id': original.get('tracking_id'),
                        'sentiment': sentiment,
                        'detected_at': datetime.now().isoformat()
                    }
                    
                    detected_replies.append(reply)
                    
                    original['replied'] = True
                    original['replied_at'] = datetime.now().isoformat()
                    original['reply_sentiment'] = sentiment
            
            mail.close()
            mail.logout()
            
            if detected_replies:
                self.reply_log['replies'].extend(detected_replies)
                self.reply_log['last_check'] = datetime.now().isoformat()
                save_reply_log(self.reply_log)
                save_email_log(email_log)
            
            return detected_replies
            
        except Exception as e:
            return []
    
    def _extract_body(self, gmail_message: Dict) -> str:
        """Extract body from Gmail API message"""
        payload = gmail_message.get('payload', {})
        
        # Try to get plain text body
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        # Fallback to main body
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return ''
    
    def _extract_body_from_message(self, msg) -> str:
        """Extract body from email.message.Message"""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ''
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of reply to determine if positive/negative.
        Simple rule-based for now, could use AI later.
        """
        if not text:
            return {'is_positive': False, 'is_negative': False, 'is_neutral': True, 'indicators': []}
        
        text_lower = text.lower()
        
        positive_indicators = [
            'interested', 'love to', 'sounds great', 'let\'s talk', 'schedule a call',
            'free to chat', 'would love', 'yes', 'absolutely', 'definitely', 'great timing',
            'perfect timing', 'send more', 'tell me more', 'book a time', 'calendar',
            'available', 'looking forward', 'excited', 'thanks for reaching out'
        ]
        
        negative_indicators = [
            'not interested', 'no thanks', 'unsubscribe', 'remove me', 'stop emailing',
            'don\'t contact', 'wrong person', 'not the right', 'no longer', 'already have',
            'not looking', 'pass', 'not now', 'bad timing', 'no budget', 'remove from list',
            'spam', 'stop sending'
        ]
        
        found_positive = [p for p in positive_indicators if p in text_lower]
        found_negative = [n for n in negative_indicators if n in text_lower]
        
        return {
            'is_positive': len(found_positive) > len(found_negative) and len(found_positive) > 0,
            'is_negative': len(found_negative) > len(found_positive) and len(found_negative) > 0,
            'is_neutral': len(found_positive) == 0 and len(found_negative) == 0,
            'positive_indicators': found_positive,
            'negative_indicators': found_negative,
            'confidence': min(1.0, (len(found_positive) + len(found_negative)) / 3)
        }
    
    def _trigger_learning_event(self, tracking_id: str, event_type: str, reply: Dict):
        """Notify the learning system"""
        # This would integrate with LearningSystem.track_outcome
        pass
    
    def get_reply_stats(self) -> Dict:
        """Get summary of reply detection"""
        reply_log = load_reply_log()
        replies = reply_log.get('replies', [])
        
        return {
            'total_replies': len(replies),
            'positive_replies': len([r for r in replies if r.get('sentiment', {}).get('is_positive')]),
            'negative_replies': len([r for r in replies if r.get('sentiment', {}).get('is_negative')]),
            'neutral_replies': len([r for r in replies if r.get('sentiment', {}).get('is_neutral')]),
            'last_check': reply_log.get('last_check'),
            'recent_replies': replies[-10:]  # Last 10
        }
