from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = 'super_secret_inventory_key'

DATABASE = 'inventory.db'

# জেমিনি এআই কনফিগারেশন
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)

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
            brand TEXT NOT NULL,
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
            brand TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity_deducted INTEGER NOT NULL,
            total_price REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_in_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_email TEXT NOT NULL,
            product_name TEXT NOT NULL,
            brand TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity_added INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
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
    <title>AI-Powered Inventory Management System</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f6f9; margin: 0; padding: 10px; }
        .container { max-width: 950px; margin: 0 auto; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2, h3 { color: #2c3e50; margin-top: 10px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; margin-bottom: 15px; }
        .user-info { font-size: 13px; color: #7f8c8d; }
        .btn-logout { background: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 12px; }
        .form-group { margin-bottom: 10px; }
        input, select, textarea { width: 100%; padding: 8px; margin-top: 3px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .btn { background: #27ae60; color: white; padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-deduct { background: #e67e22; padding: 4px 8px; }
        .btn-danger { background: #c0392b; padding: 4px 8px; color: white; text-decoration: none; border-radius: 4px; font-size: 12px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #3498db; color: white; }
        .flash { padding: 8px; background-color: #f8d7da; color: #721c24; border-radius: 4px; margin-bottom: 10px; font-size: 13px; }
        .nav-tabs { margin-bottom: 15px; display: flex; flex-wrap: wrap; gap: 5px; }
        .nav-tabs a { padding: 6px 10px; background: #e2e8f0; text-decoration: none; color: #333; border-radius: 4px; font-size: 13px; }
        .nav-tabs a.active { background: #3498db; color: white; }
        .stats-card { background: #f8f9fa; border-left: 4px solid #3498db; padding: 10px; margin-bottom: 10px; border-radius: 4px; font-size: 14px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .search-box { display: flex; gap: 8px; margin-bottom: 15px; }
        .ai-box { background: #e8f4fd; border: 1px solid #bbe1fa; padding: 15px; border-radius: 6px; margin-top: 15px; }
        @media(max-width: 600px) { .grid-2 { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        {% if session.get('user') %}
            <div class="header">
                <div>
                    <h2>📦 AI Inventory System</h2>
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
                {% if session['role'] == 'admin' %}
                    <a href="/reports" class="{% if active_tab == 'reports' %}active{% endif %}">Reports & Financials</a>
                    <a href="/ai_advisor" class="{% if active_tab == 'ai_advisor' %}active{% endif %}">🤖 Gemini AI Advisor</a>
                    <a href="/employees" class="{% if active_tab == 'employees' %}active{% endif %}">Manage Employees</a>
                    <a href="/settings" class="{% if active_tab == 'settings' %}active{% endif %}">Admin Settings</a>
                {% endif %}
            </div>

            {% if page == 'dashboard' %}
                {% if session['role'] == 'admin' %}
                    <h3>➕ Add New Product / Brand Item</h3>
                    <form action="/add_product" method="POST" style="margin-bottom: 20px; background: #fdfdfd; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                        <div class="form-group">
                            <input type="text" name="name" placeholder="Product Name (e.g. Baby Diaper)" required>
                        </div>
                        <div class="form-group">
                            <input type="text" name="brand" placeholder="Company/Brand Name (e.g. Thai, Happy Nappy, Twinkle, Huggies)" required>
                        </div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
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
                        </div>
                        <button type="submit" class="btn" style="width: 100%; margin-top: 8px;">Add Product</button>
                    </form>
                {% endif %}

                <h3>🔍 Search by Company / Brand Name</h3>
                <form method="GET" action="/" class="search-box">
                    <input type="text" name="search" placeholder="Type company name (e.g. Huggies, Thai, Twinkle)..." value="{{ search_query }}">
                    <button type="submit" class="btn" style="background: #3498db; white-space: nowrap;">Search</button>
                    {% if search_query %}
                        <a href="/" class="btn" style="background: #95a5a6; text-decoration: none; display: flex; align-items: center;">Reset</a>
                    {% endif %}
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
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr>
                            <td><b>{{ p.brand }}</b></td>
                            <td>{{ p.name }}</td>
                            <td><b>{{ p.size }}</b></td>
                            <td><b>{{ p.quantity }}</b></td>
                            <td>৳{{ p.price }}</td>
                            <td>
                                <form action="/deduct_stock/{{ p.id }}" method="POST" style="display:flex; gap:4px;">
                                    <input type="number" name="amount" value="1" min="1" max="{{ p.quantity }}" style="width: 45px; padding: 2px;">
                                    <button type="submit" class="btn btn-deduct">Deduct</button>
                                </form>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" style="text-align: center; color: #7f8c8d;">No products found! Try another company name.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

            {% elif page == 'reports' and session['role'] == 'admin' %}
                <h3>📈 Monthly & Financial Overview ({{ current_month }})</h3>
                
                <div class="grid-2">
                    <div class="stats-card">
                        <h4>📥 Monthly Stock In (Overall)</h4>
                        <p>Total Qty Added: <b>{{ monthly_in_qty }}</b></p>
                        <p>Total Investment: <b>৳{{ "%.2f"|format(monthly_in_val) }}</b></p>
                    </div>
                    <div class="stats-card" style="border-left-color: #e67e22;">
                        <h4>📤 Monthly Sales (Overall)</h4>
                        <p>Total Qty Sold: <b>{{ monthly_out_qty }}</b></p>
                        <p>Total Sales Value: <b>৳{{ "%.2f"|format(monthly_out_val) }}</b></p>
                    </div>
                </div>

                <div class="stats-card" style="border-left-color: #27ae60; margin-top: 10px;">
                    <h4>💰 Current Stock Assets (Overall)</h4>
                    <p>Total Products in Stock: <b>{{ total_stock_qty }} Pcs/Cartons</b></p>
                    <p>Total Asset Value: <b>৳{{ "%.2f"|format(total_stock_val) }}</b></p>
                </div>

                <h3>🏢 Brand-wise Detailed Report</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Company / Brand</th>
                            <th>Current Stock Qty</th>
                            <th>Current Stock Value</th>
                            <th>Monthly In (Qty)</th>
                            <th>Monthly Out (Qty)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for b in brand_reports %}
                        <tr>
                            <td><b>{{ b.brand }}</b></td>
                            <td><b>{{ b.current_qty if b.current_qty else 0 }}</b></td>
                            <td>৳{{ "%.2f"|format(b.current_val if b.current_val else 0.0) }}</td>
                            <td style="color: green; font-weight: bold;">+{{ b.in_qty if b.in_qty else 0 }}</td>
                            <td style="color: red; font-weight: bold;">-{{ b.out_qty if b.out_qty else 0 }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

                <h3>📋 Activity History</h3>
                <table>
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Brand & Product</th>
                            <th>Size</th>
                            <th>Qty</th>
                            <th>Amount</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for log in logs %}
                        <tr>
                            <td><b>{{ log.user_email }}</b></td>
                            <td>{{ log.brand }} - {{ log.product_name }}</td>
                            <td>{{ log.size }}</td>
                            <td><span style="color:red; font-weight:bold;">-{{ log.quantity_deducted }}</span></td>
                            <td>৳{{ log.total_price }}</td>
                            <td>{{ log.timestamp }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

            {% elif page == 'ai_advisor' and session['role'] == 'admin' %}
                <h3>🤖 Gemini AI Stock & Business Advisor</h3>
                <p style="font-size: 13px; color: #555;">আপনার ইনভেন্টরি ও সেলস ডাটা বিশ্লেষণ করে জেমিনি এআই থেকে যেকোনো পরামর্শ বা প্রশ্ন করতে পারেন।</p>
                
                <form action="/ask_ai" method="POST" class="ai-box">
                    <div class="form-group">
                        <label><b>Ask Gemini AI (প্রশ্ন বা নির্দেশনা লিখুন):</b></label>
                        <textarea name="ai_prompt" rows="3" placeholder="যেমন: এই মাসে কোন ব্র্যান্ডের ডায়াপার সবচেয়ে বেশি বিক্রি হয়েছে? বা কোন ব্র্যান্ডের স্টক বাড়ানো উচিত?" required></textarea>
                    </div>
                    <button type="submit" class="btn" style="background: #8e44ad;">Ask AI Assistant</button>
                </form>

                {% if ai_response %}
                    <div style="background: #fff; border: 1px solid #8e44ad; padding: 15px; border-radius: 6px; margin-top: 15px;">
                        <h4 style="color: #8e44ad; margin-top: 0;">💡 Gemini AI Response:</h4>
                        <p style="white-space: pre-line; line-height: 1.5; font-size: 14px;">{{ ai_response }}</p>
                    </div>
                {% endif %}

            {% elif page == 'employees' and session['role'] == 'admin' %}
                <h3>👥 Add New Employee</h3>
                <form action="/add_employee" method="POST" style="margin-bottom: 20px; background: #fdfdfd; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                    <div class="form-group">
                        <label>Employee Email:</label>
                        <input type="email" name="email" required placeholder="employee@system.com">
                    </div>
                    <div class="form-group">
                        <label>Password:</label>
                        <input type="password" name="password" required placeholder="******">
                    </div>
                    <button type="submit" class="btn">Create Employee Account</button>
                </form>

                <h3>Employee List</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for emp in employees %}
                        <tr>
                            <td>{{ emp.email }}</td>
                            <td>{{ emp.role }}</td>
                            <td>
                                {% if emp.email != session['user'] %}
                                    <a href="/delete_user/{{ emp.id }}" class="btn-danger" onclick="return confirm('Delete this user?')">Delete</a>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

            {% elif page == 'settings' and session['role'] == 'admin' %}
                <h3>⚙️ Change Admin Credentials</h3>
                <form action="/update_admin" method="POST" style="background: #fdfdfd; padding: 15px; border: 1px solid #ddd; border-radius: 4px;">
                    <div class="form-group">
                        <label>New Admin Email:</label>
                        <input type="email" name="email" value="{{ session['user'] }}" required>
                    </div>
                    <div class="form-group">
                        <label>New Password:</label>
                        <input type="password" name="password" placeholder="New Password">
                    </div>
                    <button type="submit" class="btn">Update Credentials</button>
                </form>
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
                <b>Default Logins:</b><br>
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
    
    search_query = request.args.get('search', '').strip()
    conn = get_db()
    
    if search_query:
        products = conn.execute("SELECT * FROM products WHERE brand LIKE ? OR name LIKE ?", 
                                ('%' + search_query + '%', '%' + search_query + '%')).fetchall()
    else:
        products = conn.execute('SELECT * FROM products').fetchall()
        
    conn.close()
    return render_template_string(HTML_TEMPLATE, page='dashboard', products=products, active_tab='inventory', search_query=search_query)

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
    brand = request.form['brand']
    size = request.form['size']
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])
    
    conn = get_db()
    conn.execute('INSERT INTO products (name, brand, size, quantity, price) VALUES (?, ?, ?, ?, ?)', (name, brand, size, quantity, price))
    conn.execute('INSERT INTO stock_in_logs (admin_email, product_name, brand, size, quantity_added, price_per_unit) VALUES (?, ?, ?, ?, ?, ?)',
                 (session['user'], name, brand, size, quantity, price))
    conn.commit()
    conn.close()
    flash('Product added successfully!')
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
        total_sale_price = amount * product['price']
        conn.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_qty, id))
        conn.execute('INSERT INTO logs (user_email, product_name, brand, size, quantity_deducted, total_price) VALUES (?, ?, ?, ?, ?, ?)',
                     (session['user'], product['name'], product['brand'], product['size'], amount, total_sale_price))
        conn.commit()
        flash('Stock deducted successfully!')
    else:
        flash('Not enough stock!')
        
    conn.close()
    return redirect(url_for('index'))

@app.route('/reports')
def reports():
    if session.get('role') != 'admin':
        flash('Access restricted to Admin only!')
        return redirect(url_for('index'))
        
    current_month_str = datetime.now().strftime('%Y-%m')
    
    conn = get_db()
    stock_in = conn.execute("SELECT SUM(quantity_added) as qty, SUM(quantity_added * price_per_unit) as val FROM stock_in_logs WHERE strftime('%Y-%m', timestamp) = ?", (current_month_str,)).fetchone()
    monthly_in_qty = stock_in['qty'] if stock_in['qty'] else 0
    monthly_in_val = stock_in['val'] if stock_in['val'] else 0.0

    stock_out = conn.execute("SELECT SUM(quantity_deducted) as qty, SUM(total_price) as val FROM logs WHERE strftime('%Y-%m', timestamp) = ?", (current_month_str,)).fetchone()
    monthly_out_qty = stock_out['qty'] if stock_out['qty'] else 0
    monthly_out_val = stock_out['val'] if stock_out['val'] else 0.0

    products = conn.execute("SELECT SUM(quantity) as qty, SUM(quantity * price) as val FROM products").fetchone()
    total_stock_qty = products['qty'] if products['qty'] else 0
    total_stock_val = products['val'] if products['val'] else 0.0

    brands_list = conn.execute("SELECT DISTINCT brand FROM products UNION SELECT DISTINCT brand FROM stock_in_logs UNION SELECT DISTINCT brand FROM logs").fetchall()
    
    brand_reports = []
    for b_row in brands_list:
        b_name = b_row['brand']
        cur = conn.execute("SELECT SUM(quantity) as qty, SUM(quantity * price) as val FROM products WHERE brand = ?", (b_name,)).fetchone()
        in_res = conn.execute("SELECT SUM(quantity_added) as qty FROM stock_in_logs WHERE brand = ? AND strftime('%Y-%m', timestamp) = ?", (b_name, current_month_str)).fetchone()
        out_res = conn.execute("SELECT SUM(quantity_deducted) as qty FROM logs WHERE brand = ? AND strftime('%Y-%m', timestamp) = ?", (b_name, current_month_str)).fetchone()
        
        brand_reports.append({
            'brand': b_name,
            'current_qty': cur['qty'] if cur and cur['qty'] else 0,
            'current_val': cur['val'] if cur and cur['val'] else 0.0,
            'in_qty': in_res['qty'] if in_res and in_res['qty'] else 0,
            'out_qty': out_res['qty'] if out_res and out_res['qty'] else 0
        })

    logs = conn.execute('SELECT * FROM logs ORDER BY timestamp DESC').fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, page='reports', 
                                  monthly_in_qty=monthly_in_qty, monthly_in_val=monthly_in_val,
                                  monthly_out_qty=monthly_out_qty, monthly_out_val=monthly_out_val,
                                  total_stock_qty=total_stock_qty, total_stock_val=total_stock_val,
                                  brand_reports=brand_reports,
                                  logs=logs, active_tab='reports', current_month=current_month_str)

@app.route('/ai_advisor')
def ai_advisor():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template_string(HTML_TEMPLATE, page='ai_advisor', active_tab='ai_advisor')

@app.route('/ask_ai', methods=['POST'])
def ask_ai():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    user_prompt = request.form['ai_prompt']
    
    conn = get_db()
    products = conn.execute("SELECT brand, name, size, quantity, price FROM products").fetchall()
    logs = conn.execute("SELECT brand, product_name, size, quantity_deducted, timestamp FROM logs ORDER BY timestamp DESC LIMIT 20").fetchall()
    conn.close()
    
    stock_summary = "\n".join([f"- Brand: {p['brand']}, Product: {p['name']}, Size: {p['size']}, Qty: {p['quantity']}, Price: {p['price']}" for p in products])
    sales_summary = "\n".join([f"- Sold: {l['quantity_deducted']} of {l['brand']} ({l['product_name']} size {l['size']}) at {l['timestamp']}" for l in logs])
    
    context = f"""
    You are an expert inventory and business advisor for a baby diaper shop. 
    Here is the current stock status:
    {stock_summary if stock_summary else "No stock available."}
    
    Here is the recent sales history:
    {sales_summary if sales_summary else "No sales yet."}
    
    Please answer the admin's question in professional and helpful Bengali (বাংলা):
    Question: {user_prompt}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(context)
        ai_reply = response.text
    except Exception as e:
        ai_reply = f"Error communicating with Gemini AI: {str(e)}"
        
    return render_template_string(HTML_TEMPLATE, page='ai_advisor', active_tab='ai_advisor', ai_response=ai_reply)

@app.route('/employees')
def employees():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    conn = get_db()
    employees = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, page='employees', employees=employees, active_tab='employees')

@app.route('/add_employee', methods=['POST'])
def add_employee():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    
    try:
        conn = get_db()
        conn.execute('INSERT INTO users (email, password, role) VALUES (?, ?, ?)', (email, password, 'employee'))
        conn.commit()
        conn.close()
        flash('Employee added successfully!')
    except:
        flash('Email already exists!')
    return redirect(url_for('employees'))

@app.route('/delete_user/<int:id>')
def delete_user(id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully!')
    return redirect(url_for('employees'))

@app.route('/settings')
def settings():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template_string(HTML_TEMPLATE, page='settings', active_tab='settings')

@app.route('/update_admin', methods=['POST'])
def update_admin():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    new_email = request.form['email']
    new_pass = request.form['password']
    
    conn = get_db()
    if new_pass:
        hashed_pass = generate_password_hash(new_pass)
        conn.execute('UPDATE users SET email = ?, password = ? WHERE email = ?', (new_email, hashed_pass, session['user']))
    else:
        conn.execute('UPDATE users SET email = ? WHERE email = ?', (new_email, session['user']))
    conn.commit()
    conn.close()
    
    session['user'] = new_email
    flash('Admin credentials updated successfully!')
    return redirect(url_for('settings'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
