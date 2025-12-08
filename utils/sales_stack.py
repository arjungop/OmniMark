"""
SALES STACK INFRASTRUCTURE
The actual tools that make a sales platform useful

Features:
1. Intent Data - Real signals that indicate buying behavior
2. Lead Enrichment - Find contacts, emails, phones, social profiles
3. Outreach Execution - Send emails, track opens/clicks, automated follow-ups
4. Pipeline Management - Deal stages, forecasting, activity logging
"""

import os
import json
import re
import hashlib
import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

# ============================================================================
# DATA FILES
# ============================================================================

INTENT_DB = "intent_signals.json"
CONTACTS_DB = "contacts_db.json"
OUTREACH_DB = "outreach_db.json"
PIPELINE_DB = "pipeline_db.json"
SEQUENCES_DB = "sequences_db.json"
ACTIVITIES_DB = "activities_db.json"
EMAIL_TRACKING_DB = "email_tracking.json"

# ============================================================================
# 1. INTENT DATA SYSTEM
# ============================================================================

class IntentDataEngine:
    """
    Track buying signals that actually matter:
    - Funding announcements
    - Leadership changes
    - Hiring patterns (esp. for your solution area)
    - Technology changes
    - Product launches
    - Website visits (when we have tracking pixel)
    - Social engagement
    """
    
    SIGNAL_TYPES = {
        'funding': {'weight': 90, 'decay_days': 30},
        'leadership_change': {'weight': 85, 'decay_days': 45},
        'hiring_surge': {'weight': 80, 'decay_days': 21},
        'tech_adoption': {'weight': 75, 'decay_days': 60},
        'product_launch': {'weight': 70, 'decay_days': 30},
        'expansion': {'weight': 85, 'decay_days': 45},
        'website_visit': {'weight': 60, 'decay_days': 7},
        'content_engagement': {'weight': 50, 'decay_days': 14},
        'competitor_mention': {'weight': 70, 'decay_days': 30},
        'pain_indicator': {'weight': 80, 'decay_days': 21},
    }
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.db = self._load_db()
    
    def _load_db(self) -> Dict:
        if os.path.exists(INTENT_DB):
            with open(INTENT_DB, 'r') as f:
                return json.load(f)
        return {"signals": {}, "companies": {}, "tracking_pixels": {}}
    
    def _save_db(self):
        with open(INTENT_DB, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def track_signal(self, company_id: str, signal_type: str, details: Dict) -> Dict:
        """Record an intent signal for a company"""
        signal_id = str(uuid.uuid4())[:12]
        
        signal = {
            "id": signal_id,
            "company_id": company_id,
            "type": signal_type,
            "source": details.get("source", "manual"),
            "title": details.get("title", ""),
            "description": details.get("description", ""),
            "url": details.get("url", ""),
            "detected_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=self.SIGNAL_TYPES.get(signal_type, {}).get('decay_days', 30))).isoformat(),
            "weight": self.SIGNAL_TYPES.get(signal_type, {}).get('weight', 50),
            "metadata": details.get("metadata", {}),
            "user": self.user_email
        }
        
        if company_id not in self.db["signals"]:
            self.db["signals"][company_id] = []
        
        self.db["signals"][company_id].append(signal)
        self._save_db()
        
        return signal
    
    def get_company_signals(self, company_id: str, include_expired: bool = False) -> List[Dict]:
        """Get all intent signals for a company"""
        signals = self.db["signals"].get(company_id, [])
        
        if not include_expired:
            now = datetime.now()
            signals = [s for s in signals if datetime.fromisoformat(s["expires_at"]) > now]
        
        return sorted(signals, key=lambda x: x["detected_at"], reverse=True)
    
    def calculate_intent_score(self, company_id: str) -> int:
        """Calculate composite intent score (0-100)"""
        signals = self.get_company_signals(company_id)
        
        if not signals:
            return 0
        
        total_weight = 0
        max_weight = 0
        
        for signal in signals:
            # Apply time decay
            detected = datetime.fromisoformat(signal["detected_at"])
            expires = datetime.fromisoformat(signal["expires_at"])
            now = datetime.now()
            
            if now > expires:
                continue
            
            # Linear decay
            total_duration = (expires - detected).days
            remaining = (expires - now).days
            decay_factor = remaining / total_duration if total_duration > 0 else 1
            
            weighted_score = signal["weight"] * decay_factor
            total_weight += weighted_score
            max_weight += signal["weight"]
        
        # Normalize to 0-100
        if max_weight == 0:
            return 0
        
        raw_score = (total_weight / max_weight) * 100
        
        # Boost for multiple signals
        signal_count_bonus = min(len(signals) * 5, 20)  # Up to 20 point bonus
        
        return min(int(raw_score + signal_count_bonus), 100)
    
    def get_hot_accounts(self, limit: int = 20) -> List[Dict]:
        """Get accounts with highest intent scores"""
        accounts = []
        
        for company_id in self.db["signals"].keys():
            score = self.calculate_intent_score(company_id)
            signals = self.get_company_signals(company_id)
            
            if score > 0:
                accounts.append({
                    "company_id": company_id,
                    "intent_score": score,
                    "signal_count": len(signals),
                    "top_signals": signals[:3],
                    "latest_signal": signals[0] if signals else None
                })
        
        return sorted(accounts, key=lambda x: x["intent_score"], reverse=True)[:limit]
    
    def scan_for_signals(self, company_name: str, company_domain: str = None) -> List[Dict]:
        """Actively scan for intent signals for a company"""
        discovered_signals = []
        
        # 1. Check for funding news
        funding_signals = self._scan_funding(company_name)
        discovered_signals.extend(funding_signals)
        
        # 2. Check for hiring activity
        hiring_signals = self._scan_hiring(company_name, company_domain)
        discovered_signals.extend(hiring_signals)
        
        # 3. Check for leadership changes
        leadership_signals = self._scan_leadership(company_name)
        discovered_signals.extend(leadership_signals)
        
        # 4. Check technographics (what tools they use)
        if company_domain:
            tech_signals = self._scan_technographics(company_domain)
            discovered_signals.extend(tech_signals)
        
        return discovered_signals
    
    def _scan_funding(self, company_name: str) -> List[Dict]:
        """Scan for funding announcements"""
        signals = []
        try:
            # Search for funding news
            query = f"{company_name} funding round raised series"
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}&tbm=nws"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Parse news results for funding mentions
                for result in soup.select('div.SoaBEf')[:3]:
                    title = result.get_text()[:200]
                    if any(word in title.lower() for word in ['funding', 'raised', 'series', 'million', 'investment']):
                        signals.append({
                            "type": "funding",
                            "source": "news_scan",
                            "title": title[:100],
                            "description": f"Potential funding activity detected for {company_name}",
                            "url": "",
                            "metadata": {"search_query": query}
                        })
        except Exception as e:
            pass
        
        return signals
    
    def _scan_hiring(self, company_name: str, domain: str = None) -> List[Dict]:
        """Scan for hiring activity"""
        signals = []
        try:
            # Check LinkedIn jobs (simplified)
            query = f"site:linkedin.com/jobs {company_name}"
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_count = len(soup.select('div.g'))
                
                if job_count > 5:
                    signals.append({
                        "type": "hiring_surge",
                        "source": "linkedin_scan",
                        "title": f"{company_name} actively hiring",
                        "description": f"Found {job_count}+ job postings on LinkedIn",
                        "metadata": {"job_count": job_count}
                    })
        except Exception:
            pass
        
        return signals
    
    def _scan_leadership(self, company_name: str) -> List[Dict]:
        """Scan for leadership changes"""
        signals = []
        try:
            query = f'"{company_name}" "new CEO" OR "new CTO" OR "new VP" OR "hired" OR "appointed"'
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}&tbm=nws"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                for result in soup.select('div.SoaBEf')[:2]:
                    title = result.get_text()[:200]
                    if any(word in title.lower() for word in ['ceo', 'cto', 'cfo', 'vp', 'hired', 'appointed', 'joins']):
                        signals.append({
                            "type": "leadership_change",
                            "source": "news_scan",
                            "title": title[:100],
                            "description": f"Leadership change detected at {company_name}",
                            "metadata": {}
                        })
        except Exception:
            pass
        
        return signals
    
    def _scan_technographics(self, domain: str) -> List[Dict]:
        """Detect technology stack from website"""
        signals = []
        try:
            url = f"https://{domain}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.ok:
                html = response.text.lower()
                
                # Common tech indicators
                tech_stack = []
                tech_patterns = {
                    'salesforce': ['salesforce', 'sfdc', 'pardot'],
                    'hubspot': ['hubspot', 'hs-scripts', 'hscollectedforms'],
                    'marketo': ['marketo', 'munchkin'],
                    'intercom': ['intercom', 'intercomcdn'],
                    'drift': ['drift.com', 'js.driftt'],
                    'segment': ['segment.com', 'analytics.js', 'cdn.segment'],
                    'mixpanel': ['mixpanel.com'],
                    'amplitude': ['amplitude.com'],
                    'stripe': ['stripe.com', 'stripe.js'],
                    'aws': ['amazonaws.com', 'aws-sdk'],
                    'google_cloud': ['googleapis.com', 'google-cloud'],
                    'azure': ['azure', 'microsoft.com/azure'],
                    'shopify': ['shopify', 'myshopify'],
                    'wordpress': ['wp-content', 'wordpress'],
                    'react': ['react', 'reactdom'],
                    'angular': ['ng-', 'angular'],
                    'vue': ['vue.js', 'vuejs'],
                    'zendesk': ['zendesk.com', 'zdassets'],
                    'freshdesk': ['freshdesk.com'],
                    'slack': ['slack.com', 'slack-edge'],
                }
                
                for tech, patterns in tech_patterns.items():
                    if any(p in html for p in patterns):
                        tech_stack.append(tech)
                
                if tech_stack:
                    signals.append({
                        "type": "tech_adoption",
                        "source": "website_scan",
                        "title": f"Tech stack detected: {', '.join(tech_stack[:5])}",
                        "description": f"Using: {', '.join(tech_stack)}",
                        "metadata": {"tech_stack": tech_stack}
                    })
        except Exception:
            pass
        
        return signals


# ============================================================================
# 2. LEAD ENRICHMENT ENGINE
# ============================================================================

class LeadEnrichmentEngine:
    """
    Find contacts at companies:
    - Email addresses (using patterns + validation)
    - Phone numbers
    - LinkedIn profiles
    - Job titles and departments
    - Social profiles
    """
    
    EMAIL_PATTERNS = [
        "{first}.{last}@{domain}",
        "{first}{last}@{domain}",
        "{f}{last}@{domain}",
        "{first}_{last}@{domain}",
        "{first}@{domain}",
        "{last}@{domain}",
        "{f}.{last}@{domain}",
    ]
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.db = self._load_db()
    
    def _load_db(self) -> Dict:
        if os.path.exists(CONTACTS_DB):
            with open(CONTACTS_DB, 'r') as f:
                return json.load(f)
        return {"contacts": {}, "companies": {}, "email_patterns": {}}
    
    def _save_db(self):
        with open(CONTACTS_DB, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def create_contact(self, company_id: str, data: Dict) -> Dict:
        """Create a new contact"""
        contact_id = str(uuid.uuid4())[:12]
        
        contact = {
            "id": contact_id,
            "company_id": company_id,
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "full_name": data.get("full_name", f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()),
            "title": data.get("title", ""),
            "department": data.get("department", ""),
            "seniority": self._detect_seniority(data.get("title", "")),
            "email": data.get("email", ""),
            "email_status": data.get("email_status", "unknown"),  # verified, valid, invalid, unknown
            "phone": data.get("phone", ""),
            "phone_type": data.get("phone_type", ""),  # direct, mobile, office
            "linkedin_url": data.get("linkedin_url", ""),
            "twitter_url": data.get("twitter_url", ""),
            "location": data.get("location", ""),
            "persona_match": data.get("persona_match", ""),
            "is_decision_maker": self._is_decision_maker(data.get("title", "")),
            "is_influencer": self._is_influencer(data.get("title", "")),
            "enrichment_source": data.get("source", "manual"),
            "enriched_at": datetime.now().isoformat(),
            "confidence": data.get("confidence", 0.5),
            "tags": data.get("tags", []),
            "notes": data.get("notes", ""),
            "created_at": datetime.now().isoformat(),
            "created_by": self.user_email
        }
        
        self.db["contacts"][contact_id] = contact
        
        # Index by company
        if company_id not in self.db["companies"]:
            self.db["companies"][company_id] = []
        self.db["companies"][company_id].append(contact_id)
        
        self._save_db()
        return contact
    
    def get_contacts_for_company(self, company_id: str) -> List[Dict]:
        """Get all contacts for a company"""
        contact_ids = self.db["companies"].get(company_id, [])
        return [self.db["contacts"][cid] for cid in contact_ids if cid in self.db["contacts"]]
    
    def find_contacts(self, company_name: str, company_domain: str, target_titles: List[str] = None) -> List[Dict]:
        """Find contacts at a company"""
        contacts = []
        
        # 1. Search LinkedIn (via Google)
        linkedin_contacts = self._search_linkedin(company_name, target_titles)
        contacts.extend(linkedin_contacts)
        
        # 2. Generate email addresses for found contacts
        for contact in contacts:
            if not contact.get("email") and contact.get("first_name") and contact.get("last_name"):
                guessed_emails = self.guess_email(
                    contact["first_name"],
                    contact["last_name"],
                    company_domain
                )
                if guessed_emails:
                    contact["email"] = guessed_emails[0]["email"]
                    contact["email_status"] = "guessed"
                    contact["email_alternatives"] = guessed_emails[1:] if len(guessed_emails) > 1 else []
        
        return contacts
    
    def guess_email(self, first_name: str, last_name: str, domain: str) -> List[Dict]:
        """Generate likely email addresses based on common patterns"""
        emails = []
        
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        f = first[0] if first else ""
        
        for pattern in self.EMAIL_PATTERNS:
            email = pattern.format(
                first=first,
                last=last,
                f=f,
                domain=domain
            )
            
            # Calculate confidence based on pattern commonality
            confidence = 0.7 if pattern == "{first}.{last}@{domain}" else 0.5
            
            emails.append({
                "email": email,
                "pattern": pattern,
                "confidence": confidence,
                "status": "unverified"
            })
        
        return emails
    
    def verify_email(self, email: str) -> Dict:
        """Verify if an email address is valid (basic check)"""
        result = {
            "email": email,
            "valid_format": False,
            "domain_exists": False,
            "deliverable": "unknown",
            "confidence": 0
        }
        
        # Check format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            result["valid_format"] = True
            result["confidence"] += 0.3
        
        # Check domain MX records
        try:
            import dns.resolver
            domain = email.split('@')[1]
            mx_records = dns.resolver.resolve(domain, 'MX')
            if mx_records:
                result["domain_exists"] = True
                result["confidence"] += 0.4
        except:
            # If dns.resolver not available, just check domain responds
            try:
                domain = email.split('@')[1]
                response = requests.head(f"https://{domain}", timeout=5)
                if response.ok:
                    result["domain_exists"] = True
                    result["confidence"] += 0.3
            except:
                pass
        
        return result
    
    def _search_linkedin(self, company_name: str, target_titles: List[str] = None) -> List[Dict]:
        """Search for contacts via LinkedIn (through Google)"""
        contacts = []
        
        try:
            # Build search query
            titles_query = " OR ".join([f'"{t}"' for t in (target_titles or ["CEO", "VP", "Director"])[:3]])
            query = f'site:linkedin.com/in "{company_name}" ({titles_query})'
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for result in soup.select('div.g')[:5]:
                    title_elem = result.select_one('h3')
                    link_elem = result.select_one('a')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text()
                        link = link_elem.get('href', '')
                        
                        # Parse LinkedIn result
                        if 'linkedin.com/in/' in link:
                            # Try to extract name and title from result
                            parsed = self._parse_linkedin_result(title)
                            if parsed:
                                parsed["linkedin_url"] = link
                                parsed["source"] = "linkedin_search"
                                parsed["confidence"] = 0.6
                                contacts.append(parsed)
        except Exception as e:
            pass
        
        return contacts
    
    def _parse_linkedin_result(self, title: str) -> Optional[Dict]:
        """Parse a LinkedIn search result title"""
        # Title format: "Name - Title - Company | LinkedIn"
        try:
            parts = title.replace(' | LinkedIn', '').split(' - ')
            if len(parts) >= 2:
                name_parts = parts[0].strip().split(' ')
                return {
                    "first_name": name_parts[0] if name_parts else "",
                    "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                    "full_name": parts[0].strip(),
                    "title": parts[1].strip() if len(parts) > 1 else "",
                }
        except:
            pass
        return None
    
    def _detect_seniority(self, title: str) -> str:
        """Detect seniority level from job title"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['ceo', 'cto', 'cfo', 'coo', 'chief', 'founder', 'president', 'owner']):
            return "c_level"
        elif any(word in title_lower for word in ['vp', 'vice president', 'svp', 'evp']):
            return "vp"
        elif any(word in title_lower for word in ['director', 'head of']):
            return "director"
        elif any(word in title_lower for word in ['manager', 'lead', 'senior']):
            return "manager"
        else:
            return "individual_contributor"
    
    def _is_decision_maker(self, title: str) -> bool:
        """Check if title indicates decision-making authority"""
        title_lower = title.lower()
        dm_keywords = ['ceo', 'cto', 'cfo', 'coo', 'chief', 'founder', 'president', 'owner', 'vp', 'vice president', 'director', 'head of']
        return any(word in title_lower for word in dm_keywords)
    
    def _is_influencer(self, title: str) -> bool:
        """Check if title indicates influencer role"""
        title_lower = title.lower()
        influencer_keywords = ['manager', 'lead', 'senior', 'architect', 'principal', 'specialist', 'analyst']
        return any(word in title_lower for word in influencer_keywords)


# ============================================================================
# 3. OUTREACH EXECUTION ENGINE
# ============================================================================

class OutreachEngine:
    """
    Execute multi-channel outreach:
    - Email sending with tracking
    - Automated sequences/cadences
    - Open/click/reply tracking
    - Multi-channel (email, LinkedIn, phone)
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.db = self._load_db()
        self.tracking_db = self._load_tracking_db()
        self.sequences_db = self._load_sequences_db()
    
    def _load_db(self) -> Dict:
        if os.path.exists(OUTREACH_DB):
            with open(OUTREACH_DB, 'r') as f:
                return json.load(f)
        return {"emails": {}, "sequences": {}, "queue": []}
    
    def _save_db(self):
        with open(OUTREACH_DB, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def _load_tracking_db(self) -> Dict:
        if os.path.exists(EMAIL_TRACKING_DB):
            with open(EMAIL_TRACKING_DB, 'r') as f:
                return json.load(f)
        return {"opens": {}, "clicks": {}, "replies": {}, "bounces": {}}
    
    def _save_tracking_db(self):
        with open(EMAIL_TRACKING_DB, 'w') as f:
            json.dump(self.tracking_db, f, indent=2)
    
    def _load_sequences_db(self) -> Dict:
        if os.path.exists(SEQUENCES_DB):
            with open(SEQUENCES_DB, 'r') as f:
                return json.load(f)
        return {"sequences": {}, "enrollments": {}}
    
    def _save_sequences_db(self):
        with open(SEQUENCES_DB, 'w') as f:
            json.dump(self.sequences_db, f, indent=2)
    
    def create_email(self, contact_id: str, company_id: str, data: Dict) -> Dict:
        """Create an email to send"""
        email_id = str(uuid.uuid4())[:12]
        
        email = {
            "id": email_id,
            "contact_id": contact_id,
            "company_id": company_id,
            "to_email": data.get("to_email", ""),
            "to_name": data.get("to_name", ""),
            "from_email": data.get("from_email", self.user_email),
            "from_name": data.get("from_name", ""),
            "subject": data.get("subject", ""),
            "body_html": data.get("body_html", ""),
            "body_text": data.get("body_text", ""),
            "status": "draft",  # draft, queued, sent, delivered, bounced, replied
            "sequence_id": data.get("sequence_id"),
            "sequence_step": data.get("sequence_step"),
            "channel": "email",
            "tracking_id": str(uuid.uuid4()),
            "scheduled_at": data.get("scheduled_at"),
            "sent_at": None,
            "opened_at": None,
            "clicked_at": None,
            "replied_at": None,
            "bounced_at": None,
            "created_at": datetime.now().isoformat(),
            "created_by": self.user_email
        }
        
        self.db["emails"][email_id] = email
        self._save_db()
        
        return email
    
    def queue_email(self, email_id: str, send_at: datetime = None) -> Dict:
        """Add email to sending queue"""
        email = self.db["emails"].get(email_id)
        if not email:
            return {"error": "Email not found"}
        
        email["status"] = "queued"
        email["scheduled_at"] = (send_at or datetime.now()).isoformat()
        
        self.db["queue"].append({
            "email_id": email_id,
            "scheduled_at": email["scheduled_at"],
            "priority": 1
        })
        
        self._save_db()
        return email
    
    def send_email(self, email_id: str, smtp_config: Dict = None) -> Dict:
        """Actually send an email (requires SMTP config)"""
        email = self.db["emails"].get(email_id)
        if not email:
            return {"error": "Email not found"}
        
        if not smtp_config:
            # Mark as sent for demo purposes
            email["status"] = "sent"
            email["sent_at"] = datetime.now().isoformat()
            self._save_db()
            return {"status": "sent_demo", "message": "Email marked as sent (no SMTP configured)"}
        
        try:
            # Real SMTP sending
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email["subject"]
            msg['From'] = f"{email['from_name']} <{email['from_email']}>"
            msg['To'] = email["to_email"]
            
            # Add tracking pixel
            tracking_pixel = f'<img src="{smtp_config.get("tracking_url", "")}/track/{email["tracking_id"]}/open.gif" width="1" height="1" />'
            body_with_tracking = email["body_html"] + tracking_pixel
            
            msg.attach(MIMEText(email["body_text"], 'plain'))
            msg.attach(MIMEText(body_with_tracking, 'html'))
            
            with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
                server.starttls()
                server.login(smtp_config["username"], smtp_config["password"])
                server.sendmail(email["from_email"], email["to_email"], msg.as_string())
            
            email["status"] = "sent"
            email["sent_at"] = datetime.now().isoformat()
            self._save_db()
            
            return {"status": "sent", "email_id": email_id}
        except Exception as e:
            email["status"] = "failed"
            email["error"] = str(e)
            self._save_db()
            return {"status": "failed", "error": str(e)}
    
    def track_open(self, tracking_id: str) -> bool:
        """Record email open"""
        for email_id, email in self.db["emails"].items():
            if email.get("tracking_id") == tracking_id:
                if not email.get("opened_at"):
                    email["opened_at"] = datetime.now().isoformat()
                    
                    if tracking_id not in self.tracking_db["opens"]:
                        self.tracking_db["opens"][tracking_id] = []
                    
                    self.tracking_db["opens"][tracking_id].append({
                        "timestamp": datetime.now().isoformat(),
                        "email_id": email_id
                    })
                    
                    self._save_db()
                    self._save_tracking_db()
                return True
        return False
    
    def track_click(self, tracking_id: str, url: str) -> bool:
        """Record link click"""
        for email_id, email in self.db["emails"].items():
            if email.get("tracking_id") == tracking_id:
                if not email.get("clicked_at"):
                    email["clicked_at"] = datetime.now().isoformat()
                
                if tracking_id not in self.tracking_db["clicks"]:
                    self.tracking_db["clicks"][tracking_id] = []
                
                self.tracking_db["clicks"][tracking_id].append({
                    "timestamp": datetime.now().isoformat(),
                    "email_id": email_id,
                    "url": url
                })
                
                self._save_db()
                self._save_tracking_db()
                return True
        return False
    
    def track_reply(self, email_id: str) -> bool:
        """Record reply received"""
        email = self.db["emails"].get(email_id)
        if email:
            email["status"] = "replied"
            email["replied_at"] = datetime.now().isoformat()
            self._save_db()
            return True
        return False
    
    def create_sequence(self, name: str, steps: List[Dict]) -> Dict:
        """Create an email sequence/cadence"""
        sequence_id = str(uuid.uuid4())[:12]
        
        sequence = {
            "id": sequence_id,
            "name": name,
            "status": "active",
            "steps": [],
            "created_at": datetime.now().isoformat(),
            "created_by": self.user_email,
            "stats": {
                "enrolled": 0,
                "completed": 0,
                "replied": 0,
                "bounced": 0
            }
        }
        
        for i, step in enumerate(steps):
            sequence["steps"].append({
                "step_number": i + 1,
                "channel": step.get("channel", "email"),
                "delay_days": step.get("delay_days", 3),
                "subject": step.get("subject", ""),
                "body": step.get("body", ""),
                "is_auto": step.get("is_auto", True)
            })
        
        self.sequences_db["sequences"][sequence_id] = sequence
        self._save_sequences_db()
        
        return sequence
    
    def enroll_in_sequence(self, sequence_id: str, contact_id: str, company_id: str) -> Dict:
        """Enroll a contact in a sequence"""
        sequence = self.sequences_db["sequences"].get(sequence_id)
        if not sequence:
            return {"error": "Sequence not found"}
        
        enrollment_id = str(uuid.uuid4())[:12]
        
        enrollment = {
            "id": enrollment_id,
            "sequence_id": sequence_id,
            "contact_id": contact_id,
            "company_id": company_id,
            "status": "active",  # active, paused, completed, replied, bounced
            "current_step": 1,
            "enrolled_at": datetime.now().isoformat(),
            "next_step_at": datetime.now().isoformat(),
            "completed_steps": []
        }
        
        self.sequences_db["enrollments"][enrollment_id] = enrollment
        self.sequences_db["sequences"][sequence_id]["stats"]["enrolled"] += 1
        self._save_sequences_db()
        
        return enrollment
    
    def get_sequence_stats(self, sequence_id: str) -> Dict:
        """Get statistics for a sequence"""
        sequence = self.sequences_db["sequences"].get(sequence_id)
        if not sequence:
            return {"error": "Sequence not found"}
        
        enrollments = [e for e in self.sequences_db["enrollments"].values() if e["sequence_id"] == sequence_id]
        
        stats = {
            "sequence_id": sequence_id,
            "name": sequence["name"],
            "total_enrolled": len(enrollments),
            "active": len([e for e in enrollments if e["status"] == "active"]),
            "completed": len([e for e in enrollments if e["status"] == "completed"]),
            "replied": len([e for e in enrollments if e["status"] == "replied"]),
            "bounced": len([e for e in enrollments if e["status"] == "bounced"]),
            "step_metrics": []
        }
        
        return stats
    
    def get_pending_outreach(self) -> List[Dict]:
        """Get all pending outreach items"""
        pending = []
        
        for email in self.db["emails"].values():
            if email["status"] in ["draft", "queued"]:
                pending.append(email)
        
        return sorted(pending, key=lambda x: x.get("scheduled_at") or x["created_at"])


# ============================================================================
# 4. PIPELINE MANAGEMENT
# ============================================================================

class PipelineEngine:
    """
    Full CRM pipeline functionality:
    - Deal stages
    - Activity logging
    - Forecasting
    - Win/loss tracking
    - Analytics
    """
    
    DEFAULT_STAGES = [
        {"id": "prospect", "name": "Prospect", "order": 1, "probability": 0.1},
        {"id": "qualified", "name": "Qualified", "order": 2, "probability": 0.2},
        {"id": "meeting", "name": "Meeting Scheduled", "order": 3, "probability": 0.4},
        {"id": "proposal", "name": "Proposal", "order": 4, "probability": 0.6},
        {"id": "negotiation", "name": "Negotiation", "order": 5, "probability": 0.8},
        {"id": "closed_won", "name": "Closed Won", "order": 6, "probability": 1.0},
        {"id": "closed_lost", "name": "Closed Lost", "order": 7, "probability": 0.0},
    ]
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.db = self._load_db()
        self.activities_db = self._load_activities_db()
    
    def _load_db(self) -> Dict:
        if os.path.exists(PIPELINE_DB):
            with open(PIPELINE_DB, 'r') as f:
                return json.load(f)
        return {
            "deals": {},
            "stages": {s["id"]: s for s in self.DEFAULT_STAGES},
            "pipelines": {"default": {"name": "Sales Pipeline", "stages": [s["id"] for s in self.DEFAULT_STAGES]}}
        }
    
    def _save_db(self):
        with open(PIPELINE_DB, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def _load_activities_db(self) -> Dict:
        if os.path.exists(ACTIVITIES_DB):
            with open(ACTIVITIES_DB, 'r') as f:
                return json.load(f)
        return {"activities": {}, "by_deal": {}, "by_company": {}}
    
    def _save_activities_db(self):
        with open(ACTIVITIES_DB, 'w') as f:
            json.dump(self.activities_db, f, indent=2)
    
    def create_deal(self, data: Dict) -> Dict:
        """Create a new deal"""
        deal_id = str(uuid.uuid4())[:12]
        
        deal = {
            "id": deal_id,
            "name": data.get("name", "New Deal"),
            "company_id": data.get("company_id"),
            "company_name": data.get("company_name", ""),
            "contact_ids": data.get("contact_ids", []),
            "stage": data.get("stage", "prospect"),
            "pipeline": data.get("pipeline", "default"),
            "value": data.get("value", 0),
            "currency": data.get("currency", "USD"),
            "probability": self.db["stages"].get(data.get("stage", "prospect"), {}).get("probability", 0.1),
            "expected_close_date": data.get("expected_close_date"),
            "actual_close_date": None,
            "win_reason": None,
            "loss_reason": None,
            "competitor": data.get("competitor"),
            "source": data.get("source", "outbound"),
            "owner": self.user_email,
            "tags": data.get("tags", []),
            "notes": data.get("notes", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "stage_history": [{
                "stage": data.get("stage", "prospect"),
                "entered_at": datetime.now().isoformat(),
                "moved_by": self.user_email
            }]
        }
        
        self.db["deals"][deal_id] = deal
        self._save_db()
        
        # Log activity
        self.log_activity(deal_id, {
            "type": "deal_created",
            "description": f"Deal created: {deal['name']}"
        })
        
        return deal
    
    def update_deal(self, deal_id: str, updates: Dict) -> Dict:
        """Update a deal"""
        deal = self.db["deals"].get(deal_id)
        if not deal:
            return {"error": "Deal not found"}
        
        old_stage = deal["stage"]
        
        for key, value in updates.items():
            if key in deal and key not in ["id", "created_at", "stage_history"]:
                deal[key] = value
        
        deal["updated_at"] = datetime.now().isoformat()
        
        # Track stage changes
        if updates.get("stage") and updates["stage"] != old_stage:
            deal["probability"] = self.db["stages"].get(updates["stage"], {}).get("probability", 0)
            deal["stage_history"].append({
                "stage": updates["stage"],
                "entered_at": datetime.now().isoformat(),
                "moved_by": self.user_email,
                "from_stage": old_stage
            })
            
            # Handle closed deals
            if updates["stage"] == "closed_won":
                deal["actual_close_date"] = datetime.now().isoformat()
            elif updates["stage"] == "closed_lost":
                deal["actual_close_date"] = datetime.now().isoformat()
            
            # Log activity
            self.log_activity(deal_id, {
                "type": "stage_changed",
                "description": f"Stage changed from {old_stage} to {updates['stage']}"
            })
        
        self._save_db()
        return deal
    
    def move_to_stage(self, deal_id: str, new_stage: str, notes: str = "") -> Dict:
        """Move a deal to a new stage"""
        return self.update_deal(deal_id, {"stage": new_stage, "notes": notes})
    
    def log_activity(self, deal_id: str, activity_data: Dict) -> Dict:
        """Log an activity against a deal"""
        activity_id = str(uuid.uuid4())[:12]
        
        deal = self.db["deals"].get(deal_id, {})
        
        activity = {
            "id": activity_id,
            "deal_id": deal_id,
            "company_id": deal.get("company_id"),
            "type": activity_data.get("type", "note"),  # call, email, meeting, note, task, stage_changed
            "direction": activity_data.get("direction", "outbound"),
            "description": activity_data.get("description", ""),
            "outcome": activity_data.get("outcome", ""),
            "duration_minutes": activity_data.get("duration_minutes"),
            "next_steps": activity_data.get("next_steps", ""),
            "logged_at": activity_data.get("logged_at", datetime.now().isoformat()),
            "logged_by": self.user_email
        }
        
        self.activities_db["activities"][activity_id] = activity
        
        # Index by deal
        if deal_id not in self.activities_db["by_deal"]:
            self.activities_db["by_deal"][deal_id] = []
        self.activities_db["by_deal"][deal_id].append(activity_id)
        
        # Index by company
        company_id = deal.get("company_id")
        if company_id:
            if company_id not in self.activities_db["by_company"]:
                self.activities_db["by_company"][company_id] = []
            self.activities_db["by_company"][company_id].append(activity_id)
        
        self._save_activities_db()
        return activity
    
    def get_deal_activities(self, deal_id: str) -> List[Dict]:
        """Get all activities for a deal"""
        activity_ids = self.activities_db["by_deal"].get(deal_id, [])
        activities = [self.activities_db["activities"][aid] for aid in activity_ids if aid in self.activities_db["activities"]]
        return sorted(activities, key=lambda x: x["logged_at"], reverse=True)
    
    def get_pipeline_view(self, pipeline_id: str = "default") -> Dict:
        """Get full pipeline view with deals by stage"""
        pipeline = self.db["pipelines"].get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not found"}
        
        view = {
            "pipeline_id": pipeline_id,
            "name": pipeline["name"],
            "stages": []
        }
        
        for stage_id in pipeline["stages"]:
            stage = self.db["stages"].get(stage_id, {})
            stage_deals = [d for d in self.db["deals"].values() if d["stage"] == stage_id]
            
            view["stages"].append({
                "id": stage_id,
                "name": stage.get("name", stage_id),
                "order": stage.get("order", 0),
                "probability": stage.get("probability", 0),
                "deal_count": len(stage_deals),
                "total_value": sum(d.get("value", 0) for d in stage_deals),
                "weighted_value": sum(d.get("value", 0) * d.get("probability", 0) for d in stage_deals),
                "deals": stage_deals
            })
        
        return view
    
    def get_forecast(self, period_days: int = 90) -> Dict:
        """Generate pipeline forecast"""
        cutoff_date = (datetime.now() + timedelta(days=period_days)).isoformat()
        
        active_deals = [
            d for d in self.db["deals"].values()
            if d["stage"] not in ["closed_won", "closed_lost"]
            and (not d.get("expected_close_date") or d["expected_close_date"] <= cutoff_date)
        ]
        
        forecast = {
            "period_days": period_days,
            "generated_at": datetime.now().isoformat(),
            "total_pipeline": sum(d.get("value", 0) for d in active_deals),
            "weighted_pipeline": sum(d.get("value", 0) * d.get("probability", 0) for d in active_deals),
            "deal_count": len(active_deals),
            "by_stage": {},
            "by_close_date": {}
        }
        
        for deal in active_deals:
            stage = deal["stage"]
            if stage not in forecast["by_stage"]:
                forecast["by_stage"][stage] = {"count": 0, "value": 0, "weighted": 0}
            
            forecast["by_stage"][stage]["count"] += 1
            forecast["by_stage"][stage]["value"] += deal.get("value", 0)
            forecast["by_stage"][stage]["weighted"] += deal.get("value", 0) * deal.get("probability", 0)
        
        return forecast
    
    def get_analytics(self) -> Dict:
        """Get pipeline analytics"""
        all_deals = list(self.db["deals"].values())
        won_deals = [d for d in all_deals if d["stage"] == "closed_won"]
        lost_deals = [d for d in all_deals if d["stage"] == "closed_lost"]
        active_deals = [d for d in all_deals if d["stage"] not in ["closed_won", "closed_lost"]]
        
        # Calculate average deal cycle
        cycle_times = []
        for deal in won_deals:
            if deal.get("actual_close_date") and deal.get("created_at"):
                created = datetime.fromisoformat(deal["created_at"])
                closed = datetime.fromisoformat(deal["actual_close_date"])
                cycle_times.append((closed - created).days)
        
        avg_cycle_days = sum(cycle_times) / len(cycle_times) if cycle_times else 0
        
        analytics = {
            "total_deals": len(all_deals),
            "active_deals": len(active_deals),
            "won_deals": len(won_deals),
            "lost_deals": len(lost_deals),
            "win_rate": len(won_deals) / (len(won_deals) + len(lost_deals)) if (won_deals or lost_deals) else 0,
            "total_won_value": sum(d.get("value", 0) for d in won_deals),
            "total_lost_value": sum(d.get("value", 0) for d in lost_deals),
            "active_pipeline_value": sum(d.get("value", 0) for d in active_deals),
            "weighted_pipeline": sum(d.get("value", 0) * d.get("probability", 0) for d in active_deals),
            "average_deal_value": sum(d.get("value", 0) for d in won_deals) / len(won_deals) if won_deals else 0,
            "average_cycle_days": avg_cycle_days,
            "top_loss_reasons": self._get_top_loss_reasons(lost_deals),
            "top_win_reasons": self._get_top_win_reasons(won_deals),
        }
        
        return analytics
    
    def _get_top_loss_reasons(self, lost_deals: List[Dict]) -> List[Dict]:
        """Get most common loss reasons"""
        reasons = {}
        for deal in lost_deals:
            reason = deal.get("loss_reason", "Unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
        
        return sorted([{"reason": r, "count": c} for r, c in reasons.items()], key=lambda x: x["count"], reverse=True)[:5]
    
    def _get_top_win_reasons(self, won_deals: List[Dict]) -> List[Dict]:
        """Get most common win reasons"""
        reasons = {}
        for deal in won_deals:
            reason = deal.get("win_reason", "Unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
        
        return sorted([{"reason": r, "count": c} for r, c in reasons.items()], key=lambda x: x["count"], reverse=True)[:5]


# ============================================================================
# INTEGRATION - CONNECT EVERYTHING
# ============================================================================

class SalesStack:
    """
    Unified interface to the complete sales stack.
    Connects intent → enrichment → outreach → pipeline
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.intent = IntentDataEngine(user_email)
        self.enrichment = LeadEnrichmentEngine(user_email)
        self.outreach = OutreachEngine(user_email)
        self.pipeline = PipelineEngine(user_email)
    
    def process_hot_account(self, company_id: str, company_name: str, company_domain: str) -> Dict:
        """
        Full workflow for a hot account:
        1. Scan for intent signals
        2. Find contacts
        3. Create deal
        4. Prepare outreach
        """
        result = {
            "company_id": company_id,
            "company_name": company_name,
            "signals": [],
            "contacts": [],
            "deal": None,
            "pending_outreach": []
        }
        
        # 1. Scan for intent signals
        signals = self.intent.scan_for_signals(company_name, company_domain)
        for signal in signals:
            tracked = self.intent.track_signal(company_id, signal["type"], signal)
            result["signals"].append(tracked)
        
        # 2. Find contacts
        contacts = self.enrichment.find_contacts(company_name, company_domain)
        for contact_data in contacts:
            contact = self.enrichment.create_contact(company_id, contact_data)
            result["contacts"].append(contact)
        
        # 3. Create deal
        intent_score = self.intent.calculate_intent_score(company_id)
        deal = self.pipeline.create_deal({
            "name": f"{company_name} - Opportunity",
            "company_id": company_id,
            "company_name": company_name,
            "contact_ids": [c["id"] for c in result["contacts"]],
            "stage": "qualified" if intent_score > 50 else "prospect",
            "source": "intent_signal"
        })
        result["deal"] = deal
        
        return result
    
    def get_dashboard_data(self) -> Dict:
        """Get all data needed for the sales dashboard"""
        return {
            "hot_accounts": self.intent.get_hot_accounts(10),
            "pipeline": self.pipeline.get_pipeline_view(),
            "forecast": self.pipeline.get_forecast(90),
            "analytics": self.pipeline.get_analytics(),
            "pending_outreach": self.outreach.get_pending_outreach()[:10]
        }
