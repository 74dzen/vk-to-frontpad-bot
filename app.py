import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Прямая таблица соответствия SKU и артикулов (1:1)
SKU_TO_ARTICLE = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

logging.basicConfig(level=logging.INFO)

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("type") == "market_order_new":
        order = data.get("object", {})
        items = order.get("preview_order_items", [])

        if not items:
            logging.warning("\u26a0\ufe0f Пустой список товаров. Пропускаем заказ.")
            return "ok"

        products = []
        for item in items:
            sku = item.get("item", {}).get("sku")
            quantity = item.get("quantity", 1)
            article = SKU_TO_ARTICLE.get(sku)

            if article:
                products.append({"article": article, "quantity": quantity})
            else:
                logging.warning(f"\u26a0\ufe0f Не найден артикул для SKU: {sku}")

        if not products:
            logging.warning("\u26a0\ufe0f Не удалось сопоставить ни один товар. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": order.get("recipient", {}).get("phone", ""),
            "name": order.get("recipient", {}).get("name", ""),
            "delivery_address": order.get("delivery", {}).get("address", ""),
            "comment": order.get("comment", ""),
            "products": products
        }

        logging.info("\ud83d\udce6 Отправляем заказ в FrontPad: %s", json.dumps(payload, ensure_ascii=False))

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", json=payload)
            logging.info("\u2705 Ответ от FrontPad: %s", response.text)
        except Exception as e:
            logging.exception("\u274c Ошибка при отправке запроса в FrontPad")

        return "ok"

    return "ok"

