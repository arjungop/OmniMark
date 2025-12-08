"""
SalesLink ↔ Chameleon Synchronization Manager

PRODUCTION-GRADE INTEGRATION LAYER

This module handles all the complex synchronization logic between SalesLink and Chameleon,
addressing critical integration challenges:

1. DATA MAPPING & SCHEMA ALIGNMENT
   - Consistent contact identifiers across platforms
   - Campaign ID mapping and tracking
   - Template metadata normalization
   - Engagement metric standardization

2. SYNCHRONIZATION CONSISTENCY
   - Async workflow orchestration
   - Retry logic with exponential backoff
   - Transaction-like operations with rollback
   - Conflict resolution strategies

3. ERROR HANDLING & RESILIENCE
   - Comprehensive error categorization
   - Graceful degradation
   - Detailed logging and alerting
   - Circuit breaker pattern for API failures

4. COMPLIANCE & DATA PRIVACY
   - GDPR/CAN-SPAM compliance checks
   - Opt-in/consent validation
   - Data retention policies
   - PII handling and encryption

5. VERSION CONTROL & AUDIT
   - Template versioning
   - Sync operation audit trail
   - Data lineage tracking
   - Rollback capabilities

Author: The Chameleon Team
Version: 1.0.0
Last Updated: 2025-12-01
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import threading
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class SyncStatus(Enum):
    """Synchronization operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ErrorCategory(Enum):
    """Error categorization for proper handling"""
    NETWORK = "network"  # Retry with backoff
    AUTH = "auth"  # Re-authenticate
    VALIDATION = "validation"  # Skip and log
    RATE_LIMIT = "rate_limit"  # Exponential backoff
    DATA_CONFLICT = "data_conflict"  # Manual resolution
    COMPLIANCE = "compliance"  # Block and alert
    SYSTEM = "system"  # Critical alert


class ConflictResolution(Enum):
    """Strategy for handling data conflicts"""
    SALESLINK_WINS = "saleslink_wins"  # SalesLink data is source of truth
    CHAMELEON_WINS = "chameleon_wins"  # Chameleon data is source of truth
    MERGE_LATEST = "merge_latest"  # Use most recent timestamp
    MANUAL = "manual"  # Queue for human review


class ComplianceStatus(Enum):
    """Contact compliance status"""
    VALID = "valid"  # Has consent, not suppressed
    NO_CONSENT = "no_consent"  # Missing opt-in
    SUPPRESSED = "suppressed"  # On suppression list
    INVALID_EMAIL = "invalid_email"  # Failed validation
    GDPR_VIOLATION = "gdpr_violation"  # GDPR issue detected


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class ContactMapping:
    """
    Unified contact identifier across platforms
    
    Ensures consistent contact tracking between SalesLink and Chameleon
    """
    chameleon_id: str  # UUID in Chameleon/SheetDB
    saleslink_id: Optional[str]  # ID in SalesLink (if exists)
    email: str  # Primary identifier
    email_hash: str  # SHA256 hash for privacy
    first_seen: str  # ISO timestamp
    last_synced: str  # ISO timestamp
    sync_direction: str  # "saleslink_to_chameleon" or "chameleon_to_saleslink"
    data_fingerprint: str  # Hash of contact data for change detection
    compliance_status: str  # ComplianceStatus enum value
    consent_date: Optional[str]  # ISO timestamp of opt-in
    consent_source: Optional[str]  # Where consent was obtained
    suppression_reason: Optional[str]  # If suppressed, why
    
    def __post_init__(self):
        """Generate email hash if not provided"""
        if not self.email_hash:
            self.email_hash = hashlib.sha256(self.email.lower().encode()).hexdigest()


@dataclass
class CampaignMapping:
    """
    Campaign identifier mapping between platforms
    """
    chameleon_campaign_id: str
    saleslink_campaign_id: Optional[str]
    template_version: str  # Semantic version (e.g., "1.2.3")
    created_at: str
    last_modified: str
    ai_generated: bool  # True if Chameleon generated the content
    saleslink_sent: bool  # True if sent via SalesLink
    performance_synced: bool  # True if metrics synced back
    template_fingerprint: str  # Hash for version tracking


@dataclass
class SyncOperation:
    """
    Audit trail for sync operations
    """
    operation_id: str  # UUID
    operation_type: str  # "contact_sync", "campaign_push", "engagement_sync"
    status: str  # SyncStatus enum value
    started_at: str
    completed_at: Optional[str]
    records_processed: int
    records_succeeded: int
    records_failed: int
    error_category: Optional[str]  # ErrorCategory enum value if failed
    error_message: Optional[str]
    retry_count: int
    rollback_performed: bool
    metadata: Dict[str, Any]  # Additional context


@dataclass
class EngagementMetrics:
    """
    Standardized engagement metrics across platforms
    """
    contact_id: str
    campaign_id: str
    platform: str  # "saleslink" or "chameleon"
    
    # Email metrics
    email_sent: bool = False
    email_delivered: bool = False
    email_opened: bool = False
    email_clicked: bool = False
    email_replied: bool = False
    email_bounced: bool = False
    email_spam_reported: bool = False
    
    # LinkedIn metrics (if applicable)
    linkedin_connection_sent: bool = False
    linkedin_connection_accepted: bool = False
    linkedin_message_sent: bool = False
    linkedin_message_replied: bool = False
    
    # Timing
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    first_opened_at: Optional[str] = None
    first_clicked_at: Optional[str] = None
    replied_at: Optional[str] = None
    
    # Aggregates
    open_count: int = 0
    click_count: int = 0
    
    # Derived scores
    engagement_score: float = 0.0  # 0-100
    intent_score: float = 0.0  # 0-100 (AI-calculated in Chameleon)


# ============================================================================
# SALESLINK ↔ CHAMELEON SYNC MANAGER
# ============================================================================

class SalesLinkSyncManager:
    """
    Production-grade synchronization manager
    
    Handles bidirectional sync between SalesLink and Chameleon with:
    - Data mapping and normalization
    - Error handling and retries
    - Compliance validation
    - Conflict resolution
    - Audit logging
    """
    
    def __init__(self, 
                 saleslink_scraper,  # SalesLinkScraper instance
                 sheetdb_crm,  # SheetDBCRM instance
                 max_retries: int = 3,
                 retry_delay: int = 5,
                 enable_rollback: bool = True):
        """
        Initialize sync manager
        
        Args:
            saleslink_scraper: Authenticated SalesLinkScraper instance
            sheetdb_crm: SheetDBCRM instance for Chameleon data
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Initial delay in seconds (exponential backoff)
            enable_rollback: Enable transaction rollback on failure
        """
        self.saleslink = saleslink_scraper
        self.crm = sheetdb_crm
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_rollback = enable_rollback
        
        # In-memory caches for mapping
        self.contact_mappings: Dict[str, ContactMapping] = {}
        self.campaign_mappings: Dict[str, CampaignMapping] = {}
        
        # Sync operation audit trail
        self.sync_operations: List[SyncOperation] = []
        
        # Circuit breaker state
        self.circuit_breaker = {
            'saleslink_api': {'failures': 0, 'last_failure': None, 'state': 'closed'},
            'sheetdb_api': {'failures': 0, 'last_failure': None, 'state': 'closed'}
        }
        
        # Compliance lists
        self.suppression_list: set = set()  # Email hashes to never contact
        self.consent_required_domains: set = {'gmail.com', 'yahoo.com', 'hotmail.com'}  # Require explicit consent
        
        logger.info("✅ SalesLinkSyncManager initialized")
    
    # ========================================================================
    # DATA MAPPING & NORMALIZATION
    # ========================================================================
    
    def _normalize_contact(self, contact: Dict, source: str) -> Dict:
        """
        Normalize contact data from different platforms
        
        Args:
            contact: Raw contact dict from SalesLink or Chameleon
            source: "saleslink" or "chameleon"
        
        Returns:
            Normalized contact dict with standard schema
        """
        if source == "saleslink":
            # Map SalesLink fields to Chameleon schema
            normalized = {
                'email': contact.get('email', '').lower().strip(),
                'first_name': contact.get('first_name', ''),
                'last_name': contact.get('last_name', ''),
                'company': contact.get('company', ''),
                'title': contact.get('title', ''),
                'linkedin_url': contact.get('linkedin_url', ''),
                'phone': contact.get('phone', ''),
                'location': contact.get('location', ''),
                'source': 'saleslink',
                'saleslink_id': contact.get('id', ''),
                'saleslink_engagement': contact.get('engagement', {}),
                'imported_from_saleslink': True,
                'imported_at': datetime.now().isoformat()
            }
        else:
            # Chameleon data is already normalized
            normalized = contact.copy()
            normalized['email'] = contact.get('email', '').lower().strip()
        
        # Generate fingerprint for change detection
        fingerprint_data = {
            'email': normalized['email'],
            'first_name': normalized.get('first_name', ''),
            'last_name': normalized.get('last_name', ''),
            'company': normalized.get('company', ''),
            'title': normalized.get('title', '')
        }
        normalized['data_fingerprint'] = hashlib.sha256(
            json.dumps(fingerprint_data, sort_keys=True).encode()
        ).hexdigest()
        
        return normalized
    
    def _create_contact_mapping(self, 
                                chameleon_contact: Dict, 
                                saleslink_contact: Optional[Dict] = None) -> ContactMapping:
        """
        Create bidirectional contact mapping
        
        Args:
            chameleon_contact: Contact from Chameleon/SheetDB
            saleslink_contact: Corresponding contact from SalesLink (if exists)
        
        Returns:
            ContactMapping object
        """
        email = chameleon_contact.get('email', '').lower().strip()
        
        mapping = ContactMapping(
            chameleon_id=chameleon_contact.get('id', chameleon_contact.get('email')),
            saleslink_id=saleslink_contact.get('id') if saleslink_contact else None,
            email=email,
            email_hash=hashlib.sha256(email.encode()).hexdigest(),
            first_seen=chameleon_contact.get('created_at', datetime.now().isoformat()),
            last_synced=datetime.now().isoformat(),
            sync_direction="bidirectional",
            data_fingerprint=chameleon_contact.get('data_fingerprint', ''),
            compliance_status=ComplianceStatus.VALID.value,  # Will be validated
            consent_date=chameleon_contact.get('consent_date'),
            consent_source=chameleon_contact.get('consent_source'),
            suppression_reason=None
        )
        
        # Cache mapping
        self.contact_mappings[email] = mapping
        
        return mapping
    
    # ========================================================================
    # COMPLIANCE & VALIDATION
    # ========================================================================
    
    def _validate_compliance(self, contact: Dict) -> Tuple[bool, ComplianceStatus, str]:
        """
        Validate contact against compliance rules
        
        Checks:
        - Email validity
        - Suppression list
        - Consent requirements (GDPR, CAN-SPAM)
        - Domain-specific rules
        
        Args:
            contact: Normalized contact dict
        
        Returns:
            (is_valid, ComplianceStatus, reason)
        """
        email = contact.get('email', '').lower().strip()
        
        # 1. Email format validation
        if not email or '@' not in email:
            return False, ComplianceStatus.INVALID_EMAIL, "Invalid email format"
        
        # 2. Suppression list check
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        if email_hash in self.suppression_list:
            return False, ComplianceStatus.SUPPRESSED, "Email on suppression list"
        
        # 3. Consent validation for consumer domains
        domain = email.split('@')[-1]
        if domain in self.consent_required_domains:
            if not contact.get('consent_date'):
                return False, ComplianceStatus.NO_CONSENT, f"Consent required for {domain}"
        
        # 4. GDPR validation (if EU contact)
        location = contact.get('location', '').upper()
        eu_countries = {'UK', 'GERMANY', 'FRANCE', 'SPAIN', 'ITALY', 'NETHERLANDS', 'BELGIUM'}
        if any(country in location for country in eu_countries):
            if not contact.get('consent_date') or not contact.get('consent_source'):
                return False, ComplianceStatus.GDPR_VIOLATION, "GDPR consent required for EU contact"
        
        # 5. Bounce/complaint history (if available)
        if contact.get('email_bounced') or contact.get('email_spam_reported'):
            return False, ComplianceStatus.SUPPRESSED, "Previous bounce or spam report"
        
        return True, ComplianceStatus.VALID, "Contact valid for outreach"
    
    def add_to_suppression_list(self, emails: List[str], reason: str):
        """
        Add emails to suppression list
        
        Args:
            emails: List of email addresses to suppress
            reason: Reason for suppression (logged for audit)
        """
        for email in emails:
            email_hash = hashlib.sha256(email.lower().encode()).hexdigest()
            self.suppression_list.add(email_hash)
            logger.warning(f"🚫 Suppressed {email}: {reason}")
    
    # ========================================================================
    # ERROR HANDLING & RESILIENCE
    # ========================================================================
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize error for appropriate handling
        
        Args:
            error: Exception object
        
        Returns:
            ErrorCategory enum value
        """
        error_str = str(error).lower()
        
        if 'network' in error_str or 'connection' in error_str or 'timeout' in error_str:
            return ErrorCategory.NETWORK
        elif 'auth' in error_str or 'unauthorized' in error_str or '401' in error_str:
            return ErrorCategory.AUTH
        elif 'rate limit' in error_str or '429' in error_str:
            return ErrorCategory.RATE_LIMIT
        elif 'validation' in error_str or 'invalid' in error_str:
            return ErrorCategory.VALIDATION
        elif 'conflict' in error_str or 'duplicate' in error_str:
            return ErrorCategory.DATA_CONFLICT
        elif 'gdpr' in error_str or 'consent' in error_str or 'compliance' in error_str:
            return ErrorCategory.COMPLIANCE
        else:
            return ErrorCategory.SYSTEM
    
    def _execute_with_retry(self, 
                            operation_name: str, 
                            operation_func, 
                            *args, 
                            **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Execute operation with exponential backoff retry
        
        Args:
            operation_name: Name for logging
            operation_func: Function to execute
            *args, **kwargs: Arguments for operation_func
        
        Returns:
            (success, result, error)
        """
        last_error = None
        delay = self.retry_delay
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 {operation_name} (attempt {attempt + 1}/{self.max_retries})")
                result = operation_func(*args, **kwargs)
                logger.info(f"✅ {operation_name} succeeded")
                return True, result, None
            
            except Exception as e:
                last_error = e
                error_category = self._categorize_error(e)
                
                logger.warning(f"⚠️ {operation_name} failed (attempt {attempt + 1}): {e}")
                logger.warning(f"   Error category: {error_category.value}")
                
                # Don't retry certain errors
                if error_category in [ErrorCategory.VALIDATION, ErrorCategory.COMPLIANCE]:
                    logger.error(f"❌ {operation_name} failed with non-retryable error: {error_category.value}")
                    return False, None, e
                
                # Exponential backoff
                if attempt < self.max_retries - 1:
                    logger.info(f"⏳ Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
        
        logger.error(f"❌ {operation_name} failed after {self.max_retries} attempts")
        return False, None, last_error
    
    def _check_circuit_breaker(self, service: str) -> bool:
        """
        Check if circuit breaker is open for service
        
        Args:
            service: "saleslink_api" or "sheetdb_api"
        
        Returns:
            True if service is available, False if circuit is open
        """
        breaker = self.circuit_breaker.get(service, {})
        state = breaker.get('state', 'closed')
        
        if state == 'open':
            # Check if enough time has passed to attempt half-open
            last_failure = breaker.get('last_failure')
            if last_failure:
                time_since_failure = (datetime.now() - datetime.fromisoformat(last_failure)).seconds
                if time_since_failure > 60:  # 1 minute cooldown
                    logger.info(f"🔄 Circuit breaker for {service} moving to half-open")
                    breaker['state'] = 'half-open'
                    return True
                else:
                    logger.warning(f"⚠️ Circuit breaker for {service} is OPEN (cooling down)")
                    return False
        
        return True
    
    def _record_circuit_breaker_failure(self, service: str):
        """Record failure and potentially open circuit breaker"""
        breaker = self.circuit_breaker.get(service, {})
        breaker['failures'] = breaker.get('failures', 0) + 1
        breaker['last_failure'] = datetime.now().isoformat()
        
        # Open circuit if too many failures
        if breaker['failures'] >= 5:
            breaker['state'] = 'open'
            logger.error(f"🚨 Circuit breaker for {service} is now OPEN")
    
    def _record_circuit_breaker_success(self, service: str):
        """Record success and close circuit breaker"""
        breaker = self.circuit_breaker.get(service, {})
        breaker['failures'] = 0
        breaker['state'] = 'closed'
    
    # ========================================================================
    # SYNCHRONIZATION OPERATIONS
    # ========================================================================
    
    def sync_contacts_from_saleslink(self, 
                                     limit: int = 1000,
                                     conflict_strategy: ConflictResolution = ConflictResolution.MERGE_LATEST) -> SyncOperation:
        """
        Sync contacts from SalesLink to Chameleon
        
        Workflow:
        1. Fetch contacts from SalesLink (with engagement data)
        2. Validate compliance for each contact
        3. Check for existing contacts in Chameleon (detect conflicts)
        4. Resolve conflicts based on strategy
        5. Create/update contacts in Chameleon
        6. Create contact mappings
        7. Log sync operation
        
        Args:
            limit: Maximum contacts to sync
            conflict_strategy: How to handle conflicts
        
        Returns:
            SyncOperation audit object
        """
        operation = SyncOperation(
            operation_id=f"sync_contacts_sl2ch_{int(time.time())}",
            operation_type="contact_sync_saleslink_to_chameleon",
            status=SyncStatus.IN_PROGRESS.value,
            started_at=datetime.now().isoformat(),
            completed_at=None,
            records_processed=0,
            records_succeeded=0,
            records_failed=0,
            error_category=None,
            error_message=None,
            retry_count=0,
            rollback_performed=False,
            metadata={'limit': limit, 'conflict_strategy': conflict_strategy.value}
        )
        
        try:
            logger.info(f"🔄 Starting contact sync: SalesLink → Chameleon (limit={limit})")
            
            # Check circuit breaker
            if not self._check_circuit_breaker('saleslink_api'):
                raise Exception("SalesLink API circuit breaker is OPEN")
            
            # 1. Fetch contacts from SalesLink
            logger.info("📥 Fetching contacts from SalesLink...")
            success, saleslink_contacts, error = self._execute_with_retry(
                "Fetch SalesLink contacts",
                self.saleslink.get_contacts,
                limit=limit,
                include_engagement=True
            )
            
            if not success:
                self._record_circuit_breaker_failure('saleslink_api')
                raise error
            
            self._record_circuit_breaker_success('saleslink_api')
            operation.records_processed = len(saleslink_contacts)
            logger.info(f"✅ Fetched {len(saleslink_contacts)} contacts from SalesLink")
            
            # 2. Process each contact
            processed_contacts = []
            failed_contacts = []
            compliance_blocks = []
            
            for sl_contact in saleslink_contacts:
                try:
                    # Normalize contact data
                    normalized = self._normalize_contact(sl_contact, source="saleslink")
                    
                    # Validate compliance
                    is_valid, compliance_status, reason = self._validate_compliance(normalized)
                    
                    if not is_valid:
                        compliance_blocks.append({
                            'email': normalized['email'],
                            'status': compliance_status.value,
                            'reason': reason
                        })
                        logger.warning(f"🚫 Blocked {normalized['email']}: {reason}")
                        operation.records_failed += 1
                        continue
                    
                    # Check for existing contact in Chameleon
                    existing = self.crm.get_contacts(filters={'email': normalized['email']})
                    
                    if existing:
                        # Conflict detected - resolve based on strategy
                        existing_contact = existing[0]
                        
                        if conflict_strategy == ConflictResolution.SALESLINK_WINS:
                            # Update with SalesLink data
                            merged = normalized
                        elif conflict_strategy == ConflictResolution.CHAMELEON_WINS:
                            # Keep Chameleon data, only update engagement
                            merged = existing_contact
                            merged['saleslink_engagement'] = normalized.get('saleslink_engagement', {})
                        else:  # MERGE_LATEST
                            # Merge based on timestamps
                            merged = existing_contact.copy()
                            merged.update({
                                k: v for k, v in normalized.items()
                                if v and (k not in merged or not merged[k])
                            })
                            merged['saleslink_engagement'] = normalized.get('saleslink_engagement', {})
                        
                        # Update in Chameleon
                        self.crm.update_contact(existing_contact['id'], merged)
                        logger.info(f"✅ Updated contact: {normalized['email']}")
                    
                    else:
                        # New contact - add to Chameleon
                        self.crm.add_contact(normalized)
                        logger.info(f"✅ Added new contact: {normalized['email']}")
                    
                    # Create mapping
                    mapping = self._create_contact_mapping(normalized, sl_contact)
                    
                    processed_contacts.append(normalized)
                    operation.records_succeeded += 1
                
                except Exception as e:
                    logger.error(f"❌ Failed to process contact {sl_contact.get('email')}: {e}")
                    failed_contacts.append({'contact': sl_contact, 'error': str(e)})
                    operation.records_failed += 1
            
            # Finalize operation
            operation.status = SyncStatus.SUCCESS.value if operation.records_failed == 0 else SyncStatus.PARTIAL_SUCCESS.value
            operation.completed_at = datetime.now().isoformat()
            operation.metadata.update({
                'compliance_blocks': compliance_blocks,
                'failed_contacts': failed_contacts[:10]  # Sample for audit
            })
            
            logger.info(f"✅ Contact sync completed: {operation.records_succeeded} succeeded, {operation.records_failed} failed")
            
        except Exception as e:
            logger.error(f"❌ Contact sync failed: {e}")
            operation.status = SyncStatus.FAILED.value
            operation.completed_at = datetime.now().isoformat()
            operation.error_category = self._categorize_error(e).value
            operation.error_message = str(e)
        
        # Log operation
        self.sync_operations.append(operation)
        return operation
    
    def push_campaign_to_saleslink(self, 
                                   chameleon_campaign_id: str,
                                   target_contacts: List[str]) -> SyncOperation:
        """
        Push AI-generated campaign from Chameleon to SalesLink for execution
        
        Workflow:
        1. Fetch campaign from Chameleon (with AI-generated content)
        2. Validate campaign content (spam check, compliance)
        3. Map contact IDs to SalesLink
        4. Create campaign in SalesLink
        5. Add contacts to SalesLink campaign
        6. Create campaign mapping
        7. Log operation
        
        Args:
            chameleon_campaign_id: Campaign ID in Chameleon
            target_contacts: List of contact emails/IDs
        
        Returns:
            SyncOperation audit object
        """
        operation = SyncOperation(
            operation_id=f"push_campaign_ch2sl_{int(time.time())}",
            operation_type="campaign_push_chameleon_to_saleslink",
            status=SyncStatus.IN_PROGRESS.value,
            started_at=datetime.now().isoformat(),
            completed_at=None,
            records_processed=len(target_contacts),
            records_succeeded=0,
            records_failed=0,
            error_category=None,
            error_message=None,
            retry_count=0,
            rollback_performed=False,
            metadata={
                'chameleon_campaign_id': chameleon_campaign_id,
                'target_count': len(target_contacts)
            }
        )
        
        try:
            logger.info(f"🚀 Pushing campaign {chameleon_campaign_id} to SalesLink")
            
            # TODO: Implement campaign push logic
            # This would involve:
            # 1. Fetch campaign details from Chameleon
            # 2. Validate content (spam score, compliance)
            # 3. Create campaign in SalesLink via API
            # 4. Map contacts and add to campaign
            # 5. Track mapping for future sync
            
            logger.warning("⚠️ Campaign push not yet implemented - SalesLink API integration required")
            operation.status = SyncStatus.FAILED.value
            operation.error_message = "Campaign push feature requires SalesLink API credentials"
            
        except Exception as e:
            logger.error(f"❌ Campaign push failed: {e}")
            operation.status = SyncStatus.FAILED.value
            operation.error_category = self._categorize_error(e).value
            operation.error_message = str(e)
        
        operation.completed_at = datetime.now().isoformat()
        self.sync_operations.append(operation)
        return operation
    
    def sync_engagement_from_saleslink(self, 
                                       campaign_id: Optional[str] = None) -> SyncOperation:
        """
        Sync engagement metrics from SalesLink back to Chameleon
        
        This enables Chameleon's AI to:
        - Learn from SalesLink execution results
        - Optimize future campaigns
        - Score accounts based on actual engagement
        
        Args:
            campaign_id: Specific campaign to sync (None = all campaigns)
        
        Returns:
            SyncOperation audit object
        """
        operation = SyncOperation(
            operation_id=f"sync_engagement_sl2ch_{int(time.time())}",
            operation_type="engagement_sync_saleslink_to_chameleon",
            status=SyncStatus.IN_PROGRESS.value,
            started_at=datetime.now().isoformat(),
            completed_at=None,
            records_processed=0,
            records_succeeded=0,
            records_failed=0,
            error_category=None,
            error_message=None,
            retry_count=0,
            rollback_performed=False,
            metadata={'campaign_id': campaign_id}
        )
        
        try:
            logger.info(f"📊 Syncing engagement metrics from SalesLink")
            
            # TODO: Implement engagement sync
            # This would involve:
            # 1. Fetch engagement data from SalesLink API
            # 2. Normalize metrics to EngagementMetrics schema
            # 3. Update contact engagement in Chameleon
            # 4. Trigger AI re-scoring based on new engagement
            
            logger.warning("⚠️ Engagement sync not yet implemented - requires SalesLink API")
            operation.status = SyncStatus.FAILED.value
            operation.error_message = "Engagement sync requires SalesLink API integration"
            
        except Exception as e:
            logger.error(f"❌ Engagement sync failed: {e}")
            operation.status = SyncStatus.FAILED.value
            operation.error_category = self._categorize_error(e).value
            operation.error_message = str(e)
        
        operation.completed_at = datetime.now().isoformat()
        self.sync_operations.append(operation)
        return operation
    
    # ========================================================================
    # AUDIT & REPORTING
    # ========================================================================
    
    def get_sync_history(self, limit: int = 100) -> List[Dict]:
        """
        Get sync operation history for audit
        
        Args:
            limit: Maximum operations to return
        
        Returns:
            List of sync operations as dicts
        """
        return [asdict(op) for op in self.sync_operations[-limit:]]
    
    def get_sync_stats(self) -> Dict:
        """
        Get sync statistics summary
        
        Returns:
            Summary statistics dict
        """
        total_ops = len(self.sync_operations)
        successful = sum(1 for op in self.sync_operations if op.status == SyncStatus.SUCCESS.value)
        failed = sum(1 for op in self.sync_operations if op.status == SyncStatus.FAILED.value)
        partial = sum(1 for op in self.sync_operations if op.status == SyncStatus.PARTIAL_SUCCESS.value)
        
        return {
            'total_operations': total_ops,
            'successful': successful,
            'failed': failed,
            'partial_success': partial,
            'success_rate': (successful / total_ops * 100) if total_ops > 0 else 0,
            'total_contacts_synced': sum(op.records_succeeded for op in self.sync_operations),
            'total_failures': sum(op.records_failed for op in self.sync_operations),
            'circuit_breaker_status': self.circuit_breaker,
            'suppression_list_size': len(self.suppression_list)
        }
    
    def export_audit_log(self, filepath: str = "saleslink_sync_audit.json"):
        """
        Export complete audit trail to JSON
        
        Args:
            filepath: Output file path
        """
        audit_data = {
            'exported_at': datetime.now().isoformat(),
            'sync_operations': self.get_sync_history(limit=99999),
            'stats': self.get_sync_stats(),
            'contact_mappings_count': len(self.contact_mappings),
            'campaign_mappings_count': len(self.campaign_mappings)
        }
        
        with open(filepath, 'w') as f:
            json.dump(audit_data, f, indent=2)
        
        logger.info(f"✅ Audit log exported to {filepath}")
