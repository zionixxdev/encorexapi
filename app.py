# encorexosint.py - Advanced API Gateway by @frappeash
# Updated for Supabase storage
from flask import Flask, request, jsonify, redirect, make_response
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import jwt
import os
import requests
import urllib.parse
import random
import time
import hashlib
import json
import uuid

# ========== SUPABASE IMPORTS ==========
from supabase import create_client, Client

# ========== CONFIGURATION ==========
ADMIN_PASSKEY = os.getenv('ADMIN_PASSKEY', 'amnbhosdi')
JWT_SECRET = os.getenv('JWT_SECRET', 'encorexosint-secret-2024')
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://zquwbwvdwvaxzeqcvauv.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpxdXdid3Zkd3ZheHplcWN2YXV2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTc3NDc2MywiZXhwIjoyMDg1MzUwNzYzfQ.XNjHhkZJgzpS8_-9NccEZwYbvPo1KORaT9L3ydIbf7o"
)
# ========== INITIALIZE ==========
app = Flask(__name__)
CORS(app)

# Initialize Supabase
supabase: Client = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected successfully!")
except Exception as e:
    print(f"⚠️ Supabase connection error: {e}")
    raise Exception("Supabase connection failed")

# ========== UTILITY FUNCTIONS ==========
def generate_api_key():
    """Generate aesthetic API key"""
    timestamp = int(time.time())
    random_hash = hashlib.sha256(f"{timestamp}{random.random()}".encode()).hexdigest()[:12]
    return f"ENC-{random_hash.upper()}"

def generate_request_id():
    """Generate unique request ID"""
    return f"REQ-{int(time.time())}-{random.randint(1000, 9999)}"

def check_auth(request):
    """Check authentication"""
    token = request.cookies.get('encore_token')
    if not token:
        return False
    try:
        jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return True
    except:
        return False

def create_token(user_id):
    """Create JWT token"""
    return jwt.encode(
        {'user_id': user_id, 'exp': datetime.now(timezone.utc) + timedelta(hours=72)},
        JWT_SECRET,
        algorithm='HS256'
    )

def verify_passkey(passkey):
    """Verify admin passkey"""
    return passkey == ADMIN_PASSKEY

def clean_response_data(data, hide_fields):
    """Remove specified fields from response data"""
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if key not in hide_fields:
                if isinstance(value, (dict, list)):
                    cleaned[key] = clean_response_data(value, hide_fields)
                else:
                    cleaned[key] = value
        return cleaned
    elif isinstance(data, list):
        return [clean_response_data(item, hide_fields) for item in data]
    else:
        return data

# ========== SUPABASE DATABASE OPERATIONS ==========
def get_all_apis():
    """Get all APIs from Supabase"""
    try:
        response = supabase.table('apis').select('*').execute()
        return response.data
    except Exception as e:
        print(f"Error fetching APIs: {e}")
        return []

def get_api_by_name(name):
    """Get API by name"""
    try:
        response = supabase.table('apis').select('*').eq('name', name).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error fetching API {name}: {e}")
        return None

def get_api_by_endpoint(endpoint):
    """Get API by endpoint"""
    try:
        response = supabase.table('apis').select('*').eq('endpoint', endpoint).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error fetching API by endpoint {endpoint}: {e}")
        return None

def create_api(api_data):
    """Create new API in Supabase"""
    try:
        # Generate unique ID and timestamp
        api_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Prepare data for Supabase
        supabase_data = {
            'id': api_id,
            'name': api_data['name'],
            'endpoint': api_data['endpoint'],
            'param': api_data['param'],
            'base_url': api_data['baseUrl'],
            'rate_limit': api_data.get('rateLimit', 1000),
            'cache_ttl': api_data.get('cacheTtl', 300),
            'timeout': api_data.get('timeout', 10),
            'hide_fields': api_data.get('hideFields', []),
            'show_powered_by': api_data.get('showPoweredBy', True),
            'disabled_message': api_data.get('disabledMessage', 'API is currently disabled'),
            'enabled': True,
            'api_key': generate_api_key(),
            'requests': 0,
            'success_rate': 100,
            'created_at': now,
            'updated_at': now
        }
        
        # Insert into Supabase
        response = supabase.table('apis').insert(supabase_data).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise Exception("No data returned from Supabase")
            
    except Exception as e:
        print(f"Error creating API: {e}")
        raise e

def update_api(api_name, updates):
    """Update API in Supabase"""
    try:
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Handle field name mapping
        supabase_updates = {}
        if 'hideFields' in updates:
            supabase_updates['hide_fields'] = updates['hideFields']
        if 'showPoweredBy' in updates:
            supabase_updates['show_powered_by'] = updates['showPoweredBy']
        if 'disabledMessage' in updates:
            supabase_updates['disabled_message'] = updates['disabledMessage']
        if 'enabled' in updates:
            supabase_updates['enabled'] = updates['enabled']
        
        response = supabase.table('apis').update(supabase_updates).eq('name', api_name).execute()
        return response.data
    except Exception as e:
        print(f"Error updating API {api_name}: {e}")
        return []

def delete_api(api_name):
    """Delete API from Supabase"""
    try:
        response = supabase.table('apis').delete().eq('name', api_name).execute()
        return response.data
    except Exception as e:
        print(f"Error deleting API {api_name}: {e}")
        return []

def increment_api_requests(api_name):
    """Increment API request count"""
    try:
        # Get current requests
        response = supabase.table('apis').select('requests').eq('name', api_name).execute()
        if response.data:
            current_requests = response.data[0]['requests']
            supabase.table('apis').update({
                'requests': current_requests + 1,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('name', api_name).execute()
    except Exception as e:
        print(f"Error incrementing requests for {api_name}: {e}")

def record_analytics(api_name, success=True):
    """Record analytics in Supabase"""
    try:
        analytics_data = {
            'id': str(uuid.uuid4()),
            'api_name': api_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': success,
            'ip_address': request.remote_addr if request else 'unknown'
        }
        
        supabase.table('analytics').insert(analytics_data).execute()
    except Exception as e:
        print(f"Error recording analytics: {e}")

def get_analytics_summary():
    """Get analytics summary from Supabase"""
    try:
        # Get total requests
        response = supabase.table('analytics').select('*', count='exact').execute()
        total_requests = response.count or 0
        
        # Get successful requests
        success_response = supabase.table('analytics').select('*', count='exact').eq('success', True).execute()
        successful_requests = success_response.count or 0
        
        # Get failed requests
        failed_requests = total_requests - successful_requests
        
        # Get API usage breakdown
        usage_response = supabase.table('analytics').select('api_name, success').execute()
        
        api_usage = {}
        for record in usage_response.data:
            api_name = record['api_name']
            if api_name not in api_usage:
                api_usage[api_name] = {'success': 0, 'failed': 0}
            
            if record['success']:
                api_usage[api_name]['success'] += 1
            else:
                api_usage[api_name]['failed'] += 1
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'api_usage': api_usage
        }
    except Exception as e:
        print(f"Error getting analytics: {e}")
        return {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'api_usage': {}
        }

# ========== HTML TEMPLATES ==========
# [Keep all your existing HTML templates exactly as they are]
# The login_html(), get_dashboard_css(), generate_api_card(), 
# generate_usage_stats(), and dashboard_html() functions remain unchanged
# Only copy these functions from your original code

def login_html(error=False):
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EncoreXOSINT | Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .login-container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo h1 {
            font-size: 32px;
            background: linear-gradient(45deg, #00dbde, #fc00ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }
        
        .logo p {
            color: #8b949e;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #c9d1d9;
            font-weight: 500;
        }
        
        .form-input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            font-size: 16px;
            color: #c9d1d9;
            transition: all 0.3s;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #00dbde;
            box-shadow: 0 0 0 3px rgba(0, 219, 222, 0.1);
        }
        
        .btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(45deg, #00dbde, #fc00ff);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0, 219, 222, 0.3);
        }
        
        .error-message {
            background: rgba(255, 87, 87, 0.1);
            border: 1px solid rgba(255, 87, 87, 0.3);
            color: #ff5757;
            padding: 12px;
            border-radius: 8px;
            margin-top: 20px;
            text-align: center;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #8b949e;
            font-size: 14px;
        }
        
        .creator {
            margin-top: 15px;
            padding: 10px;
            background: rgba(0, 219, 222, 0.1);
            border-radius: 8px;
            color: #00dbde;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1><i class="fas fa-bolt"></i> ENCOREXOSINT</h1>
            <p>Advanced API Gateway by @frappeash</p>
        </div>
        
        <form method="POST" action="/lwdalasan/login">
            <div class="form-group">
                <label><i class="fas fa-key"></i> Admin Passkey</label>
                <input type="password" name="passkey" placeholder="Enter your passkey" required class="form-input">
            </div>
            
            <button type="submit" class="btn">
                <i class="fas fa-sign-in-alt"></i> Access Dashboard
            </button>
        </form>
        
        ''' + ('''
        <div class="error-message">
            <i class="fas fa-exclamation-circle"></i> Invalid passkey. Please try again.
        </div>
        ''' if error else '') + '''
        
        <div class="footer">
            <p><i class="fas fa-shield-alt"></i> Secure Access • <i class="fas fa-clock"></i> 72h Session</p>
            <div class="creator">
                <i class="fas fa-code"></i> Created by @frappeash • t.me/frappeash
            </div>
        </div>
    </div>
</body>
</html>
'''

def get_dashboard_css():
    return '''
    <style>
        :root {
            --primary: #00dbde;
            --primary-dark: #00b4b7;
            --secondary: #fc00ff;
            --accent: #9d4edd;
            --success: #00ff88;
            --danger: #ff5757;
            --warning: #ffaa00;
            --dark: #0a0a0f;
            --light: #f8f9fa;
            --gray: #6c757d;
            --glass: rgba(255, 255, 255, 0.05);
            --border: rgba(255, 255, 255, 0.1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #e2e8f0;
            min-height: 100vh;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        .header {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px 30px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-icon {
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 20px;
        }
        
        .logo-text {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .creator-tag {
            font-size: 12px;
            color: var(--primary);
            margin-top: 2px;
        }
        
        .header-actions {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 25px;
            transition: all 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary);
        }
        
        .stat-number {
            font-size: 36px;
            font-weight: 700;
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        
        .stat-label {
            color: var(--gray);
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* API Cards */
        .api-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .api-card {
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 25px;
            position: relative;
            overflow: hidden;
        }
        
        .api-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
        }
        
        .api-card.active::before {
            background: linear-gradient(90deg, var(--success), var(--primary));
        }
        
        .api-card.disabled::before {
            background: linear-gradient(90deg, var(--danger), var(--warning));
        }
        
        .api-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 20px;
        }
        
        .api-name {
            font-size: 18px;
            font-weight: 600;
            color: white;
        }
        
        .api-status {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-active {
            background: rgba(0, 255, 136, 0.2);
            color: var(--success);
            border: 1px solid rgba(0, 255, 136, 0.3);
        }
        
        .status-inactive {
            background: rgba(255, 87, 87, 0.2);
            color: var(--danger);
            border: 1px solid rgba(255, 87, 87, 0.3);
        }
        
        .api-url {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            margin: 15px 0;
            overflow-x: auto;
            color: var(--primary);
        }
        
        .api-meta {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            font-size: 13px;
            color: var(--gray);
        }
        
        .api-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        /* Buttons */
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 10px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 219, 222, 0.3);
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid var(--border);
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        
        .btn-success {
            background: linear-gradient(45deg, var(--success), var(--primary));
            color: white;
        }
        
        .btn-danger {
            background: linear-gradient(45deg, var(--danger), var(--warning));
            color: white;
        }
        
        .btn-sm {
            padding: 8px 16px;
            font-size: 13px;
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 10px;
            margin: 30px 0;
            overflow-x: auto;
        }
        
        .tab {
            padding: 12px 24px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--gray);
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.3s;
        }
        
        .tab:hover {
            background: rgba(255, 255, 255, 0.05);
            color: white;
        }
        
        .tab.active {
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            color: white;
            border-color: transparent;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Forms */
        .form-container {
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 30px;
            max-width: 700px;
            margin: 0 auto;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            margin-bottom: 8px;
            color: white;
            font-weight: 500;
        }
        
        .form-input {
            width: 100%;
            padding: 14px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: white;
            font-size: 14px;
        }
        
        .form-input:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .form-textarea {
            width: 100%;
            padding: 14px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: white;
            font-size: 14px;
            min-height: 100px;
            resize: vertical;
        }
        
        .form-checkbox {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 15px 0;
        }
        
        /* Notification */
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 12px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            animation: slideIn 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .notification.success {
            background: linear-gradient(45deg, var(--success), var(--primary));
        }
        
        .notification.error {
            background: linear-gradient(45deg, var(--danger), var(--warning));
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 30px;
            color: var(--gray);
            font-size: 14px;
            border-top: 1px solid var(--border);
            margin-top: 50px;
        }
        
        .powered-by {
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 600;
            margin-top: 10px;
        }
        
        /* Advanced Settings */
        .advanced-settings {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .setting-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }
        
        .setting-item:last-child {
            border-bottom: none;
        }
        
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 24px;
        }
        
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 34px;
        }
        
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        
        input:checked + .toggle-slider {
            background-color: var(--primary);
        }
        
        input:checked + .toggle-slider:before {
            transform: translateX(26px);
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .dashboard {
                padding: 10px;
            }
            
            .header {
                flex-direction: column;
                gap: 15px;
                padding: 20px;
            }
            
            .api-grid {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .api-actions {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
                justify-content: center;
            }
        }
    </style>
    '''

def generate_api_card(api, host):
    enabled = api.get('enabled', True)
    requests = api.get('requests', 0)
    success_rate = api.get('success_rate', 100)
    hide_fields = api.get('hide_fields', [])
    show_powered_by = api.get('show_powered_by', True)
    
    return f'''
    <div class="api-card {'active' if enabled else 'disabled'}">
        <div class="api-header">
            <div>
                <div class="api-name">{api['name']}</div>
                <div style="color: var(--gray); font-size: 13px; margin-top: 5px;">
                    /{api['endpoint']}
                </div>
            </div>
            <span class="api-status {'status-active' if enabled else 'status-inactive'}">
                {'Active' if enabled else 'Inactive'}
            </span>
        </div>
        
        <div class="api-url">
            {host}/{api['endpoint']}?{api['param']}=value
        </div>
        
        <div class="api-meta">
            <span><i class="fas fa-key"></i> {api.get('api_key', 'N/A')}</span>
            <span><i class="fas fa-chart-line"></i> {requests} requests</span>
            <span><i class="fas fa-filter"></i> {len(hide_fields)} hidden fields</span>
            <span><i class="fas fa-bolt"></i> {'Powered' if show_powered_by else 'No tag'}</span>
        </div>
        
        <div class="advanced-settings">
            <div class="setting-item">
                <span>Hide Fields:</span>
                <span>{', '.join(hide_fields) if hide_fields else 'None'}</span>
            </div>
            <div class="setting-item">
                <span>Show "Powered by @frappeash":</span>
                <label class="toggle-switch">
                    <input type="checkbox" {'checked' if show_powered_by else ''} 
                           onchange="togglePoweredBy('{api['name']}', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
            {f'''
            <div class="setting-item">
                <span>Disabled Message:</span>
                <span style="color: var(--danger); font-size: 12px;">{api.get('disabled_message', 'API disabled')}</span>
            </div>
            ''' if not enabled else ''}
        </div>
        
        <div class="api-actions">
            <button class="btn btn-primary btn-sm" onclick="testAPI('{api['endpoint']}')">
                <i class="fas fa-play"></i> Test
            </button>
            <button class="btn btn-secondary btn-sm" onclick="copyAPIKey('{api.get('api_key', '')}')">
                <i class="fas fa-copy"></i> Copy Key
            </button>
            <button class="btn {'btn-danger' if enabled else 'btn-success'} btn-sm" 
                    onclick="toggleAPI('{api['name']}', {str(not enabled).lower()})">
                <i class="fas {'fa-toggle-on' if enabled else 'fa-toggle-off'}"></i> {'Disable' if enabled else 'Enable'}
            </button>
            <button class="btn btn-secondary btn-sm" onclick="showEditModal('{api['name']}')">
                <i class="fas fa-edit"></i> Edit
            </button>
            <button class="btn btn-danger btn-sm" onclick="deleteAPI('{api['name']}')">
                <i class="fas fa-trash"></i> Delete
            </button>
        </div>
    </div>
    '''

def generate_usage_stats():
    """Generate usage statistics HTML from Supabase"""
    analytics = get_analytics_summary()
    api_usage = analytics['api_usage']
    
    if not api_usage:
        return '<p style="color: var(--gray); text-align: center; padding: 20px;">No usage data available yet.</p>'
    
    html = '<div style="display: flex; flex-direction: column; gap: 15px;">'
    for api_name, stats in api_usage.items():
        total = stats['success'] + stats['failed']
        if total > 0:
            success_rate = (stats['success'] / total) * 100
            html += f'''
            <div style="background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="color: white;">{api_name}</span>
                    <span style="color: var(--success);">{success_rate:.1f}%</span>
                </div>
                <div style="display: flex; gap: 10px; font-size: 12px;">
                    <span style="color: var(--success);"><i class="fas fa-check"></i> {stats['success']} success</span>
                    <span style="color: var(--danger);"><i class="fas fa-times"></i> {stats['failed']} failed</span>
                    <span style="color: var(--gray);"><i class="fas fa-hashtag"></i> {total} total</span>
                </div>
            </div>
            '''
    html += '</div>'
    return html

def dashboard_html():
    apis = get_all_apis()
    total_apis = len(apis)
    enabled_apis = len([a for a in apis if a.get('enabled', True)])
    analytics = get_analytics_summary()
    total_requests = analytics['total_requests']
    success_rate = (analytics['successful_requests'] / total_requests * 100) if total_requests > 0 else 100
    host = request.host
    
    # Prepare apis data for JavaScript
    apis_json = json.dumps([
        {
            'name': api.get('name', ''),
            'hide_fields': api.get('hide_fields', []),
            'show_powered_by': api.get('show_powered_by', True),
            'disabled_message': api.get('disabled_message', 'API is currently disabled')
        }
        for api in apis
    ])
    
    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EncoreXOSINT | Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {get_dashboard_css()}
</head>
<body>
    <div class="dashboard">
        <!-- Header -->
        <div class="header">
            <div class="logo">
                <div class="logo-icon">
                    <i class="fas fa-bolt"></i>
                </div>
                <div>
                    <div class="logo-text">ENCOREXOSINT</div>
                    <div class="creator-tag">by @frappeash • t.me/frappeash</div>
                </div>
            </div>
            
            <div class="header-actions">
                <div style="display: flex; gap: 10px;">
                    <span style="background: rgba(255, 255, 255, 0.1); padding: 6px 12px; border-radius: 20px; font-size: 14px;">
                        <i class="fas fa-server"></i> {total_apis} APIs
                    </span>
                    <span style="background: rgba(0, 255, 136, 0.2); padding: 6px 12px; border-radius: 20px; font-size: 14px; color: var(--success);">
                        <i class="fas fa-signal"></i> {success_rate:.1f}% Success
                    </span>
                </div>
                <a href="/lwdalasan/logout" class="btn btn-secondary">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">
            <div class="tab active" onclick="showTab('overview')">
                <i class="fas fa-dashboard"></i> Overview
            </div>
            <div class="tab" onclick="showTab('apis')">
                <i class="fas fa-plug"></i> APIs
            </div>
            <div class="tab" onclick="showTab('create')">
                <i class="fas fa-plus-circle"></i> Create API
            </div>
            <div class="tab" onclick="showTab('analytics')">
                <i class="fas fa-chart-line"></i> Analytics
            </div>
        </div>
        
        <!-- Overview Tab -->
        <div id="overview" class="tab-content active">
            <h2 style="margin-bottom: 20px; color: white;">
                <i class="fas fa-dashboard"></i> System Overview
            </h2>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{total_apis}</div>
                    <div class="stat-label">Total APIs</div>
                    <div style="margin-top: 10px; font-size: 14px; color: var(--gray);">
                        {enabled_apis} active • {total_apis - enabled_apis} disabled
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number">{total_requests:,}</div>
                    <div class="stat-label">Total Requests</div>
                    <div style="margin-top: 10px; font-size: 14px; color: var(--gray);">
                        {analytics['successful_requests']:,} success • {analytics['failed_requests']:,} failed
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number">{success_rate:.1f}%</div>
                    <div class="stat-label">Success Rate</div>
                    <div style="margin-top: 10px;">
                        <div style="height: 6px; background: var(--border); border-radius: 3px; overflow: hidden;">
                            <div style="height: 100%; width: {success_rate}%; background: linear-gradient(90deg, var(--success), var(--primary));"></div>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number">24/7</div>
                    <div class="stat-label">Uptime</div>
                    <div style="margin-top: 10px; font-size: 14px; color: var(--gray);">
                        <i class="fas fa-check-circle" style="color: var(--success);"></i> All systems operational
                    </div>
                </div>
            </div>
            
            <div style="display: flex; gap: 15px; margin: 30px 0;">
                <button class="btn btn-primary" onclick="showTab('create')">
                    <i class="fas fa-plus"></i> New API
                </button>
                <button class="btn btn-secondary" onclick="testAllAPIs()">
                    <i class="fas fa-play"></i> Test All APIs
                </button>
                <button class="btn btn-secondary" onclick="refreshStats()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
            
            <h3 style="margin: 40px 0 20px 0; color: white;">
                <i class="fas fa-history"></i> Recent APIs
            </h3>
            
            <div class="api-grid">
                {''.join([generate_api_card(api, host) for api in apis[-3:]]) if apis else '''
                <div style="text-align: center; padding: 50px; color: var(--gray);">
                    <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 20px; opacity: 0.5;"></i>
                    <h3 style="color: white; margin-bottom: 10px;">No APIs Yet</h3>
                    <p>Create your first API to get started</p>
                    <button class="btn btn-primary" onclick="showTab('create')" style="margin-top: 20px;">
                        <i class="fas fa-plus"></i> Create First API
                    </button>
                </div>
                '''}
            </div>
        </div>
        
        <!-- APIs Tab -->
        <div id="apis" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
                <h2 style="color: white;">
                    <i class="fas fa-plug"></i> API Management
                </h2>
                <button class="btn btn-primary" onclick="showTab('create')">
                    <i class="fas fa-plus"></i> Add API
                </button>
            </div>
            
            <div class="api-grid">
                {''.join([generate_api_card(api, host) for api in apis]) if apis else '''
                <div style="text-align: center; padding: 80px; color: var(--gray);">
                    <i class="fas fa-api" style="font-size: 64px; margin-bottom: 20px; opacity: 0.5;"></i>
                    <h3 style="color: white; margin-bottom: 10px;">No APIs Found</h3>
                    <p>Start by creating your first API endpoint</p>
                </div>
                '''}
            </div>
        </div>
        
        <!-- Create API Tab -->
        <div id="create" class="tab-content">
            <div class="form-container">
                <h2 style="margin-bottom: 30px; color: white;">
                    <i class="fas fa-plus-circle"></i> Create New API
                </h2>
                
                <form id="create-api-form">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div class="form-group">
                            <label class="form-label">API Name</label>
                            <input type="text" name="name" placeholder="User Lookup" required class="form-input">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Endpoint</label>
                            <input type="text" name="endpoint" placeholder="user-lookup" required class="form-input">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Parameter Name</label>
                        <input type="text" name="param" placeholder="username" required class="form-input">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Base URL (Your API)</label>
                        <input type="text" name="baseUrl" placeholder="https://api.example.com/?key=YOUR_KEY&q=" required class="form-input">
                        <div style="font-size: 12px; color: var(--gray); margin-top: 5px;">
                            Your API URL with the parameter placeholder
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 30px 0;">
                        <div class="form-group">
                            <label class="form-label">Rate Limit/Hour</label>
                            <input type="number" name="rateLimit" value="1000" class="form-input">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Cache TTL (s)</label>
                            <input type="number" name="cacheTtl" value="300" class="form-input">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Timeout (s)</label>
                            <input type="number" name="timeout" value="10" class="form-input">
                        </div>
                    </div>
                    
                    <div class="advanced-settings">
                        <h3 style="color: white; margin-bottom: 15px;">
                            <i class="fas fa-cogs"></i> Advanced Settings
                        </h3>
                        
                        <div class="form-group">
                            <label class="form-label">Fields to Hide (comma separated)</label>
                            <input type="text" name="hideFields" placeholder="made_by, credits, author" class="form-input">
                            <div style="font-size: 12px; color: var(--gray); margin-top: 5px;">
                                These fields will be removed from the API response
                            </div>
                        </div>
                        
                        <div class="form-checkbox">
                            <input type="checkbox" name="showPoweredBy" id="showPoweredBy" checked>
                            <label for="showPoweredBy" style="color: white;">Show "API POWERED BY @FRAPPEASH" at the end of response</label>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Disabled Message (when API is turned off)</label>
                            <textarea name="disabledMessage" placeholder="This API is currently disabled for maintenance." class="form-textarea"></textarea>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 15px; margin-top: 30px;">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-check"></i> Create API
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="showTab('overview')">
                            <i class="fas fa-arrow-left"></i> Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- Analytics Tab -->
        <div id="analytics" class="tab-content">
            <div class="form-container">
                <h2 style="margin-bottom: 30px; color: white;">
                    <i class="fas fa-chart-line"></i> Analytics Dashboard
                </h2>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{analytics['total_requests']:,}</div>
                        <div class="stat-label">Total Requests</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-number">{analytics['successful_requests']:,}</div>
                        <div class="stat-label">Successful</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-number">{analytics['failed_requests']:,}</div>
                        <div class="stat-label">Failed</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-number">{success_rate:.1f}%</div>
                        <div class="stat-label">Success Rate</div>
                    </div>
                </div>
                
                <div style="margin-top: 40px;">
                    <h3 style="margin-bottom: 20px; color: white;">API Usage</h3>
                    <div style="background: rgba(0, 0, 0, 0.2); border-radius: 10px; padding: 20px;">
                        {generate_usage_stats()}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>EncoreXOSINT v2.0 • Created by @frappeash • t.me/frappeash</p>
            <p class="powered-by">
                <i class="fas fa-bolt"></i> API Gateway • <i class="fas fa-filter"></i> Response Filtering • <i class="fas fa-shield-alt"></i> Secure Proxy
            </p>
        </div>
    </div>
    
    <!-- Edit Modal -->
    <div id="editModal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.8); z-index: 1000; align-items: center; justify-content: center;">
        <div style="background: var(--glass); border: 1px solid var(--border); border-radius: 16px; padding: 30px; width: 90%; max-width: 500px;">
            <h2 style="color: white; margin-bottom: 20px;">
                <i class="fas fa-edit"></i> Edit API Settings
            </h2>
            
            <form id="edit-api-form">
                <input type="hidden" id="edit-api-name">
                
                <div class="form-group">
                    <label class="form-label">Fields to Hide (comma separated)</label>
                    <input type="text" id="edit-hide-fields" class="form-input">
                    <div style="font-size: 12px; color: var(--gray); margin-top: 5px;">
                        Example: made_by, credits, author, version
                    </div>
                </div>
                
                <div class="form-checkbox">
                    <input type="checkbox" id="edit-show-powered-by">
                    <label for="edit-show-powered-by" style="color: white;">Show "Powered by @frappeash" in response</label>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Disabled Message</label>
                    <textarea id="edit-disabled-message" class="form-textarea"></textarea>
                    <div style="font-size: 12px; color: var(--gray); margin-top: 5px;">
                        Message shown when API is disabled
                    </div>
                </div>
                
                <div style="display: flex; gap: 15px; margin-top: 30px;">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Save Changes
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="hideEditModal()">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
    // Store apis data
    const apis = {apis_json};
    
    // Tab Management
    function showTab(tabId) {{
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(tab => {{
            tab.classList.remove('active');
        }});
        
        // Remove active class from all tabs
        document.querySelectorAll('.tab').forEach(tab => {{
            tab.classList.remove('active');
        }});
        
        // Show selected tab
        document.getElementById(tabId).classList.add('active');
        
        // Add active class to clicked tab
        event.target.classList.add('active');
    }}
    
    // Create API Form
    document.getElementById('create-api-form').addEventListener('submit', async function(e) {{
        e.preventDefault();
        
        const formData = new FormData(this);
        const data = {{
            name: formData.get('name'),
            endpoint: formData.get('endpoint'),
            param: formData.get('param'),
            baseUrl: formData.get('baseUrl'),
            rateLimit: formData.get('rateLimit'),
            cacheTtl: formData.get('cacheTtl'),
            timeout: formData.get('timeout'),
            hideFields: formData.get('hideFields') ? formData.get('hideFields').split(',').map(f => f.trim()).filter(f => f) : [],
            showPoweredBy: document.getElementById('showPoweredBy').checked,
            disabledMessage: formData.get('disabledMessage') || 'API is currently disabled'
        }};
        
        const btn = this.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
        btn.disabled = true;
        
        try {{
            const response = await fetch('/lwdalasan/api/create', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(data)
            }});
            
            if (response.ok) {{
                showNotification('API created successfully!', 'success');
                setTimeout(() => {{
                    showTab('apis');
                    location.reload();
                }}, 1000);
            }} else {{
                const error = await response.json();
                throw new Error(error.error || 'Failed to create API');
            }}
        }} catch (error) {{
            showNotification(error.message, 'error');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }}
    }});
    
    // Edit Modal Functions
    function showEditModal(apiName) {{
        const api = apis.find(a => a.name === apiName);
        
        if (!api) return;
        
        document.getElementById('edit-api-name').value = apiName;
        document.getElementById('edit-hide-fields').value = api.hide_fields ? api.hide_fields.join(', ') : '';
        document.getElementById('edit-show-powered-by').checked = api.show_powered_by !== false;
        document.getElementById('edit-disabled-message').value = api.disabled_message || 'API is currently disabled';
        
        document.getElementById('editModal').style.display = 'flex';
    }}
    
    function hideEditModal() {{
        document.getElementById('editModal').style.display = 'none';
    }}
    
    document.getElementById('edit-api-form').addEventListener('submit', async function(e) {{
        e.preventDefault();
        
        const apiName = document.getElementById('edit-api-name').value;
        const data = {{
            hideFields: document.getElementById('edit-hide-fields').value.split(',').map(f => f.trim()).filter(f => f),
            showPoweredBy: document.getElementById('edit-show-powered-by').checked,
            disabledMessage: document.getElementById('edit-disabled-message').value
        }};
        
        const btn = this.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        btn.disabled = true;
        
        try {{
            const response = await fetch('/lwdalasan/api/update', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ name: apiName, ...data }})
            }});
            
            if (response.ok) {{
                showNotification('API settings updated!', 'success');
                setTimeout(() => {{
                    hideEditModal();
                    location.reload();
                }}, 1000);
            }} else {{
                const error = await response.json();
                throw new Error(error.error || 'Failed to update API');
            }}
        }} catch (error) {{
            showNotification(error.message, 'error');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }}
    }});
    
    // API Functions
    async function toggleAPI(name, enabled) {{
        try {{
            const response = await fetch('/lwdalasan/api/toggle', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ name: name, enabled: enabled }})
            }});
            
            if (response.ok) {{
                showNotification('API ' + (enabled ? 'enabled' : 'disabled') + ' successfully!', 'success');
                setTimeout(() => location.reload(), 500);
            }}
        }} catch (error) {{
            showNotification('Error updating API', 'error');
        }}
    }}
    
    async function togglePoweredBy(name, enabled) {{
        try {{
            const response = await fetch('/lwdalasan/api/update', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ 
                    name: name, 
                    showPoweredBy: enabled 
                }})
            }});
            
            if (response.ok) {{
                showNotification('"Powered by @frappeash" ' + (enabled ? 'enabled' : 'disabled') + '!', 'success');
                setTimeout(() => location.reload(), 500);
            }}
        }} catch (error) {{
            showNotification('Error updating setting', 'error');
        }}
    }}
    
    async function deleteAPI(name) {{
        if (!confirm('Delete "' + name + '"? This action cannot be undone.')) return;
        
        try {{
            const response = await fetch('/lwdalasan/api/delete', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ name: name }})
            }});
            
            if (response.ok) {{
                showNotification('API deleted successfully!', 'success');
                setTimeout(() => location.reload(), 500);
            }}
        }} catch (error) {{
            showNotification('Error deleting API', 'error');
        }}
    }}
    
    function copyAPIKey(key) {{
        navigator.clipboard.writeText(key);
        showNotification('API key copied to clipboard!', 'success');
    }}
    
    function testAPI(endpoint) {{
        const url = window.location.origin + '/' + endpoint + '?test=1';
        window.open(url, '_blank');
    }}
    
    // Utility Functions
    function showNotification(message, type) {{
        // Remove existing notification
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();
        
        const notification = document.createElement('div');
        notification.className = 'notification ' + type;
        
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'error') icon = 'exclamation-circle';
        
        notification.innerHTML = '<i class="fas fa-' + icon + '"></i> ' + message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {{
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }}, 3000);
    }}
    
    // Quick Actions
    function testAllAPIs() {{
        showNotification('Testing all APIs... This may take a moment.', 'success');
    }}
    
    function refreshStats() {{
        location.reload();
    }}
    
    // Initialize
    document.addEventListener('DOMContentLoaded', () => {{
        // Initialize first tab
        showTab('overview');
        
        // Add animation styles
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideOut {{
                from {{ transform: translateX(0); opacity: 1; }}
                to {{ transform: translateX(100%); opacity: 0; }}
            }}
        `;
        document.head.appendChild(style);
        
        // Close modal on outside click
        document.getElementById('editModal').addEventListener('click', function(e) {{
            if (e.target === this) hideEditModal();
        }});
    }});
    </script>
</body>
</html>
'''

# ========== ROUTES ==========
@app.route('/')
def home():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EncoreXOSINT | API Gateway</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            text-align: center;
        }
        
        .hero {
            max-width: 800px;
            margin: 0 auto;
        }
        
        .logo {
            font-size: 64px;
            font-weight: 800;
            background: linear-gradient(45deg, #00dbde, #fc00ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }
        
        .creator {
            font-size: 18px;
            color: #00dbde;
            margin-bottom: 40px;
        }
        
        .tagline {
            font-size: 20px;
            color: #94a3b8;
            margin-bottom: 40px;
            max-width: 600px;
        }
        
        .cta-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin: 40px 0;
        }
        
        .btn {
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 16px;
            text-decoration: none;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #00dbde, #fc00ff);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0, 219, 222, 0.3);
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            margin-top: 60px;
            max-width: 1000px;
        }
        
        .feature-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 30px;
            text-align: center;
        }
        
        .feature-icon {
            font-size: 40px;
            background: linear-gradient(45deg, #00dbde, #fc00ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }
        
        .feature-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 10px;
            color: white;
        }
        
        .feature-desc {
            color: #94a3b8;
            font-size: 14px;
        }
        
        .footer {
            margin-top: 60px;
            color: #64748b;
            font-size: 14px;
        }
        
        .powered-by {
            color: #00dbde;
            font-weight: 600;
            margin-top: 10px;
        }
        
        @media (max-width: 768px) {
            .logo {
                font-size: 48px;
            }
            
            .cta-buttons {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
                justify-content: center;
            }
            
            .features {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="hero">
        <div class="logo">
            <i class="fas fa-bolt"></i> ENCOREXOSINT
        </div>
        
        <div class="creator">
            <i class="fas fa-code"></i> Created by @frappeash • t.me/frappeash
        </div>
        
        <p class="tagline">
            Advanced API Gateway with response filtering, API masking, and real-time analytics.
            Protect your APIs and customize responses with ease.
        </p>
        
        <div class="cta-buttons">
            <a href="/lwdalasan" class="btn btn-primary">
                <i class="fas fa-terminal"></i> Launch Dashboard
            </a>
        </div>
        
        <div class="features">
            <div class="feature-card">
                <div class="feature-icon">
                    <i class="fas fa-filter"></i>
                </div>
                <h3 class="feature-title">Response Filtering</h3>
                <p class="feature-desc">Hide specific fields like "made_by", "credits" from API responses</p>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">
                    <i class="fas fa-bolt"></i>
                </div>
                <h3 class="feature-title">Powered by Tag</h3>
                <p class="feature-desc">Toggle "API POWERED BY @FRAPPEASH" at the end of responses</p>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">
                    <i class="fas fa-toggle-off"></i>
                </div>
                <h3 class="feature-title">Custom Disabled Messages</h3>
                <p class="feature-desc">Set custom messages when APIs are disabled</p>
            </div>
        </div>
        
        <div class="footer">
            <p>EncoreXOSINT v2.0 • Advanced API Gateway System</p>
            <p class="powered-by">
                <i class="fas fa-bolt"></i> API Masking • <i class="fas fa-filter"></i> Response Filter • <i class="fas fa-chart-line"></i> Analytics
            </p>
        </div>
    </div>
</body>
</html>
'''

@app.route('/lwdalasan')
def admin_panel():
    if not check_auth(request):
        return login_html()
    return dashboard_html()

@app.route('/lwdalasan/login', methods=['POST'])
def admin_login():
    passkey = request.form.get('passkey')
    
    if verify_passkey(passkey):
        token = create_token('admin')
        resp = make_response(redirect('/lwdalasan'))
        resp.set_cookie('encore_token', token, max_age=259200, httponly=True, secure=False)
        return resp
    else:
        return login_html(error=True)

@app.route('/lwdalasan/logout')
def admin_logout():
    resp = make_response(redirect('/lwdalasan'))
    resp.set_cookie('encore_token', '', expires=0)
    return resp

@app.route('/lwdalasan/api/toggle', methods=['POST'])
def api_toggle():
    if not check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    name = data.get('name')
    enabled = data.get('enabled')
    
    update_api(name, {'enabled': enabled})
    return jsonify({'success': True})

@app.route('/lwdalasan/api/create', methods=['POST'])
def api_create():
    if not check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        name = data.get('name')
        endpoint = data.get('endpoint')
        
        # Check if API with same name or endpoint exists
        existing_apis = get_all_apis()
        for api in existing_apis:
            if api.get('name') == name:
                return jsonify({'error': 'API with this name already exists'}), 400
            if api.get('endpoint') == endpoint:
                return jsonify({'error': 'API with this endpoint already exists'}), 400
        
        # Create the API
        new_api = create_api(data)
        return jsonify({'success': True, 'message': 'API created successfully', 'api': new_api})
        
    except Exception as e:
        print(f"Error in api_create: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/lwdalasan/api/update', methods=['POST'])
def api_update():
    if not check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    name = data.get('name')
    hide_fields = data.get('hideFields')
    show_powered_by = data.get('showPoweredBy')
    disabled_message = data.get('disabledMessage')
    
    updates = {}
    
    if hide_fields is not None:
        updates['hideFields'] = hide_fields
    
    if show_powered_by is not None:
        updates['showPoweredBy'] = show_powered_by
    
    if disabled_message is not None:
        updates['disabledMessage'] = disabled_message
    
    result = update_api(name, updates)
    if result:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update API'}), 500

@app.route('/lwdalasan/api/delete', methods=['POST'])
def api_delete():
    if not check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    name = data.get('name')
    
    result = delete_api(name)
    if result is not None:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to delete API'}), 500

@app.route('/<path:api_path>')
def handle_api_request(api_path):
    """API Gateway - Masks your API endpoints"""
    # Find API in Supabase
    api = get_api_by_endpoint(api_path)
    
    if not api:
        return jsonify({
            'error': 'API endpoint not found',
            'code': 404
        }), 404
    
    # Check if API is disabled
    if not api.get('enabled', True):
        disabled_message = api.get('disabled_message', 'API is currently disabled')
        return jsonify({
            'error': 'API is temporarily unavailable',
            'message': disabled_message,
            'code': 503
        }), 503
    
    param_name = api['param']
    param_value = request.args.get(param_name)
    
    if not param_value:
        return jsonify({
            'error': f'Missing required parameter: {param_name}',
            'code': 400
        }), 400
    
    # Construct the target URL (API Masking happens here)
    target_url = f"{api['base_url']}{urllib.parse.quote(param_value)}"
    
    # Add query parameters from original request (except our param)
    query_params = dict(request.args)
    if param_name in query_params:
        del query_params[param_name]
    
    if query_params:
        target_url += ('&' if '?' in target_url else '?') + urllib.parse.urlencode(query_params)
    
    try:
        response = requests.get(
            target_url, 
            timeout=api.get('timeout', 10), 
            headers={
                'User-Agent': 'EncoreXOSINT/2.0',
                'X-API-Key': api.get('api_key', ''),
                'X-Forwarded-For': request.remote_addr
            }
        )
        
        # Update statistics in Supabase
        record_analytics(api['name'], True)
        increment_api_requests(api['name'])
        
        # Process response
        if 'application/json' in response.headers.get('content-type', ''):
            try:
                response_data = response.json()
                
                # Remove hidden fields
                hide_fields = api.get('hide_fields', [])
                if hide_fields:
                    response_data = clean_response_data(response_data, hide_fields)
                
                # Add powered by tag if enabled
                if api.get('show_powered_by', True):
                    if isinstance(response_data, dict):
                        response_data['_powered_by'] = 'API POWERED BY @FRAPPEASH'
                    elif isinstance(response_data, list):
                        # For array responses, wrap in object
                        return jsonify({
                            'data': response_data,
                            '_powered_by': 'API POWERED BY @FRAPPEASH'
                        })
                
                return jsonify(response_data)
                
            except:
                # If JSON parsing fails, return as text
                return response.text
        else:
            return response.text
        
    except Exception as e:
        # Update statistics in Supabase
        record_analytics(api['name'], False)
        
        return jsonify({
            'error': 'API request failed',
            'details': 'lumdkuchnhi',
            'code': 500
        }), 500
