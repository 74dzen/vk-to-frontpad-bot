import os
import json
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Таблица соответствия SKU → артикул (артикулы от 001 до 181)
sku_to_article = {f"{i:03d}": f"{i:03d}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📩 Получен запрос от VK: {data}")

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("type") == "market_order_new":
        order = data["object"]
        items = order.get("items", [])

        if not items:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        # Собираем товары для заказа
        products = []
        for item in items:
            sku = str(item.get("item", {}).get("sku", "")).strip()
            quantity = item.get("quantity", 1)

            article = sku_to_article.get(sku)
            if article:
                products.append({
                    "article": article,
                    "quantity": quantity
                })
            else:
                logging.warning(f"⚠️ SKU {sku} не найден в таблице соответствия. Пропускаем.")

        if not products:
            logging.warning("⚠️ Не удалось найти ни одного подходящего артикула. Пропускаем заказ.")
            return "ok"

        # Адрес
        address_data = order.get("recipient", {}).get("address", {})
        if isinstance(address_data, str):
            address_str = address_data
        else:
            city = address_data.get("city", "")
            street = address_data.get("street", "")
            house = address_data.get("house", "")
            address_str = f"{city}, {street}, {house}".strip(", ")

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": order.get("recipient", {}).get("phone", ""),
            "name": order.get("recipient", {}).get("name", ""),
            "delivery_address": address_str,
            "comment": order.get("comment", ""),
            "products": products  # ⬅️ ВАЖНО: оставляем как список, НЕ строка!
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", json=payload)
            logging.info(f"✅ Ответ от FrontPad: {response.text}")
            response_data = response.json()

            if not isinstance(response_data, dict):
                logging.error("❌ Ответ от FrontPad не является словарём. Возможно, проблема на стороне FrontPad.")
            elif response_data.get("result") != "success":
                logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
        except Exception as e:
            logging.exception(f"❌ Ошибка при отправке заказа в FrontPad: {e}")

    return "ok"
