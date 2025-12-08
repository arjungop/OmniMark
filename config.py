import os

class Config:
    # Flask Config
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'chameleon-2025-unified-app-secret')
    
    # API Keys
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyBr5gXXSCd8aYeL1wcTKIcZ9TrDYbhnkVI')
    GMAIL_USER = os.environ.get('GMAIL_USER', 'arjungopal660@gmail.com')
    GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', 'yvgtkykyzigdhepk')
    HUNTER_API_KEY = os.environ.get('HUNTER_API_KEY', '8d8e63ecb78260f6c44fe70f83890760c3c7e5c6')
    
    # SheetDB Config (if needed, though not explicitly in the original app.py constants, it was used in crm init)
    SHEETDB_API_URL = os.environ.get('SHEETDB_API_URL', 'https://sheetdb.io/api/v1/your_api_id') 

    # Data Files
    USERS_FILE = "users.json"
    DATA_FILE = "chameleon_data.json"
    COMPANIES_FILE = "companies_db.json"
    RELATIONSHIPS_FILE = "relationships_db.json"
    HISTORY_FILE = "history_db.json"
    CAMPAIGNS_DB = "campaigns_db.json"
    CONTEXT_FILE = "company_context.json" # Derived from usage
