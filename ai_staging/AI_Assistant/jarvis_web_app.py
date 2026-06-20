from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import os
import json
import threading
import time
from datetime import datetime

# Import your existing modules
try:
    from jarvis_brain import JarvisBrain
    from voice_auth import authenticate_user_text, load_users, save_users, hash_password
    from enhanced_tts import speak
    from stt import listen
except ImportError:
    # Fallback functions if modules not available
    def speak(text): print(f"TTS: {text}")
    def listen(): return input("Voice input: ")
    class JarvisBrain:
        def analyze_intent(self, text): return "general"
        def generate_response(self, intent, text): return "I understand sir"
    def load_users(): return {}
    def save_users(users): pass
    def hash_password(password): return password

def register_user_text_only(username, password):
    """Register user without voice samples for the web flow."""
    if not username or not password:
        return False, "All fields required"

    users = load_users()
    if username in users:
        return False, "User already exists"

    users[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "voice_samples": [],
        "created_at": time.time(),
        "login_attempts": 0,
        "account_locked": False
    }
    save_users(users)
    return True, "Registration successful"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, 'ui')

app = Flask(__name__, static_folder=UI_DIR, static_url_path='', template_folder=UI_DIR)
app.config['SECRET_KEY'] = 'jarvis_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
active_sessions = {}
jarvis_brain = JarvisBrain()

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['user'])

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def authenticate():
    data = request.get_json()
    action = data.get('action')
    
    if action == 'login':
        username = data.get('username') or data.get('email')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'message': 'All fields required'})

        if authenticate_user_text(username, password):
            session['user'] = username
            return jsonify({'success': True, 'message': f'Welcome back {username}', 'redirect': '/'})
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    elif action == 'register':
        name = data.get('name')
        username = data.get('username') or data.get('email')
        password = data.get('password')

        success, message = register_user_text_only(username, password)
        if success:
            session['user'] = username
            return jsonify({'success': True, 'message': f'Registration successful. Welcome {name}', 'redirect': '/'})
        return jsonify({'success': False, 'message': message})
    
    return jsonify({'success': False, 'message': 'Invalid request'})

@socketio.on('connect')
def handle_connect():
    if 'user' in session:
        username = session['user']
        active_sessions[request.sid] = username
        emit('status', {'message': f'Connected as {username}'})
        speak(f"Welcome back {username} sir")

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_sessions:
        del active_sessions[request.sid]

@socketio.on('send_message')
def handle_message(data):
    if request.sid not in active_sessions:
        return
    
    username = active_sessions[request.sid]
    message = data.get('message', '').strip()
    
    if not message:
        return
    
    # Emit user message
    emit('new_message', {
        'sender': 'user',
        'message': message,
        'timestamp': datetime.now().strftime('%H:%M')
    })
    
    # Process with JARVIS brain
    try:
        intent = jarvis_brain.analyze_intent(message)
        response = process_command(message, intent)
        
        # Emit AI response
        emit('new_message', {
            'sender': 'ai',
            'message': response,
            'timestamp': datetime.now().strftime('%H:%M')
        })
        
        # Speak response
        threading.Thread(target=speak, args=(response,), daemon=True).start()
        
    except Exception as e:
        emit('new_message', {
            'sender': 'ai',
            'message': 'Sorry sir, I encountered an error processing your request',
            'timestamp': datetime.now().strftime('%H:%M')
        })

def process_command(message, intent):
    """Process user command and return response"""
    message_lower = message.lower()
    
    if "time" in message_lower:
        current_time = datetime.now().strftime("%I:%M %p")
        return f"It's {current_time} sir"
    
    elif "weather" in message_lower:
        return "Checking weather for you sir. Opening weather service"
    
    elif "music" in message_lower:
        return "Playing music sir. Opening Spotify"
    
    elif "search" in message_lower or "google" in message_lower:
        query = message_lower.replace("search", "").replace("google", "").strip()
        return f"Searching for '{query}' sir"
    
    elif "shutdown" in message_lower or "goodbye" in message_lower:
        return "Goodbye sir, have a great day!"
    
    elif "hello" in message_lower or "hi" in message_lower:
        return "Hello sir! How can I assist you today?"
    
    else:
        try:
            return jarvis_brain.generate_response(intent, message)
        except:
            return "I understand sir. How else can I help you?"

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
