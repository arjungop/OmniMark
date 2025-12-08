document.addEventListener('DOMContentLoaded', () => {
    // =========================================================================
    // TOAST NOTIFICATION SYSTEM
    // =========================================================================
    
    window.showToast = function(message, type = 'info', title = '', duration = 5000) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        const titles = {
            success: title || 'Success',
            error: title || 'Error',
            warning: title || 'Warning',
            info: title || 'Info'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${icons[type]}</div>
            <div class="toast-content">
                <div class="toast-title">${titles[type]}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        container.appendChild(toast);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.add('toast-exit');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
    };
    
    // Helper for sync manager errors
    window.showSyncError = function(errorCategory, errorMessage, retryDelay = 5) {
        const categoryMessages = {
            'network': `Network Error: ${errorMessage}`,
            'auth': `Authentication Failed: ${errorMessage}`,
            'validation': `Validation Error: ${errorMessage}`,
            'rate_limit': `Rate Limit Exceeded: Retrying in ${retryDelay}s...`,
            'data_conflict': `Data Conflict: ${errorMessage}`,
            'compliance': `Compliance Violation: ${errorMessage}`,
            'system': `System Error: ${errorMessage}`
        };
        
        const message = categoryMessages[errorCategory] || `Sync Error: ${errorMessage}`;
        const shouldRetry = ['network', 'rate_limit'].includes(errorCategory);
        
        showToast(
            shouldRetry ? `${message}\nRetrying in ${retryDelay} seconds...` : message,
            shouldRetry ? 'warning' : 'error',
            'SalesLink Sync',
            shouldRetry ? retryDelay * 1000 : 8000
        );
    };
    
    // Helper for sync success
    window.showSyncSuccess = function(stats) {
        const message = `
            Successfully synced ${stats.records_succeeded} contacts
            ${stats.records_failed > 0 ? `\n${stats.records_failed} failed (see audit log)` : ''}
        `.trim();
        
        showToast(message, 'success', 'SalesLink Sync Complete', 6000);
    };
    
    // Helper for compliance blocks
    window.showComplianceBlock = function(count, reason) {
        showToast(
            `${count} contact${count !== 1 ? 's' : ''} blocked: ${reason}\nCheck audit log for details.`,
            'warning',
            'Compliance Check',
            8000
        );
    };
    
    // Onboarding Logic
    const onboardingForm = document.getElementById('onboardingForm');
    if (onboardingForm) {
        // Analyze URL button
        window.analyzeAndNext = async () => {
            const urlInput = document.getElementById('companyUrl');
            const companyNameInput = document.querySelector('input[name="company_name"]');
            const loadingDiv = document.getElementById('loadingAnalysis');
            const analyzeBtn = document.getElementById('analyzeBtn');
            
            const url = urlInput?.value?.trim();
            const companyName = companyNameInput?.value?.trim();
            
            if (!companyName) {
                companyNameInput.style.borderColor = 'var(--error)';
                return;
            }
            
            // Helper to set default values if fields are empty
            const setDefaults = () => {
                const industryField = document.querySelector('input[name="industry"]');
                const descField = document.querySelector('textarea[name="description"]');
                const rolesField = document.querySelector('input[name="target_roles"]');
                const painField = document.querySelector('textarea[name="pain_points"]');
                const compField = document.querySelector('input[name="competitors"]');
                const valueField = document.querySelector('textarea[name="unique_value"]');
                
                if (!industryField.value) industryField.value = 'Technology';
                if (!descField.value) descField.value = `${companyName} helps businesses achieve their goals.`;
                if (!rolesField.value) rolesField.value = 'VP of Sales, Marketing Director, CEO';
                if (!painField.value) painField.value = '• Inefficient processes\n• Lack of visibility\n• Manual work that could be automated';
                if (!compField.value) compField.value = 'Competitor 1, Competitor 2, Competitor 3';
                if (!valueField.value) valueField.value = `${companyName} provides a unique solution that saves time and increases revenue.`;
            };
            
            if (!url) {
                // Skip URL analysis, go to next step with defaults
                setDefaults();
                nextStep(1);
                return;
            }
            
            // Show loading
            loadingDiv?.classList.remove('hidden');
            analyzeBtn.disabled = true;
            analyzeBtn.innerText = 'Analyzing...';
            
            try {
                const response = await fetch('/api/analyze_url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                
                const result = await response.json();
                
                if (result.status === 'success' && result.data) {
                    // Fill in the form fields
                    const d = result.data;
                    document.querySelector('input[name="company_name"]').value = d.company_name || companyName;
                    document.querySelector('input[name="industry"]').value = d.industry || '';
                    document.querySelector('textarea[name="description"]').value = d.description || '';
                    document.querySelector('input[name="target_roles"]').value = d.target_roles || '';
                    document.querySelector('textarea[name="pain_points"]').value = d.pain_points || '';
                    document.querySelector('input[name="competitors"]').value = d.competitors || '';
                    document.querySelector('textarea[name="unique_value"]').value = d.unique_value || '';
                }
                
                // Move to next step
                setDefaults(); // Fill any remaining empty fields
                nextStep(1);
            } catch (error) {
                console.error('Error analyzing URL:', error);
                setDefaults(); // Fill defaults on error
                nextStep(1); // Still proceed
            } finally {
                loadingDiv?.classList.add('hidden');
                analyzeBtn.disabled = false;
                analyzeBtn.innerText = 'Generate Strategy 🪄';
            }
        };
        
        window.nextStep = (currentStep) => {
            const currentDiv = document.getElementById(`step${currentStep}`);
            const nextDiv = document.getElementById(`step${currentStep + 1}`);
            const inputs = currentDiv.querySelectorAll('input[required], textarea[required]');

            // Basic validation
            let valid = true;
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    valid = false;
                    input.style.borderColor = 'var(--error)';
                } else {
                    input.style.borderColor = 'var(--glass-border)';
                }
            });

            if (!valid) return;

            // Animate out
            currentDiv.classList.add('hidden');
            nextDiv.classList.remove('hidden');
            nextDiv.classList.add('animate-fade-in');

            // Update progress
            updateProgress(currentStep + 1);
        };

        window.prevStep = (currentStep) => {
            const currentDiv = document.getElementById(`step${currentStep}`);
            const prevDiv = document.getElementById(`step${currentStep - 1}`);

            currentDiv.classList.add('hidden');
            prevDiv.classList.remove('hidden');
            prevDiv.classList.add('animate-fade-in');

            updateProgress(currentStep - 1);
        };

        window.submitOnboarding = async () => {
            const formData = new FormData(onboardingForm);
            const data = Object.fromEntries(formData.entries());
            data.step = 3; // Final step

            try {
                const response = await fetch('/api/save_context', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    window.location.href = '/';
                }
            } catch (error) {
                console.error('Error saving context:', error);
            }
        };

        function updateProgress(step) {
            const progressFill = document.getElementById('progressFill');
            const steps = document.querySelectorAll('.step');

            // Update bar
            const percent = ((step - 1) / 2) * 100;
            progressFill.style.width = `${percent}%`;

            // Update circles
            steps.forEach(s => {
                const sNum = parseInt(s.dataset.step);
                if (sNum <= step) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active');
                }
            });
        }
    }

    // Dashboard Logic - Research with input prompts
    let currentResearchType = null;
    
    window.startResearch = async (type, target = '') => {
        const resultsArea = document.getElementById('resultsArea');
        const loadingState = document.getElementById('loadingState');
        const resultsContent = document.getElementById('resultsContent');
        const resultsTitle = document.getElementById('resultsTitle');

        resultsArea.classList.remove('hidden');
        loadingState.classList.remove('hidden');
        resultsContent.innerHTML = '';
        
        const titles = {
            'account': '🏢 Account Research',
            'website': '🌐 Website Analysis',
            'news': '📰 Industry News',
            'jobs': '💼 Hiring Signals'
        };
        resultsTitle.innerText = titles[type] || 'Research';
        currentResearchType = type;

        try {
            const response = await fetch('/api/research', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: type, target: target })
            });

            const data = await response.json();
            loadingState.classList.add('hidden');

            if (data.need_input) {
                // Show input form
                renderInputForm(data, resultsContent);
            } else if (data.status === 'success') {
                renderResults(type, data.data, resultsContent);
            } else {
                resultsContent.innerHTML = `<p style="color: var(--error)">Error: ${data.message}</p>`;
            }
        } catch (error) {
            loadingState.classList.add('hidden');
            resultsContent.innerHTML = `<p style="color: var(--error)">Error: ${error.message}</p>`;
        }
    };
    
    function renderInputForm(data, container) {
        const html = `
            <div class="input-prompt">
                <p style="margin-bottom: 1rem;">${data.message}</p>
                <div class="form-group">
                    <label>${data.input_label}</label>
                    <input type="${data.input_type}" id="researchInput" placeholder="${data.input_placeholder}" 
                           style="font-size: 1.1rem; padding: 1rem;">
                </div>
                <button class="btn btn-primary" onclick="submitResearchInput()" style="margin-top: 1rem;">
                    Research Now →
                </button>
            </div>
        `;
        container.innerHTML = html;
        
        // Focus input and add enter key handler
        setTimeout(() => {
            const input = document.getElementById('researchInput');
            input?.focus();
            input?.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') submitResearchInput();
            });
        }, 100);
    }
    
    window.submitResearchInput = () => {
        const input = document.getElementById('researchInput');
        const value = input?.value?.trim();
        if (value && currentResearchType) {
            startResearch(currentResearchType, value);
        }
    };

    function renderResults(type, data, container) {
        let html = '';

        if (type === 'news') {
            // Render news intelligence
            const intel = data.industry_intelligence || {};
            
            // Industry Overview
            html += `<div class="glass-panel" style="margin-bottom: 1.5rem; background: linear-gradient(135deg, rgba(100,50,255,0.1), rgba(50,200,255,0.1));">`;
            html += `<h3 style="margin-bottom: 1rem;">📊 ${data.industry || 'Industry'} Intelligence</h3>`;
            
            if (intel.summary) {
                html += `<p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 1rem;">${intel.summary}</p>`;
            }
            
            // Sentiment Gauge
            if (intel.sentiment_score !== undefined) {
                const score = intel.sentiment_score;
                const color = score > 20 ? '#4ade80' : score < -20 ? '#f87171' : '#fbbf24';
                html += `<div style="display: flex; gap: 2rem; margin-bottom: 1rem; flex-wrap: wrap;">
                    <div><strong>Sentiment:</strong> <span style="color: ${color}; font-weight: bold;">${intel.sentiment_label || 'Neutral'} (${score})</span></div>
                    <div><strong>Momentum:</strong> ${intel.momentum || 'Stable'}</div>
                    <div><strong>Timing:</strong> <span style="color: var(--primary);">${intel.recommended_timing || 'Assess'}</span></div>
                </div>`;
            }
            html += `</div>`;
            
            // Key Signals
            if (intel.signals && intel.signals.length > 0) {
                html += `<h4 style="color: var(--primary); margin: 1.5rem 0 1rem;">🚨 Key Signals</h4>`;
                html += `<div class="news-grid">`;
                intel.signals.forEach(signal => {
                    const typeColors = {
                        'Expansion': '#4ade80', 'Funding': '#4ade80', 'Product Launch': '#60a5fa',
                        'Partnership': '#60a5fa', 'Contraction': '#f87171', 'Crisis': '#f87171',
                        'Leadership Change': '#fbbf24'
                    };
                    const color = typeColors[signal.type] || 'var(--text-muted)';
                    html += `<div class="glass-panel" style="background: rgba(255,255,255,0.03);">
                        <span class="tag" style="background: ${color}20; border-color: ${color}; color: ${color};">${signal.type}</span>
                        <p style="margin: 0.75rem 0;">${signal.description}</p>
                        <p style="color: var(--primary); font-size: 0.9rem;"><strong>→</strong> ${signal.action}</p>
                    </div>`;
                });
                html += `</div>`;
            }
            
            // Competitor Intelligence
            if (data.competitor_intelligence && data.competitor_intelligence.length > 0) {
                html += `<h4 style="color: var(--primary); margin: 2rem 0 1rem;">🎯 Competitor Intelligence</h4>`;
                data.competitor_intelligence.forEach(comp => {
                    const ci = comp.intelligence || {};
                    const score = ci.sentiment_score || 0;
                    const color = score > 20 ? '#4ade80' : score < -20 ? '#f87171' : '#fbbf24';
                    
                    html += `<div class="glass-panel" style="margin-bottom: 1rem; background: rgba(255,255,255,0.02);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                            <h4 style="margin: 0;">${comp.competitor}</h4>
                            <span style="color: ${color}; font-weight: bold;">${ci.sentiment_label || 'Neutral'}</span>
                        </div>
                        <p style="margin-bottom: 0.75rem;">${ci.summary || 'No data available'}</p>`;
                    
                    if (ci.buying_triggers && ci.buying_triggers.length > 0) {
                        html += `<p style="color: var(--success); font-size: 0.9rem;"><strong>🎯 Buying Trigger:</strong> ${ci.buying_triggers[0]}</p>`;
                    }
                    if (ci.outreach_hook) {
                        html += `<p style="color: var(--primary); font-size: 0.9rem; font-style: italic;">"${ci.outreach_hook}"</p>`;
                    }
                    html += `</div>`;
                });
            }
            
        } else if (type === 'jobs') {
            // Render hiring intelligence
            if (data.hiring_intelligence && data.hiring_intelligence.length > 0) {
                data.hiring_intelligence.forEach(item => {
                    const intel = item.intelligence || {};
                    
                    html += `<div class="glass-panel" style="margin-bottom: 1.5rem; background: linear-gradient(135deg, rgba(100,50,255,0.1), rgba(50,200,255,0.1));">`;
                    html += `<h3 style="margin-bottom: 1rem;">🏢 ${item.company} - Hiring Intelligence</h3>`;
                    
                    // Key Metrics
                    html += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">`;
                    html += `<div class="glass-panel" style="text-align: center; padding: 1rem;">
                        <div style="font-size: 0.8rem; color: var(--text-muted);">Hiring Velocity</div>
                        <div style="font-size: 1.2rem; font-weight: bold; color: var(--primary);">${intel.hiring_velocity || 'Unknown'}</div>
                    </div>`;
                    html += `<div class="glass-panel" style="text-align: center; padding: 1rem;">
                        <div style="font-size: 0.8rem; color: var(--text-muted);">Growth Stage</div>
                        <div style="font-size: 1.2rem; font-weight: bold; color: var(--success);">${intel.growth_stage || 'Unknown'}</div>
                    </div>`;
                    html += `<div class="glass-panel" style="text-align: center; padding: 1rem;">
                        <div style="font-size: 0.8rem; color: var(--text-muted);">Best Time to Sell</div>
                        <div style="font-size: 1.2rem; font-weight: bold; color: #fbbf24;">${intel.best_time_to_sell || 'Assess'}</div>
                    </div>`;
                    html += `</div>`;
                    
                    // Summary
                    if (intel.summary) {
                        html += `<p style="font-size: 1.05rem; line-height: 1.6; margin-bottom: 1rem;">${intel.summary}</p>`;
                    }
                    html += `</div>`;
                    
                    // Department Breakdown
                    if (intel.department_breakdown) {
                        html += `<h4 style="color: var(--primary); margin: 1.5rem 0 1rem;">📊 Department Analysis</h4>`;
                        html += `<div class="news-grid">`;
                        const depts = intel.department_breakdown;
                        const deptNames = { engineering: '💻 Engineering', sales: '💰 Sales', marketing: '📢 Marketing', operations: '⚙️ Operations', leadership: '👔 Leadership' };
                        for (const [key, dept] of Object.entries(depts)) {
                            if (dept && dept.signal) {
                                html += `<div class="glass-panel" style="background: rgba(255,255,255,0.03);">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                        <strong>${deptNames[key] || key}</strong>
                                        <span class="tag">${dept.count || 0} roles</span>
                                    </div>
                                    <p style="color: var(--text-muted); font-size: 0.9rem;">${dept.signal}</p>
                                </div>`;
                            }
                        }
                        html += `</div>`;
                    }
                    
                    // Strategic Priorities
                    if (intel.strategic_priorities && intel.strategic_priorities.length > 0) {
                        html += `<h4 style="color: var(--primary); margin: 1.5rem 0 1rem;">🎯 Strategic Priorities</h4>`;
                        intel.strategic_priorities.forEach(priority => {
                            html += `<div class="glass-panel" style="margin-bottom: 0.75rem; background: rgba(255,255,255,0.03);">
                                <strong>${priority.priority}</strong>
                                <p style="color: var(--text-muted); font-size: 0.9rem; margin: 0.5rem 0;">Evidence: ${priority.evidence}</p>
                                <p style="color: var(--success); font-size: 0.9rem;">→ ${priority.implication}</p>
                            </div>`;
                        });
                    }
                    
                    // Recommended Contacts
                    if (intel.recommended_contacts && intel.recommended_contacts.length > 0) {
                        html += `<h4 style="color: var(--primary); margin: 1.5rem 0 1rem;">👤 Who to Contact</h4>`;
                        html += `<div class="news-grid">`;
                        intel.recommended_contacts.forEach(contact => {
                            html += `<div class="glass-panel" style="background: rgba(255,255,255,0.03);">
                                <strong style="color: var(--primary);">${contact.title}</strong>
                                <p style="font-size: 0.9rem; margin: 0.5rem 0;">${contact.reason}</p>
                                <span class="tag">${contact.timing}</span>
                            </div>`;
                        });
                        html += `</div>`;
                    }
                    
                    // Pain Indicators
                    if (intel.pain_indicators && intel.pain_indicators.length > 0) {
                        html += `<h4 style="color: var(--primary); margin: 1.5rem 0 1rem;">🔥 Pain Points to Address</h4>`;
                        html += `<ul style="list-style: none; padding: 0;">`;
                        intel.pain_indicators.forEach(pain => {
                            html += `<li style="padding: 0.5rem 0; padding-left: 1.5rem; position: relative;">
                                <span style="position: absolute; left: 0; color: var(--error);">→</span>${pain}
                            </li>`;
                        });
                        html += `</ul>`;
                    }
                });
            } else {
                html = '<p>No hiring intelligence available.</p>';
            }
            
        } else if (type === 'account') {
            // Account Research with full intelligence
            if (data.company) {
                html += `<h3 style="color: var(--primary); margin-bottom: 1rem;">📊 ${data.company} - Full Intelligence Report</h3>`;
            }
            
            // News Intelligence Summary (if available)
            const newsIntel = data.news_intelligence || {};
            if (newsIntel.sentiment_score !== undefined) {
                const score = newsIntel.sentiment_score;
                const color = score > 20 ? '#4ade80' : score < -20 ? '#f87171' : '#fbbf24';
                html += `<div class="glass-panel" style="margin-bottom: 1.5rem; background: linear-gradient(135deg, rgba(100,50,255,0.1), rgba(50,200,255,0.1));">`;
                html += `<h4 style="margin-bottom: 0.75rem;">📰 News Sentiment</h4>`;
                html += `<div style="display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 1rem;">
                    <div><strong>Sentiment:</strong> <span style="color: ${color}; font-weight: bold;">${newsIntel.sentiment_label || 'Neutral'} (${score})</span></div>
                    <div><strong>Momentum:</strong> ${newsIntel.momentum || 'Stable'}</div>
                    <div><strong>Timing:</strong> <span style="color: var(--primary);">${newsIntel.recommended_timing || 'Assess'}</span></div>
                </div>`;
                if (newsIntel.outreach_hook) {
                    html += `<p style="font-style: italic; color: var(--text-muted);">"${newsIntel.outreach_hook}"</p>`;
                }
                html += `</div>`;
            }
            
            // Hiring Intelligence Summary
            const hiringIntel = data.hiring_intelligence || {};
            if (hiringIntel.hiring_velocity) {
                html += `<div class="glass-panel" style="margin-bottom: 1.5rem; background: rgba(255,255,255,0.03);">`;
                html += `<h4 style="margin-bottom: 0.75rem;">💼 Hiring Signals</h4>`;
                html += `<div style="display: flex; gap: 2rem; flex-wrap: wrap;">
                    <div><strong>Velocity:</strong> <span style="color: var(--primary);">${hiringIntel.hiring_velocity}</span></div>
                    <div><strong>Stage:</strong> ${hiringIntel.growth_stage || 'Unknown'}</div>
                    <div><strong>Best Time:</strong> ${hiringIntel.best_time_to_sell || 'Assess'}</div>
                </div>`;
                if (hiringIntel.summary) {
                    html += `<p style="margin-top: 0.75rem; color: var(--text-muted);">${hiringIntel.summary}</p>`;
                }
                html += `</div>`;
            }
            
            // Main Analysis
            if (data.analysis) {
                let analysis = data.analysis
                    .replace(/## (.*)/g, '<h3 style="color: var(--primary); margin-top: 1.5rem;">$1</h3>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/- (.*)/g, '<li>$1</li>')
                    .replace(/\n/g, '<br>');
                html += `<div class="analysis-content" style="line-height: 1.8;">${analysis}</div>`;
            }
            
        } else if (type === 'website') {
            if (data.title) {
                html += `<h3 style="color: var(--primary); margin-bottom: 1rem;">🌐 ${data.title}</h3>`;
            }
            if (data.tech_stack && data.tech_stack.length > 0) {
                html += `<div style="margin-bottom: 1.5rem;">
                    <h4>🔧 Tech Stack Detected</h4>
                    <div class="tags" style="margin-top: 0.5rem;">
                        ${data.tech_stack.map(t => `<span class="tag">${t}</span>`).join('')}
                    </div>
                </div>`;
            }
            if (data.emails && data.emails.length > 0) {
                html += `<div style="margin-bottom: 1.5rem;">
                    <h4>📧 Emails Found</h4>
                    <ul style="list-style: none; padding: 0; margin-top: 0.5rem;">
                        ${data.emails.map(e => `<li style="padding: 0.25rem 0;"><a href="mailto:${e}" style="color: var(--primary)">${e}</a></li>`).join('')}
                    </ul>
                </div>`;
            }
            if (data.analysis) {
                let analysis = data.analysis
                    .replace(/## (.*)/g, '<h3 style="color: var(--primary); margin-top: 1.5rem;">$1</h3>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/- (.*)/g, '<li>$1</li>')
                    .replace(/\n/g, '<br>');
                html += `<div class="analysis-content" style="line-height: 1.8;">${analysis}</div>`;
            }
        } else {
            html = `<pre style="white-space: pre-wrap;">${JSON.stringify(data, null, 2)}</pre>`;
        }

        container.innerHTML = html;
    }

    window.closeResults = () => {
        document.getElementById('resultsArea').classList.add('hidden');
        currentResearchType = null;
    };

    // =========================================================================
    // CAMPAIGN BUILDER
    // =========================================================================
    
    window.openCampaignBuilder = () => {
        document.getElementById('campaignModal').classList.remove('hidden');
        document.getElementById('campaignForm').classList.remove('hidden');
        document.getElementById('campaignLoading').classList.add('hidden');
        document.getElementById('campaignResults').classList.add('hidden');
    };
    
    window.closeCampaignModal = () => {
        document.getElementById('campaignModal').classList.add('hidden');
    };
    
    window.generateCampaign = async () => {
        const company = document.getElementById('campaignCompany').value.trim();
        const persona = document.getElementById('campaignPersona').value.trim();
        const strategy = document.getElementById('campaignStrategy').value;
        const numTouches = parseInt(document.getElementById('campaignTouches').value);
        const objective = document.getElementById('campaignObjective').value;
        const tone = document.getElementById('campaignTone').value;
        const trigger = document.getElementById('campaignTrigger').value.trim();
        
        if (!company) {
            alert('Please enter a target company');
            return;
        }
        
        document.getElementById('campaignForm').classList.add('hidden');
        document.getElementById('campaignLoading').classList.remove('hidden');
        
        try {
            const response = await fetch('/api/generate_campaign', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company,
                    persona: persona || 'Decision Maker',
                    strategy,
                    num_touches: numTouches,
                    objective,
                    tone,
                    trigger_event: trigger
                })
            });
            
            const data = await response.json();
            document.getElementById('campaignLoading').classList.add('hidden');
            
            if (data.status === 'success') {
                renderCampaign(data.data);
            } else {
                document.getElementById('campaignForm').classList.remove('hidden');
                alert('Error: ' + data.message);
            }
        } catch (error) {
            document.getElementById('campaignLoading').classList.add('hidden');
            document.getElementById('campaignForm').classList.remove('hidden');
            alert('Error generating campaign: ' + error.message);
        }
    };
    
    function renderCampaign(campaign) {
        const resultsDiv = document.getElementById('campaignResults');
        let html = '';
        
        // Campaign Header
        html += `<div style="margin-bottom: 1.5rem;">
            <h3 style="color: var(--primary); margin-bottom: 0.5rem;">${campaign.campaign_name || 'Your Campaign'}</h3>
            <p style="color: var(--text-muted);">${campaign.campaign_summary || ''}</p>
            <div style="display: flex; gap: 1rem; margin-top: 1rem; flex-wrap: wrap;">
                <span class="tag" style="background: rgba(74, 222, 128, 0.2); border-color: #4ade80; color: #4ade80;">
                    Est. Reply Rate: ${campaign.estimated_reply_rate || 'TBD'}
                </span>
                <span class="tag">Duration: ${campaign.total_duration_days || '?'} days</span>
                <span class="tag">${campaign.touches?.length || 0} touches</span>
            </div>
        </div>`;
        
        // Success Metrics
        if (campaign.success_metrics) {
            html += `<div class="glass-panel" style="margin-bottom: 1.5rem; background: rgba(255,255,255,0.03);">
                <h4 style="margin-bottom: 0.75rem;">📊 Target Metrics</h4>
                <div style="display: flex; gap: 2rem; flex-wrap: wrap;">
                    <div>Open Rate: <strong>${campaign.success_metrics.open_rate_target || '?'}</strong></div>
                    <div>Reply Rate: <strong>${campaign.success_metrics.reply_rate_target || '?'}</strong></div>
                    <div>Meeting Rate: <strong>${campaign.success_metrics.meeting_rate_target || '?'}</strong></div>
                </div>
            </div>`;
        }
        
        // Campaign Touches
        html += `<h4 style="color: var(--primary); margin-bottom: 1rem;">📧 Sequence</h4>`;
        
        if (campaign.touches && campaign.touches.length > 0) {
            campaign.touches.forEach(touch => {
                const typeIcons = { email: '📧', linkedin: '💼', call: '📞', video: '🎥' };
                const icon = typeIcons[touch.type] || '📧';
                
                html += `<div class="campaign-touch">
                    <div class="campaign-touch-header">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span class="touch-number">${touch.touch_number}</span>
                            <span style="font-size: 1.2rem;">${icon}</span>
                            <strong>${touch.type?.charAt(0).toUpperCase() + touch.type?.slice(1) || 'Email'}</strong>
                        </div>
                        <div class="touch-meta">
                            <span>${touch.timing || ''}</span>
                            <span>🕐 ${touch.optimal_send_time || ''}</span>
                        </div>
                    </div>`;
                
                if (touch.type === 'email' || !touch.type) {
                    html += `<div class="email-preview">
                        <div class="email-subject">Subject: ${touch.subject_line || ''}</div>
                        <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                            Preview: ${touch.preview_text || ''}
                        </div>
                        <div style="white-space: pre-wrap; font-size: 0.95rem; line-height: 1.6;">${touch.body || ''}</div>
                        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--glass-border);">
                            <strong style="color: var(--primary);">CTA:</strong> ${touch.cta || ''}
                        </div>
                    </div>`;
                    
                    // A/B Variant
                    if (touch.subject_line_b || touch.body_variant_b) {
                        html += `<div class="ab-variant">
                            <span class="ab-label">A/B VARIANT</span>
                            ${touch.subject_line_b ? `<div style="margin-top: 0.5rem;"><strong>Subject B:</strong> ${touch.subject_line_b}</div>` : ''}
                            ${touch.body_variant_b ? `<div class="email-preview" style="margin-top: 0.5rem;">${touch.body_variant_b}</div>` : ''}
                        </div>`;
                    }
                } else {
                    html += `<div style="padding: 0.5rem 0;">
                        <strong>Action:</strong> ${touch.body || touch.cta || 'Execute touch'}
                    </div>`;
                }
                
                // Psychology note
                if (touch.psychological_principle) {
                    html += `<div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px dashed var(--glass-border); font-size: 0.85rem; color: var(--text-muted);">
                        💡 <em>${touch.psychological_principle}</em>
                    </div>`;
                }
                
                html += `</div>`;
            });
        }
        
        // Personalization Requirements
        if (campaign.personalization_requirements && campaign.personalization_requirements.length > 0) {
            html += `<div class="glass-panel" style="margin-top: 1.5rem; background: rgba(255,255,255,0.03);">
                <h4 style="margin-bottom: 0.75rem;">🎯 Personalization Requirements</h4>
                <ul style="margin: 0; padding-left: 1.25rem;">
                    ${campaign.personalization_requirements.map(r => `<li style="margin-bottom: 0.25rem;">${r}</li>`).join('')}
                </ul>
            </div>`;
        }
        
        // Objection Handlers
        if (campaign.objection_handlers && Object.keys(campaign.objection_handlers).length > 0) {
            html += `<div class="glass-panel" style="margin-top: 1rem; background: rgba(255,255,255,0.03);">
                <h4 style="margin-bottom: 0.75rem;">🛡️ Objection Handlers</h4>`;
            for (const [objection, handler] of Object.entries(campaign.objection_handlers)) {
                html += `<div style="margin-bottom: 0.75rem;">
                    <strong style="color: var(--error);">"${objection}"</strong>
                    <p style="margin-top: 0.25rem; color: var(--text-muted);">→ ${handler}</p>
                </div>`;
            }
            html += `</div>`;
        }
        
        // Actions
        html += `<div style="margin-top: 1.5rem; display: flex; gap: 1rem;">
            <button class="btn btn-primary" onclick="copyCampaignToClipboard()">Copy to Clipboard</button>
            <button class="btn" onclick="openCampaignBuilder()">Generate Another</button>
        </div>`;
        
        resultsDiv.innerHTML = html;
        resultsDiv.classList.remove('hidden');
        
        // Store campaign for copying
        window.currentCampaign = campaign;
    }
    
    window.copyCampaignToClipboard = () => {
        if (!window.currentCampaign) return;
        
        let text = `CAMPAIGN: ${window.currentCampaign.campaign_name}\n\n`;
        text += `${window.currentCampaign.campaign_summary}\n\n`;
        text += `---\n\n`;
        
        window.currentCampaign.touches?.forEach(touch => {
            text += `TOUCH ${touch.touch_number} - ${touch.type || 'Email'} (${touch.timing})\n`;
            text += `Send: ${touch.optimal_send_time}\n`;
            if (touch.subject_line) text += `Subject: ${touch.subject_line}\n`;
            text += `\n${touch.body}\n`;
            text += `\nCTA: ${touch.cta}\n`;
            text += `\n---\n\n`;
        });
        
        navigator.clipboard.writeText(text).then(() => {
            alert('Campaign copied to clipboard!');
        });
    };

    // =========================================================================
    // INTELLIGENT CHAT
    // =========================================================================
    
    let chatHistory = [];
    
    window.openChat = () => {
        document.getElementById('chatPanel').classList.remove('hidden');
        document.getElementById('chatInput').focus();
    };
    
    window.closeChat = () => {
        document.getElementById('chatPanel').classList.add('hidden');
    };
    
    window.handleChatKeypress = (e) => {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    };
    
    window.sendChatMessage = async (preset) => {
        const input = document.getElementById('chatInput');
        const message = preset || input.value.trim();
        
        if (!message) return;
        
        input.value = '';
        
        // Add user message
        const messagesDiv = document.getElementById('chatMessages');
        messagesDiv.innerHTML += `<div class="chat-message user"><p>${escapeHtml(message)}</p></div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        // Add to history
        chatHistory.push({ role: 'user', content: message });
        
        // Show typing indicator
        const typingId = 'typing-' + Date.now();
        messagesDiv.innerHTML += `<div class="chat-message assistant" id="${typingId}"><p>Thinking...</p></div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: message,
                    history: chatHistory.slice(-10)
                })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            document.getElementById(typingId)?.remove();
            
            if (data.status === 'success' && data.data) {
                const result = data.data;
                
                // Add assistant response
                let responseHtml = `<div class="chat-message assistant">
                    <p>${escapeHtml(result.response || '')}</p>`;
                
                // Show insights if any
                if (result.insights && result.insights.length > 0) {
                    responseHtml += `<div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--glass-border);">
                        <strong style="font-size: 0.85rem;">💡 Insights:</strong>
                        <ul style="margin: 0.5rem 0 0 1rem; font-size: 0.9rem;">
                            ${result.insights.map(i => `<li>${escapeHtml(i)}</li>`).join('')}
                        </ul>
                    </div>`;
                }
                
                responseHtml += `</div>`;
                messagesDiv.innerHTML += responseHtml;
                
                // Show action results if any
                if (result.action_results && result.action_results.length > 0) {
                    result.action_results.forEach(ar => {
                        let actionHtml = `<div class="chat-message action">
                            <strong>📊 Research Complete: ${ar.target}</strong>`;
                        if (ar.analysis) {
                            actionHtml += `<p style="margin-top: 0.5rem; font-size: 0.9rem;">${ar.analysis.substring(0, 300)}...</p>`;
                        }
                        actionHtml += `</div>`;
                        messagesDiv.innerHTML += actionHtml;
                    });
                }
                
                // Update suggestions
                if (result.suggested_followups && result.suggested_followups.length > 0) {
                    const suggestionsDiv = document.getElementById('chatSuggestions');
                    suggestionsDiv.innerHTML = result.suggested_followups.map(s => 
                        `<button class="suggestion-chip" onclick="sendChatMessage('${escapeHtml(s)}')">${escapeHtml(s)}</button>`
                    ).join('');
                }
                
                // Add to history
                chatHistory.push({ role: 'assistant', content: result.response });
                
            } else {
                messagesDiv.innerHTML += `<div class="chat-message assistant">
                    <p style="color: var(--error);">Error: ${data.message || 'Something went wrong'}</p>
                </div>`;
            }
            
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
        } catch (error) {
            document.getElementById(typingId)?.remove();
            messagesDiv.innerHTML += `<div class="chat-message assistant">
                <p style="color: var(--error);">Error: ${error.message}</p>
            </div>`;
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    };
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // =========================================================================
    // PROACTIVE OPPORTUNITY DISCOVERY
    // =========================================================================
    
    let discoveredOpportunities = [];
    let selectedOpportunities = [];
    
    window.discoverOpportunities = async () => {
        const statusCard = document.getElementById('statusCard');
        const loadingCard = document.getElementById('loadingCard');
        const opportunitiesSection = document.getElementById('opportunitiesSection');
        
        // Hide status, show loading
        statusCard?.classList.add('hidden');
        opportunitiesSection?.classList.add('hidden');
        loadingCard?.classList.remove('hidden');
        
        try {
            const response = await fetch('/api/discover_opportunities', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ limit: 10 })
            });
            
            const result = await response.json();
            loadingCard?.classList.add('hidden');
            
            if (result.status === 'success' && result.data) {
                discoveredOpportunities = result.data.opportunities || [];
                renderOpportunities(result.data);
                
                // Update stats
                const statOpp = document.getElementById('statOpportunities');
                if (statOpp) {
                    statOpp.textContent = discoveredOpportunities.length;
                }
            } else {
                statusCard?.classList.remove('hidden');
                alert('Error discovering opportunities: ' + (result.message || 'Unknown error'));
            }
        } catch (error) {
            loadingCard?.classList.add('hidden');
            statusCard?.classList.remove('hidden');
            alert('Error: ' + error.message);
        }
    };
    
    function renderOpportunities(data) {
        const opportunitiesSection = document.getElementById('opportunitiesSection');
        const opportunitiesGrid = document.getElementById('opportunitiesGrid');
        const oppCount = document.getElementById('oppCount');
        const insightsBar = document.getElementById('insightsBar');
        
        opportunitiesSection?.classList.remove('hidden');
        
        // Update count
        if (oppCount) {
            oppCount.textContent = `${data.opportunities?.length || 0} found`;
        }
        
        // Update insights
        if (insightsBar && data.market_insights && data.market_insights.length > 0) {
            insightsBar.innerHTML = data.market_insights.map((insight, i) => 
                `<div class="insight-item">
                    <span class="insight-icon">${i === 0 ? '📈' : i === 1 ? '🎯' : '💡'}</span>
                    <span class="insight-text">${escapeHtml(insight)}</span>
                </div>`
            ).join('');
        }
        
        // Render opportunity cards
        if (opportunitiesGrid) {
            opportunitiesGrid.innerHTML = (data.opportunities || []).map((opp, index) => {
                const scoreClass = opp.score >= 70 ? 'high' : opp.score >= 50 ? 'medium' : 'low';
                const signalIcon = getSignalIcon(opp.signal_type);
                
                return `
                <div class="opportunity-card" data-index="${index}" onclick="toggleOpportunity(${index})">
                    <input type="checkbox" class="opp-checkbox" onclick="event.stopPropagation(); toggleOpportunity(${index})">
                    <div class="opp-header">
                        <div>
                            <div class="opp-company">${escapeHtml(opp.company_name)}</div>
                            <div class="opp-industry">${escapeHtml(opp.industry)} • ${escapeHtml(opp.employee_range || 'Unknown size')}</div>
                        </div>
                        <div class="opp-score">
                            <span class="score-value ${scoreClass}">${opp.score}</span>
                            <span class="score-label">Match Score</span>
                        </div>
                    </div>
                    
                    <div class="opp-signal">
                        <span class="signal-icon">${signalIcon}</span>
                        <div>
                            <div class="signal-text">${escapeHtml(opp.signal_description)}</div>
                            <div class="signal-strength ${opp.signal_strength}">${opp.signal_strength} signal</div>
                        </div>
                    </div>
                    
                    <div class="opp-match-reasons">
                        ${(opp.icp_match_reasons || []).slice(0, 3).map(r => 
                            `<span class="match-tag">${escapeHtml(r)}</span>`
                        ).join('')}
                    </div>
                    
                    <div class="opp-outreach">
                        <div class="outreach-subject">📧 ${escapeHtml(opp.email_subject || 'Draft outreach ready')}</div>
                        <div class="outreach-preview">${escapeHtml(opp.email_opener || '')}</div>
                    </div>
                    
                    <div class="opp-actions">
                        <button class="btn btn-secondary" onclick="event.stopPropagation(); researchCompany('${escapeHtml(opp.company_name)}')">
                            🔍 Deep Dive
                        </button>
                        <button class="btn btn-primary" onclick="event.stopPropagation(); approveOne(${index})">
                            ✅ Approve
                        </button>
                    </div>
                </div>`;
            }).join('');
        }
    }
    
    function getSignalIcon(signalType) {
        const icons = {
            'funding': '💰',
            'hiring': '👥',
            'expansion': '🚀',
            'tech_change': '🔧',
            'leadership_change': '👔',
            'pain_indicator': '🎯'
        };
        return icons[signalType] || '📊';
    }
    
    window.toggleOpportunity = (index) => {
        const card = document.querySelector(`.opportunity-card[data-index="${index}"]`);
        const checkbox = card?.querySelector('.opp-checkbox');
        
        if (selectedOpportunities.includes(index)) {
            selectedOpportunities = selectedOpportunities.filter(i => i !== index);
            card?.classList.remove('selected');
            if (checkbox) checkbox.checked = false;
        } else {
            selectedOpportunities.push(index);
            card?.classList.add('selected');
            if (checkbox) checkbox.checked = true;
        }
    };
    
    window.approveOne = async (index) => {
        const opp = discoveredOpportunities[index];
        if (!opp) return;
        
        // Add to queue
        addToQueue(opp);
        
        // Visual feedback
        const card = document.querySelector(`.opportunity-card[data-index="${index}"]`);
        if (card) {
            card.style.opacity = '0.5';
            card.style.transform = 'scale(0.95)';
            setTimeout(() => card.remove(), 300);
        }
    };
    
    window.approveSelected = async () => {
        if (selectedOpportunities.length === 0) {
            alert('Please select at least one opportunity');
            return;
        }
        
        selectedOpportunities.forEach(index => {
            const opp = discoveredOpportunities[index];
            if (opp) addToQueue(opp);
        });
        
        // Remove approved cards
        selectedOpportunities.forEach(index => {
            const card = document.querySelector(`.opportunity-card[data-index="${index}"]`);
            if (card) card.remove();
        });
        
        selectedOpportunities = [];
        
        // Update stats
        const statApproved = document.getElementById('statApproved');
        if (statApproved) {
            statApproved.textContent = parseInt(statApproved.textContent || '0') + selectedOpportunities.length;
        }
    };
    
    function addToQueue(opp) {
        const queueList = document.getElementById('queueList');
        const queueCount = document.getElementById('queueCount');
        
        // Clear empty state if present
        const emptyState = queueList?.querySelector('.empty-state');
        if (emptyState) emptyState.remove();
        
        // Add queue item
        if (queueList) {
            const item = document.createElement('div');
            item.className = 'queue-item';
            item.innerHTML = `
                <div class="queue-item-info">
                    <div class="queue-item-company">${escapeHtml(opp.company_name)}</div>
                    <div class="queue-item-status">✓ Approved</div>
                </div>
                <button class="btn btn-sm btn-ghost" onclick="this.parentElement.remove(); updateQueueCount()">✕</button>
            `;
            queueList.appendChild(item);
        }
        
        updateQueueCount();
    }
    
    window.updateQueueCount = () => {
        const queueList = document.getElementById('queueList');
        const queueCount = document.getElementById('queueCount');
        const count = queueList?.querySelectorAll('.queue-item').length || 0;
        if (queueCount) queueCount.textContent = count;
        
        // Update stat
        const statApproved = document.getElementById('statApproved');
        if (statApproved) statApproved.textContent = count;
    };
    
    window.researchCompany = (companyName) => {
        // Open research modal with company pre-filled
        const modal = document.getElementById('researchModal');
        const input = document.getElementById('researchCompanyInput');
        
        if (modal && input) {
            input.value = companyName;
            modal.classList.remove('hidden');
        }
    };
    
    // =========================================================================
    // RESEARCH MODAL
    // =========================================================================
    
    window.openResearchModal = () => {
        document.getElementById('researchModal')?.classList.remove('hidden');
        document.getElementById('researchCompanyInput')?.focus();
    };
    
    window.closeResearchModal = () => {
        document.getElementById('researchModal')?.classList.add('hidden');
    };
    
    window.startCompanyResearch = async () => {
        const input = document.getElementById('researchCompanyInput');
        const companyName = input?.value?.trim();
        
        if (!companyName) {
            input.style.borderColor = 'var(--error)';
            return;
        }
        
        closeResearchModal();
        
        // Use existing research function
        startResearch('account', companyName);
        
        // Update stats
        const statResearched = document.getElementById('statResearched');
        if (statResearched) {
            statResearched.textContent = parseInt(statResearched.textContent || '0') + 1;
        }
    };
    
    // =========================================================================
    // MINI CHAT
    // =========================================================================
    
    window.handleMiniChat = (e) => {
        if (e.key === 'Enter') {
            const input = document.getElementById('miniChatInput');
            const message = input?.value?.trim();
            
            if (message) {
                input.value = '';
                openChat();
                setTimeout(() => {
                    document.getElementById('chatInput').value = message;
                    sendChatMessage();
                }, 100);
            }
        }
    };
});

