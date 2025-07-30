import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
FRONTPAD_API_URL = "https://app.frontpad.ru/api/index.php"

# Таблица соответствия SKU -> артикул (все 181 товар, пример: '001': '001')
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"\U0001F4E2 Получен запрос от ВК: {json.dumps(data, ensure_ascii=False)}")

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
                logging.warning(f"⚠️ Не найден артикул для SKU: {sku}")

        if not products:
            logging.warning("⚠️ Все товары пропущены. Невозможно создать заказ.")
            return "ok"

        # Извлекаем контактные данные
        phone = order.get("phone", "")
        name = order.get("recipient_name", "")
        address = order.get("address", {})
        if isinstance(address, str):
            delivery_address = address
        else:
            street = address.get("street", "")
            house = address.get("house", "")
            flat = address.get("flat", "")
            delivery_address = f"{street}, д.{house}, кв.{flat}".strip(", ")

        comment = order.get("comment", "")

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "delivery_address": delivery_address,
            "comment": comment,
            "products": json.dumps(products, ensure_ascii=False),
        }

        logging.info(f"\U0001F4E6 Отправляем заказ в FrontPad: {json.dumps(payload, ensure_ascii=False)}")
        try:
            response = requests.post(FRONTPAD_API_URL, data=payload)
            response_data = response.json()
            logging.info(f"✅ Ответ от FrontPad: {response_data}")

            if not response_data or response_data.get("result") != "success":
                logging.error(f"❌ Ошибка от FrontPad: {response_data}")
        except Exception as e:
            logging.exception("❌ Исключение при отправке запроса в FrontPad")

    return "ok"

if __name__ == "__main__":
    app.run(debug=True)
