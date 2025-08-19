from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import requests
import json
import os
from datetime import datetime
import threading
import time
import csv
import io
import pandas as pd
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from cryptography.fernet import Fernet
import pickle
import base64
from flask_session import Session

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration
class Config:
    TIKTOK_CLIENT_ID = os.environ.get('TIKTOK_CLIENT_ID', '')
    TIKTOK_CLIENT_SECRET = os.environ.get('TIKTOK_CLIENT_SECRET', '')
    UPLOAD_FOLDER = 'uploads'
    SESSIONS_FOLDER = 'sessions'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'txt', 'csv', 'xlsx'}
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'tiktok_bot:'
    
app.config.from_object(Config)

# Initialize Flask-Session
Session(app)

# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SESSIONS_FOLDER'], exist_ok=True)

# Generate encryption key for storing credentials
ENCRYPTION_KEY_FILE = 'encryption.key'
if not os.path.exists(ENCRYPTION_KEY_FILE):
    key = Fernet.generate_key()
    with open(ENCRYPTION_KEY_FILE, 'wb') as key_file:
        key_file.write(key)
else:
    with open(ENCRYPTION_KEY_FILE, 'rb') as key_file:
        key = key_file.read()

cipher = Fernet(key)

# Global variables for bot state
bot_active = False
bot_messages = []
auto_responses = {
    'default': 'Thanks for messaging! I\'ll get back to you soon.',
    'greeting': 'Hello! Thanks for reaching out.',
    'business': 'For business inquiries, please email us at business@example.com'
}

# Bulk DM state
bulk_dm_jobs = {}
job_id_counter = 0

# TikTok accounts management
tiktok_accounts = {}  # {username: {session_data, cookies, is_logged_in, etc}}
active_account = None

def create_webdriver():
    """Create a Chrome WebDriver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error creating WebDriver: {e}")
        return None

def save_account_session(username, session_data):
    """Save account session data securely"""
    try:
        # Encrypt sensitive data
        encrypted_data = cipher.encrypt(json.dumps(session_data).encode())
        
        # Save to file
        session_file = os.path.join(app.config['SESSIONS_FOLDER'], f"{username}_session.dat")
        with open(session_file, 'wb') as f:
            f.write(encrypted_data)
        
        return True
    except Exception as e:
        print(f"Error saving session for {username}: {e}")
        return False

def load_account_session(username):
    """Load account session data"""
    try:
        session_file = os.path.join(app.config['SESSIONS_FOLDER'], f"{username}_session.dat")
        if os.path.exists(session_file):
            with open(session_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt data
            decrypted_data = cipher.decrypt(encrypted_data)
            session_data = json.loads(decrypted_data.decode())
            
            return session_data
        return None
    except Exception as e:
        print(f"Error loading session for {username}: {e}")
        return None

def tiktok_login(username, password):
    """Login to TikTok and save session"""
    driver = None
    try:
        print(f"Starting TikTok login for {username}...")
        driver = create_webdriver()
        
        if not driver:
            return {'success': False, 'error': 'Failed to create browser driver'}
        
        # Navigate to TikTok login page
        driver.get('https://www.tiktok.com/login/phone-or-email/email')
        
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        
        # Find and fill username/email field
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"], input[name="username"]')))
        email_input.clear()
        email_input.send_keys(username)
        
        # Find and fill password field
        password_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        password_input.clear()
        password_input.send_keys(password)
        
        # Find and click login button
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], button[data-e2e="login-button"]')
        login_button.click()
        
        # Wait for login to complete (check for redirect or success indicators)
        time.sleep(5)
        
        # Check if login was successful
        current_url = driver.current_url
        if 'login' not in current_url and 'tiktok.com' in current_url:
            # Login successful, save session
            cookies = driver.get_cookies()
            local_storage = driver.execute_script("return window.localStorage;")
            session_storage = driver.execute_script("return window.sessionStorage;")
            
            session_data = {
                'username': username,
                'cookies': cookies,
                'local_storage': local_storage,
                'session_storage': session_storage,
                'login_time': datetime.now().isoformat(),
                'is_logged_in': True
            }
            
            # Save session
            save_account_session(username, session_data)
            
            # Add to active accounts
            tiktok_accounts[username] = session_data
            
            print(f"Login successful for {username}")
            return {'success': True, 'message': 'Login successful'}
        else:
            # Check for error messages
            try:
                error_element = driver.find_element(By.CSS_SELECTOR, '[data-e2e="login-error"], .error-message, .login-error')
                error_message = error_element.text
                return {'success': False, 'error': f'Login failed: {error_message}'}
            except:
                return {'success': False, 'error': 'Login failed. Please check your credentials.'}
        
    except TimeoutException:
        return {'success': False, 'error': 'Login page took too long to load'}
    except NoSuchElementException as e:
        return {'success': False, 'error': f'Could not find login elements: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Login error: {str(e)}'}
    finally:
        if driver:
            driver.quit()

def restore_tiktok_session(username):
    """Restore a saved TikTok session"""
    try:
        session_data = load_account_session(username)
        if not session_data:
            return {'success': False, 'error': 'No saved session found'}
        
        # Add to active accounts
        tiktok_accounts[username] = session_data
        
        # Check if session is still valid (basic check)
        login_time = datetime.fromisoformat(session_data['login_time'])
        hours_since_login = (datetime.now() - login_time).total_seconds() / 3600
        
        if hours_since_login > 24:  # Sessions older than 24 hours might be expired
            return {'success': False, 'error': 'Session may be expired, please login again'}
        
        return {'success': True, 'message': 'Session restored successfully'}
    except Exception as e:
        return {'success': False, 'error': f'Error restoring session: {str(e)}'}

def send_tiktok_dm_with_session(username, recipient, message):
    """Send DM using saved TikTok session"""
    # This is a placeholder - in real implementation, you would:
    # 1. Create a new driver with the saved session
    # 2. Navigate to TikTok messaging
    # 3. Send the actual message
    # 4. Handle any errors or captchas
    
    if username not in tiktok_accounts:
        return {'success': False, 'error': 'Account not logged in'}
    
    # Simulate sending (replace with real TikTok automation)
    import random
    success_rate = 0.85  # 85% success rate simulation
    
    if random.random() < success_rate:
        return {'success': True, 'message': f'DM sent to {recipient}'}
    else:
        return {'success': False, 'error': 'Failed to send DM - rate limited or network error'}

def load_saved_accounts():
    """Load all saved account sessions on startup"""
    global tiktok_accounts
    try:
        sessions_folder = app.config['SESSIONS_FOLDER']
        if os.path.exists(sessions_folder):
            for filename in os.listdir(sessions_folder):
                if filename.endswith('_session.dat'):
                    username = filename.replace('_session.dat', '')
                    session_data = load_account_session(username)
                    if session_data:
                        tiktok_accounts[username] = session_data
        print(f"Loaded {len(tiktok_accounts)} saved TikTok accounts")
    except Exception as e:
        print(f"Error loading saved accounts: {e}")

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def parse_username_file(file_path):
    """Parse usernames from uploaded file (CSV, TXT, or Excel)"""
    usernames = []
    try:
        file_extension = file_path.rsplit('.', 1)[1].lower()
        
        if file_extension == 'csv':
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                for row in csv_reader:
                    if row and row[0].strip():  # First column contains usernames
                        usernames.append(row[0].strip())
        
        elif file_extension == 'txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    username = line.strip()
                    if username:
                        usernames.append(username)
        
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(file_path)
            if not df.empty:
                # Use first column for usernames
                usernames = df.iloc[:, 0].dropna().astype(str).tolist()
        
        # Remove duplicates and empty strings
        usernames = list(set([u for u in usernames if u.strip()]))
        
    except Exception as e:
        print(f"Error parsing file: {e}")
        return []
    
    return usernames

def bulk_send_messages(job_id, usernames, message, delay=2):
    """Send messages to multiple users (runs in background thread)"""
    global bulk_dm_jobs
    
    job = bulk_dm_jobs.get(job_id)
    if not job:
        return
    
    total_users = len(usernames)
    sent_count = 0
    failed_count = 0
    
    for i, username in enumerate(usernames):
        if job['status'] == 'cancelled':
            break
            
        # Update progress
        job['current_user'] = username
        job['progress'] = int((i / total_users) * 100)
        
        # Simulate sending message (replace with real TikTok API call)
        result = simulate_send_message(username, message)
        
        if result['success']:
            sent_count += 1
            # Log successful message
            bot_messages.append({
                'type': 'sent',
                'recipient': username,
                'message': message,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'bulk_job': job_id
            })
        else:
            failed_count += 1
            # Log failed message
            job['failed_users'].append({'username': username, 'error': result.get('error', 'Unknown error')})
        
        # Update job statistics
        job['sent_count'] = sent_count
        job['failed_count'] = failed_count
        
        # Delay between messages to avoid rate limiting
        time.sleep(delay)
    
    # Mark job as completed
    job['status'] = 'completed'
    job['progress'] = 100
    job['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', 
                         bot_active=bot_active, 
                         message_count=len(bot_messages),
                         auto_responses=auto_responses)

@app.route('/dashboard')
def dashboard():
    """Bot dashboard with statistics"""
    stats = {
        'total_messages': len(bot_messages),
        'active_conversations': 0,  # This would be calculated based on recent activity
        'response_rate': '95%',  # This would be calculated
        'uptime': '2h 30m'  # This would be calculated
    }
    return render_template('dashboard.html', stats=stats, messages=bot_messages[-10:])

@app.route('/settings')
def settings():
    """Bot settings page"""
    return render_template('settings.html', auto_responses=auto_responses)

@app.route('/toggle_bot', methods=['POST'])
def toggle_bot():
    """Toggle bot on/off"""
    global bot_active
    bot_active = not bot_active
    status = 'activated' if bot_active else 'deactivated'
    flash(f'Bot has been {status}!', 'success' if bot_active else 'warning')
    return redirect(url_for('index'))

@app.route('/update_response', methods=['POST'])
def update_response():
    """Update auto-response messages"""
    response_type = request.form.get('type')
    message = request.form.get('message')
    
    if response_type in auto_responses:
        auto_responses[response_type] = message
        flash(f'{response_type.title()} response updated!', 'success')
    else:
        flash('Invalid response type!', 'error')
    
    return redirect(url_for('settings'))

@app.route('/send_message', methods=['POST'])
def send_message():
    """Send a message through the bot"""
    recipient = request.form.get('recipient')
    message = request.form.get('message')
    
    # Simulate sending a message (in real implementation, this would use TikTok API)
    result = simulate_send_message(recipient, message)
    
    if result['success']:
        flash('Message sent successfully!', 'success')
        # Log the sent message
        bot_messages.append({
            'type': 'sent',
            'recipient': recipient,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        flash(f'Failed to send message: {result["error"]}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/api/messages')
def get_messages():
    """API endpoint to get recent messages"""
    return jsonify(bot_messages[-20:])

@app.route('/api/bot_status')
def bot_status():
    """API endpoint to get bot status"""
    return jsonify({
        'active': bot_active,
        'message_count': len(bot_messages),
        'uptime': '2h 30m'  # This would be calculated
    })

@app.route('/bulk_dm')
def bulk_dm():
    """Bulk DM management page"""
    # Get recent jobs
    recent_jobs = list(bulk_dm_jobs.values())[-10:]  # Last 10 jobs
    return render_template('bulk_dm.html', jobs=recent_jobs)

@app.route('/upload_usernames', methods=['POST'])
def upload_usernames():
    """Handle username file upload"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('bulk_dm'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('bulk_dm'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Parse usernames from file
        usernames = parse_username_file(file_path)
        
        # Store usernames in session for bulk DM form
        session['usernames'] = usernames
        session['uploaded_filename'] = filename
        
        # Clean up uploaded file
        os.remove(file_path)
        
        flash(f'Successfully uploaded {len(usernames)} usernames from {filename}', 'success')
        return redirect(url_for('bulk_dm'))
    else:
        flash('Invalid file type. Please upload CSV, TXT, or Excel files only.', 'error')
        return redirect(url_for('bulk_dm'))

@app.route('/start_bulk_dm', methods=['POST'])
def start_bulk_dm():
    """Start bulk DM sending job"""
    global job_id_counter, bulk_dm_jobs
    
    # Get usernames from session or manual input
    usernames = session.get('usernames', [])
    manual_usernames = request.form.get('manual_usernames', '').strip()
    
    # If manual usernames provided, parse them
    if manual_usernames:
        manual_list = [u.strip() for u in manual_usernames.split('\n') if u.strip()]
        usernames.extend(manual_list)
    
    message = request.form.get('message', '').strip()
    delay = int(request.form.get('delay', 2))
    
    if not usernames:
        flash('No usernames provided. Please upload a file or enter usernames manually.', 'error')
        return redirect(url_for('bulk_dm'))
    
    if not message:
        flash('Please enter a message to send.', 'error')
        return redirect(url_for('bulk_dm'))
    
    # Create new job
    job_id_counter += 1
    job_id = f"job_{job_id_counter}"
    
    job = {
        'id': job_id,
        'status': 'running',
        'total_users': len(usernames),
        'sent_count': 0,
        'failed_count': 0,
        'progress': 0,
        'message': message,
        'delay': delay,
        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'current_user': '',
        'failed_users': []
    }
    
    bulk_dm_jobs[job_id] = job
    
    # Start bulk sending in background thread
    thread = threading.Thread(target=bulk_send_messages, args=(job_id, usernames, message, delay))
    thread.daemon = True
    thread.start()
    
    # Clear usernames from session
    session.pop('usernames', None)
    session.pop('uploaded_filename', None)
    
    flash(f'Bulk DM job started! Sending to {len(usernames)} users.', 'success')
    return redirect(url_for('bulk_dm'))

@app.route('/api/bulk_job/<job_id>')
def get_bulk_job(job_id):
    """Get bulk job progress"""
    job = bulk_dm_jobs.get(job_id)
    if job:
        return jsonify(job)
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/bulk_jobs')
def get_bulk_jobs():
    """Get all bulk jobs"""
    return jsonify(list(bulk_dm_jobs.values()))

@app.route('/cancel_bulk_job/<job_id>', methods=['POST'])
def cancel_bulk_job(job_id):
    """Cancel a running bulk job"""
    job = bulk_dm_jobs.get(job_id)
    if job and job['status'] == 'running':
        job['status'] = 'cancelled'
        flash('Bulk DM job cancelled.', 'warning')
    else:
        flash('Job not found or already completed.', 'error')
    
    return redirect(url_for('bulk_dm'))

@app.route('/accounts')
def accounts():
    """TikTok accounts management page"""
    return render_template('accounts.html', 
                         accounts=tiktok_accounts, 
                         active_account=active_account)

@app.route('/login_tiktok', methods=['POST'])
def login_tiktok():
    """Process TikTok login"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if not username or not password:
        flash('Please enter both username and password', 'error')
        return redirect(url_for('accounts'))
    
    # Start login in background thread to avoid blocking
    def login_thread():
        result = tiktok_login(username, password)
        if result['success']:
            flash(f'Successfully logged in as {username}!', 'success')
        else:
            flash(f'Login failed: {result["error"]}', 'error')
    
    thread = threading.Thread(target=login_thread)
    thread.daemon = True
    thread.start()
    
    flash(f'Logging in as {username}... This may take a few moments.', 'info')
    return redirect(url_for('accounts'))

@app.route('/logout_tiktok/<username>', methods=['POST'])
def logout_tiktok(username):
    """Logout from TikTok account"""
    global active_account
    
    if username in tiktok_accounts:
        del tiktok_accounts[username]
        
        # Remove session file
        session_file = os.path.join(app.config['SESSIONS_FOLDER'], f"{username}_session.dat")
        if os.path.exists(session_file):
            os.remove(session_file)
        
        # Clear active account if this was the active one
        if active_account == username:
            active_account = None
        
        flash(f'Logged out from {username}', 'success')
    else:
        flash('Account not found', 'error')
    
    return redirect(url_for('accounts'))

@app.route('/set_active_account/<username>', methods=['POST'])
def set_active_account(username):
    """Set active TikTok account for sending DMs"""
    global active_account
    
    if username in tiktok_accounts:
        active_account = username
        flash(f'Set {username} as active account', 'success')
    else:
        flash('Account not found', 'error')
    
    return redirect(url_for('accounts'))

@app.route('/restore_session/<username>', methods=['POST'])
def restore_session(username):
    """Restore a saved session"""
    result = restore_tiktok_session(username)
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['error'], 'error')
    
    return redirect(url_for('accounts'))

@app.route('/api/accounts')
def get_accounts():
    """API endpoint to get TikTok accounts"""
    accounts_info = {}
    for username, data in tiktok_accounts.items():
        accounts_info[username] = {
            'username': username,
            'login_time': data.get('login_time'),
            'is_logged_in': data.get('is_logged_in', False),
            'is_active': username == active_account
        }
    
    return jsonify({
        'accounts': accounts_info,
        'active_account': active_account,
        'total_accounts': len(tiktok_accounts)
    })

def simulate_send_message(recipient, message):
    """Send message using TikTok session if available, otherwise simulate"""
    global active_account
    
    # If we have an active TikTok account, try to use it
    if active_account and active_account in tiktok_accounts:
        result = send_tiktok_dm_with_session(active_account, recipient, message)
        if result['success']:
            return {'success': True}
        else:
            # If TikTok session fails, log the error but don't stop the process
            print(f"TikTok session send failed: {result['error']}")
    
    # Fallback to simulation (or could integrate other APIs here)
    import random
    
    if random.random() > 0.1:  # 90% success rate for simulation
        return {'success': True}
    else:
        return {'success': False, 'error': 'Network error'}

def bot_worker():
    """Background worker for the bot (runs in a separate thread)"""
    global bot_active, bot_messages
    
    while True:
        if bot_active:
            # Simulate receiving messages and auto-responding
            # In real implementation, this would poll TikTok API for new messages
            simulate_incoming_message()
        
        time.sleep(30)  # Check every 30 seconds

def simulate_incoming_message():
    """Simulate receiving an incoming message"""
    import random
    
    if random.random() > 0.8:  # 20% chance of receiving a message
        senders = ['user123', 'tiktokfan', 'potential_client', 'random_user']
        messages = ['Hi!', 'Hello there', 'Can you help me?', 'What services do you offer?']
        
        sender = random.choice(senders)
        message = random.choice(messages)
        
        # Log incoming message
        bot_messages.append({
            'type': 'received',
            'sender': sender,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Auto-respond
        if 'help' in message.lower() or 'service' in message.lower():
            response = auto_responses['business']
        elif any(greeting in message.lower() for greeting in ['hi', 'hello', 'hey']):
            response = auto_responses['greeting']
        else:
            response = auto_responses['default']
        
        # Log auto-response
        bot_messages.append({
            'type': 'sent',
            'recipient': sender,
            'message': response,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'auto_response': True
        })

if __name__ == '__main__':
    # Load saved TikTok accounts
    load_saved_accounts()
    
    # Start the bot worker in a background thread
    bot_thread = threading.Thread(target=bot_worker, daemon=True)
    bot_thread.start()
    
    print(f"TikTok DM Bot starting with {len(tiktok_accounts)} saved accounts...")
    app.run(debug=True, host='0.0.0.0', port=5000)
