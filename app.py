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

# Список допустимых артикулов (001–181)
valid_skus = {f"{i:03d}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("type") == "market_order_new":
        order = data["object"]
        items = order.get("items", [])
        delivery = order.get("delivery", {})

        # Проверка: delivery может быть строкой (например, "pickup")
        if isinstance(delivery, str):
            delivery = {}

        # Извлечение данных клиента
        name = order.get("customer_name", "")
        phone = order.get("customer_phone", "")
        comment = order.get("comment", "")

        # Адрес
        street = delivery.get("address", {}).get("street", "")
        house = delivery.get("address", {}).get("house", "")
        address = f"{street}, {house}".strip(", ")

        # Если самовывоз — добавим пометку
        if order.get("delivery_type") == "pickup":
            address = "Самовывоз"

        # Первый товар
        first_item = items[0]
        sku = first_item.get("sku")

        # Проверка на допустимый SKU
        if sku not in valid_skus:
            print(f"❌ Неизвестный SKU: {sku}")
            return "ok"

        quantity = int(first_item.get("quantity", 1))

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
