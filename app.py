from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# Токен подтверждения от VK (указан на вкладке Callback API)
VK_CONFIRMATION_TOKEN = '3a6a509a'

# Доступы к FrontPad
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

@app.route("/", methods=["POST"])
def handle_vk_event():
    data = request.get_json()
    if not data:
        return "no data"

    event_type = data.get("type")

    if event_type == "confirmation":
        return VK_CONFIRMATION_TOKEN

    elif event_type == "market_order_new":
        try:
            order = data["object"]
            recipient = order["recipient"]
            phone = recipient.get("phone", "")
            name = recipient.get("name", "")
            comment = order.get("comment", "")
            address = order["delivery"].get("address", "")
            order_items = order["preview_order_items"]

            items = {}
            for item in order_items:
                sku = item.get("item", {}).get("sku")
                quantity = item.get("quantity", 1)
                if sku:
                    items[sku] = quantity

            payload = {
                "request": "add_order",
                "key": FRONTPAD_API_KEY,
                "secret": FRONTPAD_SECRET,
                "phone": phone,
                "name": name,
                "address": address,
                "comment": comment,
                "source": "VK"
            }

            for idx, (product_id, qty) in enumerate(items.items(), start=1):
                payload[f"product[{idx}]"] = product_id
                payload[f"product_kol[{idx}]"] = qty

            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            print("🟢 Ответ от FrontPad:", response.text)
            return "ok"
        except Exception as e:
            print("🔴 Ошибка:", str(e))
            return "error"

    return "unsupported"

@app.route("/", methods=["GET"])
def index():
    return "VK-Fronpad connector is working!"
