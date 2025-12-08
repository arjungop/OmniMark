"""
REAL EMAIL SENDING
Not simulation. Actually sends emails.

Supports:
- SMTP (any provider)
- SendGrid API
- Gmail API (OAuth)
"""

import os
import json
import smtplib
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import base64

# Config file for email settings
EMAIL_CONFIG_FILE = "email_config.json"
EMAIL_LOG_FILE = "email_log.json"

def load_config() -> Dict:
    if os.path.exists(EMAIL_CONFIG_FILE):
        with open(EMAIL_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config: Dict):
    with open(EMAIL_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_email_log() -> Dict:
    if os.path.exists(EMAIL_LOG_FILE):
        with open(EMAIL_LOG_FILE, 'r') as f:
            return json.load(f)
    return {'emails': []}

def save_email_log(log: Dict):
    with open(EMAIL_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)


# ============================================================================
# BASE EMAIL SENDER
# ============================================================================

class EmailSender(ABC):
    """Abstract base class for email senders"""
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.config = load_config().get(user_email, {})
    
    @abstractmethod
    def send(self, to: str, subject: str, body: str, html_body: Optional[str] = None, 
             reply_to: Optional[str] = None, attachments: List[Dict] = None) -> Dict:
        """Send an email. Returns result dict with status and message_id."""
        pass
    
    @abstractmethod
    def verify_connection(self) -> bool:
        """Verify the email sending connection is working."""
        pass
    
    def _generate_tracking_id(self, to: str, subject: str) -> str:
        """Generate unique tracking ID for this email"""
        data = f"{self.user_email}{to}{subject}{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def _inject_tracking(self, html_body: str, tracking_id: str, base_url: str) -> str:
        """Inject tracking pixel into HTML email"""
        if not html_body:
            return html_body
        
        # Tracking pixel
        pixel = f'<img src="{base_url}/track/{tracking_id}/open.gif" width="1" height="1" style="display:none" alt="">'
        
        # Inject before closing body tag or at end
        if '</body>' in html_body.lower():
            html_body = html_body.replace('</body>', f'{pixel}</body>')
            html_body = html_body.replace('</BODY>', f'{pixel}</BODY>')
        else:
            html_body += pixel
        
        return html_body
    
    def _rewrite_links(self, html_body: str, tracking_id: str, base_url: str) -> str:
        """Rewrite links to go through click tracker"""
        import re
        
        def replace_link(match):
            original_url = match.group(1)
            # Don't track our own tracking pixel
            if '/track/' in original_url:
                return match.group(0)
            tracked_url = f'{base_url}/track/{tracking_id}/click?url={original_url}'
            return f'href="{tracked_url}"'
        
        return re.sub(r'href=["\']([^"\']+)["\']', replace_link, html_body, flags=re.IGNORECASE)
    
    def _log_email(self, to: str, subject: str, tracking_id: str, result: Dict):
        """Log email send for tracking"""
        log = load_email_log()
        
        log['emails'].append({
            'tracking_id': tracking_id,
            'from': self.user_email,
            'to': to,
            'subject': subject,
            'sent_at': datetime.now().isoformat(),
            'status': result.get('status'),
            'message_id': result.get('message_id'),
            'provider': result.get('provider'),
            'opened': False,
            'opened_at': None,
            'clicked': False,
            'clicked_at': None,
            'clicked_urls': [],
            'replied': False,
            'replied_at': None,
            'bounced': False,
            'error': result.get('error')
        })
        
        # Keep last 10000 emails
        log['emails'] = log['emails'][-10000:]
        
        save_email_log(log)


# ============================================================================
# SMTP SENDER (Universal - Gmail, Outlook, any SMTP)
# ============================================================================

class SMTPSender(EmailSender):
    """
    Send emails via SMTP. Works with:
    - Gmail (smtp.gmail.com:587) - requires app password
    - Outlook (smtp.office365.com:587)
    - Custom SMTP servers
    """
    
    def __init__(self, user_email: str, smtp_host: str = None, smtp_port: int = None,
                 smtp_user: str = None, smtp_password: str = None, use_tls: bool = True):
        super().__init__(user_email)
        
        # Use provided config or load from saved config
        self.smtp_host = smtp_host or self.config.get('smtp_host')
        self.smtp_port = smtp_port or self.config.get('smtp_port', 587)
        self.smtp_user = smtp_user or self.config.get('smtp_user')
        self.smtp_password = smtp_password or self.config.get('smtp_password')
        self.use_tls = use_tls if use_tls is not None else self.config.get('use_tls', True)
    
    def configure(self, smtp_host: str, smtp_port: int, smtp_user: str, 
                  smtp_password: str, use_tls: bool = True):
        """Save SMTP configuration"""
        config = load_config()
        config[self.user_email] = {
            'provider': 'smtp',
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_user': smtp_user,
            'smtp_password': smtp_password,
            'use_tls': use_tls
        }
        save_config(config)
        
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
    
    def verify_connection(self) -> Dict:
        """Test SMTP connection"""
        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password]):
            return {'success': False, 'error': 'SMTP not configured'}
        
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10)
            
            server.login(self.smtp_user, self.smtp_password)
            server.quit()
            
            return {'success': True, 'message': f'Connected to {self.smtp_host}'}
        except smtplib.SMTPAuthenticationError:
            return {'success': False, 'error': 'Authentication failed. Check username/password.'}
        except smtplib.SMTPConnectError:
            return {'success': False, 'error': f'Could not connect to {self.smtp_host}:{self.smtp_port}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send(self, to: str, subject: str, body: str, html_body: Optional[str] = None,
             reply_to: Optional[str] = None, attachments: List[Dict] = None,
             base_url: str = "http://localhost:5001") -> Dict:
        """
        Send email via SMTP.
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            reply_to: Optional reply-to address
            attachments: List of {'filename': str, 'content': bytes, 'content_type': str}
            base_url: Base URL for tracking
        """
        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password]):
            return {'status': 'error', 'error': 'SMTP not configured', 'provider': 'smtp'}
        
        tracking_id = self._generate_tracking_id(to, subject)
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_user
            msg['To'] = to
            msg['Subject'] = subject
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Add custom header for tracking
            msg['X-Chameleon-Tracking-ID'] = tracking_id
            
            # Plain text part
            msg.attach(MIMEText(body, 'plain'))
            
            # HTML part with tracking
            if html_body:
                html_body = self._inject_tracking(html_body, tracking_id, base_url)
                html_body = self._rewrite_links(html_body, tracking_id, base_url)
                msg.attach(MIMEText(html_body, 'html'))
            
            # Attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 
                                    f'attachment; filename="{attachment["filename"]}"')
                    msg.attach(part)
            
            # Send
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            message_id = msg['Message-ID']
            server.quit()
            
            result = {
                'status': 'sent',
                'message_id': message_id,
                'tracking_id': tracking_id,
                'provider': 'smtp',
                'sent_at': datetime.now().isoformat()
            }
            
            self._log_email(to, subject, tracking_id, result)
            
            return result
            
        except smtplib.SMTPRecipientsRefused:
            result = {'status': 'bounced', 'error': 'Recipient rejected', 'provider': 'smtp', 'tracking_id': tracking_id}
            self._log_email(to, subject, tracking_id, result)
            return result
        except Exception as e:
            result = {'status': 'error', 'error': str(e), 'provider': 'smtp', 'tracking_id': tracking_id}
            self._log_email(to, subject, tracking_id, result)
            return result


# ============================================================================
# SENDGRID SENDER
# ============================================================================

class SendGridSender(EmailSender):
    """
    Send emails via SendGrid API.
    
    Benefits:
    - Higher deliverability
    - Built-in analytics
    - Handles bounces/complaints automatically
    - Scales to high volume
    
    Requires: SENDGRID_API_KEY
    """
    
    def __init__(self, user_email: str, api_key: str = None):
        super().__init__(user_email)
        self.api_key = api_key or self.config.get('sendgrid_api_key') or os.environ.get('SENDGRID_API_KEY')
        self.from_email = self.config.get('from_email', user_email)
        self.from_name = self.config.get('from_name', '')
    
    def configure(self, api_key: str, from_email: str = None, from_name: str = None):
        """Save SendGrid configuration"""
        config = load_config()
        config[self.user_email] = {
            'provider': 'sendgrid',
            'sendgrid_api_key': api_key,
            'from_email': from_email or self.user_email,
            'from_name': from_name or ''
        }
        save_config(config)
        
        self.api_key = api_key
        self.from_email = from_email or self.user_email
        self.from_name = from_name or ''
    
    def verify_connection(self) -> Dict:
        """Verify SendGrid API key is valid"""
        if not self.api_key:
            return {'success': False, 'error': 'SendGrid API key not configured'}
        
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Verify API key by checking account info
            response = requests.get(
                'https://api.sendgrid.com/v3/user/profile',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {'success': True, 'message': 'SendGrid API key valid'}
            elif response.status_code == 401:
                return {'success': False, 'error': 'Invalid API key'}
            else:
                return {'success': False, 'error': f'API error: {response.status_code}'}
                
        except ImportError:
            return {'success': False, 'error': 'requests library not installed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send(self, to: str, subject: str, body: str, html_body: Optional[str] = None,
             reply_to: Optional[str] = None, attachments: List[Dict] = None,
             base_url: str = "http://localhost:5001") -> Dict:
        """Send email via SendGrid API"""
        if not self.api_key:
            return {'status': 'error', 'error': 'SendGrid not configured', 'provider': 'sendgrid'}
        
        tracking_id = self._generate_tracking_id(to, subject)
        
        try:
            import requests
            
            # Inject tracking into HTML
            if html_body:
                html_body = self._inject_tracking(html_body, tracking_id, base_url)
                html_body = self._rewrite_links(html_body, tracking_id, base_url)
            
            # Build SendGrid payload
            payload = {
                'personalizations': [{
                    'to': [{'email': to}]
                }],
                'from': {
                    'email': self.from_email,
                    'name': self.from_name
                },
                'subject': subject,
                'content': [
                    {'type': 'text/plain', 'value': body}
                ],
                'custom_args': {
                    'tracking_id': tracking_id
                },
                'tracking_settings': {
                    'click_tracking': {'enable': True},
                    'open_tracking': {'enable': True}
                }
            }
            
            if html_body:
                payload['content'].append({'type': 'text/html', 'value': html_body})
            
            if reply_to:
                payload['reply_to'] = {'email': reply_to}
            
            if attachments:
                payload['attachments'] = [{
                    'content': base64.b64encode(att['content']).decode(),
                    'filename': att['filename'],
                    'type': att.get('content_type', 'application/octet-stream')
                } for att in attachments]
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 202]:
                message_id = response.headers.get('X-Message-Id', tracking_id)
                result = {
                    'status': 'sent',
                    'message_id': message_id,
                    'tracking_id': tracking_id,
                    'provider': 'sendgrid',
                    'sent_at': datetime.now().isoformat()
                }
            else:
                error_body = response.json() if response.content else {}
                result = {
                    'status': 'error',
                    'error': error_body.get('errors', [{}])[0].get('message', f'HTTP {response.status_code}'),
                    'provider': 'sendgrid',
                    'tracking_id': tracking_id
                }
            
            self._log_email(to, subject, tracking_id, result)
            return result
            
        except ImportError:
            return {'status': 'error', 'error': 'requests library not installed', 'provider': 'sendgrid'}
        except Exception as e:
            result = {'status': 'error', 'error': str(e), 'provider': 'sendgrid', 'tracking_id': tracking_id}
            self._log_email(to, subject, tracking_id, result)
            return result


# ============================================================================
# GMAIL API SENDER (OAuth)
# ============================================================================

class GmailSender(EmailSender):
    """
    Send emails via Gmail API with OAuth.
    
    Benefits:
    - Sends as actual user (better deliverability)
    - Access to sent folder, threads
    - Can read replies
    
    Setup:
    1. Create Google Cloud project
    2. Enable Gmail API
    3. Create OAuth credentials
    4. Download client_secret.json
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self, user_email: str, credentials_file: str = 'gmail_credentials.json'):
        super().__init__(user_email)
        self.credentials_file = credentials_file
        self.token_file = f'gmail_token_{user_email.replace("@", "_").replace(".", "_")}.json'
        self.service = None
    
    def _get_service(self):
        """Get authenticated Gmail service"""
        if self.service:
            return self.service
        
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
        except ImportError:
            raise ImportError("Gmail API requires: pip install google-auth-oauthlib google-api-python-client")
        
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Gmail credentials file not found: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token for next time
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
        return self.service
    
    def verify_connection(self) -> Dict:
        """Verify Gmail connection"""
        try:
            service = self._get_service()
            profile = service.users().getProfile(userId='me').execute()
            return {
                'success': True, 
                'message': f'Connected as {profile.get("emailAddress")}',
                'email': profile.get("emailAddress")
            }
        except FileNotFoundError as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send(self, to: str, subject: str, body: str, html_body: Optional[str] = None,
             reply_to: Optional[str] = None, attachments: List[Dict] = None,
             base_url: str = "http://localhost:5001") -> Dict:
        """Send email via Gmail API"""
        tracking_id = self._generate_tracking_id(to, subject)
        
        try:
            service = self._get_service()
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['To'] = to
            msg['Subject'] = subject
            if reply_to:
                msg['Reply-To'] = reply_to
            msg['X-Chameleon-Tracking-ID'] = tracking_id
            
            # Plain text
            msg.attach(MIMEText(body, 'plain'))
            
            # HTML with tracking
            if html_body:
                html_body = self._inject_tracking(html_body, tracking_id, base_url)
                html_body = self._rewrite_links(html_body, tracking_id, base_url)
                msg.attach(MIMEText(html_body, 'html'))
            
            # Attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 
                                    f'attachment; filename="{attachment["filename"]}"')
                    msg.attach(part)
            
            # Encode and send
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            
            sent = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            result = {
                'status': 'sent',
                'message_id': sent.get('id'),
                'thread_id': sent.get('threadId'),
                'tracking_id': tracking_id,
                'provider': 'gmail',
                'sent_at': datetime.now().isoformat()
            }
            
            self._log_email(to, subject, tracking_id, result)
            return result
            
        except Exception as e:
            result = {'status': 'error', 'error': str(e), 'provider': 'gmail', 'tracking_id': tracking_id}
            self._log_email(to, subject, tracking_id, result)
            return result


# ============================================================================
# EMAIL SENDER FACTORY
# ============================================================================

def get_email_sender(user_email: str) -> EmailSender:
    """Get the configured email sender for a user"""
    config = load_config().get(user_email, {})
    provider = config.get('provider', 'smtp')
    
    if provider == 'sendgrid':
        return SendGridSender(user_email)
    elif provider == 'gmail':
        return GmailSender(user_email)
    else:
        return SMTPSender(user_email)


# ============================================================================
# BULK EMAIL SENDING
# ============================================================================

class BulkEmailSender:
    """
    Send emails to multiple recipients with rate limiting.
    Tracks delivery status for each.
    """
    
    def __init__(self, user_email: str, rate_limit: int = 50):
        """
        Args:
            user_email: User's email
            rate_limit: Max emails per hour
        """
        self.user_email = user_email
        self.rate_limit = rate_limit
        self.sender = get_email_sender(user_email)
    
    def send_batch(self, emails: List[Dict], base_url: str = "http://localhost:5001") -> Dict:
        """
        Send a batch of emails with rate limiting.
        
        Args:
            emails: List of {'to': str, 'subject': str, 'body': str, 'html_body': str}
            base_url: Base URL for tracking
            
        Returns:
            Summary of send results
        """
        import time
        
        results = {
            'total': len(emails),
            'sent': 0,
            'failed': 0,
            'details': []
        }
        
        delay = 3600 / self.rate_limit if self.rate_limit > 0 else 0  # Seconds between emails
        
        for i, email in enumerate(emails):
            result = self.sender.send(
                to=email['to'],
                subject=email['subject'],
                body=email['body'],
                html_body=email.get('html_body'),
                reply_to=email.get('reply_to'),
                base_url=base_url
            )
            
            results['details'].append({
                'to': email['to'],
                'result': result
            })
            
            if result['status'] == 'sent':
                results['sent'] += 1
            else:
                results['failed'] += 1
            
            # Rate limiting
            if i < len(emails) - 1 and delay > 0:
                time.sleep(delay)
        
        return results


# ============================================================================
# EMAIL SEQUENCE AUTOMATION
# ============================================================================

SEQUENCE_DB_FILE = "email_sequences.json"

def load_sequences() -> Dict:
    if os.path.exists(SEQUENCE_DB_FILE):
        with open(SEQUENCE_DB_FILE, 'r') as f:
            return json.load(f)
    return {'sequences': {}, 'active_campaigns': {}}

def save_sequences(data: Dict):
    with open(SEQUENCE_DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)


class EmailSequenceManager:
    """
    Automated email sequence engine.
    
    Features:
    - Multi-email sequences with configurable delays
    - Stop conditions (replied, clicked, opened)
    - Personalization with merge fields
    - A/B testing support
    - Analytics tracking
    """
    
    def __init__(self, sender: EmailSender):
        self.sender = sender
        self.data = load_sequences()
    
    def create_sequence(self, 
                       sequence_name: str,
                       emails: List[Dict],
                       stop_on: List[str] = None) -> str:
        """
        Create an email sequence.
        
        Args:
            sequence_name: Name for this sequence
            emails: List of email templates with structure:
                {
                    'subject': 'Email subject',
                    'body': 'Plain text body',
                    'html_body': 'HTML body (optional)',
                    'delay_days': 3,  # Days after previous email
                    'send_time': '10:00'  # Optional: specific send time (HH:MM)
                }
            stop_on: List of conditions to stop sequence
                ['replied', 'clicked', 'opened', 'bounced']
        
        Returns:
            sequence_id
        """
        sequence_id = hashlib.md5(
            f"{sequence_name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        self.data['sequences'][sequence_id] = {
            'id': sequence_id,
            'name': sequence_name,
            'emails': emails,
            'stop_on': stop_on or ['replied'],
            'created_at': datetime.now().isoformat(),
            'active': True
        }
        
        save_sequences(self.data)
        return sequence_id
    
    def start_campaign(self,
                      sequence_id: str,
                      recipients: List[Dict],
                      merge_fields: Dict = None) -> str:
        """
        Start a sequence campaign for recipients.
        
        Args:
            sequence_id: ID of the sequence to use
            recipients: List of recipient dicts with 'email' and merge fields
            merge_fields: Global merge fields for all recipients
        
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
            'recipients': {},
            'stats': {
                'total_recipients': len(recipients),
                'emails_sent': 0,
                'emails_opened': 0,
                'emails_clicked': 0,
                'emails_replied': 0,
                'sequences_completed': 0,
                'sequences_stopped': 0
            }
        }
        
        # Initialize each recipient's journey
        for recipient in recipients:
            recipient_id = hashlib.md5(recipient['email'].encode()).hexdigest()[:12]
            
            self.data['active_campaigns'][campaign_id]['recipients'][recipient_id] = {
                'email': recipient['email'],
                'merge_fields': {**(merge_fields or {}), **recipient},
                'current_step': 0,
                'status': 'pending',
                'next_send_date': datetime.now().isoformat(),
                'emails_sent': [],
                'events': []
            }
        
        save_sequences(self.data)
        return campaign_id
    
    def process_campaigns(self, base_url: str = "http://localhost:5000") -> Dict:
        """
        Process all active campaigns - send scheduled emails.
        Should be called periodically (e.g., every hour via cron).
        
        Returns:
            Processing results
        """
        results = {
            'processed_campaigns': 0,
            'emails_sent': 0,
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
            
            # Process each recipient
            for recipient_id, recipient_data in campaign['recipients'].items():
                if recipient_data['status'] in ['completed', 'stopped']:
                    continue
                
                # Check if it's time to send next email
                next_send = datetime.fromisoformat(recipient_data['next_send_date'])
                if now < next_send:
                    continue
                
                # Check stop conditions
                if self._should_stop_sequence(recipient_data, sequence['stop_on']):
                    recipient_data['status'] = 'stopped'
                    campaign['stats']['sequences_stopped'] += 1
                    continue
                
                # Get current email in sequence
                step = recipient_data['current_step']
                if step >= len(sequence['emails']):
                    recipient_data['status'] = 'completed'
                    campaign['stats']['sequences_completed'] += 1
                    continue
                
                email_template = sequence['emails'][step]
                
                # Personalize email
                subject = self._apply_merge_fields(
                    email_template['subject'], 
                    recipient_data['merge_fields']
                )
                body = self._apply_merge_fields(
                    email_template['body'], 
                    recipient_data['merge_fields']
                )
                html_body = email_template.get('html_body')
                if html_body:
                    html_body = self._apply_merge_fields(html_body, recipient_data['merge_fields'])
                
                # Send email
                try:
                    result = self.sender.send(
                        to=recipient_data['email'],
                        subject=subject,
                        body=body,
                        html_body=html_body,
                        base_url=base_url
                    )
                    
                    # Log the send
                    recipient_data['emails_sent'].append({
                        'step': step,
                        'sent_at': datetime.now().isoformat(),
                        'subject': subject,
                        'message_id': result.get('message_id'),
                        'tracking_id': result.get('tracking_id')
                    })
                    
                    campaign['stats']['emails_sent'] += 1
                    results['emails_sent'] += 1
                    
                    # Schedule next email
                    recipient_data['current_step'] += 1
                    
                    if recipient_data['current_step'] < len(sequence['emails']):
                        next_email = sequence['emails'][recipient_data['current_step']]
                        delay_days = next_email.get('delay_days', 3)
                        next_send_date = now + timedelta(days=delay_days)
                        
                        # Apply specific send time if specified
                        if 'send_time' in next_email:
                            hour, minute = map(int, next_email['send_time'].split(':'))
                            next_send_date = next_send_date.replace(hour=hour, minute=minute, second=0)
                        
                        recipient_data['next_send_date'] = next_send_date.isoformat()
                    
                except Exception as e:
                    results['errors'].append({
                        'campaign_id': campaign_id,
                        'recipient': recipient_data['email'],
                        'error': str(e)
                    })
        
        save_sequences(self.data)
        return results
    
    def record_event(self, 
                    tracking_id: str, 
                    event_type: str,
                    metadata: Dict = None):
        """
        Record an email event (open, click, reply).
        
        Args:
            tracking_id: The tracking ID from the email
            event_type: 'opened', 'clicked', 'replied', 'bounced'
            metadata: Additional event data
        """
        # Find the campaign and recipient
        for campaign_id, campaign in self.data['active_campaigns'].items():
            for recipient_id, recipient_data in campaign['recipients'].items():
                # Check if this tracking_id belongs to this recipient
                for sent_email in recipient_data['emails_sent']:
                    if sent_email.get('tracking_id') == tracking_id:
                        # Record the event
                        recipient_data['events'].append({
                            'type': event_type,
                            'timestamp': datetime.now().isoformat(),
                            'email_step': sent_email['step'],
                            'metadata': metadata or {}
                        })
                        
                        # Update campaign stats
                        if event_type == 'opened':
                            campaign['stats']['emails_opened'] += 1
                        elif event_type == 'clicked':
                            campaign['stats']['emails_clicked'] += 1
                        elif event_type == 'replied':
                            campaign['stats']['emails_replied'] += 1
                        
                        save_sequences(self.data)
                        return True
        
        return False
    
    def _should_stop_sequence(self, recipient_data: Dict, stop_conditions: List[str]) -> bool:
        """Check if sequence should stop based on events"""
        event_types = [e['type'] for e in recipient_data['events']]
        
        for condition in stop_conditions:
            if condition in event_types:
                return True
        
        return False
    
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
        
        # Calculate detailed stats
        stats = campaign['stats'].copy()
        stats['campaign_id'] = campaign_id
        stats['sequence_name'] = campaign['sequence_name']
        stats['started_at'] = campaign['started_at']
        stats['status'] = campaign['status']
        
        # Calculate rates
        if stats['total_recipients'] > 0:
            stats['completion_rate'] = round(
                stats['sequences_completed'] / stats['total_recipients'] * 100, 2
            )
        
        if stats['emails_sent'] > 0:
            stats['open_rate'] = round(stats['emails_opened'] / stats['emails_sent'] * 100, 2)
            stats['click_rate'] = round(stats['emails_clicked'] / stats['emails_sent'] * 100, 2)
            stats['reply_rate'] = round(stats['emails_replied'] / stats['emails_sent'] * 100, 2)
        
        return stats
    
    def pause_campaign(self, campaign_id: str):
        """Pause a campaign"""
        if campaign_id in self.data['active_campaigns']:
            self.data['active_campaigns'][campaign_id]['status'] = 'paused'
            save_sequences(self.data)
    
    def resume_campaign(self, campaign_id: str):
        """Resume a paused campaign"""
        if campaign_id in self.data['active_campaigns']:
            self.data['active_campaigns'][campaign_id]['status'] = 'active'
            save_sequences(self.data)
    
    def stop_campaign(self, campaign_id: str):
        """Stop a campaign permanently"""
        if campaign_id in self.data['active_campaigns']:
            self.data['active_campaigns'][campaign_id]['status'] = 'stopped'
            save_sequences(self.data)
