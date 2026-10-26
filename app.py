from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
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
  # প্রোডাক্ট টেবিল
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    """)
  # ইউজার টেবিল (Admin / Employee)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
  # অ্যাক্টিভিটি লগ টেবিল
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity_deducted INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

  # ডিফল্ট অ্যাডমিন এবং এমপ্লয়ী অ্যাকাউন্ট তৈরি (যদি না থাকে)
  admin_pass = generate_password_hash('admin123')
  emp_pass = generate_password_hash('emp123')

  cursor.execute(
      'INSERT OR IGNORE INTO users (email, password, role) VALUES (?, ?, ?)',
      ('admin@system.com', admin_pass, 'admin'),
  )
  cursor.execute(
      'INSERT OR IGNORE INTO users (email, password, role) VALUES (?, ?, ?)',
      ('emp@system.com', emp_pass, 'employee'),
  )

  conn.commit()
  conn.close()


# ডেটাবেস ইনিশিয়ালাইজ করুন
init_db()

# স্টাইলিশ এবং মডার্ন UI সহ সম্পূর্ণ HTML টেমপ্লেট
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inventory Management System</title>
    <style>
      :root {
        --primary-color: #4f46e5;
        --primary-hover: #4338ca;
        --secondary-color: #06b6d4;
        --bg-color: #f8fafc;
        --card-bg: #ffffff;
        --text-color: #1e293b;
        --border-radius: 12px;
      }

      body {
        background-color: var(--bg-color);
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: var(--text-color);
        margin: 0;
        padding: 15px;
      }

      .container {
        max-width: 800px;
        margin: 0 auto;
        background: var(--card-bg);
        padding: 20px;
        border-radius: var(--border-radius);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
      }

      h2, h3 {
        color: var(--text-color);
        font-weight: 700;
      }

      .app-header, .header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 15px 20px;
        border-radius: var(--border-radius);
        box-shadow: 0 8px 20px -4px rgba(79, 70, 229, 0.25);
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .user-info {
        font-size: 14px;
        color: #e2e8f0;
      }

      .btn-logout {
        background-color: #ef4444;
        color: white;
        padding: 6px 14px;
        text-decoration: none;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        transition: background 0.2s;
      }

      .btn-logout:hover {
        background-color: #dc2626;
      }

      .form-group {
        margin-bottom: 15px;
      }

      input[type="email"], input[type="password"], input[type="text"], input[type="number"], .form-control, .form-select {
        width: 100%;
        padding: 10px 14px;
        margin-top: 5px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        box-sizing: border-box;
        font-size: 14px;
        transition: all 0.2s;
      }

      input:focus, .form-control:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
        outline: none;
      }

      .btn {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 10px 18px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        transition: transform 0.1s;
      }

      .btn:hover {
        transform: translateY(-1px);
      }

      .btn-deduct {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        padding: 6px 12px;
        box-shadow: 0 3px 10px rgba(245, 158, 11, 0.25);
      }

      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
      }

      th, td {
        padding: 12px 14px;
        text-align: left;
        border-bottom: 1px solid #f1f5f9;
      }

      th {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        font-weight: 600;
      }

      tbody tr:hover {
        background-color: #f8fafc;
      }

      .flash {
        padding: 12px;
        background-color: #fee2e2;
        color: #991b1b;
        border-radius: 8px;
        margin-bottom: 15px;
        font-size: 14px;
        border: 1px solid #fca5a5;
      }

      .nav-tabs {
        margin-bottom: 20px;
        display: flex;
        gap: 8px;
      }

      .nav-tabs a {
        padding: 8px 16px;
        background: #e2e8f0;
        text-decoration: none;
        color: #475569;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        transition: background 0.2s;
      }

      .nav-tabs a.active {
        background: var(--primary-color);
        color: white;
      }
    </style>
</head>
<body>
<div class="container">
    {% if session.get('user') %}
        <div class="header">
            <div>
                <h2>📦 Inventory System</h2>
                <div class="user-info">Logged in as: <b>{{ session['user'] }}</b> (<i>{{ session['role'] }}</i>)</div>
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
            <a href="/" class="{% if active_tab == 'inventory' %}active{% endif %}">Inventory Stock</a>
            {% if session['role'] == 'admin' %}
                <a href="/history" class="{% if active_tab == 'history' %}active{% endif %}">Activity History</a>
            {% endif %}
        </div>

        {% if page == 'dashboard' %}
            {% if session['role'] == 'admin' %}
                <h3>➕ Add New Product</h3>
                <form action="/add_product" method="POST" style="margin-bottom: 25px;">
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <input type="text" name="name" placeholder="Product Name" required style="flex: 2;">
                        <input type="number" name="quantity" placeholder="Qty" required style="flex: 1;">
                        <input type="number" name="price" step="0.01" placeholder="Price" required style="flex: 1;">
                        <button type="submit" class="btn">Add Product</button>
                    </div>
                </form>
            {% endif %}

            <h3>📊 Product Stock List</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Product Name</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in products %}
                    <tr>
                        <td>{{ p.id }}</td>
                        <td>{{ p.name }}</td>
                        <td><b>{{ p.quantity }}</b></td>
                        <td>${{ p.price }}</td>
                        <td>
                            <form action="/deduct_stock/{{ p.id }}" method="POST" style="display: flex; gap: 5px;">
                                <input type="number" name="amount" value="1" min="1" max="{{ p.quantity }}" style="width: 60px; padding: 4px;">
                                <button type="submit" class="btn btn-deduct">Deduct</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

        {% elif page == 'history' and session['role'] == 'admin' %}
            <h3>📋 Employee Activity Log</h3>
            <table>
                <thead>
                    <tr>
                        <th>Employee Email</th>
                        <th>Product</th>
                        <th>Deducted Qty</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {% for log in logs %}
                    <tr>
                        <td><b>{{ log.user_email }}</b></td>
                        <td>{{ log.product_name }}</td>
                        <td><span style="color:red; font-weight:bold;">-{{ log.quantity_deducted }}</span></td>
                        <td>{{ log.timestamp }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% endif %}

    {% else %}
        <h2 style="text-align: center;">🔐 System Login</h2>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="flash">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form action="/login" method="POST">
            <div class="form-group">
                <label>Email Address:</label>
                <input type="email" name="email" required placeholder="admin@system.com">
            </div>
            <div class="form-group">
                <label>Password:</label>
                <input type="password" name="password" required placeholder="******">
            </div>
            <button type="submit" class="btn" style="width: 100%;">Login</button>
        </form>
        <div style="margin-top: 20px; font-size: 13px; color: #666; background: #eef2f5; padding: 10px; border-radius: 5px;">
            <b>Default Logins:</b><br>
            • Admin: <code>admin@system.com</code> / Pass: <code>admin123</code><br>
            • Employee: <code>emp@system.com</code> / Pass: <code>emp123</code>
        </div>
    {% endif %}
</div>
</body>
</html>
"""


@app.route('/')
def index():
  if 'user' not in session:
    return render_template_string(HTML_TEMPLATE, page='login')

  conn = get_db()
  products = conn.execute('SELECT * FROM products').fetchall()
  conn.close()
  return render_template_string(
      HTML_TEMPLATE,
      page='dashboard',
      products=products,
      active_tab='inventory',
  )


@app.route('/login', methods=['POST'])
def login():
  email = request.form.get('email')
  password = request.form.get('password')

  conn = get_db()
  user = conn.execute(
      'SELECT * FROM users WHERE email = ?', (email,)
  ).fetchone()
  conn.close()

  if user and check_password_hash(user['password'], password):
    session['user'] = user['email']
    session['role'] = user['role']
    return redirect(url_for('index'))
  else:
    flash('Invalid email or password!')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
  session.clear()
  return redirect(url_for('index'))


@app.route('/add_product', methods=['POST'])
def add_product():
  if session.get('role') != 'admin':
    return redirect(url_for('index'))

  name = request.form.get('name')
  quantity = request.form.get('quantity')
  price = request.form.get('price')

  conn = get_db()
  conn.execute(
      'INSERT INTO products (name, quantity, price) VALUES (?, ?, ?)',
      (name, quantity, price),
  )
  conn.commit()
  conn.close()
  return redirect(url_for('index'))


@app.route('/deduct_stock/<int:product_id>', methods=['POST'])
def deduct_stock(val=None, product_id=None):
  if 'user' not in session:
    return redirect(url_for('index'))

  amount = int(request.form.get('amount', 1))

  conn = get_db()
  product = conn.execute(
      'SELECT * FROM products WHERE id = ?', (product_id,)
  ).fetchone()

  if product and product['quantity'] >= amount:
    new_qty = product['quantity'] - amount
    conn.execute(
        'UPDATE products SET quantity = ? WHERE id = ?', (new_qty, product_id)
    )
    conn.execute(
        'INSERT INTO logs (user_email, product_name, quantity_deducted) VALUES'
        ' (?, ?, ?)',
        (session['user'], product['name'], amount),
    )
    conn.commit()
  else:
    flash('Invalid quantity to deduct!')

  conn.close()
  return redirect(url_for('index'))


@app.route('/history')
def history():
  if session.get('role') != 'admin':
    return redirect(url_for('index'))

  conn = get_db()
  logs = conn.execute(
      'SELECT * FROM logs ORDER BY timestamp DESC'
  ).fetchall()
  conn.close()
  return render_template_string(
      HTML_TEMPLATE, page='history', logs=logs, active_tab='history'
  )


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)
