# 📦 Khan Enterprise Multi-Vendor Inventory & Stock Neural Engine

https://inventory-system-g6nw.onrender.com

[![Security](https://img.shields.io/badge/Security-Zero--Trust%20%7C%20RBAC-red?style=for-the-badge&logo=springsecurity)](https://github.com/hossain53504-hub/inventory-system)
[![AI Engine](https://img.shields.io/badge/AI%20Core-Gemini%20Flash%20Predictive%20Analytics-blueviolet?style=for-the-badge&logo=google)](https://github.com/hossain53504-hub/inventory-system)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20Relational%20Cluster-blue?style=for-the-badge&logo=postgresql)](https://github.com/hossain53504-hub/inventory-system)
[![Architecture](https://img.shields.io/badge/Architecture-Multi--Vendor%20%7C%20Cloud--Native-success?style=for-the-badge&logo=flask)](https://github.com/hossain53504-hub/inventory-system)

> **Khan Inventory System** is a hyper-secure, next-generation multi-vendor inventory management engine designed for high-concurrency retail, pharmacy networks, and e-commerce supply chains. Powered by Google Gemini AI and isolated multi-tenant architecture, it offers real-time stock deduction, multi-role security, and automated financial invoicing.

---

## ⚡ Key Engineering & Core Features

### 🏢 Multi-Vendor & Multi-Tenant Isolation
* **Isolated Vendor Workspaces:** Secure multi-vendor partitioning where each merchant manages their own warehouse stock, pricing rules, and suppliers safely.
* **Strict Role-Based Access Control (RBAC):** Fine-grained permission matrix differentiating Super-Admin, Vendor Admins, Warehouse Managers, and Cashiers/Employees.

### 🛡️ Super-Security & Compliance Architecture
* **Zero-Trust Access Matrix:** End-to-end encrypted API endpoints with tokenized session control.
* **Cryptographic Audit Trail:** Immutable logging for every stock-in, deduction, price alteration, and user activity.
* **SQL Injection & Fraud Shield:** Parameterized queries via `Psycopg2` with strict input sanitization.

### 🤖 Gemini AI Predictive Advisor & Analytics
* **Demand Forecasting:** Automated stock run-out predictions powered by Google Gemini AI to prevent supply chain bottlenecks.
* **Smart Business Insights:** AI-generated sales reports, anomaly detection for inventory shrinkage, and dynamic re-order recommendations.

### 📊 Automated Reporting & Enterprise Checkout
* **Smart POS & Instant Cart:** Real-time atomic stock deduction during POS checkout to prevent race conditions.
* **Official Document Generator:** Automated PDF/HTML invoice generation for monthly auditing, vendor payouts, and receipt printing.

---

## 🛠️ Technology Stack

* **Core Backend:** Python (Flask Engine, WSGI Middleware)
* **Database Layer:** PostgreSQL (Cloud-Hosted on Render / Managed Cluster via `Psycopg2`)
* **AI Intelligence:** Google Generative AI (`Gemini Flash` Integration)
* **Frontend UI/UX:** HTML5, CSS3 (Glassmorphism Dark Theme), Modern JavaScript, Framer/CSS Animation Engine

---

## 🏗️ System Architecture Flow

```text
[ Multi-Vendor Clients / POS Terminals ]
                   │
                   ▼ (TLS 1.3 / Encrypted Endpoint)
        [ Flask Security Gateway ]
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
[ RBAC Auth ] [ Stock Engine ] [ Gemini AI ]
    │              │              │
    └──────────────┼──────────────┘
                   ▼
       [ PostgreSQL Database ]
```

---

## 🚀 Quick Setup & Installation

### Prerequisites
* **Python:** `v3.10+`
* **PostgreSQL:** Cloud or Local Instance
* **Gemini API Key:** From Google AI Studio

### Installation Steps

1. **Clone Repository:**
   ```bash
   git clone https://github.com/hossain53504-hub/inventory-system.git
   cd inventory-system
   ```

2. **Set Up Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration (`.env`):**
   ```env
   SECRET_KEY=your_hyper_secure_flask_secret
   DATABASE_URL=postgresql://user:password@host:5432/inventory_db
   GEMINI_API_KEY=your_google_gemini_api_key
   ```

5. **Initialize Database & Run Application:**
   ```bash
   python app.py
   ```

---

## 📜 License & Ownership

Developed and maintained by **MD Hossain Khan**. Released under the **MIT License**.