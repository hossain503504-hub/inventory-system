from flask import Flask, render_template_string, request, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai
import io

app = Flask(__name__)
app.secret_key = 'super_secret_inventory_key'

# সেশন পার্মানেন্ট করার জন্য কুকির মেয়াদ ৩০ দিন সেট করা হলো
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=30)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            product_name TEXT NOT NULL,
            brand TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity_deducted INTEGER NOT NULL,
            total_price REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_in_logs (
            id SERIAL PRIMARY KEY,
            admin_email TEXT NOT NULL,
            product_name TEXT NOT NULL,
            brand TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity_added INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT * FROM users WHERE email = 'admin@system.com'")
    if not cursor.fetchone():
        admin_pass = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, %s)", 
                       ('admin@system.com', admin_pass, 'admin'))
                       
    conn.commit()
    cursor.close()
    conn.close()

GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
genai.configure(api_key=GEMINI_API_KEY)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Powered Inventory Management System - Dark Mode</title>
    <style>
        body { font-family: sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 10px; }
        .container { max-width: 950px; margin: 0 auto; background: #1e293b; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid #334155; }
        h2, h3 { color: #f8fafc; margin-top: 10px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #334155; padding-bottom: 8px; margin-bottom: 15px; }
        .user-info { font-size: 13px; color: #94a3b8; }
        .btn-logout { background: #ef4444; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 12px; }
        .form-group { margin-bottom: 10px; }
        input, select, textarea { width: 100%; padding: 8px; margin-top: 3px; border: 1px solid #334155; background-color: #0f172a; color: #f8fafc; border-radius: 4px; box-sizing: border-box; }
        .btn { background: #10b981; color: white; padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-danger { background: #ef4444; padding: 8px 12px; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; width: 100%; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; background-color: #0f172a; }
        th, td { border: 1px solid #334155; padding: 8px; text-align: left; color: #f8fafc; }
        th { background-color: #3b82f6; color: white; }
        .flash { padding: 8px; background-color: #7f1d1d; color: #fecaca; border: 1px solid #991b1b; border-radius: 4px; margin-bottom: 10px; font-size: 13px; }
        .nav-tabs { margin-bottom: 15px; display: flex; flex-wrap: wrap; gap: 5px; }
        .nav-tabs a { padding: 6px 10px; background: #334155; text-decoration: none; color: #cbd5e1; border-radius: 4px; font-size: 13px; }
        .nav-tabs a.active { background: #6366f1; color: white; }
        .stats-card { background: #0f172a; border-left: 4px solid #3b82f6; padding: 10px; margin-bottom: 10px; border-radius: 4px; font-size: 14px; border: 1px solid #334155; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .search-box { display: flex; gap: 8px; margin-bottom: 15px; }
        .ai-box { background: #1e293b; border: 1px solid #3b82f6; padding: 15px; border-radius: 6px; margin-top: 15px; }
        .cart-box { background: #1e293b; border: 1px solid #d97706; padding: 15px; border-radius: 6px; margin-top: 20px; }
        
        /* Futuristic Slideshow Banner Styling */
        .slideshow-container { position: relative; width: 100%; height: 180px; overflow: hidden; border-radius: 8px; margin-bottom: 15px; border: 1px solid #3b82f6; box-shadow: 0 0 15px rgba(59, 130, 246, 0.3); }
        .slide { position: absolute; width: 100%; height: 100%; opacity: 0; transition: opacity 1s ease-in-out; background-size: cover; background-position: center; display: flex; align-items: flex-end; padding: 15px; box-sizing: border-box; }
        .slide.active { opacity: 1; }
        .slide-content { background: rgba(15, 23, 42, 0.85); padding: 8px 12px; border-radius: 4px; border-left: 3px solid #10b981; width: 100%; }
        .slide-content h4 { margin: 0; color: #38bdf8; font-size: 15px; }
        .slide-content p { margin: 3px 0 0 0; font-size: 12px; color: #cbd5e1; }
        .low-stock-alert { background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; }
        @media(max-width: 600px) { .grid-2 { grid-template-columns: 1fr; } }
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
                {% if session['role'] == 'admin' %}
                    <a href="/reports" class="{% if active_tab == 'reports' %}active{% endif %}">Reports & Financials</a>
                    <a href="/ai_advisor" class="{% if active_tab == 'ai_advisor' %}active{% endif %}">🤖 Gemini AI Advisor</a>
                    <a href="/employees" class="{% if active_tab == 'employees' %}active{% endif %}">Manage Employees</a>
                    <a href="/settings" class="{% if active_tab == 'settings' %}active{% endif %}">Admin Settings</a>
                {% endif %}
            </div>

            {% if page == 'dashboard' %}
                <!-- Futuristic Auto-Sliding Banner -->
                <div class="slideshow-container">
                    <div class="slide active" style="background-image: linear-gradient(rgba(15,23,42,0.4), rgba(15,23,42,0.9)), url('https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1000&q=80')">
                        <div class="slide-content">
                            <h4>🚀 Next-Gen Automated Inventory</h4>
                            <p>Real-time cloud database tracking with AI-powered forecasting and instantaneous stock auditing.</p>
                        </div>
                    </div>
                    <div class="slide" style="background-image: linear-gradient(rgba(15,23,42,0.4), rgba(15,23,42,0.9)), url('https://images.unsplash.com/photo-1553413077-190dd305871c?auto=format&fit=crop&w=1000&q=80')">
                        <div class="slide-content">
                            <h4>📊 Advanced Financial Analytics</h4>
                            <p>Track monthly cash flow, brand-wise performance, and instant PDF report generations seamlessly.</p>
                        </div>
                    </div>
                    <div class="slide" style="background-image: linear-gradient(rgba(15,23,42,0.4), rgba(15,23,42,0.9)), url('https://images.unsplash.com/photo-1616401784845-180882ba9ba8?auto=format&fit=crop&w=1000&q=80')">
                        <div class="slide-content">
                            <h4>🤖 Gemini AI Business Advisor</h4>
                            <p>Get professional insights, low stock warnings, and data-driven suggestions instantly from AI.</p>
                        </div>
                    </div>
                </div>

                <script>
                    let currentSlide = 0;
                    const slides = document.querySelectorAll('.slide');
                    function nextSlide() {
                        slides[currentSlide].classList.remove('active');
                        currentSlide = (currentSlide + 1) % slides.length;
                        slides[currentSlide].classList.add('active');
                    }
                    setInterval(nextSlide, 4000); // Change slide every 4 seconds
                </script>

                {% if session['role'] == 'admin' %}
                    <h3>➕ Add New Product / Brand Item</h3>
                    <form action="/add_product" method="POST" style="margin-bottom: 20px; background: #0f172a; padding: 10px; border: 1px solid #334155; border-radius: 4px;">
                        <div class="form-group">
                            <input type="text" name="name" placeholder="Product Name (e.g. Baby Diaper)" required>
                        </div>
                        <div class="form-group">
                            <input type="text" name="brand" placeholder="Company/Brand Name (e.g. Thai, Happy Nappy, Twinkle, Huggies)" required>
                        </div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <select name="size" required style="flex: 1;">
                                <option value="" disabled selected style="background-color: #0f172a;">Size</option>
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
                    <button type="submit" class="btn" style="background: #3b82f6; white-space: nowrap;">Search</button>
                    {% if search_query %}
                        <a href="/" class="btn" style="background: #475569; text-decoration: none; display: flex; align-items: center;">Reset</a>
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
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr {% if p.quantity < 5 %}class="low-stock-alert"{% endif %}>
                            <td><b>{{ p.brand }}</b> {% if p.quantity < 5 %}<span style="color:#ef4444; font-size:11px;">⚠️ Low Stock</span>{% endif %}</td>
                            <td>{{ p.name }}</td>
                            <td><b>{{ p.size }}</b></td>
                            <td><b>{{ p.quantity }}</b></td>
                            <td>৳{{ p.price }}</td>
                            <td>
                                <div style="display: flex; gap: 5px; align-items: center; flex-wrap: wrap;">
                                    {% if session['role'] == 'admin' %}
                                        <button type="button" class="btn" style="padding: 4px 8px; font-size: 12px; background: #10b981;" 
                                                onclick="quickAddStock({{ p.id }}, '{{ p.brand }} - {{ p.name }} ({{ p.size }})')">
                                            ➕ Add
                                        </button>
                                        <a href="/delete_product/{{ p.id }}" class="btn-danger" style="padding: 4px 8px; font-size: 12px; text-decoration: none; display: inline-block; text-align: center; width: auto;" onclick="return confirm('Are you sure you want to remove this product?')">Remove</a>
                                    {% else %}
                                        <button type="button" class="btn" style="padding: 4px 8px; font-size: 12px; background: #f59e0b;" 
                                                onclick="addToCart({{ p.id }}, '{{ p.brand }} - {{ p.name }} ({{ p.size }})', {{ p.quantity }}, {{ p.price }})">
                                            🛒 Add to Cart
                                        </button>
                                    {% endif %}
                                </div>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" style="text-align: center; color: #94a3b8;">No products found! Try another company name.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

                {% if session['role'] != 'admin' %}
                <div class="cart-box">
                    <h3 style="margin-top: 0; color: #fbbf24;">🛒 Cart & Checkout (Deduct Stock)</h3>
                    <div id="cart-items-container" style="font-size: 13px; margin-bottom: 10px;">
                        <p style="color: #94a3b8;">Your cart is empty. Add products from the stock list above.</p>
                    </div>
                    <div id="checkout-section" style="display: none;">
                        <p><b>Total Amount: ৳<span id="cart-total">0.00</span></b></p>
                        <form action="/quick_deduct_stock" method="POST">
                            <input type="hidden" name="cart_data" id="cart_data_input">
                            <button type="submit" class="btn" style="background: #ef4444; width: 100%;">🚨 Confirm & Deduct Stock</button>
                        </form>
                    </div>
                </div>
                {% endif %}

                <script>
                    let cart = [];

                    function quickAddStock(id, name) {
                        let qtyToAdd = prompt("Enter quantity to add to stock for " + name + ":");
                        if (qtyToAdd !== null && qtyToAdd.trim() !== "") {
                            let q = parseInt(qtyToAdd);
                            if (isNaN(q) || q <= 0) {
                                alert("Please enter a valid positive number!");
                                return;
                            }
                            
                            let form = document.createElement('form');
                            form.method = 'POST';
                            form.action = '/quick_add_stock';
                            
                            let idInput = document.createElement('input');
                            idInput.type = 'hidden';
                            idInput.name = 'product_id';
                            idInput.value = id;
                            form.appendChild(idInput);
                            
                            let qtyInput = document.createElement('input');
                            qtyInput.type = 'hidden';
                            qtyInput.name = 'add_qty';
                            qtyInput.value = q;
                            form.appendChild(qtyInput);
                            
                            document.body.appendChild(form);
                            form.submit();
                        }
                    }

                    function addToCart(id, name, maxQty, price) {
                        let qtyStr = prompt("Enter quantity for " + name + " (Available: " + maxQty + "):", "1");
                        if (qtyStr !== null && qtyStr.trim() !== "") {
                            let q = parseInt(qtyStr);
                            if (isNaN(q) || q <= 0) {
                                alert("Please enter a valid positive number!");
                                return;
                            }
                            if (q > maxQty) {
                                alert("Cannot add more than available stock (" + maxQty + ")!");
                                return;
                            }

                            let existing = cart.find(item => item.id === id);
                            if (existing) {
                                if (existing.qty + q > maxQty) {
                                    alert("Total quantity in cart exceeds available stock!");
                                    return;
                                }
                                existing.qty += q;
                            } else {
                                cart.push({ id: id, name: name, qty: q, price: price });
                            }
                            updateCartUI();
                        }
                    }

                    function removeFromCart(id) {
                        cart = cart.filter(item => item.id !== id);
                        updateCartUI();
                    }

                    function updateCartUI() {
                        let container = document.getElementById('cart-items-container');
                        let checkoutSec = document.getElementById('checkout-section');
                        let totalSpan = document.getElementById('cart-total');
                        let cartDataInput = document.getElementById('cart_data_input');

                        if (cart.length === 0) {
                            container.innerHTML = '<p style="color: #94a3b8;">Your cart is empty. Add products from the stock list above.</p>';
                            checkoutSec.style.display = 'none';
                            return;
                        }

                        let html = '<table style="background: #0f172a;"><tr><th>Product</th><th>Qty</th><th>Price</th><th>Action</th></tr>';
                        let total = 0;
                        cart.forEach(item => {
                            let subtotal = item.qty * item.price;
                            total += subtotal;
                            html += `<tr><td>${item.name}</td><td><b>${item.qty}</b></td><td>৳${subtotal}</td><td><button type="button" class="btn-danger" style="padding: 2px 6px; font-size: 11px; width: auto;" onclick="removeFromCart(${item.id})">Remove</button></td></tr>`;
                        });
                        html += '</table>';

                        container.innerHTML = html;
                        totalSpan.innerText = total.toFixed(2);
                        cartDataInput.value = JSON.stringify(cart);
                        checkoutSec.style.display = 'block';
                    }
                </script>

            {% elif page == 'reports' and session['role'] == 'admin' %}
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h3>📈 Monthly & Financial Overview ({{ current_month }})</h3>
                    <a href="/download_report_pdf" class="btn" style="background: #3b82f6; text-decoration: none; font-size: 13px;">📥 Download PDF Report</a>
                </div>
                
                <div class="grid-2">
                    <div class="stats-card">
                        <h4>📥 Monthly Stock In (Overall)</h4>
                        <p>Total Qty Added: <b>{{ monthly_in_qty }}</b></p>
                        <p>Total Investment: <b>৳{{ "%.2f"|format(monthly_in_val) }}</b></p>
                    </div>
                    <div class="stats-card" style="border-left-color: #f59e0b;">
                        <h4>📤 Monthly Sales (Overall)</h4>
                        <p>Total Qty Sold: <b>{{ monthly_out_qty }}</b></p>
                        <p>Total Sales Value: <b>৳{{ "%.2f"|format(monthly_out_val) }}</b></p>
                    </div>
                </div>

                <div class="stats-card" style="border-left-color: #10b981; margin-top: 10px;">
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
                            <td style="color: #34d399; font-weight: bold;">+{{ b.in_qty if b.in_qty else 0 }}</td>
                            <td style="color: #f87171; font-weight: bold;">-{{ b.out_qty if b.out_qty else 0 }}</td>
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
                            <td><span style="color:#f87171; font-weight:bold;">-{{ log.quantity_deducted }}</span></td>
                            <td>৳{{ log.total_price }}</td>
                            <td>{{ log.timestamp }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

            {% elif page == 'ai_advisor' and session['role'] == 'admin' %}
                <h3>🤖 Gemini AI Stock & Business Advisor</h3>
                <p style="font-size: 13px; color: #94a3b8;">Analyze inventory and sales data using Gemini AI and ask any business questions.</p>
                
                <form action="/ask_ai" method="POST" class="ai-box">
                    <div class="form-group">
                        <label><b>Ask Gemini AI (Type your question or prompt):</b></label>
                        <textarea name="ai_prompt" rows="3" placeholder="e.g., Which brand diaper sold the most this month? Or which brand stock should be increased?" required></textarea>
                    </div>
                    <button type="submit" class="btn" style="background: #a855f7;">Ask AI Assistant</button>
                </form>

                {% if ai_response %}
                    <div style="background: #0f172a; border: 1px solid #a855f7; padding: 15px; border-radius: 6px; margin-top: 15px;">
                        <h4 style="color: #c084fc; margin-top: 0;">💡 Gemini AI Response:</h4>
                        <p style="white-space: pre-line; line-height: 1.5; font-size: 14px; color: #f8fafc;">{{ ai_response }}</p>
                    </div>
                {% endif %}

            {% elif page == 'employees' and session['role'] == 'admin' %}
                <h3>👥 Employee List</h3>
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
                                    <a href="/delete_user/{{ emp.id }}" class="btn-danger" style="text-decoration: none; padding: 4px 8px; font-size: 12px; display: inline-block; text-align: center; width: auto;" onclick="return confirm('Delete this user?')">Delete</a>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

            {% elif page == 'settings' and session['role'] == 'admin' %}
                <div style="background: #7f1d1d; border: 1px solid #991b1b; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                    <h3 style="color: #fca5a5; margin-top: 0;">⚠️ Danger Zone: Emergency Database Reset</h3>
                    <p style="font-size: 13px; color: #cbd5e1;">To prevent accidental clicks, type <b>DELETE</b> in the box below to enable database reset.</p>
                    <form action="/reset_database_completely" method="POST">
                        <div class="form-group">
                            <input type="text" name="confirmation_code" placeholder="Type DELETE here..." required style="border: 1px solid #fca5a5;">
                        </div>
                        <button type="submit" class="btn-danger" style="background: #991b1b;">🗑️ Clear All Database Records</button>
                    </form>
                </div>

                <h3>⚙️ Change Admin Credentials</h3>
                <form action="/update_admin" method="POST" style="background: #0f172a; padding: 15px; border: 1px solid #334155; border-radius: 4px;">
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
                        <label>Email:</label>
                        <input type="email" name="email" required placeholder="your_email@gmail.com">
                    </div>
                    <div class="form-group">
                        <label>Password:</label>
                        <input type="password" name="password" required placeholder="******">
                    </div>
                    <button type="submit" class="btn" style="width: 100%;">Register Account</button>
                </form>
                <div style="text-align: center; margin-top: 15px; font-size: 13px;">
                    <a href="/" style="color: #60a5fa; text-decoration: none;">Already have an account? Login here</a>
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
                        <label>Email:</label>
                        <input type="email" name="email" required placeholder="admin@system.com">
                    </div>
                    <div class="form-group">
                        <label>Password:</label>
                        <input type="password" name="password" required placeholder="******">
                    </div>
                    <button type="submit" class="btn" style="width: 100%;">Login</button>
                </form>
                <div style="text-align: center; margin-top: 15px; font-size: 13px;">
                    <a href="/register" style="color: #60a5fa; text-decoration: none;">Don't have an account? Create one (Sign Up)</a>
                </div>
                <div style="margin-top: 15px; font-size: 12px; color: #94a3b8; background: #0f172a; padding: 8px; border: 1px solid #334155; border-radius: 4px;">
                    <b>Default Logins:</b><br>
                    • Admin: <code>admin@system.com</code> / <code>admin123</code><br>
                    • Employee: <code>emp@system.com</code> / <code>emp123</code>
                </div>
            {% endif %}
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
    cursor = conn.cursor()
    
    if search_query:
        cursor.execute("SELECT * FROM products WHERE brand ILIKE %s OR name ILIKE %s", 
                       ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template_string(HTML_TEMPLATE, page='dashboard', products=products, active_tab='inventory', search_query=search_query)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template_string(HTML_TEMPLATE, page='register')
        
    email = request.form['email'].strip()
    password = request.form['password']
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT COUNT(*) as cnt FROM users')
        user_count = cursor.fetchone()['cnt']
        role = 'admin' if user_count == 0 else 'employee'
        
        hashed_pass = generate_password_hash(password)
        cursor.execute('INSERT INTO users (email, password, role) VALUES (%s, %s, %s)', (email, hashed_pass, role))
        conn.commit()
        flash('Account created successfully! Please login.')
    except Exception as e:
        flash('Email already exists or registration failed!')
    
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()
    cursor.close()
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
        
    name = request.form['name'].strip()
    brand = request.form['brand'].strip()
    size = request.form['size'].strip()
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM products WHERE LOWER(brand) = LOWER(%s) AND LOWER(name) = LOWER(%s) AND LOWER(size) = LOWER(%s)', (brand, name, size))
    existing_product = cursor.fetchone()
    
    if existing_product:
        new_qty = existing_product['quantity'] + quantity
        cursor.execute('UPDATE products SET quantity = %s, price = %s WHERE id = %s', (new_qty, price, existing_product['id']))
    else:
        cursor.execute('INSERT INTO products (name, brand, size, quantity, price) VALUES (%s, %s, %s, %s, %s)', (name, brand, size, quantity, price))
        
    cursor.execute('INSERT INTO stock_in_logs (admin_email, product_name, brand, size, quantity_added, price_per_unit) VALUES (%s, %s, %s, %s, %s, %s)',
                 (session['user'], name, brand, size, quantity, price))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Product added/updated successfully!')
    return redirect(url_for('index'))

@app.route('/quick_add_stock', methods=['POST'])
def quick_add_stock():
    if session.get('role') != 'admin':
        flash('Only Admin can update stock!')
        return redirect(url_for('index'))
        
    product_id = request.form.get('product_id')
    add_qty = int(request.form.get('add_qty', 0))
    
    if product_id and add_qty > 0:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()
        
        if product:
            new_qty = product['quantity'] + add_qty
            cursor.execute('UPDATE products SET quantity = %s WHERE id = %s', (new_qty, product_id))
            cursor.execute('INSERT INTO stock_in_logs (admin_email, product_name, brand, size, quantity_added, price_per_unit) VALUES (%s, %s, %s, %s, %s, %s)',
                         (session['user'], product['name'], product['brand'], product['size'], add_qty, product['price']))
            conn.commit()
            flash(f"Successfully added {add_qty} pcs to {product['brand']} ({product['size']})!")
        
        cursor.close()
        conn.close()
        
    return redirect(url_for('index'))

@app.route('/quick_deduct_stock', methods=['POST'])
def quick_deduct_stock():
    cart_data_str = request.form.get('cart_data')
    if not cart_data_str:
        flash('Cart is empty!')
        return redirect(url_for('index'))
        
    try:
        cart_items = json.loads(cart_data_str)
    except:
        flash('Invalid cart data!')
        return redirect(url_for('index'))
        
    conn = get_db()
    cursor = conn.cursor()
    
    for item in cart_items:
        p_id = item['id']
        deduct_qty = int(item['qty'])
        
        cursor.execute('SELECT * FROM products WHERE id = %s', (p_id,))
        product = cursor.fetchone()
        
        if product and product['quantity'] >= deduct_qty:
            new_qty = product['quantity'] - deduct_qty
            total_price = deduct_qty * product['price']
            
            cursor.execute('UPDATE products SET quantity = %s WHERE id = %s', (new_qty, p_id))
            cursor.execute('INSERT INTO logs (user_email, product_name, brand, size, quantity_deducted, total_price) VALUES (%s, %s, %s, %s, %s, %s)',
                         (session['user'], product['name'], product['brand'], product['size'], deduct_qty, total_price))
            
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Cart checked out and stock deducted successfully!')
    return redirect(url_for('index'))

@app.route('/delete_product/<int:id>')
def delete_product(id):
    if session.get('role') != 'admin':
        flash('Only Admin can delete products!')
        return redirect(url_for('index'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Product removed successfully!')
    return redirect(url_for('index'))

@app.route('/reports')
def reports():
    if session.get('role') != 'admin':
        flash('Access restricted to Admin only!')
        return redirect(url_for('index'))
        
    current_month_str = datetime.now().strftime('%Y-%m')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(quantity_added) as qty, SUM(quantity_added * price_per_unit) as val FROM stock_in_logs WHERE TO_CHAR(timestamp, 'YYYY-MM') = %s", (current_month_str,))
    stock_in = cursor.fetchone()
    monthly_in_qty = stock_in['qty'] if stock_in and stock_in['qty'] else 0
    monthly_in_val = stock_in['val'] if stock_in and stock_in['val'] else 0.0

    cursor.execute("SELECT SUM(quantity_deducted) as qty, SUM(total_price) as val FROM logs WHERE TO_CHAR(timestamp, 'YYYY-MM') = %s", (current_month_str,))
    stock_out = cursor.fetchone()
    monthly_out_qty = stock_out['qty'] if stock_out and stock_out['qty'] else 0
    monthly_out_val = stock_out['val'] if stock_out and stock_out['val'] else 0.0

    cursor.execute("SELECT SUM(quantity) as qty, SUM(quantity * price) as val FROM products")
    products = cursor.fetchone()
    total_stock_qty = products['qty'] if products and products['qty'] else 0
    total_stock_val = products['val'] if products and products['val'] else 0.0

    cursor.execute("SELECT DISTINCT brand FROM products UNION SELECT DISTINCT brand FROM stock_in_logs UNION SELECT DISTINCT brand FROM logs")
    brands_list = cursor.fetchall()
    
    brand_reports = []
    for b_row in brands_list:
        b_name = b_row['brand']
        cursor.execute("SELECT SUM(quantity) as qty, SUM(quantity * price) as val FROM products WHERE brand = %s", (b_name,))
        cur = cursor.fetchone()
        
        cursor.execute("SELECT SUM(quantity_added) as qty FROM stock_in_logs WHERE brand = %s AND TO_CHAR(timestamp, 'YYYY-MM') = %s", (b_name, current_month_str))
        in_res = cursor.fetchone()
        
        cursor.execute("SELECT SUM(quantity_deducted) as qty FROM logs WHERE brand = %s AND TO_CHAR(timestamp, 'YYYY-MM') = %s", (b_name, current_month_str))
        out_res = cursor.fetchone()
        
        brand_reports.append({
            'brand': b_name,
            'current_qty': cur['qty'] if cur and cur['qty'] else 0,
            'current_val': cur['val'] if cur and cur['val'] else 0.0,
            'in_qty': in_res['qty'] if in_res and in_res['qty'] else 0,
            'out_qty': out_res['qty'] if out_res['qty'] else 0
        })

    cursor.execute('SELECT * FROM logs ORDER BY timestamp DESC')
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, page='reports', 
                                  monthly_in_qty=monthly_in_qty, monthly_in_val=monthly_in_val,
                                  monthly_out_qty=monthly_out_qty, monthly_out_val=monthly_out_val,
                                  total_stock_qty=total_stock_qty, total_stock_val=total_stock_val,
                                  brand_reports=brand_reports,
                                  logs=logs, active_tab='reports', current_month=current_month_str)

@app.route('/download_report_pdf')
def download_report_pdf():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    current_month_str = datetime.now().strftime('%Y-%m')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(quantity) as qty, SUM(quantity * price) as val FROM products")
    products = cursor.fetchone()
    cursor.close()
    conn.close()
    
    # Simple HTML text format exportable as text/HTML or downloadable report
    report_content = f"""
    KHAN INVENTORY SYSTEM - FINANCIAL REPORT ({current_month_str})
    --------------------------------------------------
    Total Products in Stock: {products['qty'] if products and products['qty'] else 0} Pcs
    Total Asset Value: BDT {products['val'] if products and products['val'] else 0.0}
    Generated by: {session['user']}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    response = make_response(report_content)
    response.headers["Content-Disposition"] = f"attachment; filename=inventory_report_{current_month_str}.txt"
    response.headers["Content-Type"] = "text/plain"
    return response

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
    cursor = conn.cursor()
    cursor.execute("SELECT brand, name, size, quantity, price FROM products")
    products = cursor.fetchall()
    cursor.execute("SELECT brand, product_name, size, quantity_deducted, timestamp FROM logs ORDER BY timestamp DESC LIMIT 20")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    
    stock_summary = "\n".join([f"- Brand: {p['brand']}, Product: {p['name']}, Size: {p['size']}, Qty: {p['quantity']}, Price: {p['price']}" for p in products])
    sales_summary = "\n".join([f"- Sold: {l['quantity_deducted']} of {l['brand']} ({l['product_name']} size {l['size']}) at {l['timestamp']}" for l in logs])
    
    context = f"""
    You are an expert inventory and business advisor for a baby diaper shop. 
    Here is the current stock status:
    {stock_summary if stock_summary else "No stock available."}
    
    Here is the recent sales history:
    {sales_summary if sales_summary else "No sales yet."}
    
    Please answer the admin's question in professional and helpful English:
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
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template_string(HTML_TEMPLATE, page='employees', employees=employees, active_tab='employees')

@app.route('/delete_user/<int:id>')
def delete_user(id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
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
    cursor = conn.cursor()
    if new_pass:
        hashed_pass = generate_password_hash(new_pass)
        cursor.execute('UPDATE users SET email = %s, password = %s WHERE email = %s', (new_email, hashed_pass, session['user']))
    else:
        cursor.execute('UPDATE users SET email = %s WHERE email = %s', (new_email, session['user']))
    conn.commit()
    cursor.close()
    conn.close()
    
    session['user'] = new_email
    flash('Admin credentials updated successfully!')
    return redirect(url_for('settings'))

# --- SECURE PERMANENT DATABASE RESET ROUTE ---
@app.route('/reset_database_completely', methods=['POST'])
def reset_database_completely():
    if session.get('role') != 'admin':
        flash('Unauthorized access!')
        return redirect(url_for('index'))
        
    confirmation = request.form.get('confirmation_code', '').strip()
    if confirmation != 'DELETE':
        flash('Incorrect confirmation word! Database was not reset.')
        return redirect(url_for('settings'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products;')
    cursor.execute('DELETE FROM stock_in_logs;')
    cursor.execute('DELETE FROM logs;')
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Database and all reports have been completely cleared successfully!')
    return redirect(url_for('settings'))
# ---------------------------------------------

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
