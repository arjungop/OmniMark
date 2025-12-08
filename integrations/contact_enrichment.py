"""
CONTACT ENRICHMENT & VERIFICATION
Real data, not guesses.

Integrations:
- Hunter.io - Email finding & verification
- ZeroBounce - Email validation
- Clearbit - Firmographic/demographic data
- Apollo.io - Contact database
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

ENRICHMENT_CACHE_FILE = "enrichment_cache.json"
VERIFICATION_CACHE_FILE = "verification_cache.json"

def load_cache(filename: str) -> Dict:
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_cache(filename: str, data: Dict):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# EMAIL FINDER - Hunter.io
# ============================================================================

class HunterIO:
    """
    Find and verify professional email addresses.
    
    Features:
    - Domain search (find all emails at a company)
    - Email finder (find specific person's email)
    - Email verification (check deliverability)
    
    API: https://hunter.io/api
    Pricing: 25 free searches/month, $49/month for 500
    """
    
    BASE_URL = "https://api.hunter.io/v2"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('HUNTER_API_KEY')
        self.cache = load_cache(ENRICHMENT_CACHE_FILE)
    
    def find_email(self, domain: str, first_name: str, last_name: str) -> Dict:
        """
        Find email address for a specific person at a company.
        
        Returns:
            {
                'email': 'john@acme.com',
                'score': 95,  # Confidence score
                'verified': True,
                'sources': [...]
            }
        """
        if not self.api_key:
            return self._guess_email(domain, first_name, last_name)
        
        # Check cache
        cache_key = f"finder_{domain}_{first_name}_{last_name}".lower()
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['cached_at']) > datetime.now() - timedelta(days=30):
                return cached['data']
        
        try:
            import requests
            
            response = requests.get(
                f"{self.BASE_URL}/email-finder",
                params={
                    'domain': domain,
                    'first_name': first_name,
                    'last_name': last_name,
                    'api_key': self.api_key
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                result = {
                    'email': data.get('email'),
                    'score': data.get('score', 0),
                    'verified': data.get('verification', {}).get('status') == 'valid',
                    'sources': data.get('sources', []),
                    'position': data.get('position'),
                    'linkedin': data.get('linkedin_url'),
                    'provider': 'hunter'
                }
                
                # Cache result
                self.cache[cache_key] = {'data': result, 'cached_at': datetime.now().isoformat()}
                save_cache(ENRICHMENT_CACHE_FILE, self.cache)
                
                return result
            else:
                return self._guess_email(domain, first_name, last_name)
                
        except Exception as e:
            return self._guess_email(domain, first_name, last_name)
    
    def search_domain(self, domain: str, limit: int = 10) -> Dict:
        """
        Find all email addresses at a domain.
        
        Returns list of emails with names, positions, confidence scores.
        """
        if not self.api_key:
            return {'emails': [], 'provider': 'none', 'error': 'No API key'}
        
        # Check cache
        cache_key = f"domain_{domain}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['cached_at']) > datetime.now() - timedelta(days=7):
                return cached['data']
        
        try:
            import requests
            
            response = requests.get(
                f"{self.BASE_URL}/domain-search",
                params={
                    'domain': domain,
                    'limit': limit,
                    'api_key': self.api_key
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                
                emails = []
                for email_data in data.get('emails', []):
                    emails.append({
                        'email': email_data.get('value'),
                        'first_name': email_data.get('first_name'),
                        'last_name': email_data.get('last_name'),
                        'position': email_data.get('position'),
                        'department': email_data.get('department'),
                        'seniority': email_data.get('seniority'),
                        'linkedin': email_data.get('linkedin'),
                        'confidence': email_data.get('confidence', 0),
                        'sources': len(email_data.get('sources', []))
                    })
                
                result = {
                    'domain': domain,
                    'organization': data.get('organization'),
                    'emails': emails,
                    'email_count': data.get('emails_count', 0),
                    'pattern': data.get('pattern'),
                    'provider': 'hunter'
                }
                
                self.cache[cache_key] = {'data': result, 'cached_at': datetime.now().isoformat()}
                save_cache(ENRICHMENT_CACHE_FILE, self.cache)
                
                return result
            
            return {'emails': [], 'provider': 'hunter', 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'emails': [], 'provider': 'hunter', 'error': str(e)}
    
    def verify_email(self, email: str) -> Dict:
        """
        Verify if an email address is deliverable.
        
        Returns:
            {
                'status': 'valid' | 'invalid' | 'unknown',
                'score': 95,
                'deliverable': True,
                'disposable': False,
                'gibberish': False
            }
        """
        if not self.api_key:
            return {'status': 'unknown', 'provider': 'none', 'error': 'No API key'}
        
        # Check cache
        cache_key = f"verify_{email}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['cached_at']) > datetime.now() - timedelta(days=7):
                return cached['data']
        
        try:
            import requests
            
            response = requests.get(
                f"{self.BASE_URL}/email-verifier",
                params={
                    'email': email,
                    'api_key': self.api_key
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                
                result = {
                    'email': email,
                    'status': data.get('status', 'unknown'),
                    'score': data.get('score', 0),
                    'deliverable': data.get('status') == 'valid',
                    'disposable': data.get('disposable', False),
                    'webmail': data.get('webmail', False),
                    'gibberish': data.get('gibberish', False),
                    'mx_records': data.get('mx_records', False),
                    'smtp_check': data.get('smtp_check', False),
                    'provider': 'hunter'
                }
                
                self.cache[cache_key] = {'data': result, 'cached_at': datetime.now().isoformat()}
                save_cache(ENRICHMENT_CACHE_FILE, self.cache)
                
                return result
            
            return {'status': 'unknown', 'provider': 'hunter', 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'status': 'unknown', 'provider': 'hunter', 'error': str(e)}
    
    def _guess_email(self, domain: str, first_name: str, last_name: str) -> Dict:
        """Fallback: guess email pattern"""
        patterns = [
            f"{first_name.lower()}.{last_name.lower()}@{domain}",
            f"{first_name.lower()}{last_name.lower()}@{domain}",
            f"{first_name[0].lower()}{last_name.lower()}@{domain}",
            f"{first_name.lower()}@{domain}",
            f"{first_name.lower()}_{last_name.lower()}@{domain}"
        ]
        
        return {
            'email': patterns[0],  # Most common pattern
            'alternatives': patterns[1:],
            'score': 40,  # Low confidence
            'verified': False,
            'guessed': True,
            'provider': 'pattern_guess'
        }


# ============================================================================
# EMAIL VERIFICATION - ZeroBounce
# ============================================================================

class ZeroBounce:
    """
    Professional email validation service.
    
    More accurate than Hunter for verification.
    Better catch-all detection.
    
    API: https://www.zerobounce.net/docs/
    Pricing: $16 for 2000 validations
    """
    
    BASE_URL = "https://api.zerobounce.net/v2"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('ZEROBOUNCE_API_KEY')
        self.cache = load_cache(VERIFICATION_CACHE_FILE)
    
    def validate(self, email: str) -> Dict:
        """
        Validate email address.
        
        Returns detailed validation result including:
        - Status (valid, invalid, catch-all, unknown, spamtrap, abuse, do_not_mail)
        - Sub-status with more detail
        - Account info (name, gender, etc. if available)
        """
        if not self.api_key:
            return {'status': 'unknown', 'provider': 'none', 'error': 'No API key'}
        
        # Check cache
        cache_key = f"zb_{email}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['cached_at']) > datetime.now() - timedelta(days=30):
                return cached['data']
        
        try:
            import requests
            
            response = requests.get(
                f"{self.BASE_URL}/validate",
                params={
                    'email': email,
                    'api_key': self.api_key,
                    'ip_address': ''  # Optional
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    'email': email,
                    'status': data.get('status', 'unknown'),
                    'sub_status': data.get('sub_status'),
                    'deliverable': data.get('status') == 'valid',
                    'catch_all': data.get('status') == 'catch-all',
                    'free_email': data.get('free_email', False),
                    'disposable': data.get('disposable', False),
                    'toxic': data.get('toxic', False),
                    'first_name': data.get('firstname'),
                    'last_name': data.get('lastname'),
                    'gender': data.get('gender'),
                    'creation_date': data.get('creation_date'),
                    'domain_age_days': data.get('domain_age_days'),
                    'smtp_provider': data.get('smtp_provider'),
                    'mx_record': data.get('mx_record'),
                    'provider': 'zerobounce'
                }
                
                self.cache[cache_key] = {'data': result, 'cached_at': datetime.now().isoformat()}
                save_cache(VERIFICATION_CACHE_FILE, self.cache)
                
                return result
            
            return {'status': 'unknown', 'provider': 'zerobounce', 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'status': 'unknown', 'provider': 'zerobounce', 'error': str(e)}
    
    def get_credits(self) -> Dict:
        """Check remaining API credits"""
        if not self.api_key:
            return {'credits': 0, 'error': 'No API key'}
        
        try:
            import requests
            
            response = requests.get(
                f"{self.BASE_URL}/getcredits",
                params={'api_key': self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return {'credits': 0, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'credits': 0, 'error': str(e)}


# ============================================================================
# COMPANY ENRICHMENT - Clearbit
# ============================================================================

class ClearbitEnrichment:
    """
    Company and contact enrichment.
    
    Features:
    - Company lookup (firmographics, tech stack, social)
    - Person lookup (demographics, employment, social)
    - Prospector (find contacts at companies)
    
    API: https://clearbit.com/docs
    Pricing: $99+/month
    """
    
    BASE_URL = "https://company.clearbit.com/v2"
    PERSON_URL = "https://person.clearbit.com/v2"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('CLEARBIT_API_KEY')
        self.cache = load_cache(ENRICHMENT_CACHE_FILE)
    
    def enrich_company(self, domain: str) -> Dict:
        """
        Get company data from domain.
        
        Returns:
            - Name, description, founded year
            - Industry, sector, sub-industry
            - Employee count, estimated revenue
            - Location, phone, social profiles
            - Tech stack, keywords/tags
        """
        if not self.api_key:
            return {'provider': 'none', 'error': 'No API key'}
        
        # Check cache
        cache_key = f"clearbit_company_{domain}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['cached_at']) > datetime.now() - timedelta(days=30):
                return cached['data']
        
        try:
            import requests
            
            response = requests.get(
                f"{self.BASE_URL}/companies/find",
                params={'domain': domain},
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    'domain': domain,
                    'name': data.get('name'),
                    'legal_name': data.get('legalName'),
                    'description': data.get('description'),
                    'founded_year': data.get('foundedYear'),
                    
                    'industry': data.get('category', {}).get('industry'),
                    'sector': data.get('category', {}).get('sector'),
                    'sub_industry': data.get('category', {}).get('subIndustry'),
                    'industry_group': data.get('category', {}).get('industryGroup'),
                    
                    'employee_count': data.get('metrics', {}).get('employees'),
                    'employee_range': data.get('metrics', {}).get('employeesRange'),
                    'estimated_revenue': data.get('metrics', {}).get('estimatedAnnualRevenue'),
                    'raised': data.get('metrics', {}).get('raised'),
                    'alexa_rank': data.get('metrics', {}).get('alexaGlobalRank'),
                    
                    'location': {
                        'city': data.get('geo', {}).get('city'),
                        'state': data.get('geo', {}).get('state'),
                        'country': data.get('geo', {}).get('country'),
                        'street_address': data.get('geo', {}).get('streetAddress')
                    },
                    
                    'phone': data.get('phone'),
                    'email_addresses': data.get('emailAddresses', []),
                    
                    'social': {
                        'linkedin': data.get('linkedin', {}).get('handle'),
                        'twitter': data.get('twitter', {}).get('handle'),
                        'facebook': data.get('facebook', {}).get('handle'),
                        'crunchbase': data.get('crunchbase', {}).get('handle')
                    },
                    
                    'tech': data.get('tech', []),
                    'tags': data.get('tags', []),
                    
                    'type': data.get('type'),  # company, education, government, nonprofit
                    'indexed_at': data.get('indexedAt'),
                    
                    'provider': 'clearbit'
                }
                
                self.cache[cache_key] = {'data': result, 'cached_at': datetime.now().isoformat()}
                save_cache(ENRICHMENT_CACHE_FILE, self.cache)
                
                return result
            
            elif response.status_code == 404:
                return {'domain': domain, 'found': False, 'provider': 'clearbit'}
            
            return {'provider': 'clearbit', 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'provider': 'clearbit', 'error': str(e)}
    
    def enrich_person(self, email: str) -> Dict:
        """
        Get person data from email.
        
        Returns:
            - Name, bio, location
            - Employment (current company, title, seniority)
            - Social profiles
        """
        if not self.api_key:
            return {'provider': 'none', 'error': 'No API key'}
        
        # Check cache
        cache_key = f"clearbit_person_{email}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['cached_at']) > datetime.now() - timedelta(days=30):
                return cached['data']
        
        try:
            import requests
            
            response = requests.get(
                f"{self.PERSON_URL}/people/find",
                params={'email': email},
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    'email': email,
                    'name': data.get('name', {}).get('fullName'),
                    'first_name': data.get('name', {}).get('givenName'),
                    'last_name': data.get('name', {}).get('familyName'),
                    'bio': data.get('bio'),
                    'avatar': data.get('avatar'),
                    
                    'location': data.get('location'),
                    'timezone': data.get('timeZone'),
                    
                    'employment': {
                        'company': data.get('employment', {}).get('name'),
                        'domain': data.get('employment', {}).get('domain'),
                        'title': data.get('employment', {}).get('title'),
                        'role': data.get('employment', {}).get('role'),
                        'seniority': data.get('employment', {}).get('seniority')
                    },
                    
                    'social': {
                        'linkedin': data.get('linkedin', {}).get('handle'),
                        'twitter': data.get('twitter', {}).get('handle'),
                        'github': data.get('github', {}).get('handle')
                    },
                    
                    'indexed_at': data.get('indexedAt'),
                    'provider': 'clearbit'
                }
                
                self.cache[cache_key] = {'data': result, 'cached_at': datetime.now().isoformat()}
                save_cache(ENRICHMENT_CACHE_FILE, self.cache)
                
                return result
            
            elif response.status_code == 404:
                return {'email': email, 'found': False, 'provider': 'clearbit'}
            
            return {'provider': 'clearbit', 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'provider': 'clearbit', 'error': str(e)}


# ============================================================================
# UNIFIED CONTACT ENRICHMENT
# ============================================================================

class ContactEnrichment:
    """
    Unified interface for contact enrichment.
    Uses best available provider.
    """
    
    def __init__(self, hunter_api_key: str = None, zerobounce_api_key: str = None,
                 clearbit_api_key: str = None):
        self.hunter = HunterIO(hunter_api_key)
        self.zerobounce = ZeroBounce(zerobounce_api_key)
        self.clearbit = ClearbitEnrichment(clearbit_api_key)
    
    def find_email(self, domain: str, first_name: str, last_name: str,
                   verify: bool = True) -> Dict:
        """
        Find and optionally verify email for a person.
        
        Uses Hunter.io for finding, ZeroBounce for verification.
        """
        # Find email
        result = self.hunter.find_email(domain, first_name, last_name)
        
        if result.get('email') and verify:
            # Verify with ZeroBounce if available
            if self.zerobounce.api_key:
                verification = self.zerobounce.validate(result['email'])
                result['verification'] = verification
                result['deliverable'] = verification.get('deliverable', False)
            elif self.hunter.api_key:
                # Fall back to Hunter verification
                verification = self.hunter.verify_email(result['email'])
                result['verification'] = verification
                result['deliverable'] = verification.get('deliverable', False)
        
        return result
    
    def enrich_contact(self, email: str = None, domain: str = None) -> Dict:
        """
        Enrich a contact with all available data.
        
        Returns combined data from all providers.
        """
        result = {
            'email': email,
            'domain': domain,
            'person': None,
            'company': None,
            'email_verification': None
        }
        
        # Person enrichment
        if email and self.clearbit.api_key:
            result['person'] = self.clearbit.enrich_person(email)
            if not domain and result['person']:
                domain = result['person'].get('employment', {}).get('domain')
        
        # Company enrichment
        if domain and self.clearbit.api_key:
            result['company'] = self.clearbit.enrich_company(domain)
        
        # Email verification
        if email:
            if self.zerobounce.api_key:
                result['email_verification'] = self.zerobounce.validate(email)
            elif self.hunter.api_key:
                result['email_verification'] = self.hunter.verify_email(email)
        
        return result
    
    def find_contacts_at_company(self, domain: str, limit: int = 10) -> Dict:
        """Find contacts at a company"""
        return self.hunter.search_domain(domain, limit)
    
    def bulk_verify(self, emails: List[str]) -> List[Dict]:
        """Verify multiple emails"""
        results = []
        
        for email in emails:
            if self.zerobounce.api_key:
                result = self.zerobounce.validate(email)
            elif self.hunter.api_key:
                result = self.hunter.verify_email(email)
            else:
                result = {'email': email, 'status': 'unknown', 'error': 'No verification API configured'}
            
            results.append(result)
        
        return results
