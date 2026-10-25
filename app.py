from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_inventory_key'

DATABASE = 'inventory.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_name TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity_deducted INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT * FROM users WHERE email = 'admin@system.com'")
    if not cursor.fetchone():
        admin_pass = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
                       ('admin@system.com', admin_pass, 'admin'))
        
    cursor.execute("SELECT * FROM users WHERE email = 'emp@system.com'")
    if not cursor.fetchone():
        emp_pass = generate_password_hash('emp123')
        cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
                       ('emp@system.com', emp_pass, 'employee'))
                       
    conn.commit()
    conn.close()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inventory Management System</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f6f9; margin: 0; padding: 10px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2, h3 { color: #2c3e50; margin-top: 10px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; margin-bottom: 15px; }
        .user-info { font-size: 13px; color: #7f8c8d; }
        .btn-logout { background: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 12px; }
        .form-group { margin-bottom: 10px; }
        input, select { width: 100%; padding: 8px; margin-top: 3px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .btn { background: #27ae60; color: white; padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-deduct { background: #e67e22; padding: 4px 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #3498db; color: white; }
        .flash { padding: 8px; background-color: #f8d7da; color: #721c24; border-radius: 4px; margin-bottom: 10px; font-size: 13px; }
        .nav-tabs { margin-bottom: 15px; }
        .nav-tabs a { padding: 6px 12px; background: #e2e8f0; text-decoration: none; color: #333; border-radius: 4px; margin-right: 5px; font-size: 14px; }
        .nav-tabs a.active { background: #3498db; color: white; }
    </style>
</head>
<body>
    <div class="container">
        {% if session.get('user') %}
            <div class="header">
                <div>
                    <h2>📦 Inventory System</h2>
                    <div class="user-info">User: <b>{{ session['user'] }}</b> (<i>{{ session['role'] }}</i>)</div>
                </div>
                <a href="/logout" class="btn-logout">Logout</a>
            </div>

            {% with messages = get_flashed_messages() %}
              {% if messages %}
                {% for message in messages %}
                  <div class="flash">{{ message }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}

            <div class="nav-tabs">
                <a href="/" class="{% if active_tab == 'inventory' %}active{% endif %}">Stock</a>
                {% if session['role'] == 'admin' %}
                    <a href="/history" class="{%
