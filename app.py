import os
import json
import logging
from flask import Flask, request
import requests

app = Flask(__name__)

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Секретный ключ от FrontPad
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Таблица соответствия SKU -> артикул FrontPad
SKU_TO_ARTICLE = {f"{i:03}": f"{i:03}" for i in range(1, 182)}  # SKU "001".."181" → артикул "001".."181"

@app.route("/", methods=["POST"])
def handle_vk_order():
    data = request.json
    logging.info("📥 Получено событие от VK: %s", json.dumps(data, ensure_ascii=False))

    if data.get("type") != "market_order_new":
        logging.info("ℹ️ Не событие market_order_new, пропускаем")
        return "ok"

    order = data.get("object", {})
    recipient = order.get("recipient", {})
    delivery = order.get("delivery", {})
    items = order.get("preview_order_items", [])
    comment = order.get("comment", "")

    # Парсинг продуктов
    products = []
    for item in items:
        sku = item.get("item", {}).get("sku")
        logging.info(f"🔎 Обнаружен SKU: {sku}")
        if sku and sku in SKU_TO_ARTICLE:
            article = SKU_TO_ARTICLE[sku]
            quantity = item.get("quantity", 1)
            products.append({
                "article": article,
                "quantity": quantity
            })
        else:
            logging.warning(f"❌ SKU {sku} не найден в таблице артикулов!")

    if not products:
        logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
        return "ok"

    payload = {
        "secret": FRONTPAD_SECRET,
        "action": "new_order",
        "phone": recipient.get("phone", ""),
        "name": recipient.get("name", ""),
        "delivery_address": delivery.get("address", ""),
        "comment": comment,
        "products": json.dumps(products, ensure_ascii=False)
    }

    logging.info("📦 Отправляем заказ в FrontPad: %s", json.dumps(payload, ensure_ascii=False))

    try:
        response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
        logging.info("📤 Статус ответа от FrontPad: %s", response.status_code)
        logging.info("📤 Тело ответа от FrontPad (text): %s", response.text)
        try:
            json_response = response.json()
        except Exception:
            json_response = None
        logging.info("✅ Ответ от FrontPad (json): %s", json_response)
    except Exception as e:
        logging.error("🔥 Ошибка при отправке заказа в FrontPad: %s", str(e))

    return "ok"

@app.route("/", methods=["GET"])
def health():
    return "Server is running", 200
