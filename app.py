import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Переменные окружения
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Таблица соответствия SKU и артикулов (SKU == Артикул)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json
    logging.info(f"\ud83d\udcca Получены данные: {data}")

    # Обработка подтверждения сервера ВКонтакте
    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    # Обработка нового заказа
    if data.get("type") == "market_order_new":
        order_data = data.get("object", {})

        items = order_data.get("items", [])
        if not items:
            logging.warning("\u26a0\ufe0f Пустой список товаров. Пропускаем заказ.")
            return "ok"

        products = []
        for item in items:
            sku = item.get("sku")
            quantity = item.get("quantity", 1)

            article = sku_to_article.get(sku)
            if article:
                products.append({"article": article, "quantity": quantity})
            else:
                logging.warning(f"\u26a0\ufe0f SKU {sku} не найден в таблице соответствий.")

        if not products:
            logging.warning("\u26a0\ufe0f Ни один артикул не найден. Пропускаем заказ.")
            return "ok"

        # Получение информации о клиенте
        phone = order_data.get("customer", {}).get("phone", "")
        name = order_data.get("customer", {}).get("name", "")
        address = order_data.get("delivery", {}).get("address", "")
        comment = order_data.get("comment", "")

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "delivery_address": address,
            "comment": comment,
            "products": json.dumps(products, ensure_ascii=False),
        }

        logging.info(f"\ud83d\udce6 Отправляем заказ в FrontPad: {payload}")
        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload, timeout=10)
            response_data = response.json()
            logging.info(f"\u2705 Ответ от FrontPad: {response_data}")

            if not response_data or response_data.get("result") != "success":
                logging.error(f"\u274c Ошибка от FrontPad: {response_data.get('error') if response_data else 'Пустой ответ'}")
        except Exception as e:
            logging.exception(f"\u274c Исключение при отправке в FrontPad: {e}")

    return "ok"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
