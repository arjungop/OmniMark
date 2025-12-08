from datetime import datetime
import uuid

def generate_id():
    """Generate a unique ID"""
    return str(uuid.uuid4())[:12]

def create_company_profile():
    """Factory for structured company profiles"""
    return {
        "id": None,
        "name": "",
        "domain": "",
        "created_at": None,
        "updated_at": None,
        
        # Firmographics
        "firmographics": {
            "industry": "",
            "sub_industry": "",
            "employee_count": None,
            "employee_range": "",  # "1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"
            "revenue_range": "",   # "$0-1M", "$1-10M", "$10-50M", "$50-100M", "$100M+"
            "founding_year": None,
            "headquarters": {
                "city": "",
                "state": "",
                "country": ""
            },
            "company_type": "",    # "Private", "Public", "Subsidiary", "Nonprofit"
            "stock_ticker": None,
            "funding_stage": "",   # "Bootstrapped", "Seed", "Series A/B/C", "Public"
            "total_funding": None,
            "last_funding_date": None,
            "last_funding_amount": None
        },
        
        # Technographics
        "technographics": {
            "tech_stack": [],      # List of detected technologies
            "cloud_provider": [],  # AWS, GCP, Azure
            "crm": "",            # Salesforce, HubSpot, etc.
            "marketing_automation": "",
            "analytics": [],
            "payment_processor": "",
            "detected_tools": [],  # Full list with confidence scores
            "tech_sophistication_score": None  # 1-10
        },
        
        # Intent Signals
        "intent_signals": {
            "score": 0,           # 0-100 composite intent score
            "signals": [],        # List of signal objects
            "buying_stage": "",   # "Unaware", "Aware", "Considering", "Evaluating", "Deciding"
            "budget_indicators": [],
            "timeline_indicators": [],
            "pain_indicators": []
        },
        
        # ICP Matching
        "icp_match": {
            "score": 0,           # 0-100 match score
            "matching_criteria": [],
            "missing_criteria": [],
            "fit_tier": ""        # "Tier 1", "Tier 2", "Tier 3", "Disqualified"
        },
        
        # Competitive Intelligence
        "competitive_intel": {
            "known_vendors": [],   # What solutions they currently use
            "contract_renewal_dates": [],
            "competitor_relationships": [],
            "switching_likelihood": None  # 1-10
        },
        
        # Key People
        "key_contacts": [],  # List of contact objects
        
        # Account Status
        "account_status": {
            "stage": "prospect",  # "prospect", "lead", "opportunity", "customer", "churned"
            "owner": None,
            "priority": "medium",  # "critical", "high", "medium", "low"
            "tags": [],
            "lists": []
        },
        
        # Engagement Metrics
        "engagement": {
            "total_touches": 0,
            "last_touch_date": None,
            "last_touch_type": None,
            "response_rate": None,
            "meetings_held": 0,
            "emails_sent": 0,
            "emails_opened": 0,
            "emails_replied": 0
        }
    }

def create_contact_profile():
    """Factory for structured contact profiles"""
    return {
        "id": None,
        "company_id": None,
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "linkedin_url": "",
        "title": "",
        "department": "",
        "seniority": "",      # "C-Level", "VP", "Director", "Manager", "Individual Contributor"
        "is_decision_maker": False,
        "is_influencer": False,
        "is_champion": False,
        "persona_match": "",  # Which buyer persona they match
        "notes": "",
        "engagement_history": [],
        "mutual_connections": [],
        "created_at": None,
        "updated_at": None
    }

def create_relationship_record():
    """Factory for relationship/connection records"""
    return {
        "id": None,
        "type": "",           # "knows_personally", "linkedin_connection", "met_at_event", "warm_intro_possible", "cold"
        "your_contact_id": None,  # Person at your company
        "target_contact_id": None,  # Person at target company
        "target_company_id": None,
        "strength": 0,        # 1-10 relationship strength
        "context": "",        # How they know each other
        "last_interaction": None,
        "intro_requested": False,
        "intro_made": False,
        "notes": "",
        "created_at": None
    }

def create_interaction_record():
    """Factory for interaction/engagement history"""
    return {
        "id": None,
        "company_id": None,
        "contact_id": None,
        "type": "",           # "email", "call", "meeting", "linkedin", "event", "demo", "proposal"
        "direction": "",      # "outbound", "inbound"
        "date": None,
        "subject": "",
        "summary": "",
        "outcome": "",        # "positive", "neutral", "negative", "no_response"
        "next_steps": "",
        "sentiment": None,    # -1 to 1
        "key_learnings": [],  # What we learned about the account
        "objections_raised": [],
        "interests_expressed": [],
        "competitors_mentioned": [],
        "budget_discussed": False,
        "timeline_discussed": False,
        "decision_process_info": "",
        "created_by": None,
        "created_at": None
    }

def create_time_series_snapshot():
    """Factory for historical tracking"""
    return {
        "id": None,
        "company_id": None,
        "snapshot_date": None,
        "snapshot_type": "",  # "daily", "weekly", "event_triggered"
        
        # Point-in-time metrics
        "employee_count": None,
        "job_postings_count": None,
        "news_sentiment_score": None,
        "social_engagement": None,
        "website_traffic_rank": None,
        "tech_stack_snapshot": [],
        "funding_status": None,
        
        # Computed changes
        "employee_change_30d": None,
        "employee_change_90d": None,
        "hiring_velocity": None,  # jobs/month
        "sentiment_trend": "",    # "improving", "stable", "declining"
        "momentum_score": None,   # Composite momentum indicator
        
        # Event markers
        "events": [],  # Significant events that occurred
        
        "raw_data": {}  # Store raw scraped data for reprocessing
    }
