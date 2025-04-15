# 🌾 Crop Recommendation System using Flask

This is an intelligent Flask-based web application designed to help farmers and agriculture enthusiasts by recommending the most suitable crops and fertilizers based on soil and weather conditions. The system integrates multiple machine learning algorithms, provides live weather updates, features an AI-powered AgroBot, and includes email OTP verification for secure access.

---

## 🚀 Features

- 🌱 **Crop Recommendation** using various machine learning algorithms.
- 🧪 **Fertilizer Suggestion** based on nutrient imbalance.
- ☁️ **Live Weather Updates** using OpenWeatherMap API.
- 🤖 **Intelligent AgroBot** for agriculture-related queries.
- 📧 **Email OTP Verification** during user registration.
- 📊 **Multiple Model Comparison** to choose best prediction.

---

## 🧠 Machine Learning Models Used

The system uses a range of machine learning models trained on agricultural datasets to make accurate predictions:

```python
models = {
    "Decision Tree": load_model("DecisionTree.pkl"),
    "Logistic Regression": load_model("LogisticRegression.pkl"),
    "Random Forest": load_model("RandomForest.pkl"),
    "Naive Bayes": load_model("NBClassifier.pkl"),
    "SVM": load_model("SVMClassifier.pkl"),
    "XGBoost": load_model("XGBoost.pkl")
}
```

## 🛠 Technologies Used
- Flask – Backend web framework (Python)

- HTML/CSS/JavaScript – Frontend development

- scikit-learn, XGBoost – Model training & evaluation

- OpenWeatherMap API – Real-time weather updates

- SMTP (Python smtplib) – Email OTP verification

- SQLite – Lightweight database for storing user data

## 📸 Demo



## ⚙️ Installation & Setup
1. Clone the Repository
```
git clone https://github.com/yourusername/Crop-Recommendation-System.git
cd Crop-Recommendation-System
```
2. Create and Activate Virtual Environment
```
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```
3. Install Dependencies
```
pip install -r requirements.txt
```
4. Run the Flask App
```
python app.py
```
5. Access the App
```
http://127.0.0.1:5000
```

## 📥 Inputs Required
- Nitrogen (N)

- Phosphorus (P)

- Potassium (K)

- Temperature (°C)

- Humidity (%)

- pH level

- Rainfall (mm)

## 💬 AgroBot
AgroBot is an intelligent chatbot integrated into the system that answers agriculture-related queries in real-time using NLP and pre-trained data.

## 🧪 Prediction Output
- Recommended Crop based on soil & weather parameters.

- Fertilizer Advice based on soil deficiencies.





