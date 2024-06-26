# app.py

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import find_dotenv, load_dotenv
from langchain_community.llms import OpenAI
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
import requests
import pygame.mixer
import os

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')  # Secret key for session management

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Mock database
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

users = {
    "1": User("1", "expert", generate_password_hash("expert99."))
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

# Define route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        for user in users.values():
            if user.username == username and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

# Define route for logout
@app.route('/logout')
@login_required  # Ensure the user is logged in to access this route
def logout():
    logout_user()
    return redirect(url_for('login'))

# Define route for signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        user_id = str(len(users) + 1)
        new_user = User(user_id, username, password_hash)
        users[user_id] = new_user
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('signup.html')

# Home route
@app.route("/")
@login_required  # Ensure the user is logged in to access this route
def home():
    return render_template("index.html")

# Route to handle AI interaction
@app.route('/send_message', methods=['POST'])
@login_required  # Ensure the user is logged in to access this route
def send_message():
    human_input = request.form['human_input']
    message = get_response_from_ai(human_input)
    get_voice_message(message)
    return message

# Function to read text from a file
def read_text_from_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

# Function to interact with AI
def get_response_from_ai(human_input):
    file_path = 'gfprompt.txt'
    prompt_text = read_text_from_file(file_path)
    template = f"""
    {prompt_text}
    
    {{history}}
    Boyfriend: {{human_input}}
    AVA:
    """

    prompt = PromptTemplate(
        input_variables=["history", "human_input"],
        template=template
    )

    chatgpt_chain = LLMChain(
        llm=OpenAI(temperature=0.5),
        prompt=prompt,
        verbose=True,
        memory=ConversationBufferWindowMemory(k=2)
    )

    output = chatgpt_chain.predict(human_input=human_input)

    return output

# Function to get voice message
def get_voice_message(message):
    payload = {
        "text": message,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0,
            "similarity_boost": 0
        }
    }

    headers = {
        'accept': 'audio/mpeg',
        'xi-api-key': os.getenv("ELEVEN_LABS_API_KEY"),
        'Content-Type': 'application/json'
    }

    response = requests.post('https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM?optimize_streaming_latency=0', json=payload, headers=headers)
    if response.status_code == 200 and response.content:
        with open('audio.mp3', 'wb') as f:
            f.write(response.content)

        pygame.mixer.init()
        pygame.mixer.music.load('audio.mp3')
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()

        return response.content

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
