# app.py

import os
import json
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Сопоставление SKU -> артикул (от 001 до 181)
sku_to_article = {str(i).zfill(3): str(i).zfill(3) for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info("📩 Получены данные от VK: %s", data)

    # Обрабатываем событие создания заказа
    if data.get("type") == "market_order_new":
        order = data.get("object", {})
        first_name = order.get("first_name", "")
        last_name = order.get("last_name", "")
        phone = order.get("phone", "")
        address_data = order.get("address", {})
        comment = order.get("comment", "")
        items = order.get("items", [])

        full_name = f"{first_name} {last_name}".strip()

        # Обработка адреса
        if isinstance(address_data, dict):
            street = address_data.get("street", "")
            city = address_data.get("city", "")
            delivery_address = f"{city}, {street}".strip(", ")
        else:
            delivery_address = ""

        # Обработка товаров
        products = []
        for item in items:
            sku = item.get("sku", "").zfill(3)
            quantity = int(item.get("quantity", 1))
            article = sku_to_article.get(sku)
            if article:
                products.append({"article": article, "quantity": quantity})

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": full_name,
            "delivery_address": delivery_address,
            "comment": comment,
            "products": json.dumps(products, ensure_ascii=False),
        }

        logging.info("📦 Отправляем заказ в FrontPad: %s", payload)

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload, timeout=10)
            response_data = response.json() if response.text else None
            logging.info("✅ Ответ от FrontPad: %s", response_data)

            if not response_data or response_data.get("result") != "success":
                logging.error("❌ Ошибка от FrontPad: %s", response_data.get("error") if response_data else "Нет ответа")
        except Exception as e:
            logging.exception("🚨 Исключение при отправке запроса в FrontPad: %s", e)

    return "ok"
