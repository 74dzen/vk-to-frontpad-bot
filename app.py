from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# Токен подтверждения от VK
VK_CONFIRMATION_TOKEN = '3a6a509a'

# Доступы к FrontPad
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

@app.route("/", methods=["POST"])
def handle_vk_event():
    data = request.get_json()
    if not data:
        print("🔴 Нет данных от VK")
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
            address = order.get("delivery", {}).get("address", "")
            order_items = order.get("preview_order_items", [])

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

            for idx, item in enumerate(order_items):
                sku = item.get("item", {}).get("sku")
                quantity = item.get("quantity", 1)
                if sku:
                    payload[f"items[{idx}][id]"] = sku
                    payload[f"items[{idx}][quantity]"] = quantity

            print("📦 Отправка в FrontPad:", json.dumps(payload, indent=2, ensure_ascii=False))
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            print("🟢 Ответ от FrontPad:", response.text)
            return "ok"
        except Exception as e:
            print("🔴 Ошибка:", str(e))
            return "error"

    print("⚠️ Необработанный тип события:", event_type)
    return "unsupported"

@app.route("/", methods=["GET"])
def index():
    return "VK-Fronpad connector is working!"
