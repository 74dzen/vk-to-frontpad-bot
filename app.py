import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
FRONTPAD_API_URL = "https://app.frontpad.ru/api/index.php?new_order"

# Таблица соответствий SKU → артикул (в твоем случае они одинаковы от '001' до '181')
SKU_TO_ARTICLE = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()

    if data.get("type") == "confirmation":
        return os.getenv("VK_CONFIRMATION_CODE")

    if data.get("type") == "market_order_new":
        order = data.get("object", {})
        logger.info("\U0001F4C1 Получен заказ из ВК: %s", order)

        items = order.get("items", [])
        products = []

        for item in items:
            sku = str(item.get("item", {}).get("sku"))
            quantity = int(item.get("quantity", 1))
            article = SKU_TO_ARTICLE.get(sku)
            if article:
                products.append((article, quantity))
            else:
                logger.warning("\u26a0\ufe0f Неизвестный SKU: %s", sku)

        if not products:
            logger.warning("\u26a0\ufe0f Пустой список товаров. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": order.get("customer" , {}).get("phone", ""),
            "name": order.get("customer" , {}).get("name", ""),
            "delivery_address": order.get("delivery_address", ""),
            "comment": order.get("comment", ""),
        }

        for idx, (article, quantity) in enumerate(products):
            payload[f"product[{idx}]"] = article
            payload[f"product_kol[{idx}]"] = str(quantity)

        logger.info("\U0001F4E6 Отправляем заказ в FrontPad: %s", payload)
        try:
            response = requests.post(FRONTPAD_API_URL, data=payload, timeout=10)
            response_data = response.json()
        except Exception as e:
            logger.error("\u274C Ошибка при отправке заказа: %s", e)
            return "ok"

        logger.info("\u2705 Ответ от FrontPad: %s", response_data)

        if response_data.get("result") != "success":
            logger.error("\u274C Ошибка от FrontPad: %s", response_data.get("error"))

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
