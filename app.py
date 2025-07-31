import os
import logging
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Загрузка переменных среды
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Секреты
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")

# Таблица соответствия SKU → артикул (все от 001 до 181)
ARTICLES = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json(force=True)
    logging.info(f"📥 Получен запрос от ВКонтакте:\n{json.dumps(data, indent=2, ensure_ascii=False)}")

    # Проверка подтверждения сервера
    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    # Проверка секрета
    if data.get("secret") != VK_SECRET:
        logging.warning("❌ Неверный секрет от ВКонтакте!")
        return "not ok"

    # Обработка нового заказа
    if data.get("type") == "market_order_new":
        order = data.get("object", {})

        recipient = order.get("recipient", {})
        delivery = order.get("delivery", {})
        items = order.get("preview_order_items", [])

        name = recipient.get("name", "")
        phone = recipient.get("phone", "")
        address = delivery.get("address", "")
        comment = order.get("comment", "")

        # Сбор товаров
        products = []
        for item in items:
            sku = item.get("item", {}).get("sku")
            quantity = item.get("quantity", 1)

            if not sku:
                logging.warning(f"❌ SKU не найден в товаре: {item}")
                continue

            article = ARTICLES.get(sku)
            if not article:
                logging.warning(f"❌ SKU {sku} не найден в ARTICLES")
                continue

            products.append({
                "article": article,
                "quantity": quantity
            })

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        # Формируем payload
        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "delivery_address": address,
            "comment": comment,
            "products": json.dumps(products)
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            logging.info(f"📤 Статус ответа от FrontPad: {response.status_code}")
            logging.info(f"📤 Тело ответа от FrontPad (text): {response.text}")
            try:
                json_data = response.json()
                logging.info(f"✅ Ответ от FrontPad (json): {json_data}")
            except Exception:
                logging.error("❌ Ошибка при разборе JSON-ответа от FrontPad")
        except Exception as e:
            logging.exception(f"🚨 Ошибка при отправке запроса в FrontPad: {e}")

    return "ok"
