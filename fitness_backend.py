from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import sqlite3
import hashlib
import jwt
from passlib.context import CryptContext
import uvicorn

app = FastAPI(title="FitTracker Pro API", version="1.0.0")

# CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

# Database setup
def init_db():
    conn = sqlite3.connect('fitness_app.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            weight REAL,
            height REAL,
            age INTEGER,
            gender TEXT,
            body_type TEXT,
            goal TEXT,
            daily_calorie_goal INTEGER DEFAULT 2000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Food logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            food_name TEXT NOT NULL,
            calories INTEGER NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Exercise logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            exercise_name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            intensity TEXT NOT NULL,
            calories_burned INTEGER NOT NULL,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Weight logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            weight REAL NOT NULL,
            unit TEXT NOT NULL,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Water logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            glasses INTEGER NOT NULL,
            logged_date DATE NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Steps logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS steps_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            steps INTEGER NOT NULL,
            logged_date DATE NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    name: str
    weight: Optional[float] = None
    height: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    body_type: Optional[str] = None
    goal: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class FoodLog(BaseModel):
    food_name: str
    calories: int
    quantity: float
    unit: str
    meal_type: str

class ExerciseLog(BaseModel):
    exercise_name: str
    duration: int
    intensity: str
    calories_burned: int

class WeightLog(BaseModel):
    weight: float
    unit: str

class WaterLog(BaseModel):
    glasses: int

class StepsLog(BaseModel):
    steps: int

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('fitness_app.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_username(username: str):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None

# Food database (simplified - in production, use external API)
FOOD_DATABASE = {
    "apple": {"calories_per_100g": 52, "protein": 0.3, "carbs": 14, "fat": 0.2},
    "banana": {"calories_per_100g": 89, "protein": 1.1, "carbs": 23, "fat": 0.3},
    "chicken breast": {"calories_per_100g": 165, "protein": 31, "carbs": 0, "fat": 3.6},
    "rice": {"calories_per_100g": 130, "protein": 2.7, "carbs": 28, "fat": 0.3},
    "oatmeal": {"calories_per_100g": 68, "protein": 2.4, "carbs": 12, "fat": 1.4},
    "salmon": {"calories_per_100g": 208, "protein": 25, "carbs": 0, "fat": 12},
    "broccoli": {"calories_per_100g": 34, "protein": 2.8, "carbs": 7, "fat": 0.4},
    "egg": {"calories_per_100g": 155, "protein": 13, "carbs": 1.1, "fat": 11},
    "yogurt": {"calories_per_100g": 59, "protein": 10, "carbs": 3.6, "fat": 0.4},
    "bread": {"calories_per_100g": 265, "protein": 9, "carbs": 49, "fat": 3.2}
}

# Exercise database (simplified)
EXERCISE_DATABASE = {
    "running": {"calories_per_minute": 10, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.3}},
    "walking": {"calories_per_minute": 4, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.2}},
    "cycling": {"calories_per_minute": 8, "intensity_multiplier": {"low": 0.7, "moderate": 1.0, "high": 1.4}},
    "swimming": {"calories_per_minute": 11, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.3}},
    "weightlifting": {"calories_per_minute": 6, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.2}},
    "yoga": {"calories_per_minute": 3, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.1}},
    "pilates": {"calories_per_minute": 4, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.2}},
    "dancing": {"calories_per_minute": 5, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.3}},
    "basketball": {"calories_per_minute": 8, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.4}},
    "tennis": {"calories_per_minute": 7, "intensity_multiplier": {"low": 0.8, "moderate": 1.0, "high": 1.3}}
}

# API Routes

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/")
async def root():
    return {"message": "FitTracker Pro API is running!"}

@app.post("/register")
async def register(user: UserCreate):
    conn = get_db_connection()

    # Check if user exists
    existing_user = conn.execute('SELECT id FROM users WHERE username = ? OR email = ?', 
                                (user.username, user.email)).fetchone()
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already registered")

    # Hash password and create user
    password_hash = pwd_context.hash(user.password)

    cursor = conn.execute("""
        INSERT INTO users (username, email, password_hash, name, weight, height, age, gender, body_type, goal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user.username, user.email, password_hash, user.name, user.weight, user.height, 
          user.age, user.gender, user.body_type, user.goal))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Create access token
    access_token = create_access_token(data={"sub": user.username})

    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}

@app.post("/login")
async def login(user: UserLogin):
    db_user = get_user_by_username(user.username)

    if not db_user or not pwd_context.verify(user.password, db_user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "user_id": db_user['id']}

@app.get("/user/profile")
async def get_profile(token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user['id'],
        "username": user['username'],
        "email": user['email'],
        "name": user['name'],
        "weight": user['weight'],
        "height": user['height'],
        "age": user['age'],
        "gender": user['gender'],
        "body_type": user['body_type'],
        "goal": user['goal'],
        "daily_calorie_goal": user['daily_calorie_goal']
    }

@app.post("/food/log")
async def log_food(food: FoodLog, token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    conn.execute("""
        INSERT INTO food_logs (user_id, food_name, calories, quantity, unit, meal_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user['id'], food.food_name, food.calories, food.quantity, food.unit, food.meal_type))

    conn.commit()
    conn.close()

    return {"message": "Food logged successfully"}

@app.get("/food/search/{food_name}")
async def search_food(food_name: str):
    food_name_lower = food_name.lower()

    # Search in our simple database
    matches = {}
    for food, data in FOOD_DATABASE.items():
        if food_name_lower in food:
            matches[food] = data

    if not matches:
        # Return a default estimation
        return {
            "results": [{
                "name": food_name,
                "calories_per_100g": 100,  # Default estimation
                "protein": 5,
                "carbs": 15,
                "fat": 2
            }]
        }

    results = []
    for food, data in matches.items():
        results.append({
            "name": food.title(),
            "calories_per_100g": data["calories_per_100g"],
            "protein": data["protein"],
            "carbs": data["carbs"],
            "fat": data["fat"]
        })

    return {"results": results}

@app.get("/food/today")
async def get_today_food(token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    today = date.today()
    foods = conn.execute("""
        SELECT * FROM food_logs 
        WHERE user_id = ? AND DATE(logged_at) = ?
        ORDER BY logged_at DESC
    """, (user['id'], today)).fetchall()

    conn.close()

    food_list = []
    total_calories = 0

    for food in foods:
        food_dict = {
            "id": food['id'],
            "food_name": food['food_name'],
            "calories": food['calories'],
            "quantity": food['quantity'],
            "unit": food['unit'],
            "meal_type": food['meal_type'],
            "logged_at": food['logged_at']
        }
        food_list.append(food_dict)
        total_calories += food['calories']

    return {"foods": food_list, "total_calories": total_calories}

@app.post("/exercise/log")
async def log_exercise(exercise: ExerciseLog, token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    conn.execute("""
        INSERT INTO exercise_logs (user_id, exercise_name, duration, intensity, calories_burned)
        VALUES (?, ?, ?, ?, ?)
    """, (user['id'], exercise.exercise_name, exercise.duration, exercise.intensity, exercise.calories_burned))

    conn.commit()
    conn.close()

    return {"message": "Exercise logged successfully"}

@app.get("/exercise/calculate")
async def calculate_exercise_calories(exercise_name: str, duration: int, intensity: str):
    exercise_name_lower = exercise_name.lower()

    if exercise_name_lower not in EXERCISE_DATABASE:
        # Default calculation for unknown exercises
        base_calories = 5
        intensity_multiplier = {"low": 0.8, "moderate": 1.0, "high": 1.3}
    else:
        exercise_data = EXERCISE_DATABASE[exercise_name_lower]
        base_calories = exercise_data["calories_per_minute"]
        intensity_multiplier = exercise_data["intensity_multiplier"]

    multiplier = intensity_multiplier.get(intensity, 1.0)
    calories_burned = int(base_calories * duration * multiplier)

    return {"calories_burned": calories_burned}

@app.get("/exercise/today")
async def get_today_exercise(token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    today = date.today()
    exercises = conn.execute("""
        SELECT * FROM exercise_logs 
        WHERE user_id = ? AND DATE(logged_at) = ?
        ORDER BY logged_at DESC
    """, (user['id'], today)).fetchall()

    conn.close()

    exercise_list = []
    total_calories_burned = 0

    for exercise in exercises:
        exercise_dict = {
            "id": exercise['id'],
            "exercise_name": exercise['exercise_name'],
            "duration": exercise['duration'],
            "intensity": exercise['intensity'],
            "calories_burned": exercise['calories_burned'],
            "logged_at": exercise['logged_at']
        }
        exercise_list.append(exercise_dict)
        total_calories_burned += exercise['calories_burned']

    return {"exercises": exercise_list, "total_calories_burned": total_calories_burned}

@app.post("/weight/log")
async def log_weight(weight: WeightLog, token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    # Update user's current weight
    conn.execute('UPDATE users SET weight = ? WHERE id = ?', (weight.weight, user['id']))

    # Log weight entry
    conn.execute("""
        INSERT INTO weight_logs (user_id, weight, unit)
        VALUES (?, ?, ?)
    """, (user['id'], weight.weight, weight.unit))

    conn.commit()
    conn.close()

    return {"message": "Weight logged successfully"}

@app.get("/weight/history")
async def get_weight_history(token: str, days: int = 30):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    weights = conn.execute("""
        SELECT weight, unit, logged_at FROM weight_logs 
        WHERE user_id = ? 
        ORDER BY logged_at DESC 
        LIMIT ?
    """, (user['id'], days)).fetchall()

    conn.close()

    weight_history = []
    for weight in weights:
        weight_history.append({
            "weight": weight['weight'],
            "unit": weight['unit'],
            "logged_at": weight['logged_at']
        })

    return {"weight_history": weight_history}

@app.post("/water/log")
async def log_water(water: WaterLog, token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    today = date.today()

    # Check if entry exists for today
    existing = conn.execute("""
        SELECT id FROM water_logs WHERE user_id = ? AND logged_date = ?
    """, (user['id'], today)).fetchone()

    if existing:
        # Update existing entry
        conn.execute("""
            UPDATE water_logs SET glasses = ? WHERE user_id = ? AND logged_date = ?
        """, (water.glasses, user['id'], today))
    else:
        # Create new entry
        conn.execute("""
            INSERT INTO water_logs (user_id, glasses, logged_date)
            VALUES (?, ?, ?)
        """, (user['id'], water.glasses, today))

    conn.commit()
    conn.close()

    return {"message": "Water intake logged successfully"}

@app.get("/water/today")
async def get_today_water(token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    today = date.today()
    water_log = conn.execute("""
        SELECT glasses FROM water_logs WHERE user_id = ? AND logged_date = ?
    """, (user['id'], today)).fetchone()

    conn.close()

    glasses = water_log['glasses'] if water_log else 0
    return {"glasses": glasses, "goal": 8}

@app.post("/steps/log")
async def log_steps(steps: StepsLog, token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    today = date.today()

    # Check if entry exists for today
    existing = conn.execute("""
        SELECT id FROM steps_logs WHERE user_id = ? AND logged_date = ?
    """, (user['id'], today)).fetchone()

    if existing:
        # Update existing entry
        conn.execute("""
            UPDATE steps_logs SET steps = ? WHERE user_id = ? AND logged_date = ?
        """, (steps.steps, user['id'], today))
    else:
        # Create new entry
        conn.execute("""
            INSERT INTO steps_logs (user_id, steps, logged_date)
            VALUES (?, ?, ?)
        """, (user['id'], steps.steps, today))

    conn.commit()
    conn.close()

    return {"message": "Steps logged successfully"}

@app.get("/steps/today")
async def get_today_steps(token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    today = date.today()
    steps_log = conn.execute("""
        SELECT steps FROM steps_logs WHERE user_id = ? AND logged_date = ?
    """, (user['id'], today)).fetchone()

    conn.close()

    steps = steps_log['steps'] if steps_log else 0
    return {"steps": steps, "goal": 10000}

@app.get("/dashboard/summary")
async def get_dashboard_summary(token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    conn = get_db_connection()

    today = date.today()

    # Get today's food calories
    food_calories = conn.execute("""
        SELECT COALESCE(SUM(calories), 0) as total FROM food_logs 
        WHERE user_id = ? AND DATE(logged_at) = ?
    """, (user['id'], today)).fetchone()['total']

    # Get today's exercise calories
    exercise_calories = conn.execute("""
        SELECT COALESCE(SUM(calories_burned), 0) as total FROM exercise_logs 
        WHERE user_id = ? AND DATE(logged_at) = ?
    """, (user['id'], today)).fetchone()['total']

    # Get today's steps
    steps = conn.execute("""
        SELECT COALESCE(steps, 0) as steps FROM steps_logs 
        WHERE user_id = ? AND logged_date = ?
    """, (user['id'], today)).fetchone()['steps']

    # Get today's water
    water = conn.execute("""
        SELECT COALESCE(glasses, 0) as glasses FROM water_logs 
        WHERE user_id = ? AND logged_date = ?
    """, (user['id'], today)).fetchone()['glasses']

    conn.close()

    net_calories = food_calories - exercise_calories
    calorie_goal = user['daily_calorie_goal']
    remaining_calories = calorie_goal - net_calories

    return {
        "calories_consumed": food_calories,
        "calories_burned": exercise_calories,
        "net_calories": net_calories,
        "calorie_goal": calorie_goal,
        "remaining_calories": remaining_calories,
        "steps": steps,
        "steps_goal": 10000,
        "water_glasses": water,
        "water_goal": 8,
        "progress_percentage": min(100, (net_calories / calorie_goal) * 100) if calorie_goal > 0 else 0
    }

@app.get("/recommendations")
async def get_recommendations(token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)

    # Generate recommendations based on user's body type and goal
    body_type = user['body_type'] or 'mesomorph'
    goal = user['goal'] or 'maintain'

    recommendations = {
        "meals": [],
        "exercises": [],
        "tips": []
    }

    # Meal recommendations based on body type
    if body_type.lower() == 'ectomorph':
        recommendations["meals"] = [
            {"time": "7:00 AM - 8:00 AM", "meal": "High-Calorie Breakfast", "description": "Oatmeal with nuts, banana, and protein powder", "calories": 450},
            {"time": "12:00 PM - 1:00 PM", "meal": "Protein-Rich Lunch", "description": "Chicken and rice bowl with vegetables", "calories": 550},
            {"time": "6:00 PM - 7:00 PM", "meal": "Hearty Dinner", "description": "Salmon with quinoa and avocado", "calories": 500}
        ]
    elif body_type.lower() == 'endomorph':
        recommendations["meals"] = [
            {"time": "7:00 AM - 8:00 AM", "meal": "Low-Carb Breakfast", "description": "Egg omelet with vegetables and cheese", "calories": 300},
            {"time": "12:00 PM - 1:00 PM", "meal": "Lean Protein Lunch", "description": "Grilled chicken salad with olive oil", "calories": 350},
            {"time": "6:00 PM - 7:00 PM", "meal": "Light Dinner", "description": "Baked fish with steamed broccoli", "calories": 300}
        ]
    else:  # mesomorph
        recommendations["meals"] = [
            {"time": "7:00 AM - 8:00 AM", "meal": "Balanced Breakfast", "description": "Greek yogurt with berries and nuts", "calories": 350},
            {"time": "12:00 PM - 1:00 PM", "meal": "Balanced Lunch", "description": "Grilled chicken salad with quinoa", "calories": 450},
            {"time": "6:00 PM - 7:00 PM", "meal": "Balanced Dinner", "description": "Baked salmon with roasted vegetables", "calories": 400}
        ]

    # Exercise recommendations
    if goal.lower() == 'lose weight':
        recommendations["exercises"] = [
            {"time": "6:30 AM - 7:30 AM", "exercise": "Morning Cardio", "description": "30-minute moderate run", "calories": 300},
            {"time": "5:00 PM - 6:00 PM", "exercise": "Strength Training", "description": "Full body weight training", "calories": 250}
        ]
    elif goal.lower() == 'gain muscle':
        recommendations["exercises"] = [
            {"time": "7:00 AM - 8:00 AM", "exercise": "Weight Training", "description": "Heavy compound movements", "calories": 200},
            {"time": "5:00 PM - 6:00 PM", "exercise": "Strength Training", "description": "Targeted muscle groups", "calories": 250}
        ]
    else:  # maintain
        recommendations["exercises"] = [
            {"time": "6:30 AM - 7:30 AM", "exercise": "Mixed Cardio", "description": "Alternating running and walking", "calories": 250},
            {"time": "5:00 PM - 6:00 PM", "exercise": "Strength Training", "description": "Moderate weight training", "calories": 200}
        ]

    # General tips
    recommendations["tips"] = [
        "💧 Drink a glass of water before each meal to help with portion control",
        "😴 Aim for 7-8 hours of sleep for optimal recovery and weight management",
        "🍽️ Try to finish eating 3 hours before bedtime for better digestion",
        "🚶 Take the stairs instead of elevators when possible",
        "🥗 Fill half your plate with vegetables at each meal"
    ]

    return recommendations

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
