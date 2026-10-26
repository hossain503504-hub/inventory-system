from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_inventory_key'

# --- Flask-Mail Configuration ---
# আপনার জিমেইল এবং App Password এখানে বসিয়ে নেবেন
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # আপনার জিমেইল দিন
app.config['MAIL_PASSWORD'] = 'your_app_password'  # জিমেইলের App Password দিন
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'

mail = Mail(app)

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
            company TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    """)
  # ইউজার টেবিল
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

  # ডিফল্ট অ্যাডমিন অ্যাকাউন্ট তৈরি
  admin_pass = generate_password_hash('admin123')
  cursor.execute(
      'INSERT OR IGNORE INTO users (email, password, role) VALUES (?, ?, ?)',
      ('admin@system.com', admin_pass, 'admin'),
  )

  conn.commit()
  conn.close()


init_db()

# সেলফ রেজিস্ট্রেশন এবং ডার্ক মোড সহ সম্পূর্ণ HTML টেমপ্লেট
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Inventory System - Dark Mode</title>
    <style>
      :root {
        --primary-color: #6366f1;
        --primary-hover: #4f46e5;
        --bg-color: #0f172a;
        --card-bg: #1e293b;
        --text-color: #f8fafc;
        --text-muted: #94a3b8;
        --border-color: #334155;
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
        max-width: 900px;
        margin: 0 auto;
        background: var(--card-bg);
        padding: 20px;
        border-radius: var(--border-radius);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        border: 1px solid var(--border-color);
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
        flex-wrap: wrap;
        gap: 10px;
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

      input[type="email"], input[type="password"], input[type="text"], input[type="number"], select, .form-control, .form-select {
        width: 100%;
        padding: 10px 14px;
        margin-top: 5px;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        box-sizing: border-box;
        font-size: 14px;
        background-color: #0f172a;
        color: var(--text-color);
        transition: all 0.2s;
      }

      input:focus, select:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
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

      .btn-danger {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        padding: 6px 12px;
        box-shadow: 0 3px 10px rgba(239, 68, 68, 0.25);
      }

      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        border-radius: 8px;
        overflow: hidden;
        background-color: #0f172a;
      }

      th, td {
        padding: 12px 14px;
        text-align: left;
        border-bottom: 1px solid var(--border-color);
        font-size: 14px;
        color: var(--text-color);
      }

      th {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        font-weight: 600;
      }

      tbody tr:hover {
        background-color: #1e293b;
      }

      .flash {
        padding: 12px;
        background-color: #7f1d1d;
        color: #fecaca;
        border-radius: 8px;
        margin-bottom: 15px;
        font-size: 14px;
        border: 1px solid #991b1b;
      }

      .nav-tabs {
        margin-bottom: 20px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }

      .nav-tabs a {
        padding: 8px 16px;
        background: #334155;
        text-decoration: none;
        color: #cbd5e1;
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
                <h2>📦 AI Inventory System (Cloud DB)</h2>
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
            <a href="/" class="{% if active_tab == 'inventory' %}active{% endif %}">Stock & Search</a>
            <a href="/financials" class="{% if active_tab == 'financials' %}active{% endif %}">Reports & Financials</a>
            <a href="/ai_advisor" class="{% if active_tab == 'ai_advisor' %}active{% endif %}">🤖 Gemini AI Advisor</a>
            {% if session['role'] == 'admin' %}
                <a href="/history" class="{% if active_tab == 'history' %}active{% endif %}">Admin Settings & Logs</a>
            {% endif %}
        </div>

        {% if page == 'dashboard' %}
            {% if session['role'] == 'admin' %}
                <h3>➕ Add New Product / Brand Item</h3>
                <form action="/add_product" method="POST" style="margin-bottom: 25px;">
                    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px;">
                        <input type="text" name="name" placeholder="Product Name (e.g. Baby Diaper)" required style="flex: 2;">
                        <input type="text" name="company" placeholder="Company/Brand Name (e.g. Twinkle)" required style="flex: 2;">
                    </div>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <select name="size" required style="flex: 1;">
                            <option value="" disabled selected style="background-color: #0f172a;">Select Size</option>
                            <option value="S">S</option>
                            <option value="M">M</option>
                            <option value="L">L</option>
                            <option value="XL">XL</option>
                            <option value="XXL">XXL</option>
                            <option value="Free Size">Free Size</option>
                        </select>
                        <input type="number" name="quantity" placeholder="Qty" required style="flex: 1;">
                        <input type="number" name="price" step="0.01" placeholder="Price" required style="flex: 1;">
                        <button type="submit" class="btn">Add Product</button>
                    </div>
                </form>
            {% endif %}

            <h3>🔍 Search by Company / Brand Name</h3>
            <form action="/" method="GET" style="margin-bottom: 25px;">
                <div style="display: flex; gap: 10px;">
                    <input type="text" name="search" value="{{ search_query }}" placeholder="Type company name (e.g. Twinkle)...">
                    <button type="submit" class="btn" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);">Search</button>
                </div>
            </form>

            <h3>📊 Stock List</h3>
            <table>
                <thead>
                    <tr>
                        <th>Company / Brand</th>
                        <th>Product Name</th>
                        <th>Size</th>
                        <th>Qty</th>
                        <th>Price</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in products %}
                    <tr>
                        <td><b>{{ p.company }}</b></td>
                        <td>{{ p.name }}</td>
                        <td>{{ p.size }}</td>
                        <td><b>{{ p.quantity }}</b></td>
                        <td>৳{{ p.price }}</td>
                        <td>
                            <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                                <form action="/deduct_stock/{{ p.id }}" method="POST" style="display: flex; gap: 3px;">
                                    <input type="number" name="amount" value="1" min="1" max="{{ p.quantity }}" style="width: 50px; padding: 4px;">
                                    <button type="submit" class="btn btn-deduct">Add</button>
                                </form>
                                {% if session['role'] == 'admin' %}
                                <form action="/remove_stock/{{ p.id }}" method="POST">
                                    <button type="submit" class="btn btn-danger" onclick="return confirm('Are you sure?')">Remove</button>
                                </form>
                                {% endif %}
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

        {% elif page == 'financials' %}
            <h3>📈 Reports & Financial Summary</h3>
            <div style="background: #0f172a; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid var(--border-color);">
                <p><b>Total Inventory Items:</b> {{ total_items }}</p>
                <p><b>Total Stock Value:</b> ৳{{ total_value }}</p>
            </div>

        {% elif page == 'ai_advisor' %}
            <h3>🤖 Gemini AI Inventory Advisor</h3>
            <div style="background: #0f172a; border: 1px solid var(--border-color); padding: 15px; border-radius: 8px;">
                <p><b>AI Insight:</b> Your inventory is running smoothly. Keep track of fast-moving items!</p>
            </div>

        {% elif page == 'history' and session['role'] == 'admin' %}
            <h3>📋 Admin Settings & Activity Logs</h3>
            <table>
                <thead>
                    <tr><th>Email</th><th>Product</th><th>Qty</th><th>Time</th></tr>
                </thead>
                <tbody>
                    {% for log in logs %}
                    <tr>
                        <td><b>{{ log.user_email }}</b></td>
                        <td>{{ log.product_name }}</td>
                        <td><span style="color:#f87171; font-weight:bold;">-{{ log.quantity_deducted }}</span></td>
                        <td>{{ log.timestamp }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% endif %}

    {% else %}
        {% if page == 'register' %}
            <h2 style="text-align: center;">📝 Create New Account</h2>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="flash">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            <form action="/register" method="POST">
                <div class="form-group">
                    <label>Email Address:</label>
                    <input type="email" name="email" required placeholder="your_email@gmail.com">
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required placeholder="******">
                </div>
                <button type="submit" class="btn" style="width: 100%;">Register & Send Email</button>
            </form>
            <div style="text-align: center; margin-top: 15px;">
                <a href="/" style="color: #6366f1; text-decoration: none;">Already have an account? Login here</a>
            </div>
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
            <div style="text-align: center; margin-top: 15px;">
                <a href="/register" style="color: #6366f1; text-decoration: none;">Don't have an account? Create one</a>
            </div>
        {% endif %}
    {% endif %}
</div>
</body>
</html>
"""


@app.route('/')
def index():
  if 'user' not in session:
    return render_template_string(HTML_TEMPLATE, page='login')

  search_query = request.args.get('search', '')
  conn = get_db()
  if search_query:
    products = conn.execute(
        'SELECT * FROM products WHERE company LIKE ? OR name LIKE ?',
        (f'%{search_query}%', f'%{search_query}%'),
    ).fetchall()
  else:
    products = conn.execute('SELECT * FROM products').fetchall()
  conn.close()

  return render_template_string(
      HTML_TEMPLATE,
      page='dashboard',
      products=products,
      active_tab='inventory',
      search_query=search_query,
  )


@app.route('/register', methods=['GET', 'POST'])
def register():
  if request.method == 'GET':
    return render_template_string(HTML_TEMPLATE, page='register')

  email = request.form.get('email')
  password = generate_password_hash(request.form.get('password'))

  conn = get_db()
  try:
    # প্রথম যে অ্যাকাউন্ট খুলবে সে স্বয়ংক্রিয়ভাবে admin হতে পারে, বাকিরা employee
    user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    role = 'admin' if user_count == 0 else 'employee'

    conn.execute(
        'INSERT INTO users (email, password, role) VALUES (?, ?, ?)',
        (email, password, role),
    )
    conn.commit()

    # জিমেইলে ওয়েলকাম মেসেজ পাঠানো
    try:
      msg = Message(
          'Welcome to AI Inventory System!',
          recipients=[email],
      )
      msg.body = (
          f'Hello,\n\nYour account has been successfully created in AI'
          f' Inventory System.\nYour Role: {role}\n\nThank you!'
      )
      mail.send(msg)
    except Exception as e:
      print('Mail Error:', e)

    flash('Account created successfully! Please login.')
    return redirect(url_for('index'))
  except sqlite3.IntegrityError:
    flash('Email already registered!')
    return redirect(url_for('register'))
  finally:
    conn.close()


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
  company = request.form.get('company')
  size = request.form.get('size')
  quantity = request.form.get('quantity')
  price = request.form.get('price')

  conn = get_db()
  conn.execute(
      'INSERT INTO products (name, company, size, quantity, price) VALUES (?,'
      ' ?, ?, ?, ?)',
      (name, company, size, quantity, price),
  )
  conn.commit()
  conn.close()
  return redirect(url_for('index'))


@app.route('/deduct_stock/<int:product_id>', methods=['POST'])
def deduct_stock(product_id):
  if 'user' not in session:
    return redirect(url_for('index'))

  amount = int(request.form.get('amount', 1))
  conn = get_db()
  product = conn.execute(
      'SELECT * FROM products WHERE id = ?', (product_id,)
  ).fetchone()

  if product:
    new_qty = product['quantity'] + amount
    conn.execute(
        'UPDATE products SET quantity = ? WHERE id = ?', (new_qty, product_id)
    )
    conn.commit()
  conn.close()
  return redirect(url_for('index'))


@app.route('/remove_stock/<int:product_id>', methods=['POST'])
def remove_stock(product_id):
  if session.get('role') != 'admin':
    return redirect(url_for('index'))

  conn = get_db()
  product = conn.execute(
      'SELECT * FROM products WHERE id = ?', (product_id,)
  ).fetchone()
  if product:
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
  conn.close()
  return redirect(url_for('index'))


@app.route('/financials')
def financials():
  if 'user' not in session:
    return redirect(url_for('index'))

  conn = generate_financials = get_db()
  products = conn.execute('SELECT * FROM products').fetchall()
  conn.close()

  total_items = sum(p['quantity'] for p in products)
  total_value = sum(p['quantity'] * p['price'] for p in products)

  return render_template_string(
      HTML_TEMPLATE,
      page='financials',
      total_items=total_items,
      total_value=total_value,
      active_tab='financials',
  )


@app.route('/ai_advisor')
def ai_advisor():
  if 'user' not in session:
    return redirect(url_for('index'))
  return render_template_string(
      HTML_TEMPLATE, page='ai_advisor', active_tab='ai_advisor'
  )


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
