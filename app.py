import os
import logging
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")

# Все 181 товара с артикулом = SKU
ARTICLE_MAP = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json(force=True)
    logging.info(f"📥 Получен запрос от VK:\n{json.dumps(data, indent=2, ensure_ascii=False)}")

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("secret") != VK_SECRET:
        logging.warning("❌ Секрет от VK не совпадает!")
        return "not ok"

    if data.get("type") == "market_order_new":
        order = data.get("object", {})

        recipient = order.get("recipient", {})
        delivery = order.get("delivery", {})
        items = order.get("preview_order_items", [])

        name = recipient.get("name", "")
        phone = recipient.get("phone", "")
        address = delivery.get("address", "")
        comment = order.get("comment", "")

        products_list = []
        for item in items:
            sku = item.get("item", {}).get("sku")
            quantity = item.get("quantity", 1)

            if not sku:
                logging.warning(f"❌ Не найден SKU у товара: {item}")
                continue

            article = ARTICLE_MAP.get(sku)
            if not article:
                logging.warning(f"❌ SKU {sku} не найден в таблице артикулов!")
                continue

            products_list.append({
                "article": article,
                "quantity": quantity
            })

        if not products_list:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        # Готовим строку с JSON товаров
        products_json = json.dumps(products_list, ensure_ascii=False)

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "delivery_address": address,
            "comment": comment,
            "products": products_json  # Важно: строка!
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
