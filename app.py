import os
import json
import logging
from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
FRONTPAD_URL = "https://app.frontpad.ru/api/index.php"

# Таблица соответствий SKU → артикул
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}  # 001–181

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json
    logging.info(f"📩 Входящие данные от ВК: {data}")

    if "type" not in data:
        logging.warning("⚠️ Нет типа события. Пропускаем.")
        return "ok"

    if data["type"] == "confirmation":
        return VK_CONFIRMATION

    if data["type"] == "market_order_new":
        order_data = data.get("object", {})
        items = order_data.get("items", [])
        logging.info(f"📦 Товары в заказе: {items}")

        products = []
        for item in items:
            sku = str(item.get("sku", "")).strip()
            quantity = int(item.get("quantity", 1))

            article = sku_to_article.get(sku)
            if article:
                products.append({"article": article, "quantity": quantity})
            else:
                logging.warning(f"❌ Нет артикула для SKU: {sku}")

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": "+79999999999",
            "name": "Уасяяяяяя Уасяяяяяяя",
            "delivery_address": "Челябинск",
            "comment": "Тестовый заказ, не реагируйте на него)",
            "products": json.dumps(products, ensure_ascii=False),
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")
        try:
            response = requests.post(FRONTPAD_URL, data=payload, timeout=10)
            response_data = response.json() if response.content else None
            logging.info(f"✅ Ответ от FrontPad: {response_data}")

            if not response_data:
                logging.error("❌ Пустой ответ от FrontPad!")
            elif response_data.get("result") != "success":
                logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")

        except Exception as e:
            logging.exception("❌ Ошибка при отправке запроса в FrontPad")

    return "ok"

