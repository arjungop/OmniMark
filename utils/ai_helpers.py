import requests
import re
import json
from bs4 import BeautifulSoup
import google.generativeai as genai
from config import Config

# Configure Gemini
genai.configure(api_key=Config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Try to import tldextract
try:
    import tldextract
    TLDEXTRACT_AVAILABLE = True
except ImportError:
    TLDEXTRACT_AVAILABLE = False

def scrape_website(url):
    """Extract real data from a website"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text content
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        text = soup.get_text(separator=' ', strip=True)[:5000]
        
        # Extract emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = list(set(re.findall(email_pattern, response.text)))
        
        # Extract tech stack indicators
        tech_indicators = []
        html_lower = response.text.lower()
        
        tech_checks = {
            'React': ['react', 'reactdom'],
            'Vue.js': ['vue.js', 'vuejs'],
            'Angular': ['angular'],
            'Next.js': ['next.js', '_next'],
            'WordPress': ['wp-content', 'wordpress'],
            'Shopify': ['shopify', 'cdn.shopify'],
            'HubSpot': ['hubspot', 'hs-scripts'],
            'Salesforce': ['salesforce', 'pardot'],
            'Google Analytics': ['google-analytics', 'gtag', 'ga.js'],
            'Stripe': ['stripe.com', 'stripe.js'],
            'Intercom': ['intercom', 'intercomcdn'],
            'Zendesk': ['zendesk'],
            'Segment': ['segment.com', 'analytics.js'],
            'Cloudflare': ['cloudflare'],
            'AWS': ['amazonaws.com'],
            'Tailwind CSS': ['tailwind'],
            'Bootstrap': ['bootstrap'],
        }
        
        for tech, patterns in tech_checks.items():
            if any(p in html_lower for p in patterns):
                tech_indicators.append(tech)
        
        # Get domain info
        if TLDEXTRACT_AVAILABLE:
            ext = tldextract.extract(url)
            domain = f"{ext.domain}.{ext.suffix}"
        else:
            # Fallback to basic domain extraction
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
        
        return {
            'url': url,
            'domain': domain,
            'text_content': text,
            'emails': emails[:10],
            'tech_stack': tech_indicators,
            'title': soup.title.string if soup.title else domain
        }
    except Exception as e:
        return {'error': str(e), 'url': url}

def search_google_news(query, num_results=10):
    """Search for real news using Google News RSS"""
    try:
        search_url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'xml')
        
        articles = []
        items = soup.find_all('item')[:num_results]
        
        for item in items:
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            source = item.find('source')
            
            articles.append({
                'title': title.text if title else 'No title',
                'link': link.text if link else '#',
                'date': pub_date.text if pub_date else '',
                'source': source.text if source else 'Unknown',
                'snippet': ''
            })
        
        return articles
    except Exception as e:
        return [{'error': str(e)}]

def ai_analyze_news_intelligence(articles, company_name, user_context=None):
    """Transform raw news into actionable intelligence with sentiment, trends, and alerts"""
    if not articles or all('error' in a for a in articles):
        return {'error': 'No articles to analyze'}
    
    try:
        # Prepare news summaries for AI
        news_text = "\n".join([f"- {a.get('title', '')} ({a.get('source', '')}, {a.get('date', '')})" 
                               for a in articles if 'error' not in a][:15])
        
        context_info = ""
        if user_context:
            context_info = f"""
YOUR COMPANY: {user_context.get('company_name', 'Unknown')}
YOU SELL: {user_context.get('description', 'Unknown')}
YOUR COMPETITORS: {user_context.get('competitors', 'Unknown')}
"""
        
        prompt = f"""You are a strategic intelligence analyst. Analyze these news articles about {company_name} and provide ACTIONABLE sales intelligence.

NEWS ARTICLES:
{news_text}

{context_info}

Provide analysis in this EXACT JSON format (return ONLY valid JSON):
{{
    "sentiment_score": <number from -100 to 100, negative=bad news, positive=good news>,
    "sentiment_label": "<Bearish/Neutral/Bullish>",
    "momentum": "<Declining/Stable/Growing/Accelerating>",
    "key_events": [
        {{
            "event": "<what happened>",
            "impact": "<High/Medium/Low>",
            "sales_angle": "<how to use this in outreach>"
        }}
    ],
    "signals": [
        {{
            "type": "<Expansion/Contraction/Leadership Change/Product Launch/Funding/Partnership/Crisis>",
            "description": "<brief description>",
            "action": "<specific action to take>"
        }}
    ],
    "buying_triggers": ["<specific reasons they might buy NOW based on news>"],
    "risk_flags": ["<reasons to be cautious>"],
    "recommended_timing": "<Now - Hot Lead/This Week/This Month/Wait - Bad Timing>",
    "outreach_hook": "<a specific opening line referencing recent news>",
    "summary": "<2-3 sentence executive summary>"
}}

Return ONLY valid JSON, no markdown."""

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean JSON
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            'sentiment_score': 0,
            'sentiment_label': 'Neutral',
            'summary': 'Unable to analyze news sentiment',
            'signals': [],
            'key_events': []
        }
    except Exception as e:
        return {'error': str(e)}

def search_job_signals(company_name):
    """Search for hiring signals from multiple sources"""
    try:
        jobs = []
        
        # Try LinkedIn via Google
        query = f"{company_name} jobs hiring site:linkedin.com/jobs"
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for g in soup.find_all('div', class_='g')[:10]:
            title_elem = g.find('h3')
            link_elem = g.find('a')
            snippet_elem = g.find('div', class_='VwiC3b')
            
            if title_elem and link_elem:
                jobs.append({
                    'title': title_elem.text,
                    'link': link_elem.get('href', '#'),
                    'snippet': snippet_elem.text if snippet_elem else '',
                    'company': company_name
                })
        
        return jobs if jobs else [{'title': 'Check LinkedIn directly', 'link': f'https://www.linkedin.com/jobs/search/?keywords={company_name}', 'company': company_name}]
    except Exception as e:
        return [{'error': str(e)}]

def ai_analyze_hiring_intelligence(jobs, company_name, user_context=None):
    """Transform raw job listings into strategic hiring intelligence"""
    if not jobs or all('error' in j for j in jobs):
        return {'error': 'No jobs to analyze'}
    
    try:
        # Prepare jobs for analysis
        jobs_text = "\n".join([f"- {j.get('title', '')}" for j in jobs if 'error' not in j][:20])
        
        context_info = ""
        if user_context:
            context_info = f"""
YOUR COMPANY: {user_context.get('company_name', 'Unknown')}
YOU SELL: {user_context.get('description', 'Unknown')}
TARGET ROLES: {user_context.get('target_roles', 'Unknown')}
"""
        
        prompt = f"""You are a strategic hiring analyst. Analyze these job postings from {company_name} and provide ACTIONABLE intelligence about their growth strategy.

JOB POSTINGS:
{jobs_text}

{context_info}

Provide analysis in this EXACT JSON format (return ONLY valid JSON):
{{
    "hiring_velocity": "<Aggressive/Moderate/Slow/Freezing>",
    "growth_stage": "<Early Stage/Growth Mode/Scale Up/Mature/Restructuring>",
    "strategic_priorities": [
        {{
            "priority": "<what they're investing in>",
            "evidence": "<job titles that prove this>",
            "implication": "<what this means for you as a seller>"
        }}
    ],
    "department_breakdown": {{
        "engineering": {{
            "count": <number>,
            "signal": "<Building new product/Scaling infrastructure/Maintenance mode>"
        }},
        "sales": {{
            "count": <number>,
            "signal": "<Expansion mode/New market entry/Account management focus>"
        }},
        "marketing": {{
            "count": <number>,
            "signal": "<Brand building/Demand gen push/Content focus>"
        }},
        "operations": {{
            "count": <number>,
            "signal": "<Scaling ops/Cost optimization/Process improvement>"
        }},
        "leadership": {{
            "count": <number>,
            "signal": "<Building leadership team/Restructuring/Stable>"
        }}
    }},
    "key_hires": [
        {{
            "role": "<important role they're hiring>",
            "why_matters": "<why this is significant>",
            "your_angle": "<how to leverage this in sales>"
        }}
    ],
    "org_insights": [
        "<inference about their org structure or culture>"
    ],
    "pain_indicators": [
        "<problems they likely have based on what they're hiring for>"
    ],
    "best_time_to_sell": "<Now/After key hire/Wait 3 months/etc>",
    "recommended_contacts": [
        {{
            "title": "<job title to reach out to>",
            "reason": "<why they'd care about your solution>",
            "timing": "<when to reach out>"
        }}
    ],
    "competitive_insight": "<what their hiring tells you about competitive positioning>",
    "summary": "<3-4 sentence executive summary of hiring strategy>"
}}

Return ONLY valid JSON, no markdown."""

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean JSON
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            'hiring_velocity': 'Unknown',
            'growth_stage': 'Unknown', 
            'summary': 'Unable to analyze hiring patterns',
            'strategic_priorities': [],
            'key_hires': []
        }
    except Exception as e:
        return {'error': str(e)}


def ai_enrich_company_profile(company_name, news_intel, hiring_intel, user_context=None):
    """Use AI to extract structured firmographic/technographic data from research"""
    try:
        news_summary = news_intel.get('summary', '') if news_intel else ''
        hiring_summary = hiring_intel.get('summary', '') if hiring_intel else ''
        hiring_velocity = hiring_intel.get('hiring_velocity', '') if hiring_intel else ''
        growth_stage = hiring_intel.get('growth_stage', '') if hiring_intel else ''
        
        prompt = f"""Based on this research about {company_name}, extract structured company profile data.

NEWS INTELLIGENCE:
{news_summary}

HIRING INTELLIGENCE:
{hiring_summary}
Hiring Velocity: {hiring_velocity}
Growth Stage: {growth_stage}

Extract and return this JSON structure with your best estimates. Use null if unknown:
{{
    "firmographics": {{
        "industry": "<primary industry>",
        "sub_industry": "<specific sub-industry>",
        "employee_range": "<1-10/11-50/51-200/201-500/501-1000/1000+>",
        "revenue_range": "<$0-1M/$1-10M/$10-50M/$50-100M/$100M+>",
        "company_type": "<Private/Public/Subsidiary>",
        "funding_stage": "<Bootstrapped/Seed/Series A/Series B/Series C+/Public>",
        "headquarters": {{
            "city": "<city or null>",
            "country": "<country>"
        }}
    }},
    "technographics": {{
        "tech_sophistication_score": <1-10 based on hiring patterns and industry>,
        "likely_tech_stack": ["<technologies they probably use>"],
        "cloud_provider": ["<AWS/GCP/Azure based on job posts>"]
    }},
    "intent_signals": {{
        "score": <0-100 buying intent score>,
        "buying_stage": "<Unaware/Aware/Considering/Evaluating/Deciding>",
        "signals": [
            {{"signal": "<what indicates intent>", "strength": "<high/medium/low>"}}
        ],
        "pain_indicators": ["<likely pain points based on research>"]
    }},
    "competitive_intel": {{
        "likely_current_solutions": ["<what they might be using now>"],
        "switching_likelihood": <1-10>
    }}
}}

Return ONLY valid JSON."""

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
    except:
        return None


def ai_analyze_company(company_name, website_data=None, user_context=None):
    """Use Gemini to generate deep company analysis"""
    try:
        context_info = ""
        if user_context:
            context_info = f"""
YOUR COMPANY CONTEXT (use this to personalize the analysis):
- Your Company: {user_context.get('company_name', 'Unknown')}
- Industry: {user_context.get('industry', 'Unknown')}
- What you sell: {user_context.get('description', 'Unknown')}
- Target roles: {user_context.get('target_roles', 'Unknown')}
- Pain points you solve: {user_context.get('pain_points', 'Unknown')}
- Your competitors: {user_context.get('competitors', 'Unknown')}
- Your unique value: {user_context.get('unique_value', 'Unknown')}
"""
        
        website_info = ""
        if website_data and 'text_content' in website_data:
            website_info = f"""
WEBSITE DATA:
{website_data.get('text_content', '')[:3000]}

Tech Stack Detected: {', '.join(website_data.get('tech_stack', []))}
"""
        
        prompt = f"""You are a B2B sales intelligence analyst. Analyze this target company and provide actionable insights.

TARGET COMPANY: {company_name}

{context_info}

{website_info}

Provide a comprehensive analysis in this EXACT format:

## 🎯 Company Overview
Brief description of what {company_name} does

## 💡 Why They'd Buy From You
Based on their business and your offering, explain specific reasons they would be a good prospect

## 🔥 Pain Points You Can Address
List 3-5 specific pain points they likely have that your solution solves

## 👤 Key Decision Makers to Target
- List specific job titles to reach out to
- Explain why each would care about your solution

## 📧 Personalized Outreach Angle
A specific angle or hook to use when reaching out to this company

## ⚠️ Potential Objections
List 2-3 objections they might have and how to handle them

## 📊 Fit Score: X/10
Rate how well this prospect fits your ICP and explain why

Be specific, actionable, and reference actual details where possible."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

def ai_analyze_website(url, user_context=None):
    """Analyze a website for sales intelligence"""
    website_data = scrape_website(url)
    
    if 'error' in website_data:
        return {'error': website_data['error']}
    
    try:
        context_info = ""
        if user_context:
            context_info = f"""
YOUR COMPANY sells: {user_context.get('description', 'Unknown')}
You target: {user_context.get('target_roles', 'Unknown')}
"""
        
        prompt = f"""Analyze this website for B2B sales intelligence.

URL: {url}
WEBSITE CONTENT:
{website_data.get('text_content', '')[:4000]}

TECH STACK DETECTED: {', '.join(website_data.get('tech_stack', []))}

{context_info}

Provide analysis in this format:

## 🏢 What This Company Does
Brief description based on their website

## 💰 Business Model
How they make money (B2B, B2C, SaaS, etc.)

## 🎯 Their Target Market
Who they sell to

## 🔧 Technology Insights
What their tech stack tells us about them (budget, sophistication, growth stage)

## 📈 Growth Signals
Any indicators of growth, funding, or expansion

## 🤝 Sales Opportunity
How to approach this company based on the website analysis

Be specific and actionable."""

        response = model.generate_content(prompt)
        
        return {
            'analysis': response.text,
            'emails': website_data.get('emails', []),
            'tech_stack': website_data.get('tech_stack', []),
            'title': website_data.get('title', url)
        }
    except Exception as e:
        return {'error': str(e), 'emails': website_data.get('emails', []), 'tech_stack': website_data.get('tech_stack', [])}

def ai_generate_company_context(url):
    """Auto-generate company context from website URL"""
    website_data = scrape_website(url)
    
    if 'error' in website_data:
        return {'error': website_data['error']}
    
    try:
        prompt = f"""Based on this website, generate a company profile for a B2B marketing tool.

WEBSITE: {url}
CONTENT: {website_data.get('text_content', '')[:4000]}

Analyze this company and extract key information. Be ACCURATE with industry classification.

Industry examples:
- Sports/Athletic (Nike, Adidas, Under Armour)
- Technology/SaaS (Salesforce, HubSpot, Slack)
- E-commerce (Shopify, Amazon, eBay)
- Finance (PayPal, Stripe, banks)
- Healthcare (hospitals, medical devices, pharma)
- Manufacturing (factories, production)
- Retail (stores, consumer goods)
- Professional Services (consulting, agencies)

Return a JSON object with these exact fields:
{{
    "company_name": "The company name",
    "industry": "Primary industry (be specific - e.g., 'Sports & Athletic Apparel' not just 'Retail')",
    "description": "A 2-3 sentence elevator pitch of what they do",
    "target_roles": ["Job title 1", "Job title 2"],
    "pain_points": ["Pain point 1", "Pain point 2"],
    "competitors": ["Competitor 1", "Competitor 2"],
    "unique_value": "Their unique value proposition"
}}

Return ONLY valid JSON, no markdown or extra text."""

        response = model.generate_content(prompt)
        
        # Clean up response and parse JSON
        text = response.text.strip()
        # Remove markdown code blocks if present
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
    except json.JSONDecodeError:
        # Return a basic structure if JSON parsing fails
        return {
            'company_name': website_data.get('title', 'Unknown'),
            'industry': 'Unknown',
            'description': 'Please fill in your company description',
            'target_roles': [],
            'pain_points': [],
            'competitors': [],
            'unique_value': 'Please fill in your unique value'
        }
    except Exception as e:
        return {'error': str(e)}

def ai_generate_strategic_campaign(company, scenario, competitor, industry, goal, market_conditions, user_context=None):
    """Generate a comprehensive strategic ABM campaign based on a scenario"""
    try:
        context_info = ""
        if user_context:
            context_info = f"""
YOUR CONTEXT:
- You are: {user_context.get('company_name', company)}
- You sell: {user_context.get('description', 'Unknown')}
- Your Value: {user_context.get('unique_value', 'Unknown')}
"""

        prompt = f"""You are a Machiavellian ABM Strategist. Your style is:
- LOGICAL: Every claim must be backed by reasoning.
- CUNNING: Find the competitor's hidden weakness and exploit it ruthlessly.
- SHARP: concise, punchy, no fluff.
- FACTUAL: Do not patronize. Use objective business language.
- PERFECT: Zero hallucinations, precise strategy.

CAMPAIGN PARAMETERS:
- YOUR COMPANY: {company}
- TARGET SCENARIO: {scenario}
- COMPETITOR TO BEAT: {competitor}
- INDUSTRY: {industry}
- GOAL: {goal}
- MARKET CONTEXT: {market_conditions}

{context_info}

TASK:
Design a masterclass ABM campaign to achieve the TARGET SCENARIO.
Refer to YOUR COMPANY as "{company}" (not "Us" or "We").
Refer to the competitor as "{competitor}".

If the scenario is "Convince X to switch from Y to Z", focus entirely on the *cost of inaction* and the *specific advantage* of {company}.

Provide the output in this EXACT JSON format:

{{
    "strategy": {{
        "market_analysis": {{
            "industry_overview": "Brief overview of the industry landscape",
            "market_size": "Estimated market size",
            "growth_trends": ["Trend 1", "Trend 2"],
            "timing_rationale": "Why now is the right time"
        }},
        "audience_strategy": {{
            "icp": {{
                "company_size": "Target company size",
                "revenue": "Target revenue range",
                "industry_verticals": ["Vertical 1", "Vertical 2"]
            }},
            "buyer_personas": [
                {{
                    "title": "Decision Maker Title",
                    "pain_points": ["Pain 1", "Pain 2"],
                    "goals": ["Goal 1", "Goal 2"]
                }}
            ]
        }},
        "positioning": {{
            "value_proposition": "Core value prop",
            "tagline": "Catchy tagline",
            "elevator_pitch": "30-second pitch",
            "differentiation": ["Diff 1", "Diff 2"]
        }},
        "content_strategy": {{
            "tone": "Brand tone",
            "themes": ["Theme 1", "Theme 2"],
            "key_messages": ["Msg 1", "Msg 2"]
        }},
        "metrics": {{
            "primary_kpis": ["KPI 1", "KPI 2"],
            "success_benchmarks": {{
                "open_rate": "20%",
                "conversion_rate": "5%"
            }}
        }}
    }},
    "competitive_intel": {{
        "positioning_analysis": {{
            "competitor_position": "How they position themselves",
            "their_strengths": ["Strength 1", "Strength 2"],
            "their_weaknesses": ["Weakness 1", "Weakness 2"]
        }},
        "feature_comparison": [
            {{
                "feature": "Feature Name",
                "our_capability": "Specific detail about {company}'s capability (Do NOT repeat feature name)",
                "competitor_capability": "Specific detail about {competitor}'s capability",
                "winner": "{company} or {competitor}"
            }}
        ],
        "customer_sentiment": {{
            "what_customers_love_about_competitor": ["Love 1", "Love 2"],
            "what_customers_hate_about_competitor": ["Hate 1", "Hate 2"],
            "switching_triggers": ["Trigger 1", "Trigger 2"]
        }},
        "vulnerabilities": ["Vuln 1", "Vuln 2"],
        "battle_plan": {{
            "attack_vectors": ["Vector 1", "Vector 2"],
            "win_themes": ["Theme 1", "Theme 2"]
        }}
    }},
    "narrative_arc": {{
        "act1_problem": {{
            "hook": "Opening hook",
            "problem_statement": "The core problem",
            "stakes": "What's at stake"
        }},
        "act2_journey": {{
            "exploration": "Exploring the issue",
            "urgency_driver": "Why act now"
        }},
        "act3_transformation": {{
            "solution_reveal": "How we solve it"
        }},
        "act4_cta": {{
            "call_to_action": "The ask"
        }}
    }},
    "campaign_sequence": [
        {{
            "name": "Touch 1",
            "channel": "Email",
            "timing": "Day 1",
            "subject": "Subject line",
            "message": "Email body content"
        }},
        {{
            "name": "Touch 2",
            "channel": "LinkedIn",
            "timing": "Day 3",
            "message": "LinkedIn message content"
        }}
    ],
    "content_variants": {{
        "c_suite": {{
            "key_message": "Strategic ROI message",
            "language_style": "Concise, data-driven",
            "pain_points": ["Risk", "Bottom line"],
            "cta": "Book Strategy Session",
            "sample_email": {{
                "subject": "Strategic Subject Line",
                "body": "Email body text..."
            }}
        }},
        "vp_director": {{
            "key_message": "Operational efficiency message",
            "language_style": "Professional, solution-oriented",
            "pain_points": ["Efficiency", "Team performance"],
            "cta": "View Demo",
            "sample_email": {{
                "subject": "Operational Subject Line",
                "body": "Email body text..."
            }}
        }},
        "manager_ic": {{
            "key_message": "Ease of use message",
            "language_style": "Friendly, tactical",
            "pain_points": ["Time saving", "Features"],
            "cta": "Start Free Trial",
            "sample_email": {{
                "subject": "Tactical Subject Line",
                "body": "Email body text..."
            }}
        }}
    }},
    "performance_predictions": {{
        "email_metrics": {{
            "predicted_open_rate": "45%",
            "predicted_reply_rate": "12%",
            "predicted_click_rate": "8%"
        }},
        "conversion_metrics": {{
            "predicted_meeting_rate": "5%",
            "predicted_close_rate": "20%",
            "time_to_conversion": "3 months"
        }}
    }},
    "campaign_analysis": {{
        "overall_score": 85,
        "strategic_soundness": {{ "score": 90, "critique": "Strong alignment with goals" }},
        "audience_targeting": {{ "score": 85, "critique": "Well defined ICP" }},
        "competitive_positioning": {{ "score": 80, "critique": "Good differentiation" }},
        "content_strategy": {{ "score": 88, "critique": "Compelling narrative" }},
        "conversion_architecture": {{ "score": 82, "critique": "Clear CTAs" }},
        "metrics_attribution": {{ "score": 85, "critique": "Solid KPI selection" }},
        "red_flags": ["Potential risk 1", "Potential risk 2"],
        "optimization_recommendations": ["Recommendation 1", "Recommendation 2"]
    }}
}}

Return ONLY valid JSON."""

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text, strict=False)
    except Exception as e:
        return {'error': str(e)}

def ai_generate_creative_brief(company, target, competitor, narrative):
    """Generate a creative brief for the campaign"""
    try:
        prompt = f"""You are a Visionary Creative Director.
        
CAMPAIGN CONTEXT:
- COMPANY: {company}
- TARGET: {target}
- COMPETITOR: {competitor}
- NARRATIVE: {narrative}

TASK:
Develop a high-impact creative concept for this campaign.
Focus on visual storytelling, brand aesthetics, and platform-specific adaptations.

Provide the output in this EXACT JSON format:

{{
    "creative_concept": {{
        "headline": "Punchy Campaign Headline (5-7 words)",
        "tagline": "Supporting tagline or subheader",
        "visual_metaphor": "The key visual metaphor/concept",
        "color_palette": ["#1E40AF", "#10B981", "#F59E0B"]
    }},
    "platform_adaptations": {{
        "instagram": {{
            "format": "Carousel / Reel / Story",
            "hook": "The hook that stops the scroll"
        }},
        "linkedin": {{
            "format": "Document / Carousel / Video",
            "hook": "Professional angle/hook"
        }},
        "twitter": {{
            "format": "Thread / Single Tweet",
            "hook": "Controversial or thought-provoking hook"
        }},
        "youtube": {{
            "format": "Pre-roll / Mid-roll",
            "hook": "Skip-proof hook"
        }}
    }},
    "brand_moodboard": {{
        "photography_style": "Description of photography style",
        "typography_style": "Typography approach",
        "design_principles": ["Principle 1", "Principle 2", "Principle 3"]
    }}
}}

Return ONLY valid JSON."""

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text, strict=False)
    except Exception as e:
        return {'error': str(e)}
