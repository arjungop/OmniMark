import unittest
import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import save_user_context, save_users
from config import Config

# Map old names to new locations for compatibility in tests
CONTEXT_FILE = Config.CONTEXT_FILE
USERS_FILE = Config.USERS_FILE
save_user = save_users

class MarketingAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        # Create a dummy context file for testing
        self.test_context = {
            'company_name': 'Test Corp',
            'industry': 'SaaS',
            'description': 'We make testing software.',
            'competitors': 'CompA, CompB',
            'completed_onboarding': True
        }
        # Clean up files
        if os.path.exists(USERS_FILE): os.remove(USERS_FILE)
        if os.path.exists(CONTEXT_FILE): os.remove(CONTEXT_FILE)

    def tearDown(self):
        # Clean up
        if os.path.exists(USERS_FILE): os.remove(USERS_FILE)
        if os.path.exists(CONTEXT_FILE): os.remove(CONTEXT_FILE)
        # Also clean up user-specific context files if any created
        for f in os.listdir('.'):
            if f.endswith(CONTEXT_FILE) and f != CONTEXT_FILE:
                os.remove(f)

    def login(self, email, password):
        return self.app.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def register(self, email, password, name):
        return self.app.post('/register', data=dict(
            email=email,
            password=password,
            name=name
        ), follow_redirects=True)

    def test_auth_flow(self):
        # Register
        response = self.register('test@example.com', 'password', 'Test User')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Let\'s build your intelligence profile', response.data) # Should redirect to onboarding
        
        # Logout
        self.app.get('/logout', follow_redirects=True)
        
        # Login
        response = self.login('test@example.com', 'password')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Let\'s build your intelligence profile', response.data)

    def test_protected_routes(self):
        # Try accessing dashboard without login
        response = self.app.get('/', follow_redirects=True)
        self.assertIn(b'Sign In', response.data) # Should be on login page

    def test_analyze_url(self):
        # Register and login first
        self.register('test@example.com', 'password', 'Test User')
        self.login('test@example.com', 'password')
        
        # Test the analysis endpoint
        # We mock the scraper/ai helper internally or just check validation for now
        response = self.app.post('/api/analyze_url', 
                                 data=json.dumps({'url': ''}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200) # It returns JSON with error status, not 400 status code in the new implementation
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'URL is required')

if __name__ == '__main__':
    unittest.main()
