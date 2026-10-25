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
                    <a href="/history" class="{% if active_tab == 'history' %}active{% endif %}">Activity Log</a>
                {% endif %}
            </div>

            {% if page == 'dashboard' %}
                {% if session['role'] == 'admin' %}
                    <h3>➕ Add New Diaper / Product</h3>
                    <form action="/add_product" method="POST" style="margin-bottom: 20px;">
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <input type="text" name="name" placeholder="Product Name" required style="flex: 2;">
                            <select name="size" required style="flex: 1;">
                                <option value="" disabled selected>Size</option>
                                <option value="S">S</option>
                                <option value="M">M</option>
                                <option value="L">L</option>
                                <option value="XL">XL</option>
                                <option value="XXL">XXL</option>
                                <option value="XXXL">XXXL</option>
                            </select>
                            <input type="number" name="quantity" placeholder="Qty" required style="flex: 1;">
                            <input type="number" step="0.01" name="price" placeholder="Price" required style="flex: 1;">
                            <button type="submit" class="btn" style="width: 100%; margin-top: 5px;">Add Product</button>
                        </div>
                    </form>
                {% endif %}

                <h3>📊 Product & Size Stock</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Size</th>
                            <th>Qty</th>
                            <th>Price</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr>
                            <td>{{ p.name }}</td>
                            <td><b>{{ p.size }}</b></td>
                            <td><b>{{ p.quantity }}</b></td>
                            <td>${{ p.price }}</td>
                            <td>
                                <form action="/deduct_stock/{{ p.id }}" method="POST" style="display:flex; gap:4px;">
                                    <input type="number" name="amount" value="1" min="1" max="{{ p.quantity }}" style="width: 50px; padding: 3px;">
                                    <button type="submit" class="btn btn-deduct">Deduct</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

            {% elif page == 'history' and session['role'] == 'admin' %}
                <h3>📋 Employee Activity History</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Employee</th>
                            <th>Product & Size</th>
                            <th>Qty</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for log in logs %}
                        <tr>
                            <td><b>{{ log.user_email }}</b></td>
                            <td>{{ log.product_name }} ({{ log.size }})</td>
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
                    <label>Email:</label>
                    <input type="email" name="email" required placeholder="admin@system.com">
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required placeholder="******">
                </div>
                <button type="submit" class="btn" style="width: 100%;">Login</button>
            </form>
            <div style="margin-top: 15px; font-size: 12px; color: #666; background: #eef2f5; padding: 8px; border-radius: 4px;">
                <b>Logins:</b><br>
                • Admin: <code>admin@system.com</code> / <code>admin123</code><br>
                • Employee: <code>emp@system.com</code> / <code>emp123</code>
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    if 'user' not in session:
        return render_template_string(HTML_TEMPLATE, page='login')
    
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, page='dashboard', products=products, active_tab='inventory')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['user'] = user['email']
        session['role'] = user['role']
        return redirect(url_for('index'))
    else:
        flash('Invalid Email or Password!')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        flash('Only Admin can add products!')
        return redirect(url_for('index'))
        
    name = request.form['name']
    size = request.form['size']
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])
    
    conn = get_db()
    conn.execute('INSERT INTO products (name, size, quantity, price) VALUES (?, ?, ?, ?)', (name, size, quantity, price))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/deduct_stock/<int:id>', methods=['POST'])
def deduct_stock(id):
    if 'user' not in session:
        return redirect(url_for('index'))
        
    amount = int(request.form['amount'])
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    
    if product and product['quantity'] >= amount:
        new_qty = product['quantity'] - amount
        conn.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_qty, id))
        conn.execute('INSERT INTO logs (user_email, product_name, size, quantity_deducted) VALUES (?, ?, ?, ?)',
                     (session['user'], product['name'], product['size'], amount))
        conn.commit()
    else:
        flash('Not enough stock!')
        
    conn.close()
    return redirect(url_for('index'))

@app.route('/history')
def history():
    if session.get('role') != 'admin':
        flash('Access restricted to Admin only!')
        return redirect(url_for('index'))
        
    conn = get_db()
    logs = conn.execute('SELECT * FROM logs ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, page='history', logs=logs, active_tab='history')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
