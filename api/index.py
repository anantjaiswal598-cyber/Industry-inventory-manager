from flask import Flask, request, jsonify
import json
import urllib.request
from datetime import datetime
import os
from twilio.rest import Client

app = Flask(__name__)

FIREBASE_URL = "https://industry-e1b0b-default-rtdb.firebaseio.com/.json"

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"

def send_whatsapp_alert(message_body, phone_number):
    if not phone_number: return
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message_body, from_=TWILIO_WHATSAPP_FROM, to=phone_number)
    except Exception as e:
        print(f"Twilio WhatsApp Error: {e}")

def check_low_stock_and_alert(data):
    stock = {}
    for p in data["purchases"]:
        stock[p["item"]] = stock.get(p["item"], 0) + p["quantity"]
    for u in data["usage"]:
        if u["item"] in stock: stock[u["item"]] -= u["quantity"]
            
    low_stock_items = [item for item, qty in stock.items() if qty < 50]
    admin_phone = data.get("admin_whatsapp")
    if low_stock_items and admin_phone:
        msg = f"🚨 *Industry Alert: Low Stock Warning!*\n\nThe following items have dropped below 50 units:\n• " + "\n• ".join(low_stock_items) + "\n\nPlease restock soon!"
        send_whatsapp_alert(msg, admin_phone)

def load_data():
    default_data = {
        "purchases": [], "usage": [], "suppliers": [], "barcodes": {},
        "admin_whatsapp": "",
        "users": {"admin": {"password": "admin123", "role": "admin"}}
    }
    try:
        req = urllib.request.Request(FIREBASE_URL)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data is None: return default_data
            if "purchases" not in data or data["purchases"] is None: data["purchases"] = []
            if "usage" not in data or data["usage"] is None: data["usage"] = []
            if "suppliers" not in data or data["suppliers"] is None: data["suppliers"] = []
            if "barcodes" not in data or data["barcodes"] is None: data["barcodes"] = {}
            if "admin_whatsapp" not in data: data["admin_whatsapp"] = ""
            if "users" not in data or data["users"] is None: data["users"] = default_data["users"]
            return data
    except Exception as e:
        print(f"Error loading from Firebase: {e}")
        return default_data

def save_data(data):
    try:
        req = urllib.request.Request(FIREBASE_URL, data=json.dumps(data).encode(), method='PUT')
        req.add_header('Content-Type', 'application/json')
        urllib.request.urlopen(req)
        check_low_stock_and_alert(data)
    except Exception as e:
        print(f"Error saving to Firebase: {e}")

@app.route('/api/login', methods=['POST'])
def login():
    data = load_data()
    req = request.json
    username = req.get("username", "").lower()
    password = req.get("password", "")
    portal = req.get("portal", "") 
    user = data["users"].get(username)
    if user and user["password"] == password:
        if portal == "admin" and user["role"] != "admin":
            return jsonify({"success": False, "message": "Admin privileges required."}), 403
        return jsonify({"success": True, "role": user["role"]})
    return jsonify({"success": False, "message": "Invalid username or password."}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = load_data()
    req = request.json
    username = req.get("username", "").lower()
    password = req.get("password", "")
    if not username or not password: return jsonify({"success": False, "message": "Missing fields"}), 400
    if username in data["users"]: return jsonify({"success": False, "message": "Username already exists."}), 409
    data["users"][username] = {"password": password, "role": "staff"}
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/resolve_barcode', methods=['GET'])
def resolve_barcode():
    data = load_data()
    code = request.args.get('code')
    return jsonify({"name": data["barcodes"].get(code, "")})

@app.route('/api/link_barcode', methods=['POST'])
def link_barcode():
    data = load_data()
    req = request.json
    data["barcodes"][req.get("barcode")] = req.get("name")
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/set_admin_whatsapp', methods=['POST'])
def set_admin_whatsapp():
    data = load_data()
    req = request.json
    if req.get("role") != "admin": return jsonify({"success": False, "message": "Unauthorized"}), 403
    data["admin_whatsapp"] = req.get("whatsapp", "")
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/get_admin_whatsapp', methods=['GET'])
def get_admin_whatsapp():
    data = load_data()
    return jsonify({"whatsapp": data.get("admin_whatsapp", "")})

@app.route('/api/stock', methods=['GET'])
def get_stock():
    data = load_data()
    stock, units = {}, {}
    for p in data["purchases"]:
        stock[p["item"]] = stock.get(p["item"], 0) + p["quantity"]
        units[p["item"]] = p["unit"]
    for u in data["usage"]:
        if u["item"] in stock: stock[u["item"]] -= u["quantity"]
    
    stock_list = []
    for k, v in stock.items():
        status = "Normal"
        if v < 50: status = "Low Stock"
        if v <= 0: status = "Out of Stock"
        stock_list.append({"item": k, "remaining": v, "unit": units.get(k, ""), "status": status})
    return jsonify(stock_list)

@app.route('/api/category_distribution', methods=['GET'])
def get_category_distribution():
    data = load_data()
    categories = {}
    for p in data["purchases"]:
        cat = p.get("category", "Uncategorized")
        categories[cat] = categories.get(cat, 0) + p["quantity"]
    return jsonify({"labels": list(categories.keys()), "data": list(categories.values())})

@app.route('/api/purchase', methods=['POST'])
def add_purchase():
    data = load_data()
    req = request.json
    supplier_name = req.get("supplier")
    source = req.get("source", "")
    if supplier_name and not any(s["name"].lower() == supplier_name.lower() for s in data["suppliers"]):
        data["suppliers"].append({"name": supplier_name, "location": source})
    data["purchases"].append({
        "date": req.get("date") or datetime.now().strftime("%Y-%m-%d"),
        "category": req.get("category", "Uncategorized"),
        "item": req.get("item"),
        "supplier": supplier_name,
        "source": source,
        "quantity": float(req.get("quantity", 0)),
        "unit": req.get("unit"),
        "price": float(req.get("price", 0)),
    })
    save_data(data)
    return jsonify({"message": "Purchase saved."})

@app.route('/api/usage', methods=['POST'])
def add_usage():
    data = load_data()
    req = request.json
    data["usage"].append({
        "date": req.get("date") or datetime.now().strftime("%Y-%m-%d"),
        "item": req.get("item"),
        "quantity": float(req.get("quantity", 0)),
        "purpose": req.get("purpose"),
    })
    save_data(data)
    return jsonify({"message": "Usage saved."})

@app.route('/api/monthly_usage', methods=['GET'])
def get_monthly_usage():
    data = load_data()
    monthly = {}
    for u in data["usage"]:
        purpose = u.get("purpose", "Other") 
        monthly[purpose] = monthly.get(purpose, 0) + u["quantity"]
    return jsonify({"labels": list(monthly.keys()), "data": list(monthly.values())})

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify(data["purchases"])

@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    data = load_data()
    stats = {}
    for p in data["purchases"]:
        name = p.get("supplier", "Unknown")
        stats.setdefault(name, {"count": 0, "total": 0})
        stats[name]["count"] += 1
        stats[name]["total"] += p.get("price", 0)
    result = []
    for s in data["suppliers"]:
        name = s["name"]
        result.append({"name": name, "location": s.get("location", ""), "count": stats.get(name, {}).get("count", 0), "total": stats.get(name, {}).get("total", 0)})
    return jsonify(result)

@app.route('/api/supplier_action', methods=['POST'])
def manage_supplier():
    data = load_data()
    req = request.json
    action, name = req.get("action"), req.get("name")
    if action == "add":
        if not any(s["name"].lower() == name.lower() for s in data["suppliers"]):
            data["suppliers"].append({"name": name, "location": req.get("location", "")})
    elif action == "delete":
        if req.get("role") != "admin": return jsonify({"error": "Unauthorized"}), 403
        data["suppliers"] = [s for s in data["suppliers"] if s["name"].lower() != name.lower()]
    save_data(data)
    return jsonify({"message": "Success"})
