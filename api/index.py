from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# File path for serverless storage on Vercel
DATA_FILE = '/tmp/crusher_data.json'

# Hardcoded roles for Phase 1
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"purchases": [], "usage": [], "suppliers_deleted": []}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"purchases": [], "usage": [], "suppliers_deleted": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/api/login', methods=['POST'])
def login():
    req = request.json
    username = req.get('username')
    password = req.get('password')
    if username in USERS and USERS[username]['password'] == password:
        return jsonify({"success": True, "role": USERS[username]['role']})
    return jsonify({"success": False}), 401

@app.route('/api/purchase', methods=['POST'])
def add_purchase():
    data = load_data()
    req = request.json
    purchase = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "category": req.get('category'),
        "item": req.get('item'),
        "supplier": req.get('supplier'),
        "source": req.get('source'),
        "quantity": float(req.get('quantity', 0)),
        "unit": req.get('unit'),
        "price": float(req.get('price', 0))
    }
    data["purchases"].append(purchase)
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/usage', methods=['POST'])
def add_usage():
    data = load_data()
    req = request.json
    usage = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "item": req.get('item'),
        "quantity": float(req.get('quantity', 0)),
        "purpose": req.get('purpose')
    }
    data["usage"].append(usage)
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/stock', methods=['GET'])
def get_stock():
    data = load_data()
    stock = {}
    
    # Add purchases
    for p in data["purchases"]:
        item = p["item"]
        if item not in stock:
            stock[item] = {"remaining": 0, "unit": p["unit"]}
        stock[item]["remaining"] += p["quantity"]
        
    # Subtract usage
    for u in data["usage"]:
        item = u["item"]
        if item in stock:
            stock[item]["remaining"] -= u["quantity"]
            
    # Format for frontend
    result = [{"item": k, "remaining": v["remaining"], "unit": v["unit"]} for k, v in stock.items()]
    return jsonify(result)

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify(data["purchases"])

@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    data = load_data()
    suppliers = {}
    deleted_suppliers = data.get("suppliers_deleted", [])
    
    for p in data["purchases"]:
        name = p["supplier"]
        if name and name not in deleted_suppliers:
            if name not in suppliers:
                suppliers[name] = {"name": name, "location": p["source"], "count": 0}
            suppliers[name]["count"] += 1
            
    return jsonify(list(suppliers.values()))

@app.route('/api/supplier_action', methods=['POST'])
def supplier_action():
    req = request.json
    if req.get('role') != 'admin':
        return jsonify({"success": False, "error": "Unauthorized"}), 403
        
    if req.get('action') == 'delete':
        data = load_data()
        name = req.get('name')
        if "suppliers_deleted" not in data:
            data["suppliers_deleted"] = []
        if name not in data["suppliers_deleted"]:
            data["suppliers_deleted"].append(name)
        save_data(data)
        return jsonify({"success": True})
        
    return jsonify({"success": False}), 400

@app.route('/api/monthly_usage', methods=['GET'])
def get_monthly_usage():
    data = load_data()
    usage_counts = {}
    
    for u in data["usage"]:
        purpose = u.get("purpose", "Other")
        if purpose not in usage_counts:
            usage_counts[purpose] = 0
        usage_counts[purpose] += 1
        
    labels = list(usage_counts.keys())
    values = list(usage_counts.values())
    
    return jsonify({"labels": labels, "data": values})

# For local testing
if __name__ == '__main__':
    app.run(debug=True)
