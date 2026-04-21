"""
CONTINUOUS LEARNING SYSTEM
The system that makes OmniMark smarter over time.

Unlike dumb chatbots that forget everything, this system:
1. Tracks every email sent and outcome
2. Learns which approaches work for which personas
3. Improves scoring weights based on actual conversions
4. Builds a knowledge base unique to each customer
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

# ============================================================================
# DATA STORAGE
# ============================================================================

FEEDBACK_DB = "feedback_db.json"
EMAIL_PERFORMANCE_DB = "email_performance_db.json"
AB_TESTS_DB = "ab_tests_db.json"
IMPROVEMENT_LOG_DB = "improvement_log_db.json"

def load_db(filename: str) -> Dict:
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_db(filename: str, data: Dict):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# 1. OUTCOME TRACKING SYSTEM
# ============================================================================

class OutcomeTracker:
    """
    Track every interaction and its outcome.
    This is the data that powers learning.
    """
    
    OUTCOMES = {
        # Email outcomes
        'email_bounced': {'score': -1, 'type': 'email'},
        'email_delivered': {'score': 0, 'type': 'email'},
        'email_opened': {'score': 1, 'type': 'email'},
        'email_clicked': {'score': 2, 'type': 'email'},
        'email_replied': {'score': 5, 'type': 'email'},
        'email_replied_positive': {'score': 8, 'type': 'email'},
        'email_replied_negative': {'score': -2, 'type': 'email'},
        
        # Meeting outcomes
        'meeting_scheduled': {'score': 10, 'type': 'meeting'},
        'meeting_completed': {'score': 15, 'type': 'meeting'},
        'meeting_no_show': {'score': -3, 'type': 'meeting'},
        
        # Deal outcomes
        'opportunity_created': {'score': 20, 'type': 'deal'},
        'proposal_sent': {'score': 25, 'type': 'deal'},
        'deal_won': {'score': 100, 'type': 'deal'},
        'deal_lost': {'score': -10, 'type': 'deal'},
    }
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.feedback_db = load_db(FEEDBACK_DB)
        self.email_db = load_db(EMAIL_PERFORMANCE_DB)
        
        if user_email not in self.feedback_db:
            self.feedback_db[user_email] = {'events': [], 'stats': {}}
    
    def record_outcome(self, 
                       outcome: str, 
                       context: Dict) -> Dict:
        """
        Record an outcome with full context for learning.
        
        context should include:
        - account_id, account_name, industry, size
        - contact_id, contact_title, seniority
        - email_id, subject_line, approach_used
        - signal_types that were present
        """
        
        outcome_data = self.OUTCOMES.get(outcome, {'score': 0, 'type': 'unknown'})
        
        event = {
            'id': hashlib.md5(f"{datetime.now().isoformat()}{outcome}".encode()).hexdigest()[:12],
            'outcome': outcome,
            'score': outcome_data['score'],
            'type': outcome_data['type'],
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        self.feedback_db[self.user_email]['events'].append(event)
        
        # Keep last 10000 events
        self.feedback_db[self.user_email]['events'] = self.feedback_db[self.user_email]['events'][-10000:]
        
        # Update aggregate stats
        self._update_stats(outcome, context)
        
        save_db(FEEDBACK_DB, self.feedback_db)
        
        return event
    
    def _update_stats(self, outcome: str, context: Dict):
        """Update aggregate statistics"""
        stats = self.feedback_db[self.user_email].get('stats', {})
        
        # Overall stats
        if 'overall' not in stats:
            stats['overall'] = defaultdict(int)
        stats['overall'][outcome] = stats['overall'].get(outcome, 0) + 1
        
        # By industry
        industry = context.get('industry', 'unknown')
        if 'by_industry' not in stats:
            stats['by_industry'] = {}
        if industry not in stats['by_industry']:
            stats['by_industry'][industry] = defaultdict(int)
        stats['by_industry'][industry][outcome] = stats['by_industry'][industry].get(outcome, 0) + 1
        
        # By seniority
        seniority = context.get('seniority', 'unknown')
        if 'by_seniority' not in stats:
            stats['by_seniority'] = {}
        if seniority not in stats['by_seniority']:
            stats['by_seniority'][seniority] = defaultdict(int)
        stats['by_seniority'][seniority][outcome] = stats['by_seniority'][seniority].get(outcome, 0) + 1
        
        # By approach
        approach = context.get('approach', 'unknown')
        if 'by_approach' not in stats:
            stats['by_approach'] = {}
        if approach not in stats['by_approach']:
            stats['by_approach'][approach] = defaultdict(int)
        stats['by_approach'][approach][outcome] = stats['by_approach'][approach].get(outcome, 0) + 1
        
        self.feedback_db[self.user_email]['stats'] = stats
    
    def get_stats(self) -> Dict:
        """Get aggregate statistics"""
        return self.feedback_db[self.user_email].get('stats', {})
    
    def get_conversion_funnel(self) -> Dict:
        """Get conversion funnel metrics"""
        events = self.feedback_db[self.user_email].get('events', [])
        
        funnel = {
            'emails_sent': 0,
            'emails_delivered': 0,
            'emails_opened': 0,
            'emails_clicked': 0,
            'emails_replied': 0,
            'meetings_scheduled': 0,
            'meetings_completed': 0,
            'opportunities_created': 0,
            'deals_won': 0
        }
        
        for event in events:
            outcome = event['outcome']
            if outcome in ['email_delivered', 'email_opened', 'email_clicked', 'email_replied', 
                          'email_replied_positive']:
                if outcome == 'email_delivered':
                    funnel['emails_delivered'] += 1
                elif outcome == 'email_opened':
                    funnel['emails_opened'] += 1
                elif outcome == 'email_clicked':
                    funnel['emails_clicked'] += 1
                elif outcome in ['email_replied', 'email_replied_positive']:
                    funnel['emails_replied'] += 1
            elif outcome == 'meeting_scheduled':
                funnel['meetings_scheduled'] += 1
            elif outcome == 'meeting_completed':
                funnel['meetings_completed'] += 1
            elif outcome == 'opportunity_created':
                funnel['opportunities_created'] += 1
            elif outcome == 'deal_won':
                funnel['deals_won'] += 1
        
        # Calculate conversion rates
        funnel['open_rate'] = round(funnel['emails_opened'] / funnel['emails_delivered'] * 100, 1) if funnel['emails_delivered'] > 0 else 0
        funnel['reply_rate'] = round(funnel['emails_replied'] / funnel['emails_delivered'] * 100, 1) if funnel['emails_delivered'] > 0 else 0
        funnel['meeting_rate'] = round(funnel['meetings_scheduled'] / funnel['emails_replied'] * 100, 1) if funnel['emails_replied'] > 0 else 0
        funnel['win_rate'] = round(funnel['deals_won'] / funnel['opportunities_created'] * 100, 1) if funnel['opportunities_created'] > 0 else 0
        
        return funnel


# ============================================================================
# 2. EMAIL PERFORMANCE ANALYZER
# ============================================================================

class EmailPerformanceAnalyzer:
    """
    Analyze which emails perform best and why.
    Build knowledge about what works.
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.db = load_db(EMAIL_PERFORMANCE_DB)
        self.feedback_db = load_db(FEEDBACK_DB)
    
    def record_email(self, email_data: Dict):
        """
        Record an email for performance tracking.
        
        email_data should include:
        - id: unique email ID
        - subject: subject line
        - body: email body
        - approach: the strategy used (value_first, challenger, etc.)
        - recipient: contact info
        - account: account info
        - variables: any personalization variables used
        """
        if self.user_email not in self.db:
            self.db[self.user_email] = {'emails': {}}
        
        email_id = email_data.get('id')
        self.db[self.user_email]['emails'][email_id] = {
            **email_data,
            'sent_at': datetime.now().isoformat(),
            'opened': False,
            'clicked': False,
            'replied': False,
            'reply_sentiment': None,
            'meeting_booked': False
        }
        
        # Extract features for learning
        self.db[self.user_email]['emails'][email_id]['features'] = {
            'subject_length': len(email_data.get('subject', '')),
            'body_length': len(email_data.get('body', '')),
            'has_question': '?' in email_data.get('body', ''),
            'has_cta': any(cta in email_data.get('body', '').lower() for cta in ['would you', 'can we', 'let me know', 'what do you think']),
            'personalization_count': email_data.get('body', '').count('{') if email_data.get('body') else 0,
            'approach': email_data.get('approach', 'unknown'),
            'recipient_seniority': email_data.get('recipient', {}).get('seniority', 'unknown'),
            'account_industry': email_data.get('account', {}).get('industry', 'unknown'),
            'account_size': email_data.get('account', {}).get('employee_count', 0),
            'day_of_week': datetime.now().strftime('%A'),
            'hour_sent': datetime.now().hour
        }
        
        save_db(EMAIL_PERFORMANCE_DB, self.db)
    
    def update_email_outcome(self, email_id: str, outcome: str):
        """Update an email's outcome"""
        if self.user_email not in self.db:
            return
        
        if email_id in self.db[self.user_email].get('emails', {}):
            email = self.db[self.user_email]['emails'][email_id]
            
            if outcome == 'opened':
                email['opened'] = True
                email['opened_at'] = datetime.now().isoformat()
            elif outcome == 'clicked':
                email['clicked'] = True
                email['clicked_at'] = datetime.now().isoformat()
            elif outcome == 'replied':
                email['replied'] = True
                email['replied_at'] = datetime.now().isoformat()
            elif outcome == 'replied_positive':
                email['replied'] = True
                email['reply_sentiment'] = 'positive'
            elif outcome == 'replied_negative':
                email['replied'] = True
                email['reply_sentiment'] = 'negative'
            elif outcome == 'meeting_booked':
                email['meeting_booked'] = True
            
            save_db(EMAIL_PERFORMANCE_DB, self.db)
    
    def analyze_performance(self) -> Dict:
        """Analyze email performance patterns"""
        emails = self.db.get(self.user_email, {}).get('emails', {})
        
        if len(emails) < 10:
            return {
                'status': 'insufficient_data',
                'message': f'Need at least 10 emails for analysis (have {len(emails)})',
                'insights': []
            }
        
        analysis = {
            'total_emails': len(emails),
            'by_approach': self._analyze_by_approach(emails),
            'by_day': self._analyze_by_day(emails),
            'by_time': self._analyze_by_time(emails),
            'by_subject_length': self._analyze_by_subject_length(emails),
            'by_seniority': self._analyze_by_seniority(emails),
            'winning_patterns': self._find_winning_patterns(emails),
            'insights': []
        }
        
        # Generate insights
        analysis['insights'] = self._generate_insights(analysis)
        
        return analysis
    
    def _analyze_by_approach(self, emails: Dict) -> Dict:
        """Analyze performance by approach/strategy"""
        results = defaultdict(lambda: {'sent': 0, 'opened': 0, 'replied': 0, 'meetings': 0})
        
        for email in emails.values():
            approach = email.get('features', {}).get('approach', 'unknown')
            results[approach]['sent'] += 1
            if email.get('opened'):
                results[approach]['opened'] += 1
            if email.get('replied'):
                results[approach]['replied'] += 1
            if email.get('meeting_booked'):
                results[approach]['meetings'] += 1
        
        # Calculate rates
        for approach, stats in results.items():
            stats['open_rate'] = round(stats['opened'] / stats['sent'] * 100, 1) if stats['sent'] > 0 else 0
            stats['reply_rate'] = round(stats['replied'] / stats['sent'] * 100, 1) if stats['sent'] > 0 else 0
            stats['meeting_rate'] = round(stats['meetings'] / stats['replied'] * 100, 1) if stats['replied'] > 0 else 0
        
        return dict(results)
    
    def _analyze_by_day(self, emails: Dict) -> Dict:
        """Analyze performance by day of week"""
        results = defaultdict(lambda: {'sent': 0, 'opened': 0, 'replied': 0})
        
        for email in emails.values():
            day = email.get('features', {}).get('day_of_week', 'Unknown')
            results[day]['sent'] += 1
            if email.get('opened'):
                results[day]['opened'] += 1
            if email.get('replied'):
                results[day]['replied'] += 1
        
        for day, stats in results.items():
            stats['open_rate'] = round(stats['opened'] / stats['sent'] * 100, 1) if stats['sent'] > 0 else 0
            stats['reply_rate'] = round(stats['replied'] / stats['sent'] * 100, 1) if stats['sent'] > 0 else 0
        
        return dict(results)
    
    def _analyze_by_time(self, emails: Dict) -> Dict:
        """Analyze performance by time of day"""
        results = defaultdict(lambda: {'sent': 0, 'opened': 0, 'replied': 0})
        
        for email in emails.values():
            hour = email.get('features', {}).get('hour_sent', 0)
            time_bucket = f"{hour:02d}:00-{hour:02d}:59"
            results[time_bucket]['sent'] += 1
            if email.get('opened'):
                results[time_bucket]['opened'] += 1
            if email.get('replied'):
                results[time_bucket]['replied'] += 1
        
        for bucket, stats in results.items():
            stats['open_rate'] = round(stats['opened'] / stats['sent'] * 100, 1) if stats['sent'] > 0 else 0
            stats['reply_rate'] = round(stats['replied'] / stats['sent'] * 100, 1) if stats['sent'] > 0 else 0
        
        return dict(results)
    
    def _analyze_by_subject_length(self, emails: Dict) -> Dict:
        """Analyze performance by subject line length"""
        buckets = {
            'short': {'range': (0, 30), 'sent': 0, 'opened': 0, 'replied': 0},
            'medium': {'range': (31, 60), 'sent': 0, 'opened': 0, 'replied': 0},
            'long': {'range': (61, 100), 'sent': 0, 'opened': 0, 'replied': 0},
            'very_long': {'range': (101, 999), 'sent': 0, 'opened': 0, 'replied': 0}
        }
        
        for email in emails.values():
            length = email.get('features', {}).get('subject_length', 0)
            
            for bucket_name, bucket in buckets.items():
                if bucket['range'][0] <= length <= bucket['range'][1]:
                    bucket['sent'] += 1
                    if email.get('opened'):
                        bucket['opened'] += 1
                    if email.get('replied'):
                        bucket['replied'] += 1
                    break
        
        for bucket in buckets.values():
            bucket['open_rate'] = round(bucket['opened'] / bucket['sent'] * 100, 1) if bucket['sent'] > 0 else 0
            bucket['reply_rate'] = round(bucket['replied'] / bucket['sent'] * 100, 1) if bucket['sent'] > 0 else 0
        
        return buckets
    
    def _analyze_by_seniority(self, emails: Dict) -> Dict:
        """Analyze performance by recipient seniority"""
        results = defaultdict(lambda: {'sent': 0, 'opened': 0, 'replied': 0, 'meetings': 0})
        
        for email in emails.values():
            seniority = email.get('features', {}).get('recipient_seniority', 'unknown')
            results[seniority]['sent'] += 1
            if email.get('opened'):
                results[seniority]['opened'] += 1
            if email.get('replied'):
                results[seniority]['replied'] += 1
            if email.get('meeting_booked'):
                results[seniority]['meetings'] += 1
        
        for seniority, stats in results.items():
            stats['open_rate'] = round(stats['opened'] / stats['sent'] * 100, 1) if stats['sent'] > 0 else 0
            stats['reply_rate'] = round(stats['replied'] / stats['sent'] * 100, 1) if stats['sent'] > 0 else 0
        
        return dict(results)
    
    def _find_winning_patterns(self, emails: Dict) -> List[Dict]:
        """Find patterns in successful emails"""
        successful = [e for e in emails.values() if e.get('replied') or e.get('meeting_booked')]
        
        if len(successful) < 5:
            return []
        
        patterns = []
        
        # Find common features in successful emails
        feature_counts = defaultdict(int)
        for email in successful:
            features = email.get('features', {})
            if features.get('has_question'):
                feature_counts['includes_question'] += 1
            if features.get('has_cta'):
                feature_counts['includes_cta'] += 1
            if features.get('subject_length', 0) < 40:
                feature_counts['short_subject'] += 1
            if features.get('body_length', 0) < 500:
                feature_counts['concise_body'] += 1
        
        total = len(successful)
        for feature, count in feature_counts.items():
            if count / total > 0.6:  # Present in >60% of successful emails
                patterns.append({
                    'pattern': feature,
                    'frequency': round(count / total * 100),
                    'recommendation': f"Use {feature} - present in {round(count / total * 100)}% of successful emails"
                })
        
        return patterns
    
    def _generate_insights(self, analysis: Dict) -> List[str]:
        """Generate actionable insights from analysis"""
        insights = []
        
        # Best approach
        by_approach = analysis.get('by_approach', {})
        if by_approach:
            best_approach = max(by_approach.items(), key=lambda x: x[1].get('reply_rate', 0))
            if best_approach[1].get('sent', 0) >= 5:  # Minimum sample
                insights.append(f"🎯 {best_approach[0].replace('_', ' ').title()} approach has highest reply rate ({best_approach[1]['reply_rate']}%)")
        
        # Best day
        by_day = analysis.get('by_day', {})
        if by_day:
            best_day = max(by_day.items(), key=lambda x: x[1].get('reply_rate', 0))
            if best_day[1].get('sent', 0) >= 3:
                insights.append(f"📅 {best_day[0]} shows highest engagement ({best_day[1]['reply_rate']}% reply rate)")
        
        # Subject line length
        by_length = analysis.get('by_subject_length', {})
        if by_length:
            best_length = max(by_length.items(), key=lambda x: x[1].get('reply_rate', 0))
            if best_length[1].get('sent', 0) >= 5:
                insights.append(f"✍️ {best_length[0].replace('_', ' ').title()} subject lines perform best ({best_length[1]['reply_rate']}% reply rate)")
        
        # Winning patterns
        for pattern in analysis.get('winning_patterns', [])[:3]:
            insights.append(f"✨ {pattern['recommendation']}")
        
        return insights


# ============================================================================
# 3. A/B TESTING ENGINE
# ============================================================================

class ABTestingEngine:
    """
    Run A/B tests to continuously improve.
    Not guessing - measuring.
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.db = load_db(AB_TESTS_DB)
        
        if user_email not in self.db:
            self.db[user_email] = {'tests': {}}
    
    def create_test(self, 
                    name: str,
                    hypothesis: str,
                    variant_a: Dict,
                    variant_b: Dict,
                    metric: str = 'reply_rate',
                    sample_size: int = 100) -> Dict:
        """
        Create a new A/B test.
        
        variant_a and variant_b should include:
        - subject_template: subject line template
        - body_template: email body template
        - approach: strategy being used
        """
        test_id = hashlib.md5(f"{datetime.now().isoformat()}{name}".encode()).hexdigest()[:12]
        
        test = {
            'id': test_id,
            'name': name,
            'hypothesis': hypothesis,
            'variant_a': {**variant_a, 'sends': 0, 'opens': 0, 'replies': 0, 'meetings': 0},
            'variant_b': {**variant_b, 'sends': 0, 'opens': 0, 'replies': 0, 'meetings': 0},
            'metric': metric,
            'sample_size': sample_size,
            'status': 'running',
            'created_at': datetime.now().isoformat(),
            'winner': None,
            'confidence': 0
        }
        
        self.db[self.user_email]['tests'][test_id] = test
        save_db(AB_TESTS_DB, self.db)
        
        return test
    
    def get_variant(self, test_id: str) -> Tuple[str, Dict]:
        """
        Get which variant to use for next send.
        Balances 50/50 with slight randomization.
        """
        test = self.db[self.user_email]['tests'].get(test_id)
        
        if not test or test['status'] != 'running':
            return None, None
        
        # Simple 50/50 split
        a_sends = test['variant_a']['sends']
        b_sends = test['variant_b']['sends']
        
        # Pick variant with fewer sends (with slight randomization)
        import random
        if a_sends < b_sends or (a_sends == b_sends and random.random() < 0.5):
            return 'A', test['variant_a']
        else:
            return 'B', test['variant_b']
    
    def record_outcome(self, test_id: str, variant: str, outcome: str):
        """Record an outcome for a test variant"""
        test = self.db[self.user_email]['tests'].get(test_id)
        
        if not test:
            return
        
        variant_key = 'variant_a' if variant == 'A' else 'variant_b'
        
        test[variant_key]['sends'] += 1
        
        if outcome == 'opened':
            test[variant_key]['opens'] += 1
        elif outcome in ['replied', 'replied_positive']:
            test[variant_key]['replies'] += 1
        elif outcome == 'meeting_booked':
            test[variant_key]['meetings'] += 1
        
        # Check if test should conclude
        total_sends = test['variant_a']['sends'] + test['variant_b']['sends']
        if total_sends >= test['sample_size']:
            self._conclude_test(test_id)
        
        save_db(AB_TESTS_DB, self.db)
    
    def _conclude_test(self, test_id: str):
        """Conclude a test and determine winner"""
        test = self.db[self.user_email]['tests'].get(test_id)
        
        if not test:
            return
        
        metric = test['metric']
        
        # Calculate rates
        a_rate = self._calculate_rate(test['variant_a'], metric)
        b_rate = self._calculate_rate(test['variant_b'], metric)
        
        # Simple statistical significance check
        a_sends = test['variant_a']['sends']
        b_sends = test['variant_b']['sends']
        
        # Calculate confidence (simplified)
        if a_sends >= 30 and b_sends >= 30:
            diff = abs(a_rate - b_rate)
            pooled_rate = (a_rate * a_sends + b_rate * b_sends) / (a_sends + b_sends) if (a_sends + b_sends) > 0 else 0
            se = math.sqrt(pooled_rate * (1 - pooled_rate / 100) * (1/a_sends + 1/b_sends)) if pooled_rate > 0 else 0
            z_score = diff / se if se > 0 else 0
            
            # Rough confidence calculation
            confidence = min(99, max(50, 50 + z_score * 15))
        else:
            confidence = 50
        
        # Determine winner
        if confidence >= 90:
            test['winner'] = 'A' if a_rate > b_rate else 'B'
        elif confidence >= 70:
            test['winner'] = 'A' if a_rate > b_rate else 'B'  # Tentative winner
        else:
            test['winner'] = 'inconclusive'
        
        test['status'] = 'completed'
        test['confidence'] = round(confidence)
        test['completed_at'] = datetime.now().isoformat()
        test['results'] = {
            'variant_a_rate': a_rate,
            'variant_b_rate': b_rate,
            'improvement': round(abs(a_rate - b_rate) / max(a_rate, b_rate) * 100, 1) if max(a_rate, b_rate) > 0 else 0
        }
        
        save_db(AB_TESTS_DB, self.db)
        
        # Log the improvement
        self._log_improvement(test)
    
    def _calculate_rate(self, variant: Dict, metric: str) -> float:
        """Calculate the rate for a given metric"""
        sends = variant['sends']
        
        if sends == 0:
            return 0
        
        if metric == 'open_rate':
            return round(variant['opens'] / sends * 100, 1)
        elif metric == 'reply_rate':
            return round(variant['replies'] / sends * 100, 1)
        elif metric == 'meeting_rate':
            return round(variant['meetings'] / variant['replies'] * 100, 1) if variant['replies'] > 0 else 0
        
        return 0
    
    def _log_improvement(self, test: Dict):
        """Log improvement from test"""
        improvement_db = load_db(IMPROVEMENT_LOG_DB)
        
        if self.user_email not in improvement_db:
            improvement_db[self.user_email] = {'improvements': []}
        
        improvement_db[self.user_email]['improvements'].append({
            'test_name': test['name'],
            'hypothesis': test['hypothesis'],
            'winner': test['winner'],
            'confidence': test['confidence'],
            'improvement': test.get('results', {}).get('improvement', 0),
            'timestamp': datetime.now().isoformat()
        })
        
        save_db(IMPROVEMENT_LOG_DB, improvement_db)
    
    def get_test_results(self, test_id: str) -> Dict:
        """Get results for a test"""
        return self.db[self.user_email]['tests'].get(test_id, {})
    
    def get_all_tests(self) -> List[Dict]:
        """Get all tests for user"""
        return list(self.db[self.user_email]['tests'].values())
    
    def suggest_tests(self) -> List[Dict]:
        """Suggest A/B tests to run based on current data"""
        suggestions = [
            {
                'name': 'Subject Line: Question vs Statement',
                'hypothesis': 'Questions in subject lines increase open rates',
                'variant_a': {'subject_template': 'Quick question about {company}'},
                'variant_b': {'subject_template': 'Ideas for {company}'},
                'metric': 'open_rate'
            },
            {
                'name': 'Email Length: Short vs Detailed',
                'hypothesis': 'Shorter emails get more replies',
                'variant_a': {'body_template': 'short', 'max_length': 100},
                'variant_b': {'body_template': 'detailed', 'max_length': 300},
                'metric': 'reply_rate'
            },
            {
                'name': 'Opening: Value First vs Direct Ask',
                'hypothesis': 'Leading with value increases engagement',
                'variant_a': {'approach': 'value_first'},
                'variant_b': {'approach': 'direct'},
                'metric': 'reply_rate'
            },
            {
                'name': 'Personalization: Light vs Heavy',
                'hypothesis': 'More personalization = more replies',
                'variant_a': {'personalization_level': 'light'},
                'variant_b': {'personalization_level': 'heavy'},
                'metric': 'reply_rate'
            }
        ]
        
        return suggestions


# ============================================================================
# 4. IMPROVEMENT RECOMMENDATION ENGINE
# ============================================================================

class ImprovementEngine:
    """
    Based on all learning data, recommend improvements.
    Continuous improvement engine.
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.outcome_tracker = OutcomeTracker(user_email)
        self.email_analyzer = EmailPerformanceAnalyzer(user_email)
        self.ab_engine = ABTestingEngine(user_email)
    
    def get_recommendations(self) -> Dict:
        """Get all improvement recommendations"""
        recommendations = {
            'immediate_actions': [],
            'suggested_tests': [],
            'performance_insights': [],
            'learning_summary': {}
        }
        
        # Get email analysis
        email_analysis = self.email_analyzer.analyze_performance()
        if email_analysis.get('insights'):
            recommendations['performance_insights'] = email_analysis['insights']
        
        # Get funnel data
        funnel = self.outcome_tracker.get_conversion_funnel()
        
        # Generate recommendations based on funnel
        if funnel.get('open_rate', 0) < 25:
            recommendations['immediate_actions'].append({
                'priority': 'high',
                'action': 'Improve subject lines',
                'reason': f"Open rate is {funnel['open_rate']}% (industry avg is 25-35%)",
                'suggestion': 'Try shorter, more specific subject lines that reference the company'
            })
        
        if funnel.get('reply_rate', 0) < 5:
            recommendations['immediate_actions'].append({
                'priority': 'high',
                'action': 'Improve email body',
                'reason': f"Reply rate is {funnel['reply_rate']}% (should aim for 5-15%)",
                'suggestion': 'Make emails shorter, include a specific question, lead with value'
            })
        
        if funnel.get('meeting_rate', 0) < 20:
            recommendations['immediate_actions'].append({
                'priority': 'medium',
                'action': 'Improve reply-to-meeting conversion',
                'reason': f"Only {funnel['meeting_rate']}% of replies convert to meetings",
                'suggestion': 'Respond faster to replies, have clear CTA in follow-ups'
            })
        
        # Suggest A/B tests
        recommendations['suggested_tests'] = self.ab_engine.suggest_tests()
        
        # Learning summary
        stats = self.outcome_tracker.get_stats()
        recommendations['learning_summary'] = {
            'total_outcomes_tracked': len(self.outcome_tracker.feedback_db.get(self.user_email, {}).get('events', [])),
            'by_industry': stats.get('by_industry', {}),
            'by_seniority': stats.get('by_seniority', {}),
            'conversion_funnel': funnel
        }
        
        return recommendations


# ============================================================================
# 5. UNIFIED LEARNING INTERFACE
# ============================================================================

class LearningSystem:
    """
    Unified interface to all learning capabilities.
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.outcome_tracker = OutcomeTracker(user_email)
        self.email_analyzer = EmailPerformanceAnalyzer(user_email)
        self.ab_engine = ABTestingEngine(user_email)
        self.improvement_engine = ImprovementEngine(user_email)
    
    def track_outcome(self, outcome: str, context: Dict):
        """Track an outcome"""
        return self.outcome_tracker.record_outcome(outcome, context)
    
    def record_email(self, email_data: Dict):
        """Record an email for tracking"""
        return self.email_analyzer.record_email(email_data)
    
    def update_email_outcome(self, email_id: str, outcome: str):
        """Update email outcome"""
        return self.email_analyzer.update_email_outcome(email_id, outcome)
    
    def get_email_analysis(self):
        """Get email performance analysis"""
        return self.email_analyzer.analyze_performance()
    
    def create_ab_test(self, name: str, hypothesis: str, variant_a: Dict, variant_b: Dict, metric: str = 'reply_rate'):
        """Create an A/B test"""
        return self.ab_engine.create_test(name, hypothesis, variant_a, variant_b, metric)
    
    def get_ab_variant(self, test_id: str):
        """Get variant for A/B test"""
        return self.ab_engine.get_variant(test_id)
    
    def record_ab_outcome(self, test_id: str, variant: str, outcome: str):
        """Record A/B test outcome"""
        return self.ab_engine.record_outcome(test_id, variant, outcome)
    
    def get_recommendations(self):
        """Get improvement recommendations"""
        return self.improvement_engine.get_recommendations()
    
    def get_conversion_funnel(self):
        """Get conversion funnel"""
        return self.outcome_tracker.get_conversion_funnel()
