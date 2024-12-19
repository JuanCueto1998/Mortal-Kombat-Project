from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import pika
import sqlite3

app = Flask(__name__)
DATABASE = "combat_management.db"

# Configuración de la base de datos
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Función para conectarse a la base de datos
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(query, args)
    rv = cursor.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# Rutas de registro y autenticación
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    hashed_password = generate_password_hash(password)
    try:
        query_db("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
    if user and check_password_hash(user[2], password):
        return jsonify({"message": "Login successful"}), 200
    return jsonify({"error": "Invalid username or password"}), 401

# RabbitMQ - Iniciar un combate
@app.route('/start_combat', methods=['POST'])
def start_combat():
    data = request.json
    player1 = data.get("player1")
    player2 = data.get("player2")

    if not player1 or not player2:
        return jsonify({"error": "Both players are required to start a combat"}), 400

    # Comunicación con RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='combat_queue')

    message = {
        "player1": player1,
        "player2": player2
    }
    channel.basic_publish(exchange='', routing_key='combat_queue', body=str(message))
    connection.close()

    return jsonify({"message": "Combat initiated"}), 200

if __name__ == "__main__":
    app.run(debug=True)
