import os
import json
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")

# Инициализация Flask-приложения
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Таблица соответствия SKU и артикулов (001-181)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📩 Получены данные: {data}")

    # Обработка события подтверждения
    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    # Обработка нового заказа
    if data.get("type") == "market_order_new":
        order = data.get("object", {})
        items = order.get("items", [])

        if not items:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        products = []
        for item in items:
            sku = item.get("item", {}).get("sku")
            quantity = item.get("quantity", 1)
            article = sku_to_article.get(sku)
            if article:
                products.append({"article": article, "quantity": quantity})
            else:
                logging.warning(f"❌ Не найден артикул для SKU: {sku}")

        if not products:
            logging.warning("⚠️ Не удалось сопоставить ни один товар. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": order.get("phone", ""),
            "name": order.get("recipient_name", ""),
            "delivery_address": order.get("address", {}).get("street", "") + ", " + order.get("address", {}).get("city", ""),
            "comment": order.get("comment", ""),
            "products": json.dumps(products, ensure_ascii=False)
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            response_data = response.json()
            logging.info(f"✅ Ответ от FrontPad: {response_data}")
            if response_data.get("result") != "success":
                logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
        except Exception as e:
            logging.exception("❌ Ошибка при отправке запроса в FrontPad")

        return "ok"

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

