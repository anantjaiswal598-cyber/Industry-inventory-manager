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
        print(f
