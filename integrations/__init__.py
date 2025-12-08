"""
REAL INTEGRATIONS
Not demo mode. Actual APIs that do actual things.
"""

from .email_sender import EmailSender, GmailSender, SendGridSender, SMTPSender
from .email_tracker import ReplyDetector
from .contact_enrichment import (
    ContactEnrichment,
    HunterIO,
    ZeroBounce,
    ClearbitEnrichment
)
from .linkedin_automation import (
    PhantomBuster,
    Waalaxy,
    MultiChannelSequence,
    LinkedInTracker,
    get_sequence_templates
)
from .calendar_integration import (
    CalendlyIntegration,
    CalComIntegration,
    GoogleCalendarIntegration,
    MeetingManager,
    BookingLinkManager,
    MeetingStatus,
    MeetingOutcome,
    handle_calendly_webhook,
    handle_calcom_webhook
)

__all__ = [
    # Email
    'EmailSender',
    'GmailSender', 
    'SendGridSender',
    'SMTPSender',
    'ReplyDetector',
    # Contact Enrichment
    'ContactEnrichment',
    'HunterIO',
    'ZeroBounce',
    'ClearbitEnrichment',
    # LinkedIn
    'PhantomBuster',
    'Waalaxy',
    'MultiChannelSequence',
    'LinkedInTracker',
    'get_sequence_templates',
    # Calendar
    'CalendlyIntegration',
    'CalComIntegration',
    'GoogleCalendarIntegration',
    'MeetingManager',
    'BookingLinkManager',
    'MeetingStatus',
    'MeetingOutcome',
    'handle_calendly_webhook',
    'handle_calcom_webhook'
]
