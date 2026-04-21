# 🎯 The OmniMark - ABM Campaign Intelligence Platform

> **AI-powered Account-Based Marketing platform that adapts to any business like a omnimark adapts to its environment**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-green.svg)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini%202.0-orange.svg)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Problem Statement

B2B marketers face a critical challenge: **creating highly personalized campaigns at scale**. Traditional marketing tools force teams to choose between:
- **Generic mass campaigns** → Low engagement, wasted resources
- **Hyper-personalized outreach** → Time-consuming, doesn't scale

## 💡 Our Solution

**The OmniMark** leverages AI to generate strategic, hyper-personalized ABM campaigns in minutes, not days. Like its namesake, it adapts to each target account's unique characteristics, industry, and pain points.

### Key Features

🧠 **Strategic AI Intelligence**
- Google Gemini 2.0 Flash for deep business analysis
- Account research and pain point identification
- Multi-channel campaign orchestration

🎨 **Visual Content Generation**
- AI-generated campaign visuals via FLUX 1.1 Pro
- Industry-specific imagery
- Brand-aligned designs

📧 **Full Campaign Stack**
- Email sequence generation
- LinkedIn messaging templates
- Retargeting ad copy
- Landing page suggestions

📊 **Campaign Management**
- Save and organize campaigns
- Track generated content
- Export to marketing platforms

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│                  (Flask + Jinja2 Templates)                     │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│    │  Dashboard  │  │  Campaign   │  │  Settings   │           │
│    │   Studio    │  │   Manager   │  │   Panel     │           │
│    └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK API LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   /api/      │  │   /api/      │  │   /api/      │          │
│  │  strategic   │  │   email      │  │   save       │          │
│  │  campaign    │  │   sender     │  │  campaign    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI GENERATION ENGINE                         │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │   Google Gemini      │  │   FLUX 1.1 Pro       │            │
│  │   2.0 Flash          │  │   (Puter.js)         │            │
│  │                      │  │                      │            │
│  │  • Strategy Gen      │  │  • Hero Images       │            │
│  │  • Email Copy        │  │  • Ad Creatives      │            │
│  │  • LinkedIn Posts    │  │  • Social Graphics   │            │
│  │  • Pain Points       │  │                      │            │
│  └──────────────────────┘  └──────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  campaigns   │  │   users      │  │   rate       │          │
│  │  _db.json    │  │   .json      │  │   limits     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Google Gemini API key (free tier available)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/omnimark-abm.git
cd omnimark-abm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your-gemini-api-key"
export FLASK_SECRET_KEY="your-secret-key"

# Run the application
python app_hackathon.py
```

The app will be available at `http://localhost:5001`

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `FLASK_SECRET_KEY` | Recommended | Flask session secret |
| `OPENROUTER_API_KEY` | Optional | Backup AI provider |
| `GMAIL_USER` | Optional | Email sender address |
| `GMAIL_APP_PASSWORD` | Optional | Gmail app password |

## 📸 Screenshots

### Dashboard
*Strategic campaign generation interface with AI-powered recommendations*

### Campaign Generator
*Multi-channel content generation with real-time preview*

### Saved Campaigns
*Campaign management with load, edit, and delete functionality*

## 🎥 Demo Video

[Watch The OmniMark in Action](link-to-demo-video)

## 🔧 Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | Flask 3.1 | Web framework & API |
| AI Text | Google Gemini 2.0 Flash | Strategic content generation |
| AI Images | FLUX 1.1 Pro via Puter.js | Visual content generation |
| Security | bcrypt | Password hashing |
| Frontend | HTML5/CSS3/JavaScript | User interface |
| Data | JSON files | Campaign & user storage |

## 🛡️ Security Features

- **bcrypt password hashing** with secure salting
- **Input sanitization** to prevent XSS attacks
- **Rate limiting** (20 campaigns/hr, 10 emails/hr)
- **Environment variable** based configuration
- **Automatic temp file cleanup** on shutdown

## 🔮 Future Roadmap

- [ ] SQLite/PostgreSQL migration for scalability
- [ ] CRM integrations (Salesforce, HubSpot)
- [ ] Campaign performance analytics
- [ ] Team collaboration features
- [ ] A/B testing for generated content
- [ ] Advanced personalization with company data enrichment

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

Built with ❤️ for the Linkenite Hackathon

---

**The OmniMark** - *Adapt. Personalize. Convert.* 🎯
