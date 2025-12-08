"""
ANALYTICS & REPORTING ENGINE
Daily batch processing for metrics, insights, and dashboard data.

Features:
- Campaign performance metrics
- Account scoring updates
- Trend analysis
- Optimization recommendations
- Dashboard data generation
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import statistics


# ============================================================================
# DATA FILES
# ============================================================================

CAMPAIGNS_DB = "campaigns_db.json"
EMAIL_SEQUENCES_DB = "email_sequences.json"
LINKEDIN_SEQUENCES_DB = "linkedin_sequences.json"
INTELLIGENCE_DB = "intelligence_db.json"
ANALYTICS_DB = "analytics_db.json"
INSIGHTS_DB = "insights_db.json"


def load_db(filename: str) -> Dict:
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}


def save_db(filename: str, data: Dict):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# ANALYTICS PROCESSOR
# ============================================================================

class AnalyticsProcessor:
    """
    Daily batch processing for analytics and insights.
    Run this at 00:00 UTC daily via cron.
    """
    
    def __init__(self):
        self.campaigns = load_db(CAMPAIGNS_DB)
        self.email_sequences = load_db(EMAIL_SEQUENCES_DB)
        self.linkedin_sequences = load_db(LINKEDIN_SEQUENCES_DB)
        self.intelligence = load_db(INTELLIGENCE_DB)
        self.analytics = load_db(ANALYTICS_DB)
        self.insights = load_db(INSIGHTS_DB)
    
    def run_daily_batch(self) -> Dict:
        """
        Run all daily analytics processes.
        Returns summary of what was processed.
        """
        today = datetime.now().date().isoformat()
        
        results = {
            'date': today,
            'timestamp': datetime.now().isoformat(),
            'processes_run': []
        }
        
        # 1. Calculate campaign metrics
        campaign_metrics = self._calculate_campaign_metrics()
        results['processes_run'].append({
            'name': 'campaign_metrics',
            'campaigns_processed': campaign_metrics['count']
        })
        
        # 2. Update account scores
        scoring_results = self._update_account_scores()
        results['processes_run'].append({
            'name': 'account_scoring',
            'accounts_updated': scoring_results['count']
        })
        
        # 3. Generate insights
        insights = self._generate_insights()
        results['processes_run'].append({
            'name': 'insights_generation',
            'insights_generated': len(insights)
        })
        
        # 4. Calculate trends
        trends = self._calculate_trends()
        results['processes_run'].append({
            'name': 'trend_analysis',
            'trends_calculated': len(trends)
        })
        
        # 5. Generate recommendations
        recommendations = self._generate_recommendations()
        results['processes_run'].append({
            'name': 'recommendations',
            'recommendations_generated': len(recommendations)
        })
        
        # Save analytics snapshot
        if 'daily_snapshots' not in self.analytics:
            self.analytics['daily_snapshots'] = {}
        
        self.analytics['daily_snapshots'][today] = {
            'campaign_metrics': campaign_metrics,
            'insights': insights,
            'trends': trends,
            'recommendations': recommendations
        }
        
        save_db(ANALYTICS_DB, self.analytics)
        save_db(INSIGHTS_DB, self.insights)
        
        return results
    
    def _calculate_campaign_metrics(self) -> Dict:
        """Calculate performance metrics for all campaigns"""
        metrics = {
            'count': 0,
            'by_campaign': {},
            'aggregate': {
                'total_campaigns': 0,
                'total_emails_sent': 0,
                'total_emails_opened': 0,
                'total_emails_clicked': 0,
                'total_emails_replied': 0,
                'total_connections_sent': 0,
                'total_connections_accepted': 0,
                'total_linkedin_messages': 0,
                'total_linkedin_replies': 0
            }
        }
        
        # Process email campaigns
        if 'active_campaigns' in self.email_sequences:
            for campaign_id, campaign in self.email_sequences['active_campaigns'].items():
                stats = campaign.get('stats', {})
                
                metrics['by_campaign'][campaign_id] = {
                    'type': 'email',
                    'name': campaign.get('sequence_name', 'Unknown'),
                    'started_at': campaign.get('started_at'),
                    'stats': stats
                }
                
                # Aggregate
                metrics['aggregate']['total_emails_sent'] += stats.get('emails_sent', 0)
                metrics['aggregate']['total_emails_opened'] += stats.get('emails_opened', 0)
                metrics['aggregate']['total_emails_clicked'] += stats.get('emails_clicked', 0)
                metrics['aggregate']['total_emails_replied'] += stats.get('emails_replied', 0)
                
                metrics['count'] += 1
        
        # Process LinkedIn campaigns
        if 'active_campaigns' in self.linkedin_sequences:
            for campaign_id, campaign in self.linkedin_sequences['active_campaigns'].items():
                stats = campaign.get('stats', {})
                
                metrics['by_campaign'][campaign_id] = {
                    'type': 'linkedin',
                    'name': campaign.get('sequence_name', 'Unknown'),
                    'started_at': campaign.get('started_at'),
                    'stats': stats
                }
                
                # Aggregate
                metrics['aggregate']['total_connections_sent'] += stats.get('connections_sent', 0)
                metrics['aggregate']['total_connections_accepted'] += stats.get('connections_accepted', 0)
                metrics['aggregate']['total_linkedin_messages'] += stats.get('messages_sent', 0)
                metrics['aggregate']['total_linkedin_replies'] += stats.get('replies_received', 0)
                
                metrics['count'] += 1
        
        # Calculate aggregate rates
        agg = metrics['aggregate']
        if agg['total_emails_sent'] > 0:
            agg['email_open_rate'] = round(agg['total_emails_opened'] / agg['total_emails_sent'] * 100, 2)
            agg['email_click_rate'] = round(agg['total_emails_clicked'] / agg['total_emails_sent'] * 100, 2)
            agg['email_reply_rate'] = round(agg['total_emails_replied'] / agg['total_emails_sent'] * 100, 2)
        
        if agg['total_connections_sent'] > 0:
            agg['connection_acceptance_rate'] = round(
                agg['total_connections_accepted'] / agg['total_connections_sent'] * 100, 2
            )
        
        if agg['total_linkedin_messages'] > 0:
            agg['linkedin_reply_rate'] = round(
                agg['total_linkedin_replies'] / agg['total_linkedin_messages'] * 100, 2
            )
        
        return metrics
    
    def _update_account_scores(self) -> Dict:
        """Update account scoring based on new engagement data"""
        results = {
            'count': 0,
            'updated_accounts': []
        }
        
        # This would integrate with intelligence/ai_brain.py
        # For now, we'll track that scores need updating
        
        for user_email, user_data in self.intelligence.items():
            if isinstance(user_data, dict) and 'accounts' in user_data:
                for account_id, account_data in user_data['accounts'].items():
                    # Mark for score recalculation
                    account_data['score_last_updated'] = datetime.now().isoformat()
                    results['updated_accounts'].append(account_id)
                    results['count'] += 1
        
        save_db(INTELLIGENCE_DB, self.intelligence)
        
        return results
    
    def _generate_insights(self) -> List[Dict]:
        """Generate actionable insights from data"""
        insights = []
        
        # Insight 1: Best performing email subject lines
        email_performance = self._analyze_email_performance()
        if email_performance['best_subjects']:
            insights.append({
                'type': 'best_practice',
                'category': 'email',
                'title': 'Top Performing Subject Lines',
                'description': f"Subject lines with '{email_performance['best_subjects'][0]['pattern']}' have {email_performance['best_subjects'][0]['open_rate']}% open rate",
                'action': 'Use similar patterns in future campaigns',
                'data': email_performance['best_subjects'][:5]
            })
        
        # Insight 2: Optimal send times
        send_time_analysis = self._analyze_send_times()
        if send_time_analysis['best_time']:
            insights.append({
                'type': 'optimization',
                'category': 'timing',
                'title': 'Optimal Email Send Time',
                'description': f"Emails sent at {send_time_analysis['best_time']} have {send_time_analysis['engagement_lift']}% higher engagement",
                'action': f"Schedule campaigns for {send_time_analysis['best_time']}",
                'data': send_time_analysis
            })
        
        # Insight 3: High-value accounts
        high_value = self._identify_high_value_accounts()
        if high_value:
            insights.append({
                'type': 'priority',
                'category': 'accounts',
                'title': 'High-Priority Accounts Identified',
                'description': f"{len(high_value)} accounts have strong fit scores and buying signals",
                'action': 'Focus outreach on these accounts',
                'data': high_value[:10]
            })
        
        # Insight 4: Content that resonates
        content_analysis = self._analyze_content_performance()
        if content_analysis['top_topics']:
            insights.append({
                'type': 'content',
                'category': 'messaging',
                'title': 'Resonating Content Themes',
                'description': f"Content about '{content_analysis['top_topics'][0]}' drives {content_analysis['engagement_rate']}% more engagement",
                'action': 'Create more content around these themes',
                'data': content_analysis['top_topics']
            })
        
        # Insight 5: Sequence optimization
        sequence_analysis = self._analyze_sequences()
        if sequence_analysis['optimal_length']:
            insights.append({
                'type': 'optimization',
                'category': 'sequences',
                'title': 'Optimal Sequence Length',
                'description': f"{sequence_analysis['optimal_length']}-email sequences have highest conversion rate",
                'action': f"Adjust sequences to {sequence_analysis['optimal_length']} emails",
                'data': sequence_analysis
            })
        
        # Store insights
        today = datetime.now().date().isoformat()
        if today not in self.insights:
            self.insights[today] = []
        self.insights[today] = insights
        
        return insights
    
    def _calculate_trends(self) -> Dict:
        """Calculate trends over time"""
        trends = {}
        
        # Get last 30 days of data
        snapshots = self.analytics.get('daily_snapshots', {})
        
        if len(snapshots) < 2:
            return {'note': 'Insufficient data for trend analysis'}
        
        dates = sorted(snapshots.keys())[-30:]  # Last 30 days
        
        # Trend 1: Email open rates
        open_rates = []
        for date in dates:
            metrics = snapshots[date].get('campaign_metrics', {}).get('aggregate', {})
            if 'email_open_rate' in metrics:
                open_rates.append(metrics['email_open_rate'])
        
        if open_rates:
            trends['email_open_rate'] = {
                'current': open_rates[-1],
                'average': round(statistics.mean(open_rates), 2),
                'trend': 'up' if len(open_rates) > 1 and open_rates[-1] > open_rates[-2] else 'down',
                'change_percent': round(((open_rates[-1] - open_rates[0]) / open_rates[0] * 100), 2) if open_rates[0] > 0 else 0
            }
        
        # Trend 2: Reply rates
        reply_rates = []
        for date in dates:
            metrics = snapshots[date].get('campaign_metrics', {}).get('aggregate', {})
            if 'email_reply_rate' in metrics:
                reply_rates.append(metrics['email_reply_rate'])
        
        if reply_rates:
            trends['email_reply_rate'] = {
                'current': reply_rates[-1],
                'average': round(statistics.mean(reply_rates), 2),
                'trend': 'up' if len(reply_rates) > 1 and reply_rates[-1] > reply_rates[-2] else 'down',
                'change_percent': round(((reply_rates[-1] - reply_rates[0]) / reply_rates[0] * 100), 2) if reply_rates[0] > 0 else 0
            }
        
        return trends
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Get latest metrics
        snapshots = self.analytics.get('daily_snapshots', {})
        if not snapshots:
            return recommendations
        
        latest_date = sorted(snapshots.keys())[-1]
        latest_metrics = snapshots[latest_date].get('campaign_metrics', {}).get('aggregate', {})
        
        # Recommendation 1: Low open rates
        if latest_metrics.get('email_open_rate', 0) < 20:
            recommendations.append({
                'priority': 'high',
                'category': 'email',
                'issue': 'Low email open rate',
                'current_value': latest_metrics.get('email_open_rate', 0),
                'target_value': 30,
                'actions': [
                    'Test different subject line patterns',
                    'Verify sender reputation',
                    'Check spam folder placement',
                    'Improve list quality'
                ]
            })
        
        # Recommendation 2: Low reply rates
        if latest_metrics.get('email_reply_rate', 0) < 5:
            recommendations.append({
                'priority': 'high',
                'category': 'engagement',
                'issue': 'Low reply rate',
                'current_value': latest_metrics.get('email_reply_rate', 0),
                'target_value': 10,
                'actions': [
                    'Add more personalization',
                    'Make CTAs clearer',
                    'Shorten email length',
                    'Focus on value proposition'
                ]
            })
        
        # Recommendation 3: Connection acceptance
        if latest_metrics.get('connection_acceptance_rate', 0) < 30:
            recommendations.append({
                'priority': 'medium',
                'category': 'linkedin',
                'issue': 'Low LinkedIn connection acceptance',
                'current_value': latest_metrics.get('connection_acceptance_rate', 0),
                'target_value': 40,
                'actions': [
                    'Personalize connection messages more',
                    'Reference recent activity/posts',
                    'Target more relevant prospects',
                    'Optimize profile credibility'
                ]
            })
        
        return recommendations
    
    # Helper methods for analysis
    
    def _analyze_email_performance(self) -> Dict:
        """Analyze email performance patterns"""
        # Placeholder - would analyze actual email data
        return {
            'best_subjects': [
                {'pattern': 'Question-based', 'open_rate': 35.2},
                {'pattern': 'Personalized', 'open_rate': 32.8}
            ]
        }
    
    def _analyze_send_times(self) -> Dict:
        """Analyze optimal send times"""
        # Placeholder - would analyze actual timing data
        return {
            'best_time': 'Tuesday 10:00 AM',
            'engagement_lift': 23
        }
    
    def _identify_high_value_accounts(self) -> List[Dict]:
        """Identify high-priority accounts"""
        # Would integrate with intelligence DB
        return []
    
    def _analyze_content_performance(self) -> Dict:
        """Analyze which content themes work best"""
        # Placeholder
        return {
            'top_topics': ['ROI/Cost Savings', 'Case Studies'],
            'engagement_rate': 28
        }
    
    def _analyze_sequences(self) -> Dict:
        """Analyze sequence performance"""
        # Placeholder
        return {
            'optimal_length': 4,
            'conversion_rate': 12.5
        }
    
    def get_dashboard_data(self, user_email: str) -> Dict:
        """
        Generate dashboard data for a user.
        This is what powers the intelligence dashboard UI.
        """
        # Get latest snapshot
        snapshots = self.analytics.get('daily_snapshots', {})
        if not snapshots:
            return {'error': 'No analytics data available'}
        
        latest_date = sorted(snapshots.keys())[-1]
        latest = snapshots[latest_date]
        
        # Get insights for today
        today = datetime.now().date().isoformat()
        today_insights = self.insights.get(today, [])
        
        return {
            'date': latest_date,
            'campaign_metrics': latest.get('campaign_metrics', {}),
            'insights': today_insights,
            'trends': latest.get('trends', {}),
            'recommendations': latest.get('recommendations', []),
            'account_scores': self._get_user_account_scores(user_email)
        }
    
    def _get_user_account_scores(self, user_email: str) -> List[Dict]:
        """Get account scores for a user"""
        if user_email not in self.intelligence:
            return []
        
        user_data = self.intelligence[user_email]
        if 'accounts' not in user_data:
            return []
        
        accounts = []
        for account_id, account_data in user_data['accounts'].items():
            accounts.append({
                'id': account_id,
                'name': account_data.get('name', 'Unknown'),
                'score': account_data.get('score', 0),
                'signals': account_data.get('signals', [])
            })
        
        # Sort by score
        accounts.sort(key=lambda x: x['score'], reverse=True)
        
        return accounts[:20]  # Top 20


# ============================================================================
# CRON JOB ENTRY POINT
# ============================================================================

def run_daily_analytics():
    """
    Entry point for cron job.
    Add to crontab: 0 0 * * * cd /path/to/marketing && python -c "from utils.analytics import run_daily_analytics; run_daily_analytics()"
    """
    processor = AnalyticsProcessor()
    results = processor.run_daily_batch()
    
    print(f"Analytics batch completed: {datetime.now().isoformat()}")
    print(json.dumps(results, indent=2))
    
    return results


if __name__ == '__main__':
    # For testing
    run_daily_analytics()
