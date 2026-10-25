from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# ডাটাবেজ ইনিশিয়ালাইজ করার ফাংশন
def init_db():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# হোম পেজ / এমপ্লয়ি ও এডমিন ড্যাশবোর্ড
@app.route('/')
def index():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, products=products)

# নতুন প্রোডাক্ট যোগ করার রুট (এডমিন)
@app.route('/add', methods=['POST'])
def add_product():
    name = request.form['name']
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])
    
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, quantity, price) VALUES (?, ?, ?)', (name, quantity, price))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# স্টক কমানোর রুট (এমপ্লয়ি)
@app.route('/deduct/<int:product_id>', methods=['POST'])
def deduct_stock(product_id):
    deduct_qty = int(request.form['deduct_qty'])
    
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    
    # বর্তমান পরিমাণ চেক করা
    cursor.execute('SELECT quantity FROM products WHERE id = ?', (product_id,))
    current_qty = cursor.fetchone()[0]
    
    new_qty = max(0, current_qty - deduct_qty)
    
    cursor.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_qty, product_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ফ্রন্টএন্ড ডিজাইন (HTML + CSS)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inventory Management System</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2, h3 { color: #007bff; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: center; }
        th { background-color: #007bff; color: white; }
        form { display: inline-block; margin: 0; }
        input[type="text"], input[type="number"] { padding: 6px; margin: 4px 0; width: 120px; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #28a745; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
        button.deduct { background: #dc3545; }
        button:hover { opacity: 0.9; }
        .section { margin-bottom: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📦 Inventory Management System</h2>
        
        <!-- এডমিন সেকশন: প্রোডাক্ট যোগ করা -->
        <div class="section">
            <h3>Add New Product (Admin)</h3>
            <form action="/add" method="POST">
                <input type="text" name="name" placeholder="Product Name" required>
                <input type="number" name="quantity" placeholder="Quantity" required>
                <input type="text" name="price" placeholder="Price" required>
                <button type="submit">Add Product</button>
            </form>
        </div>

        <!-- এমপ্লয়ি ও স্টক লিস্ট সেকশন -->
        <div class="section">
            <h3>Product Stock (Employee & Admin)</h3>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Product Name</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Action (Deduct Stock)</th>
                </tr>
                {% for product in products %}
                <tr>
                    <td>{{ product[0] }}</td>
                    <td>{{ product[1] }}</td>
                    <td><b>{{ product[2] }}</b></td>
                    <td>{{ product[3] }}</td>
                    <td>
                        <form action="/deduct/{{ product[0] }}" method="POST">
                            <input type="number" name="deduct_qty" value="1" min="1" max="{{ product[2] }}" required style="width: 60px;">
                            <button type="submit" class="deduct">Deduct</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5">No products found in inventory.</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
