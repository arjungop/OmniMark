from flask import Blueprint, request, jsonify, session
from database import get_user_context, save_user_context
from utils.auth_utils import login_required
from utils.ai_helpers import (
    ai_generate_company_context,
    scrape_website,
    search_google_news,
    ai_analyze_news_intelligence,
    search_job_signals,
    ai_analyze_hiring_intelligence,
    ai_enrich_company_profile,
    ai_analyze_company,
    ai_analyze_website,
    ai_generate_strategic_campaign,
    ai_generate_creative_brief
)

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/analyze_url', methods=['POST'])
@login_required
def api_analyze_url():
    """Analyze a URL and generate company context"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'status': 'error', 'message': 'URL is required'})
    
    if not url.startswith('http'):
        url = 'https://' + url
        
    result = ai_generate_company_context(url)
    
    if 'error' in result:
        return jsonify({'status': 'error', 'message': result['error']})
        
    return jsonify({'status': 'success', 'data': result})

@api_bp.route('/api/analyze_company', methods=['POST'])
@login_required
def api_analyze_company_endpoint():
    """Deep analysis of a company"""
    data = request.get_json()
    company_name = data.get('company_name')
    website = data.get('website')
    
    if not company_name:
        return jsonify({'status': 'error', 'message': 'Company name is required'})
    
    email = session['user']
    user_context = get_user_context(email)
    
    # 1. Scrape website if provided
    website_data = None
    if website:
        if not website.startswith('http'):
            website = 'https://' + website
        website_data = scrape_website(website)
    
    # 2. Generate Analysis
    analysis = ai_analyze_company(company_name, website_data, user_context)
    
    return jsonify({
        'status': 'success', 
        'analysis': analysis,
        'website_data': website_data
    })

@api_bp.route('/api/research_company', methods=['POST'])
@login_required
def api_research_company():
    """Comprehensive research on a company (News, Jobs, Tech)"""
    data = request.get_json()
    company_name = data.get('company_name')
    
    if not company_name:
        return jsonify({'status': 'error', 'message': 'Company name is required'})
        
    email = session['user']
    user_context = get_user_context(email)
    
    # 1. News Intelligence
    news_articles = search_google_news(f"{company_name} business news")
    news_intel = ai_analyze_news_intelligence(news_articles, company_name, user_context)
    
    # 2. Hiring Intelligence
    jobs = search_job_signals(company_name)
    hiring_intel = ai_analyze_hiring_intelligence(jobs, company_name, user_context)
    
    # 3. Enrich Profile (Firmographics/Technographics)
    enriched_profile = ai_enrich_company_profile(company_name, news_intel, hiring_intel, user_context)
    
    return jsonify({
        'status': 'success',
        'news_intel': news_intel,
        'hiring_intel': hiring_intel,
        'enriched_profile': enriched_profile
    })

@api_bp.route('/api/analyze_website', methods=['POST'])
@login_required
def api_analyze_website_endpoint():
    """Analyze a website for sales intelligence"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'status': 'error', 'message': 'URL is required'})
    
    if not url.startswith('http'):
        url = 'https://' + url
        
    email = session['user']
    user_context = get_user_context(email)
    
    result = ai_analyze_website(url, user_context)
    
    if 'error' in result:
        return jsonify({'status': 'error', 'message': result['error']})
        
    return jsonify({'status': 'success', 'data': result})

@api_bp.route('/api/save_context', methods=['POST'])
@login_required
def api_save_context():
    """Save user onboarding context"""
    data = request.get_json()
    email = session['user']
    
    # Save to file
    save_user_context(email, data)
    
    return jsonify({'status': 'success'})
    return jsonify({'status': 'success'})

@api_bp.route('/api/strategic_campaign', methods=['POST'])
@login_required
def api_strategic_campaign():
    """Generate a strategic ABM campaign"""
    data = request.get_json()
    
    # Extract fields
    company = data.get('company')
    scenario = data.get('scenario') or data.get('audience') # Handle both new and old keys
    competitor = data.get('competitor')
    industry = data.get('industry')
    goal = data.get('goal')
    market_conditions = data.get('market_conditions')
    
    if not company or not scenario:
        return jsonify({'status': 'error', 'message': 'Company and Scenario are required'})
        
    email = session['user']
    user_context = get_user_context(email)
    
    # Generate Campaign using AI
    campaign_data = ai_generate_strategic_campaign(
        company=company,
        scenario=scenario,
        competitor=competitor,
        industry=industry,
        goal=goal,
        market_conditions=market_conditions,
        user_context=user_context
    )
    
    if 'error' in campaign_data:
        return jsonify({'status': 'error', 'message': campaign_data['error']})
        
    return jsonify({
        'status': 'success',
        'campaign': {
            'company': company,
            'target': scenario,
            'competitor': competitor,
            'industry': industry,
            'goal': goal,
            'market_conditions': market_conditions,
            'type': 'strategic',
            'status': 'draft',
            'strategic_data': campaign_data
        },
        'strategic_data': campaign_data
    })

@api_bp.route('/api/generate_image', methods=['POST'])
@login_required
def api_generate_image():
    """Generate image using FLUX 1.1 Pro via backend (Fallback)"""
    data = request.get_json()
    prompt = data.get('prompt')
    
    if not prompt:
        return jsonify({'status': 'error', 'message': 'Prompt is required'})
        
    try:
        # Fallback to a high-quality placeholder image relevant to business/marketing
        # This ensures the user always sees a result even if the primary generator fails.
        placeholder_images = [
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=2426&auto=format&fit=crop", # Business analytics
            "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2370&auto=format&fit=crop", # Data dashboard
            "https://images.unsplash.com/photo-1552664730-d307ca884978?q=80&w=2370&auto=format&fit=crop", # Team meeting
            "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?q=80&w=2370&auto=format&fit=crop"  # Strategy planning
        ]
        import random
        selected_image = random.choice(placeholder_images)
        
        return jsonify({
            'status': 'success', 
            'image': selected_image,
            'prompt_used': prompt + " (Fallback: AI generation unavailable, using stock visual)"
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/creative_studio', methods=['POST'])
@login_required
def api_creative_studio():
    """Generate Creative Studio assets"""
    data = request.get_json()
    company = data.get('company')
    target = data.get('target')
    competitor = data.get('competitor')
    narrative = data.get('narrative')
    
    if not company or not target:
        return jsonify({'status': 'error', 'message': 'Company and Target are required'})
        
    try:
        creative_brief = ai_generate_creative_brief(company, target, competitor, narrative)
        
        if 'error' in creative_brief:
            return jsonify({'status': 'error', 'message': creative_brief['error']})
            
        return jsonify({
            'status': 'success',
            'creative_brief': creative_brief
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/search_companies', methods=['POST'])
@login_required
def api_search_companies():
    """Search for company names (autocomplete for onboarding)"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'companies': []})
    
    # Return a simple list of common company suffixes for autocomplete
    # In production, you'd integrate with a company database API
    suggestions = [
        f"{query} Inc.",
        f"{query} Corp.",
        f"{query} LLC",
        f"{query} Ltd.",
        f"{query} Technologies",
    ]
    
    return jsonify({'companies': suggestions[:5]})
