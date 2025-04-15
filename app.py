from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import random
import sqlite3
import pickle
import smtplib
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'crop_recommendation_secret')

# API Keys
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '79ed0441f03883b0101c4c5215a9434f')  # Replace with your key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyC7Ag57-RnZxRRMnXpQde_95JcdXpRDBk4')  # Replace with your key

# Email Configuration
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'killisunitha525@gmail.com')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')  # Must be an app-specific password

# Configure Google Generative AI
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')  # Verify model availability with genai.list_models()

# OTP Generation and Email Sending
def send_otp(email):
    otp = random.randint(1000, 9999)
    session['otp'] = otp

    subject = "Your OTP for Crop Recommendation System"
    message = f"Your OTP is: {otp}"

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"OTP sent to {email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("SMTP Authentication failed. Verify email and app-specific password.")
        return False
    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")
        return False
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False

# Database Connection
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Homepage Route
@app.route('/')
def home():
    return render_template('index.html')

# About Us Route
@app.route('/aboutus')
def about_us():
    return render_template('aboutus.html')

# Contact Route
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Unified Entry Point
@app.route('/register_login')
def entry_page():
    return render_template('register_login.html')

@app.route('/register_login', methods=['POST'])
def register_or_login():
    username = request.form['username'].strip()
    email = request.form['email'].strip()
    password = request.form['password'].strip()

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, email TEXT, password TEXT)")
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()

        if user:
            return redirect('/login')

        session['temp_user'] = (username, email, password)
        if send_otp(email):
            return redirect('/verify')
        else:
            return render_template('register_login.html', error="Failed to send OTP. Check email settings.")

@app.route('/verify')
def otp_page():
    return render_template('verify.html')

@app.route('/verify', methods=['POST'])
def verify_otp():
    user_otp = request.form['otp'].strip()
    if str(session.get('otp')) == user_otp:
        username, email, password = session.get('temp_user', (None, None, None))
        if not username:
            return render_template('verify.html', error="Session expired. Please register again.")
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users VALUES (?, ?, ?)", (username, email, password))
            conn.commit()
        session['user'] = username
        session.pop('otp', None)
        session.pop('temp_user', None)
        return redirect('/dashboard')
    return render_template('verify.html', error="Invalid OTP!")

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_user():
    username = request.form['username'].strip()
    password = request.form['password'].strip()

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()

        if user:
            session['user'] = user['username']
            return redirect('/dashboard')
    return render_template('login.html', error="Invalid credentials or user not found!")

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html', username=session['user'])

# Model Loading
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

def load_model(filename):
    model_path = os.path.join(MODEL_DIR, filename)
    if os.path.exists(model_path):
        with open(model_path, "rb") as file:
            return pickle.load(file)
    else:
        print(f"Warning: Model file '{filename}' not found!")
        return None

models = {
    "Decision Tree": load_model("DecisionTree.pkl"),
    "Logistic Regression": load_model("LogisticRegression.pkl"),
    "Random Forest": load_model("RandomForest.pkl"),
    "Naive Bayes": load_model("NBClassifier.pkl"),
    "SVM": load_model("SVMClassifier.pkl"),
    "XGBoost": load_model("XGBoost.pkl")
}

@app.route('/crop_prediction')
def prediction_page():
    if 'user' not in session:
        return redirect('/login')
    return render_template('crop_prediction.html')

@app.route('/predict', methods=['POST'])
def predict_crop():
    try:
        n = float(request.form['nitrogen'])
        p = float(request.form['phosphorus'])
        k = float(request.form['potassium'])
        rainfall = float(request.form['rainfall'])
        humidity = float(request.form['humidity'])
        temperature = float(request.form['temperature'])
        ph = float(request.form['ph'])
        algorithm = request.form['algorithm']

        # Validation
        if temperature > 43.67549:
            return render_template('crop_prediction.html', error="Cannot recommend crop. Invalid value for Temperature")
        if humidity > 99.98188:
            return render_template('crop_prediction.html', error="Cannot recommend crop. Invalid value for Humidity")
        if rainfall > 298.5601:
            return render_template('crop_prediction.html', error="Cannot recommend crop. Invalid value for Rainfall")
        if k > 205:
            return render_template('crop_prediction.html', error="Cannot recommend crop. Invalid value for Potassium")
        if p > 145:
            return render_template('crop_prediction.html', error="Cannot recommend crop. Invalid value for Phosphorus")
        if n > 140:
            return render_template('crop_prediction.html', error="Cannot recommend crop. Invalid value for Nitrogen")
        if ph > 9.935091:
            return render_template('crop_prediction.html', error="Cannot recommend crop. Invalid value for Ph")

        model = models.get(algorithm)
        if not model:
            return render_template('crop_prediction.html', error=f"Model {algorithm} not found")
        prediction = model.predict([[n, p, k, temperature, humidity, ph, rainfall]])[0]
        session['recommended_crop'] = prediction
        return redirect('/crop_recommendation')

    except ValueError:
        return render_template('crop_prediction.html', error="Please enter valid numerical inputs")
    except Exception as e:
        return render_template('crop_prediction.html', error=f"Error in prediction: {str(e)}")

@app.route('/weather', methods=['GET', 'POST'])
def weather_page():
    if 'user' not in session:
        return redirect('/login')

    weather_data = {
        "temp": "N/A",
        "description": "Enter a city to get weather",
        "icon": "unknown",
        "city": None,
        "animation": "default"
    }

    animation_map = {
        "01d": "sunny", "01n": "clear_night",
        "02d": "partly_cloudy", "02n": "partly_cloudy_night",
        "03d": "cloudy", "03n": "cloudy",
        "04d": "overcast", "04n": "overcast",
        "09d": "rain", "09n": "rain",
        "10d": "rain_day", "10n": "rain_night",
        "11d": "storm", "11n": "storm",
        "13d": "snow", "13n": "snow",
        "50d": "mist", "50n": "mist"
    }

    if request.method == 'POST':
        city = request.form.get('city', 'London').strip()
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        try:
            response = requests.get(url, timeout=5).json()
            if response.get("cod") != 200:
                weather_data["description"] = f"Unable to fetch weather for {city}"
            else:
                icon = response["weather"][0]["icon"]
                weather_data = {
                    "temp": response["main"]["temp"],
                    "description": response["weather"][0]["description"],
                    "icon": icon,
                    "city": city,
                    "animation": animation_map.get(icon, "default")
                }
        except requests.RequestException as e:
            weather_data["description"] = f"Error fetching weather: {str(e)}"

    return render_template('weather.html', weather=weather_data)

# Crop and Fertilizer Data
fertilizer_data = {
    "rice": {
        "fertilizers": ["Urea", "Super Phosphate", "Potash"],
        "image": "rice.jpg",
        "description": "Rice is a staple crop grown in flooded fields, requiring high water levels and warm temperatures. It is rich in carbohydrates and a primary food source for billions worldwide."
    },
    "maize": {
        "fertilizers": ["Ammonium Nitrate", "Urea", "Super Phosphate"],
        "image": "maize.jpg",
        "description": "Maize, or corn, is a versatile cereal crop that thrives in warm climates. It’s used for food, animal feed, and industrial products, known for its high yield potential."
    },
    "chickpea": {
        "fertilizers": ["Urea", "Super Phosphate"],
        "image": "chickpea.jpg",
        "description": "Chickpea is a legume rich in protein and fiber, grown in semi-arid regions. It fixes nitrogen in the soil, improving fertility, and is drought-tolerant."
    },
    "kidneybeans": {
        "fertilizers": ["Ammonium Nitrate", "Super Phosphate"],
        "image": "kidneybeans.jpg",
        "description": "Kidney beans are protein-rich legumes that prefer well-drained soils and moderate climates. They are popular in various cuisines and known for their nutritional value."
    },
    "pigeonpeas": {
        "fertilizers": ["DAP", "Potash"],
        "image": "pigeonpeas.jpg",
        "description": "Pigeon peas are drought-resistant legumes grown in tropical regions. They provide protein and improve soil health through nitrogen fixation."
    },
    "mothbeans": {
        "fertilizers": ["Urea", "MOP"],
        "image": "mothbeans.jpg",
        "description": "Moth beans are hardy legumes suited to arid conditions. They are a good source of protein and thrive in low-water environments."
    },
    "mungbean": {
        "fertilizers": ["Super Phosphate", "MOP"],
        "image": "mungbeans.jpg",
        "description": "Mung beans are small, green legumes that grow quickly in warm climates. They are rich in vitamins and minerals, often used in sprouts and dals."
    },
    "blackgram": {
        "fertilizers": ["DAP", "MOP"],
        "image": "blackgram.jpg",
        "description": "Black gram, or urad, is a protein-rich pulse crop grown in warm, moist conditions. It’s widely used in Indian cuisine and enhances soil fertility."
    },
    "lentil": {
        "fertilizers": ["Urea", "Super Phosphate"],
        "image": "lentil.jpg",
        "description": "Lentils are small, nutrient-dense legumes that grow well in cool climates. They are high in protein and fiber, making them a dietary staple."
    },
    "pomegranate": {
        "fertilizers": ["Potash", "DAP"],
        "image": "pomegranate.jpg",
        "description": "Pomegranate is a fruit crop that thrives in dry, warm climates. It’s rich in antioxidants and known for its juicy, seed-filled arils."
    },
    "banana": {
        "fertilizers": ["Urea", "Super Phosphate"],
        "image": "banana.jpg",
        "description": "Banana is a tropical fruit crop requiring high humidity and warm temperatures. It’s a rich source of potassium and energy."
    },
    "mango": {
        "fertilizers": ["Potash", "Super Phosphate"],
        "image": "mango.jpg",
        "description": "Mango is a tropical fruit known as the 'king of fruits.' It grows in warm climates and is prized for its sweet, juicy flesh and rich vitamin content."
    },
    "grapes": {
        "fertilizers": ["MOP", "Potash"],
        "image": "grapes.jpg",
        "description": "Grapes are vine-grown fruits that thrive in temperate climates. They are used for fresh eating, wine, and raisins, rich in antioxidants."
    },
    "watermelon": {
        "fertilizers": ["Urea", "DAP"],
        "image": "watermelon.jpg",
        "description": "Watermelon is a juicy fruit crop that grows in warm, sunny conditions. It’s high in water content and refreshing, ideal for hot climates."
    },
    "muskmelon": {
        "fertilizers": ["Super Phosphate", "MOP"],
        "image": "muskmelon.jpg",
        "description": "Muskmelon is a sweet, aromatic fruit that prefers warm, dry weather. It’s rich in vitamins A and C, perfect for summer consumption."
    },
    "apple": {
        "fertilizers": ["Urea", "Potash"],
        "image": "apple.jpg",
        "description": "Apple is a temperate fruit crop requiring cool climates and well-drained soil. It’s high in fiber and antioxidants, a global favorite."
    },
    "orange": {
        "fertilizers": ["DAP", "MOP"],
        "image": "orange.jpg",
        "description": "Orange is a citrus fruit grown in subtropical regions. It’s packed with vitamin C and known for its juicy, tangy flavor."
    },
    "papaya": {
        "fertilizers": ["Super Phosphate", "MOP"],
        "image": "papaya.jpg",
        "description": "Papaya is a tropical fruit rich in enzymes and vitamins. It grows quickly in warm, moist conditions and has a soft, sweet flesh."
    },
    "coconut": {
        "fertilizers": ["Potash", "MOP"],
        "image": "coconut.jpg",
        "description": "Coconut is a tropical palm crop yielding versatile nuts. It thrives near coastlines and provides water, oil, and fiber."
    },
    "jute": {
        "fertilizers": ["Urea", "MOP"],
        "image": "jute.jpg",
        "description": "Jute is a fiber crop grown in warm, humid climates. It’s used for making burlap and ropes, known for its strong fibers."
    },
    "coffee": {
        "fertilizers": ["Urea", "Potash"],
        "image": "coffee.jpg",
        "description": "Coffee is a beverage crop grown in tropical highlands. It requires shade and moderate rainfall, famous for its stimulating beans."
    }
}

fertilizer_images = {
    "Urea": {
        "image": "urea.jpg",
        "description": "Urea is a nitrogen-rich fertilizer (46% nitrogen) that promotes vigorous plant growth and leaf development. It’s highly soluble in water, making it ideal for quick nutrient delivery."
    },
    "Super Phosphate": {
        "image": "super_phosphate.jpg",
        "description": "Super Phosphate provides phosphorus (16-20%), essential for root development, flowering, and fruiting. It’s commonly used to enhance early plant growth."
    },
    "Potash": {
        "image": "potash.jpg",
        "description": "Potash supplies potassium (up to 60%), crucial for improving plant resistance to disease, water uptake, and fruit quality. It’s vital for overall plant health."
    },
    "Ammonium Nitrate": {
        "image": "ammonium_nitrate.jpg",
        "description": "Ammonium Nitrate (34% nitrogen) is a fast-acting nitrogen fertilizer that boosts vegetative growth. It’s effective in cooler soils but requires careful handling due to its reactivity."
    },
    "DAP": {
        "image": "dap.jpg",
        "description": "Diammonium Phosphate (DAP) contains 18% nitrogen and 46% phosphorus. It’s excellent for early growth stages, supporting root establishment and energy transfer in plants."
    },
    "MOP": {
        "image": "mop.jpg",
        "description": "Muriate of Potash (MOP) provides potassium (60%) in a chloride form. It enhances crop yield, quality, and stress tolerance, especially in potassium-deficient soils."
    }
}

@app.route('/crop_recommendation')
def crop_recommendation_page():
    if 'user' not in session:
        return redirect('/login')
    crop = session.get('recommended_crop', 'Unknown Crop').lower()
    crop_data = fertilizer_data.get(crop, {
        "fertilizers": ["No specific fertilizers available"],
        "image": "default.jpg",
        "description": "No description available for this crop."
    })
    return render_template('crop_recommendation.html',
                          crop=crop,
                          crop_image=crop_data["image"],
                          description=crop_data["description"])

@app.route('/fertilizer_recommendation')
def fertilizer_recommendation_page():
    if 'user' not in session:
        return redirect('/login')
    crop = session.get('recommended_crop', 'Unknown Crop').lower()
    crop_data = fertilizer_data.get(crop, {
        "fertilizers": ["No specific fertilizers available"],
        "image": "default.jpg",
        "description": "No description available for this crop."
    })
    fertilizers_with_images = [
        (fert,
         fertilizer_images.get(fert, {"image": "default_fertilizer.jpg", "description": "No description available"})["image"],
         fertilizer_images.get(fert, {"image": "default_fertilizer.jpg", "description": "No description available"})["description"])
        for fert in crop_data["fertilizers"]
    ]
    return render_template('fertilizer_recommendation.html',
                          crop=crop,
                          fertilizers=fertilizers_with_images)

@app.route('/chatbot')
def chatbot_page():
    if 'user' not in session:
        return redirect('/login')
    return render_template('chatbot.html', username=session['user'])

@app.route('/chatbot_response', methods=['POST'])
def chatbot_response():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'response': 'Please send a valid message!'}), 400

        user_message = data['message'].strip()
        response = generate_gemini_response(user_message)
        return jsonify({'response': response})
    except Exception as e:
        print(f"Error in chatbot_response: {e}")
        return jsonify({'response': 'Oops, I hit a snag! Let’s try again—what’s your question?'}), 500

def generate_gemini_response(message):
    prompt = f"""
    You are AgriBot, an expert in agriculture, farming, crops, fertilizers, and related topics.
    Provide accurate, detailed, and helpful answers. If the question is unrelated to agriculture,
    still give a thoughtful response like a general-purpose AI. Answer this: "{message}"
    """
    try:
        result = model.generate_content(prompt)
        return result.text.strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        if 'hi' in message.lower() or 'hello' in message.lower():
            return f"Hi {session.get('user', 'there')}! I’m AgriBot, ready to help with farming questions or anything else. What’s up?"
        elif 'fertilizer' in message.lower() and 'rice' in message.lower():
            return "For rice, common fertilizers include Urea (46% nitrogen) for growth, Super Phosphate (phosphorus) for roots, and Potash (potassium) for resilience. Apply about 100-150 kg/ha of Urea, adjusted to soil tests."
        else:
            return "I couldn’t connect to my full knowledge base, but I can still help! What do you want to know about farming or anything else?"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)