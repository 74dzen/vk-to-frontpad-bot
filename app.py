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

        # Защита от случая, когда delivery — это строка (например, "pickup")
        if not isinstance(delivery, dict):
            delivery = {}

        address_data = delivery.get("address", {})
        street = address_data.get("street", "")
        house = address_data.get("house", "")
        address = f"{street}, {house}".strip(", ")

        # Если тип доставки явно указан как самовывоз — помечаем
        if order.get("delivery_type") == "pickup":
            address = "Самовывоз"

        name = order.get("customer_name", "")
        phone = order.get("customer_phone", "")
        comment = order.get("comment", "")

        # Обработка первого товара
        first_item = items[0]
        sku = first_item.get("sku")
        quantity = int(first_item.get("quantity", 1))

        # Проверка на допустимый артикул
        if sku not in valid_skus:
            print(f"❌ Ошибка: неизвестный SKU {sku}")
            return "ok"

        # Отправка заказа в FrontPad
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

