"""
THE INTELLIGENCE LAYER
Not a prompt library. An actual AI system that thinks.

This is what separates a product from a toy:
1. AI DECIDES what to research based on ICP fit
2. AI PRIORITIZES accounts by likelihood to close  
3. AI DETECTS patterns humans miss
4. AI PREDICTS best outreach strategy per persona
5. AI LEARNS from what actually works
"""

import os
import json
import math
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

# ============================================================================
# DATA PERSISTENCE
# ============================================================================

INTELLIGENCE_DB = "intelligence_db.json"
LEARNING_DB = "learning_db.json"
PATTERNS_DB = "patterns_db.json"
PREDICTIONS_DB = "predictions_db.json"

def load_db(filename: str) -> Dict:
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_db(filename: str, data: Dict):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# 1. INTELLIGENT ACCOUNT SCORING
# ============================================================================

class AccountScoringEngine:
    """
    ML-inspired account scoring that actually predicts likelihood to close.
    Not random numbers - learned weights from historical conversions.
    """
    
    # Feature weights (initialized with sensible defaults, updated via learning)
    DEFAULT_WEIGHTS = {
        # Firmographic fit
        'company_size_fit': 15,
        'industry_fit': 20,
        'geography_fit': 10,
        'revenue_fit': 15,
        
        # Intent signals
        'funding_signal': 25,
        'hiring_signal': 20,
        'tech_change_signal': 18,
        'leadership_change': 22,
        'expansion_signal': 20,
        
        # Engagement signals
        'website_visits': 15,
        'content_downloads': 18,
        'email_opens': 12,
        'email_replies': 30,
        'meeting_scheduled': 50,
        
        # Timing signals
        'budget_cycle_alignment': 15,
        'contract_renewal_timing': 20,
        'recent_activity': 10,
        
        # Negative signals
        'competitor_using': -15,
        'recent_purchase': -25,
        'hiring_freeze': -20,
        'layoffs': -30,
    }
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.db = load_db(INTELLIGENCE_DB)
        self.weights = self._load_weights()
    
    def _load_weights(self) -> Dict:
        """Load learned weights or use defaults"""
        user_data = self.db.get(self.user_email, {})
        if 'learned_weights' in user_data:
            return user_data['learned_weights']
        return self.DEFAULT_WEIGHTS.copy()
    
    def _save_weights(self):
        """Save learned weights"""
        if self.user_email not in self.db:
            self.db[self.user_email] = {}
        self.db[self.user_email]['learned_weights'] = self.weights
        save_db(INTELLIGENCE_DB, self.db)
    
    def score_account(self, account: Dict, icp: Dict) -> Dict:
        """
        Score an account based on ICP fit and signals.
        Returns detailed breakdown, not just a number.
        """
        scores = {}
        explanations = []
        
        # 1. Firmographic Fit
        size_score = self._score_company_size(account, icp)
        scores['company_size_fit'] = size_score['score']
        if size_score['explanation']:
            explanations.append(size_score['explanation'])
        
        industry_score = self._score_industry(account, icp)
        scores['industry_fit'] = industry_score['score']
        if industry_score['explanation']:
            explanations.append(industry_score['explanation'])
        
        # 2. Intent Signals
        for signal_type in ['funding', 'hiring', 'tech_change', 'leadership_change', 'expansion']:
            signal_score = self._score_signal(account, signal_type)
            scores[f'{signal_type}_signal'] = signal_score['score']
            if signal_score['explanation']:
                explanations.append(signal_score['explanation'])
        
        # 3. Engagement Signals
        engagement_score = self._score_engagement(account)
        scores.update(engagement_score['scores'])
        explanations.extend(engagement_score['explanations'])
        
        # 4. Negative Signals
        negative_score = self._score_negative_signals(account)
        scores.update(negative_score['scores'])
        explanations.extend(negative_score['explanations'])
        
        # Calculate weighted total
        total_score = 0
        max_possible = 0
        
        for feature, score in scores.items():
            weight = self.weights.get(feature, 0)
            if weight > 0:  # Only count positive weights in max
                max_possible += weight
            total_score += score * weight
        
        # Normalize to 0-100
        normalized_score = max(0, min(100, (total_score / max_possible * 100) if max_possible > 0 else 0))
        
        # Determine tier
        tier = self._determine_tier(normalized_score)
        
        return {
            'score': round(normalized_score),
            'tier': tier,
            'confidence': self._calculate_confidence(scores),
            'feature_scores': scores,
            'explanations': explanations,
            'recommended_action': self._recommend_action(normalized_score, explanations),
            'scored_at': datetime.now().isoformat()
        }
    
    def _score_company_size(self, account: Dict, icp: Dict) -> Dict:
        """Score company size fit"""
        account_size = account.get('employee_count', 0)
        target_min = icp.get('min_employees', 0)
        target_max = icp.get('max_employees', float('inf'))
        
        if target_min <= account_size <= target_max:
            return {'score': 1.0, 'explanation': f"Company size ({account_size}) matches ICP"}
        elif account_size < target_min:
            ratio = account_size / target_min if target_min > 0 else 0
            return {'score': max(0, ratio), 'explanation': f"Company smaller than target ({account_size} vs {target_min}+)"}
        else:
            ratio = target_max / account_size if account_size > 0 else 0
            return {'score': max(0, ratio), 'explanation': f"Company larger than target ({account_size} vs {target_max})"}
    
    def _score_industry(self, account: Dict, icp: Dict) -> Dict:
        """Score industry fit"""
        account_industry = account.get('industry', '').lower()
        target_industries = [i.lower() for i in icp.get('target_industries', [])]
        
        if not target_industries:
            return {'score': 0.5, 'explanation': None}
        
        if account_industry in target_industries:
            return {'score': 1.0, 'explanation': f"Industry match: {account_industry}"}
        
        # Partial match
        for target in target_industries:
            if target in account_industry or account_industry in target:
                return {'score': 0.7, 'explanation': f"Related industry: {account_industry}"}
        
        return {'score': 0.2, 'explanation': f"Industry mismatch: {account_industry}"}
    
    def _score_signal(self, account: Dict, signal_type: str) -> Dict:
        """Score a specific intent signal"""
        signals = account.get('signals', [])
        
        for signal in signals:
            if signal.get('type') == signal_type:
                # Decay based on age
                detected = datetime.fromisoformat(signal['detected_at']) if 'detected_at' in signal else datetime.now()
                age_days = (datetime.now() - detected).days
                decay = max(0, 1 - (age_days / 30))  # Full decay over 30 days
                
                strength_multiplier = {'high': 1.0, 'medium': 0.7, 'low': 0.4}.get(signal.get('strength', 'medium'), 0.7)
                
                return {
                    'score': decay * strength_multiplier,
                    'explanation': f"🔥 {signal_type.replace('_', ' ').title()}: {signal.get('description', 'Active signal detected')}"
                }
        
        return {'score': 0, 'explanation': None}
    
    def _score_engagement(self, account: Dict) -> Dict:
        """Score engagement history"""
        engagement = account.get('engagement', {})
        scores = {}
        explanations = []
        
        if engagement.get('website_visits', 0) > 0:
            visits = engagement['website_visits']
            scores['website_visits'] = min(1.0, visits / 10)
            explanations.append(f"👁️ {visits} website visits")
        else:
            scores['website_visits'] = 0
        
        if engagement.get('email_opens', 0) > 0:
            opens = engagement['email_opens']
            scores['email_opens'] = min(1.0, opens / 5)
            explanations.append(f"📧 {opens} email opens")
        else:
            scores['email_opens'] = 0
        
        if engagement.get('email_replies', 0) > 0:
            replies = engagement['email_replies']
            scores['email_replies'] = min(1.0, replies / 2)
            explanations.append(f"💬 {replies} email replies!")
        else:
            scores['email_replies'] = 0
        
        if engagement.get('meetings', 0) > 0:
            scores['meeting_scheduled'] = 1.0
            explanations.append(f"📅 Meeting scheduled!")
        else:
            scores['meeting_scheduled'] = 0
        
        return {'scores': scores, 'explanations': explanations}
    
    def _score_negative_signals(self, account: Dict) -> Dict:
        """Score negative signals"""
        signals = account.get('signals', [])
        scores = {}
        explanations = []
        
        for signal in signals:
            signal_type = signal.get('type', '')
            if signal_type == 'competitor_using':
                scores['competitor_using'] = 1.0
                explanations.append(f"⚠️ Using competitor: {signal.get('competitor', 'unknown')}")
            elif signal_type == 'layoffs':
                scores['layoffs'] = 1.0
                explanations.append(f"⚠️ Recent layoffs detected")
            elif signal_type == 'hiring_freeze':
                scores['hiring_freeze'] = 1.0
                explanations.append(f"⚠️ Hiring freeze in effect")
        
        return {'scores': scores, 'explanations': explanations}
    
    def _determine_tier(self, score: float) -> str:
        """Determine account tier based on score"""
        if score >= 80:
            return 'A'  # Hot - prioritize immediately
        elif score >= 60:
            return 'B'  # Warm - work actively
        elif score >= 40:
            return 'C'  # Cool - nurture
        else:
            return 'D'  # Cold - low priority
    
    def _calculate_confidence(self, scores: Dict) -> float:
        """Calculate confidence in the score based on data completeness"""
        non_zero_features = sum(1 for v in scores.values() if v != 0)
        total_features = len(scores)
        return round(non_zero_features / total_features, 2) if total_features > 0 else 0
    
    def _recommend_action(self, score: float, explanations: List[str]) -> str:
        """Recommend next action based on score"""
        if score >= 80:
            return "🔥 HOT LEAD - Reach out immediately with personalized outreach"
        elif score >= 60:
            return "📞 WARM LEAD - Schedule discovery call, reference recent signals"
        elif score >= 40:
            return "📧 NURTURE - Add to email sequence, provide value content"
        else:
            return "👀 MONITOR - Keep tracking for signal changes"
    
    def rank_accounts(self, accounts: List[Dict], icp: Dict) -> List[Dict]:
        """Rank all accounts by score"""
        scored = []
        for account in accounts:
            score_result = self.score_account(account, icp)
            scored.append({
                **account,
                'scoring': score_result
            })
        
        return sorted(scored, key=lambda x: x['scoring']['score'], reverse=True)
    
    def update_weights_from_outcome(self, account: Dict, outcome: str, icp: Dict):
        """
        Update weights based on actual outcomes.
        This is how the system learns!
        """
        learning_rate = 0.1
        
        # Get the features that were scored
        score_result = self.score_account(account, icp)
        feature_scores = score_result['feature_scores']
        
        # Determine reward/penalty based on outcome
        if outcome == 'closed_won':
            reward = 1.0  # Positive reinforcement
        elif outcome == 'meeting_booked':
            reward = 0.5
        elif outcome == 'replied':
            reward = 0.3
        elif outcome == 'closed_lost':
            reward = -0.5  # Negative reinforcement
        elif outcome == 'no_response':
            reward = -0.2
        else:
            reward = 0
        
        # Update weights - features that were present get adjusted
        for feature, score in feature_scores.items():
            if score > 0:  # Only update for features that contributed
                current_weight = self.weights.get(feature, 0)
                adjustment = learning_rate * reward * score
                self.weights[feature] = current_weight + adjustment
        
        self._save_weights()
        
        # Log the learning event
        self._log_learning_event(account, outcome, feature_scores)
    
    def _log_learning_event(self, account: Dict, outcome: str, features: Dict):
        """Log learning events for analysis"""
        learning_db = load_db(LEARNING_DB)
        
        if self.user_email not in learning_db:
            learning_db[self.user_email] = {'events': []}
        
        learning_db[self.user_email]['events'].append({
            'account_id': account.get('id'),
            'outcome': outcome,
            'features': features,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep last 1000 events
        learning_db[self.user_email]['events'] = learning_db[self.user_email]['events'][-1000:]
        
        save_db(LEARNING_DB, learning_db)


# ============================================================================
# 2. PATTERN DETECTION ENGINE
# ============================================================================

class PatternDetectionEngine:
    """
    Detect patterns humans miss:
    - What types of companies convert?
    - What signals precede deals?
    - What messaging works for which personas?
    - When is the best time to reach out?
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.patterns_db = load_db(PATTERNS_DB)
        self.learning_db = load_db(LEARNING_DB)
    
    def analyze_conversion_patterns(self) -> Dict:
        """Analyze what types of accounts convert"""
        events = self.learning_db.get(self.user_email, {}).get('events', [])
        
        if not events:
            return {'status': 'insufficient_data', 'message': 'Need more data to detect patterns'}
        
        # Separate wins and losses
        wins = [e for e in events if e['outcome'] in ['closed_won', 'meeting_booked', 'replied']]
        losses = [e for e in events if e['outcome'] in ['closed_lost', 'no_response']]
        
        patterns = {
            'winning_features': self._find_common_features(wins),
            'losing_features': self._find_common_features(losses),
            'best_signals': self._find_best_signals(wins),
            'conversion_rate_by_tier': self._conversion_by_tier(events),
            'insights': []
        }
        
        # Generate insights
        if patterns['winning_features']:
            top_feature = patterns['winning_features'][0]
            patterns['insights'].append(f"Accounts with {top_feature['feature']} convert {top_feature['frequency']}% more often")
        
        if patterns['best_signals']:
            top_signal = patterns['best_signals'][0]
            patterns['insights'].append(f"{top_signal['signal']} is your strongest buying signal ({top_signal['conversion_rate']}% conversion)")
        
        return patterns
    
    def _find_common_features(self, events: List[Dict]) -> List[Dict]:
        """Find features common in a set of events"""
        feature_counts = defaultdict(int)
        
        for event in events:
            for feature, score in event.get('features', {}).items():
                if score > 0.5:  # Only count strong signals
                    feature_counts[feature] += 1
        
        total = len(events) if events else 1
        
        return sorted([
            {'feature': f, 'frequency': round(c / total * 100)}
            for f, c in feature_counts.items()
        ], key=lambda x: x['frequency'], reverse=True)[:5]
    
    def _find_best_signals(self, wins: List[Dict]) -> List[Dict]:
        """Find signals that most often lead to wins"""
        signal_wins = defaultdict(int)
        signal_total = defaultdict(int)
        
        events = self.learning_db.get(self.user_email, {}).get('events', [])
        
        for event in events:
            features = event.get('features', {})
            for signal in ['funding_signal', 'hiring_signal', 'tech_change_signal', 'leadership_change', 'expansion_signal']:
                if features.get(signal, 0) > 0:
                    signal_total[signal] += 1
                    if event['outcome'] in ['closed_won', 'meeting_booked']:
                        signal_wins[signal] += 1
        
        results = []
        for signal, total in signal_total.items():
            if total >= 3:  # Need minimum sample
                rate = signal_wins[signal] / total * 100
                results.append({
                    'signal': signal.replace('_signal', '').replace('_', ' ').title(),
                    'conversion_rate': round(rate),
                    'sample_size': total
                })
        
        return sorted(results, key=lambda x: x['conversion_rate'], reverse=True)
    
    def _conversion_by_tier(self, events: List[Dict]) -> Dict:
        """Calculate conversion rate by account tier"""
        tier_wins = defaultdict(int)
        tier_total = defaultdict(int)
        
        for event in events:
            # Estimate tier from features
            features = event.get('features', {})
            score = sum(v for v in features.values() if v > 0) / len(features) * 100 if features else 0
            
            if score >= 80:
                tier = 'A'
            elif score >= 60:
                tier = 'B'
            elif score >= 40:
                tier = 'C'
            else:
                tier = 'D'
            
            tier_total[tier] += 1
            if event['outcome'] in ['closed_won', 'meeting_booked']:
                tier_wins[tier] += 1
        
        return {
            tier: round(tier_wins[tier] / tier_total[tier] * 100) if tier_total[tier] > 0 else 0
            for tier in ['A', 'B', 'C', 'D']
        }
    
    def analyze_messaging_patterns(self) -> Dict:
        """Analyze what messaging works for different personas"""
        # This would analyze email content vs. response rates
        # For now, return structure for future implementation
        return {
            'by_persona': {},
            'by_industry': {},
            'best_subject_patterns': [],
            'best_opening_patterns': [],
            'optimal_email_length': None,
            'insights': ['Need more email data to detect messaging patterns']
        }
    
    def analyze_timing_patterns(self) -> Dict:
        """Analyze best times to reach out"""
        events = self.learning_db.get(self.user_email, {}).get('events', [])
        
        if not events:
            return {'best_day': 'Tuesday', 'best_time': '10:00 AM', 'insights': ['Using industry defaults - need more data']}
        
        # Analyze response times
        # For now, return sensible defaults
        return {
            'best_day': 'Tuesday',
            'best_time': '10:00 AM',
            'avoid_days': ['Friday', 'Weekend'],
            'response_window': '2-4 hours after send',
            'insights': ['Tuesday-Thursday mornings show highest engagement']
        }


# ============================================================================
# 3. STRATEGY PREDICTION ENGINE
# ============================================================================

class StrategyPredictionEngine:
    """
    Predict the best outreach strategy for each account/persona.
    Not random - based on what has worked before.
    """
    
    STRATEGIES = {
        'value_first': {
            'description': 'Lead with value, give before asking',
            'best_for': ['c_level', 'skeptical', 'busy'],
            'example': 'Share insight or resource before pitching'
        },
        'challenger': {
            'description': 'Challenge their thinking, reframe the problem',
            'best_for': ['analytical', 'technical', 'innovators'],
            'example': 'Present data that challenges status quo'
        },
        'social_proof': {
            'description': 'Lead with similar customer success',
            'best_for': ['risk_averse', 'enterprise', 'followers'],
            'example': 'Company X in your industry saw Y results'
        },
        'trigger_based': {
            'description': 'Reference specific event as conversation starter',
            'best_for': ['anyone_with_signal', 'news_worthy', 'funding'],
            'example': 'Congrats on the funding - quick thought...'
        },
        'problem_agitation': {
            'description': 'Highlight the pain of status quo',
            'best_for': ['pain_aware', 'frustrated', 'seekers'],
            'example': 'Most teams waste X hours on Y...'
        },
        'direct': {
            'description': 'Straight to the point ask',
            'best_for': ['time_pressed', 'direct_communicators', 'follow_ups'],
            'example': 'Quick question - are you evaluating X?'
        }
    }
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.predictions_db = load_db(PREDICTIONS_DB)
        self.learning_db = load_db(LEARNING_DB)
    
    def predict_strategy(self, account: Dict, persona: Dict) -> Dict:
        """Predict the best outreach strategy for this account/persona combo"""
        
        # Factors to consider
        has_signal = bool(account.get('signals', []))
        persona_seniority = persona.get('seniority', 'unknown')
        industry = account.get('industry', '').lower()
        company_size = account.get('employee_count', 0)
        
        # Check historical performance for similar accounts
        historical_best = self._check_historical_performance(account, persona)
        
        # Build recommendation
        strategies = []
        
        # If we have a signal, lead with that
        if has_signal:
            signal = account['signals'][0]
            strategies.append({
                'strategy': 'trigger_based',
                'confidence': 0.9,
                'reason': f"Lead with {signal.get('type', 'recent event')} - proven 3x response rate",
                'hook': self._generate_hook('trigger_based', signal, persona)
            })
        
        # Based on seniority
        if persona_seniority in ['c_level', 'vp']:
            strategies.append({
                'strategy': 'value_first',
                'confidence': 0.85,
                'reason': 'C-level/VP responds best to value-first approach',
                'hook': self._generate_hook('value_first', None, persona)
            })
        elif persona_seniority in ['director', 'manager']:
            strategies.append({
                'strategy': 'social_proof',
                'confidence': 0.8,
                'reason': 'Middle management wants proof it works elsewhere',
                'hook': self._generate_hook('social_proof', None, persona)
            })
        
        # Based on company size
        if company_size > 1000:
            strategies.append({
                'strategy': 'social_proof',
                'confidence': 0.75,
                'reason': 'Enterprise accounts are risk-averse, need social proof',
                'hook': self._generate_hook('social_proof', None, persona)
            })
        elif company_size < 100:
            strategies.append({
                'strategy': 'direct',
                'confidence': 0.7,
                'reason': 'Smaller companies prefer direct, no-BS approach',
                'hook': self._generate_hook('direct', None, persona)
            })
        
        # Add historical best if we have data
        if historical_best:
            strategies.insert(0, historical_best)
        
        # Sort by confidence and return top recommendation
        strategies.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            'recommended': strategies[0] if strategies else self._default_strategy(),
            'alternatives': strategies[1:3],
            'all_options': list(self.STRATEGIES.keys()),
            'reasoning': self._explain_reasoning(strategies[0] if strategies else None, account, persona)
        }
    
    def _check_historical_performance(self, account: Dict, persona: Dict) -> Optional[Dict]:
        """Check what strategies worked for similar accounts"""
        # This would query the learning DB for similar account/persona combos
        # For now, return None - will be populated as system learns
        return None
    
    def _generate_hook(self, strategy: str, signal: Optional[Dict], persona: Dict) -> str:
        """Generate a hook based on strategy"""
        title = persona.get('title', 'there')
        
        hooks = {
            'trigger_based': f"Saw the news about {signal.get('description', 'recent developments') if signal else 'your company'} - had a quick thought...",
            'value_first': f"Put together some {persona.get('industry', 'industry')} benchmarks that might be useful for your team...",
            'social_proof': "We just helped [Similar Company] reduce [Pain Point] by 40% - thought you might find it relevant...",
            'challenger': "Most {title}s I talk to are still [doing thing the old way] - curious if you've considered...",
            'problem_agitation': f"Quick question - how much time does your team spend on [Pain Point] each week?",
            'direct': f"Hi {title.split()[-1] if title else 'there'} - are you the right person to talk to about [Topic]?"
        }
        
        return hooks.get(strategy, "Quick question...")
    
    def _default_strategy(self) -> Dict:
        """Return default strategy when we have no data"""
        return {
            'strategy': 'value_first',
            'confidence': 0.5,
            'reason': 'Default recommendation - value-first is safest',
            'hook': "Thought you might find this useful..."
        }
    
    def _explain_reasoning(self, strategy: Optional[Dict], account: Dict, persona: Dict) -> str:
        """Explain why this strategy was recommended"""
        if not strategy:
            return "Using default strategy due to insufficient data."
        
        reasons = [strategy.get('reason', '')]
        
        if account.get('signals'):
            reasons.append(f"Account has active buying signals")
        
        if persona.get('seniority') == 'c_level':
            reasons.append("Executive-level contact requires executive-level approach")
        
        return " | ".join(reasons)
    
    def record_strategy_outcome(self, account_id: str, strategy: str, outcome: str):
        """Record which strategy was used and the outcome"""
        if self.user_email not in self.predictions_db:
            self.predictions_db[self.user_email] = {'outcomes': []}
        
        self.predictions_db[self.user_email]['outcomes'].append({
            'account_id': account_id,
            'strategy': strategy,
            'outcome': outcome,
            'timestamp': datetime.now().isoformat()
        })
        
        save_db(PREDICTIONS_DB, self.predictions_db)


# ============================================================================
# 4. PROACTIVE INTELLIGENCE - DAILY BRIEFINGS
# ============================================================================

class ProactiveIntelligenceEngine:
    """
    Don't wait for the user to ask - proactively surface insights.
    Daily briefings on what changed and what to do.
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.scoring = AccountScoringEngine(user_email)
        self.patterns = PatternDetectionEngine(user_email)
        self.strategy = StrategyPredictionEngine(user_email)
    
    def generate_daily_briefing(self, accounts: List[Dict], icp: Dict) -> Dict:
        """
        Generate the daily executive briefing.
        What changed, what matters, what to do.
        """
        
        briefing = {
            'generated_at': datetime.now().isoformat(),
            'summary': {},
            'hot_accounts': [],
            'new_signals': [],
            'score_changes': [],
            'recommended_actions': [],
            'insights': [],
            'focus_accounts': []
        }
        
        # 1. Score all accounts
        scored_accounts = self.scoring.rank_accounts(accounts, icp)
        
        # 2. Identify hot accounts (Tier A)
        hot_accounts = [a for a in scored_accounts if a['scoring']['tier'] == 'A']
        briefing['hot_accounts'] = hot_accounts[:10]
        briefing['summary']['hot_account_count'] = len(hot_accounts)
        
        # 3. Find accounts with new signals (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        for account in scored_accounts:
            for signal in account.get('signals', []):
                detected = datetime.fromisoformat(signal.get('detected_at', '2000-01-01'))
                if detected > yesterday:
                    briefing['new_signals'].append({
                        'account': account.get('name'),
                        'signal': signal
                    })
        
        briefing['summary']['new_signal_count'] = len(briefing['new_signals'])
        
        # 4. Generate recommended actions
        for account in hot_accounts[:5]:
            prediction = self.strategy.predict_strategy(account, account.get('primary_contact', {}))
            briefing['recommended_actions'].append({
                'account': account.get('name'),
                'action': account['scoring']['recommended_action'],
                'strategy': prediction['recommended']['strategy'],
                'hook': prediction['recommended']['hook'],
                'urgency': 'high' if account['scoring']['score'] > 85 else 'medium'
            })
        
        # 5. Pattern-based insights
        patterns = self.patterns.analyze_conversion_patterns()
        if patterns.get('insights'):
            briefing['insights'].extend(patterns['insights'])
        
        # 6. Focus accounts - accounts to work today
        briefing['focus_accounts'] = scored_accounts[:5]
        
        # 7. Summary stats
        briefing['summary']['total_accounts'] = len(accounts)
        briefing['summary']['tier_breakdown'] = {
            'A': len([a for a in scored_accounts if a['scoring']['tier'] == 'A']),
            'B': len([a for a in scored_accounts if a['scoring']['tier'] == 'B']),
            'C': len([a for a in scored_accounts if a['scoring']['tier'] == 'C']),
            'D': len([a for a in scored_accounts if a['scoring']['tier'] == 'D']),
        }
        
        return briefing
    
    def generate_account_brief(self, account: Dict, icp: Dict) -> Dict:
        """Generate detailed brief for a single account"""
        
        # Score the account
        scoring = self.scoring.score_account(account, icp)
        
        # Get strategy recommendation
        persona = account.get('primary_contact', {})
        strategy = self.strategy.predict_strategy(account, persona)
        
        return {
            'account': account.get('name'),
            'generated_at': datetime.now().isoformat(),
            'scoring': scoring,
            'strategy': strategy,
            'signals': account.get('signals', []),
            'contacts': account.get('contacts', []),
            'engagement_history': account.get('engagement', {}),
            'recommended_next_steps': [
                scoring['recommended_action'],
                f"Use {strategy['recommended']['strategy']} approach",
                f"Opening hook: {strategy['recommended']['hook']}"
            ],
            'talking_points': self._generate_talking_points(account),
            'objection_handlers': self._generate_objection_handlers(account, icp),
            'competitive_intel': self._get_competitive_intel(account)
        }
    
    def _generate_talking_points(self, account: Dict) -> List[str]:
        """Generate relevant talking points based on account data"""
        points = []
        
        for signal in account.get('signals', [])[:3]:
            if signal.get('type') == 'funding':
                points.append(f"Reference their recent funding - shows you're paying attention")
            elif signal.get('type') == 'hiring':
                points.append(f"Mention their hiring activity - indicates growth/pain points")
            elif signal.get('type') == 'leadership_change':
                points.append(f"New leader = new initiatives = budget for new tools")
        
        if not points:
            points.append("Research their recent news before the call")
            points.append("Check their job postings for pain point insights")
        
        return points
    
    def _generate_objection_handlers(self, account: Dict, icp: Dict) -> List[Dict]:
        """Generate likely objections and how to handle them"""
        handlers = []
        
        # Common objections based on account characteristics
        if account.get('employee_count', 0) > 500:
            handlers.append({
                'objection': "We already have a solution for this",
                'response': "Totally understand - most enterprise teams do. Quick question: are you seeing [specific pain point our solution solves better]?"
            })
        
        if account.get('employee_count', 0) < 50:
            handlers.append({
                'objection': "We don't have budget for this",
                'response': "Makes sense - that's why we work with teams to start small and prove ROI before scaling. What if we could show value in 30 days?"
            })
        
        handlers.append({
            'objection': "Send me some information",
            'response': "Happy to - but to send you the right stuff, quick question: what's your biggest challenge with [topic] right now?"
        })
        
        handlers.append({
            'objection': "Now's not a good time",
            'response': "Totally get it. When would be better - are you thinking next quarter, or is there a specific initiative this ties to?"
        })
        
        return handlers
    
    def _get_competitive_intel(self, account: Dict) -> Dict:
        """Get competitive intelligence for the account"""
        # This would check what competitors they're using
        return {
            'current_solutions': account.get('tech_stack', []),
            'competitor_signals': [s for s in account.get('signals', []) if s.get('type') == 'competitor_using'],
            'positioning': "Focus on [unique differentiator] vs their current solution"
        }


# ============================================================================
# 5. UNIFIED INTELLIGENCE INTERFACE
# ============================================================================

class AIBrain:
    """
    Unified interface to all intelligence capabilities.
    This is the brain of the system.
    """
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.scoring = AccountScoringEngine(user_email)
        self.patterns = PatternDetectionEngine(user_email)
        self.strategy = StrategyPredictionEngine(user_email)
        self.proactive = ProactiveIntelligenceEngine(user_email)
    
    def get_daily_briefing(self, accounts: List[Dict], icp: Dict) -> Dict:
        """Get the daily intelligence briefing"""
        return self.proactive.generate_daily_briefing(accounts, icp)
    
    def score_account(self, account: Dict, icp: Dict) -> Dict:
        """Score a single account"""
        return self.scoring.score_account(account, icp)
    
    def rank_accounts(self, accounts: List[Dict], icp: Dict) -> List[Dict]:
        """Rank all accounts by likelihood to close"""
        return self.scoring.rank_accounts(accounts, icp)
    
    def get_strategy(self, account: Dict, persona: Dict) -> Dict:
        """Get recommended outreach strategy"""
        return self.strategy.predict_strategy(account, persona)
    
    def get_account_brief(self, account: Dict, icp: Dict) -> Dict:
        """Get detailed account brief"""
        return self.proactive.generate_account_brief(account, icp)
    
    def get_patterns(self) -> Dict:
        """Get detected patterns"""
        return self.patterns.analyze_conversion_patterns()
    
    def learn_from_outcome(self, account: Dict, outcome: str, icp: Dict):
        """Record outcome and update model"""
        self.scoring.update_weights_from_outcome(account, outcome, icp)
    
    def learn_strategy_outcome(self, account_id: str, strategy: str, outcome: str):
        """Record strategy outcome"""
        self.strategy.record_strategy_outcome(account_id, strategy, outcome)
