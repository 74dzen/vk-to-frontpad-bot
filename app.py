import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv('FRONTPAD_SECRET')
VK_CONFIRMATION = os.getenv('VK_CONFIRMATION')

# Таблица соответствия: SKU ВКонтакте = Артикул FrontPad (все от 001 до 181)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.json

    # Подтверждение сервера
    if data.get('type') == 'confirmation':
        return VK_CONFIRMATION

    if data.get('type') == 'market_order_new':
        order = data['object']
        user_name = order['recipient']['name']
        user_phone = order['recipient']['phone']
        user_address = order['delivery']['address']
        comment = order['comment']

        products = []
        for item in order.get('preview_order_items', []):
            sku = item.get('item', {}).get('sku')
            quantity = item.get('quantity', 1)
            if sku in sku_to_article:
                products.append({
                    "article": sku_to_article[sku],
                    "quantity": quantity
                })
            else:
                logging.warning(f"❗ Неизвестный SKU: {sku}")

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": user_phone,
            "name": user_name,
            "delivery_address": user_address,
            "comment": comment,
            "products": products  # Список словарей — не JSON-строка!
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")
        response = requests.post("https://app.frontpad.ru/api/index.php", json=payload)
        try:
            response_data = response.json()
        except Exception:
            logging.error(f"❌ FrontPad вернул некорректный JSON: {response.text}")
            return "ok"

        logging.info(f"✅ Ответ от FrontPad: {response_data}")
        if response_data.get("result") != "success":
            logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")

    return "ok"
