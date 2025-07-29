import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

app = Flask(__name__)

# Таблица соответствия SKU и артикулов (SKU = артикул)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}  # от 001 до 181 включительно

@app.route("/", methods=["POST"])
def vk_callback():
    try:
        data = request.get_json()
        logging.info(f"\ud83d\udd0d Получен запрос: {data}")

        # Обработка подтверждения сервера
        if data.get("type") == "confirmation":
            return VK_CONFIRMATION

        # Обработка нового заказа
        if data.get("type") == "market_order_new":
            order = data.get("object", {})

            # Извлекаем товары
            items = order.get("items", [])
            products = []
            for item in items:
                sku = str(item.get("sku", "")).strip()
                quantity = int(item.get("quantity", 1))
                article = sku_to_article.get(sku)
                if article:
                    products.append({"article": article, "quantity": quantity})
                else:
                    logging.warning(f"\u26a0\ufe0f SKU не найден в таблице: {sku}")

            if not products:
                logging.warning("\u26a0\ufe0f Пустой список товаров. Пропускаем заказ.")
                return "ok"

            # Данные покупателя
            name = order.get("customer_name", "Неизвестный покупатель")
            phone = order.get("customer_phone", "")

            # Адрес доставки (если доступен)
            address_data = order.get("delivery", {})
            if isinstance(address_data, dict):
                address = address_data.get("address", {}).get("street", "")
            else:
                address = ""

            # Комментарий к заказу
            comment = order.get("comment", "")

            payload = {
                "secret": FRONTPAD_SECRET,
                "action": "new_order",
                "phone": phone,
                "name": name,
                "delivery_address": address,
                "comment": comment,
                "products": json.dumps(products, ensure_ascii=False)
            }

            logging.info(f"\ud83d\udce6 Отправляем заказ в FrontPad: {payload}")
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)

            try:
                response_data = response.json()
            except Exception:
                response_data = None

            logging.info(f"\u2705 Ответ от FrontPad: {response_data}")

            if not response_data:
                logging.error("\u274c Ошибка: пустой ответ от FrontPad")
            elif response_data.get("result") != "success":
                logging.error(f"\u274c Ошибка от FrontPad: {response_data.get('error')}")

        return "ok"

    except Exception as e:
        logging.exception("\ud83d\udd25 Необработанная ошибка в vk_callback")
        return "error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
