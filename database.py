import os
import json
from datetime import datetime
from config import Config
from models import (
    create_company_profile, create_time_series_snapshot, 
    create_relationship_record, create_interaction_record,
    generate_id
)
from utils.sheetdb_crm import SheetDBCRM

# Initialize SheetDB CRM
crm = SheetDBCRM(Config.SHEETDB_API_URL)

def load_json_file(filepath, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default or {}
    return default or {}

def save_json_file(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

# ============================================================================
# COMPANIES DB
# ============================================================================

def load_companies_db():
    return load_json_file(Config.COMPANIES_FILE, {"companies": {}, "contacts": {}, "index_by_domain": {}})

def save_companies_db(db):
    save_json_file(Config.COMPANIES_FILE, db)

def get_or_create_company(name, domain=None):
    """Get existing company or create new one"""
    db = load_companies_db()
    
    # Try to find by domain first
    if domain:
        domain = domain.lower().replace('www.', '')
        if domain in db.get('index_by_domain', {}):
            company_id = db['index_by_domain'][domain]
            return db['companies'][company_id], False
    
    # Try to find by name (fuzzy)
    name_lower = name.lower().strip()
    for cid, company in db.get('companies', {}).items():
        if company['name'].lower() == name_lower:
            return company, False
    
    # Create new company
    company = create_company_profile()
    company['id'] = generate_id()
    company['name'] = name
    company['domain'] = domain or ""
    company['created_at'] = datetime.now().isoformat()
    company['updated_at'] = datetime.now().isoformat()
    
    db['companies'][company['id']] = company
    if domain:
        db['index_by_domain'][domain] = company['id']
    
    save_companies_db(db)
    return company, True

def update_company(company_id, updates):
    """Update a company record"""
    db = load_companies_db()
    if company_id in db['companies']:
        company = db['companies'][company_id]
        deep_merge(company, updates)
        company['updated_at'] = datetime.now().isoformat()
        save_companies_db(db)
        return company
    return None

def deep_merge(base, updates):
    """Deep merge updates into base dict"""
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value

# ============================================================================
# RELATIONSHIPS DB
# ============================================================================

def load_relationships_db():
    return load_json_file(Config.RELATIONSHIPS_FILE, {"relationships": {}, "interactions": {}, "index_by_company": {}})

def save_relationships_db(db):
    save_json_file(Config.RELATIONSHIPS_FILE, db)

def add_relationship(your_contact, target_contact_id, target_company_id, rel_type, strength, context):
    """Add a relationship record"""
    db = load_relationships_db()
    
    rel = create_relationship_record()
    rel['id'] = generate_id()
    rel['type'] = rel_type
    rel['your_contact_id'] = your_contact
    rel['target_contact_id'] = target_contact_id
    rel['target_company_id'] = target_company_id
    rel['strength'] = strength
    rel['context'] = context
    rel['created_at'] = datetime.now().isoformat()
    
    db['relationships'][rel['id']] = rel
    
    # Update index
    if target_company_id not in db['index_by_company']:
        db['index_by_company'][target_company_id] = []
    db['index_by_company'][target_company_id].append(rel['id'])
    
    save_relationships_db(db)
    return rel

def get_relationships_for_company(company_id):
    """Get all relationships for a target company"""
    db = load_relationships_db()
    rel_ids = db.get('index_by_company', {}).get(company_id, [])
    return [db['relationships'][rid] for rid in rel_ids if rid in db['relationships']]

def add_interaction(company_id, contact_id, interaction_type, direction, summary, outcome=None, learnings=None):
    """Log an interaction with a company/contact"""
    db = load_relationships_db()
    
    interaction = create_interaction_record()
    interaction['id'] = generate_id()
    interaction['company_id'] = company_id
    interaction['contact_id'] = contact_id
    interaction['type'] = interaction_type
    interaction['direction'] = direction
    interaction['date'] = datetime.now().isoformat()
    interaction['summary'] = summary
    interaction['outcome'] = outcome or "pending"
    interaction['key_learnings'] = learnings or []
    interaction['created_at'] = datetime.now().isoformat()
    
    db['interactions'][interaction['id']] = interaction
    
    save_relationships_db(db)
    
    # Update company engagement metrics
    companies_db = load_companies_db()
    if company_id in companies_db['companies']:
        company = companies_db['companies'][company_id]
        company['engagement']['total_touches'] += 1
        company['engagement']['last_touch_date'] = interaction['date']
        company['engagement']['last_touch_type'] = interaction_type
        save_companies_db(companies_db)
    
    return interaction

def get_interaction_history(company_id=None, contact_id=None, limit=50):
    """Get interaction history for a company or contact"""
    db = load_relationships_db()
    
    interactions = []
    for iid, interaction in db.get('interactions', {}).items():
        if company_id and interaction.get('company_id') != company_id:
            continue
        if contact_id and interaction.get('contact_id') != contact_id:
            continue
        interactions.append(interaction)
    
    # Sort by date descending
    interactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    return interactions[:limit]

# ============================================================================
# HISTORY DB
# ============================================================================

def load_history_db():
    return load_json_file(Config.HISTORY_FILE, {"snapshots": {}, "index_by_company": {}, "index_by_date": {}})

def save_history_db(db):
    save_json_file(Config.HISTORY_FILE, db)

def add_company_snapshot(company_id, snapshot_data):
    """Add a time-series snapshot for a company"""
    db = load_history_db()
    
    snapshot = create_time_series_snapshot()
    snapshot['id'] = generate_id()
    snapshot['company_id'] = company_id
    snapshot['snapshot_date'] = datetime.now().isoformat()
    snapshot['snapshot_type'] = snapshot_data.get('type', 'event_triggered')
    
    # Copy in provided data
    for key in ['employee_count', 'job_postings_count', 'news_sentiment_score', 
                'tech_stack_snapshot', 'events', 'raw_data', 'hiring_velocity',
                'momentum_score', 'sentiment_trend']:
        if key in snapshot_data:
            snapshot[key] = snapshot_data[key]
    
    # Compute changes vs previous snapshots
    company_snapshots = db.get('index_by_company', {}).get(company_id, [])
    if company_snapshots:
        # Get most recent snapshot for comparison
        prev_id = company_snapshots[-1]
        prev = db['snapshots'].get(prev_id, {})
        
        if prev.get('employee_count') and snapshot.get('employee_count'):
            snapshot['employee_change_30d'] = snapshot['employee_count'] - prev['employee_count']
    
    # Store snapshot
    db['snapshots'][snapshot['id']] = snapshot
    
    # Update indexes
    if company_id not in db['index_by_company']:
        db['index_by_company'][company_id] = []
    db['index_by_company'][company_id].append(snapshot['id'])
    
    date_key = datetime.now().strftime('%Y-%m-%d')
    if date_key not in db['index_by_date']:
        db['index_by_date'][date_key] = []
    db['index_by_date'][date_key].append(snapshot['id'])
    
    save_history_db(db)
    return snapshot

def get_company_history(company_id, limit=30):
    """Get historical snapshots for a company"""
    db = load_history_db()
    snapshot_ids = db.get('index_by_company', {}).get(company_id, [])
    
    snapshots = []
    for sid in snapshot_ids[-limit:]:
        if sid in db['snapshots']:
            snapshots.append(db['snapshots'][sid])
    
    return sorted(snapshots, key=lambda x: x.get('snapshot_date', ''), reverse=True)

def compute_company_trends(company_id):
    """Compute trends from historical data"""
    history = get_company_history(company_id, limit=90)
    
    if len(history) < 2:
        return {"has_history": False, "message": "Not enough historical data yet"}
    
    trends = {
        "has_history": True,
        "data_points": len(history),
        "date_range": {
            "start": history[-1].get('snapshot_date'),
            "end": history[0].get('snapshot_date')
        },
        "employee_trend": None,
        "sentiment_trend": None,
        "hiring_trend": None,
        "momentum": None,
        "notable_changes": []
    }
    
    # Compute employee trend
    employee_counts = [h.get('employee_count') for h in history if h.get('employee_count')]
    if len(employee_counts) >= 2:
        change = employee_counts[0] - employee_counts[-1]
        pct_change = (change / employee_counts[-1]) * 100 if employee_counts[-1] else 0
        trends['employee_trend'] = {
            "direction": "growing" if change > 0 else "shrinking" if change < 0 else "stable",
            "absolute_change": change,
            "percent_change": round(pct_change, 1)
        }
    
    # Compute sentiment trend
    sentiments = [h.get('news_sentiment_score') for h in history if h.get('news_sentiment_score') is not None]
    if len(sentiments) >= 2:
        avg_recent = sum(sentiments[:5]) / len(sentiments[:5])
        avg_older = sum(sentiments[-5:]) / len(sentiments[-5:])
        trends['sentiment_trend'] = {
            "direction": "improving" if avg_recent > avg_older else "declining" if avg_recent < avg_older else "stable",
            "recent_avg": round(avg_recent, 1),
            "older_avg": round(avg_older, 1)
        }
    
    # Collect notable events
    for h in history[:10]:
        if h.get('events'):
            for event in h['events']:
                trends['notable_changes'].append({
                    "date": h['snapshot_date'],
                    "event": event
                })
    
    return trends

# ============================================================================
# USERS & DATA
# ============================================================================

def load_users():
    return load_json_file(Config.USERS_FILE, {})

def save_users(users):
    save_json_file(Config.USERS_FILE, users)

def load_data():
    return load_json_file(Config.DATA_FILE, {})

def save_data(data):
    save_json_file(Config.DATA_FILE, data)

def get_user_context(email):
    """Get company context for a user"""
    context_file = f"{email}_company_context.json"
    return load_json_file(context_file, {})

def save_user_context(email, context):
    """Save company context for a user"""
    context_file = f"{email}_company_context.json"
    save_json_file(context_file, context)
