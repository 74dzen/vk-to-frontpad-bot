import os
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
FRONTPAD_URL = "https://app.frontpad.ru/api/index.php"

valid_skus = {f"{i:03d}" for i in range(1, 182)}  # 001–181

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("type") == "market_order_new":
        order = data["object"]
        items = order.get("items", [])
        delivery = order.get("delivery", {})

        # Проверка: если delivery — строка, превращаем в пустой словарь
        if not isinstance(delivery, dict):
            delivery = {}

        address = "Не указано"

        # Проверка: если address — словарь, собираем улицу и дом
        if isinstance(delivery.get("address"), dict):
            street = delivery["address"].get("street", "")
            house = delivery["address"].get("house", "")
            address = f"{street}, {house}".strip(", ")
        elif isinstance(delivery.get("address"), str):
            address = delivery["address"]

        # Обработка самовывоза
        if order.get("delivery_type") == "pickup":
            address = "Самовывоз"

        name = order.get("customer_name", "")
        phone = order.get("customer_phone", "")
        comment = order.get("comment", "")

        first_item = items[0]
        sku = first_item.get("sku")
        quantity = int(first_item.get("quantity", 1))

        if sku not in valid_skus:
            print(f"❌ Ошибка: неизвестный SKU {sku}")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "comment": comment,
            "delivery_address": address,
            "products[0][id]": sku,
            "products[0][quantity]": quantity
        }

        response = requests.post(FRONTPAD_URL, data=payload)
        print("✅ Ответ от FrontPad:", response.text)
        return "ok"

    return "ok"
