import logging
from flask import Flask, request
import requests
import json

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = 'ВАШ_СЕКРЕТ_ОТ_FRONTPAD'  # ← замени на свой
VK_CONFIRMATION_TOKEN = 'ВАШ_ТОКЕН_ПОДТВЕРЖДЕНИЯ'  # ← замени на свой

# Таблица артикулов: SKU = артикул (от 001 до 181)
sku_to_article = {f'{i:03}': f'{i:03}' for i in range(1, 182)}

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    logging.info("📥 Получен JSON от ВК: %s", json.dumps(data, ensure_ascii=False, indent=2))

    if data.get('type') == 'confirmation':
        return VK_CONFIRMATION_TOKEN

    if data.get('type') == 'market_order_new':
        order = data['object']
        customer = order.get('recipient', {})
        name = customer.get('name', '')
        phone = customer.get('phone', '')
        address = order.get('delivery', {}).get('address', '')
        comment = order.get('comment', '')

        items_raw = order.get('preview_order_items', [])
        logging.info("🛒 Обработка %d товаров", len(items_raw))

        products = []
        for item in items_raw:
            try:
                sku = item.get('item', {}).get('sku')
                quantity = item.get('quantity', 1)
                if sku:
                    article = sku_to_article.get(sku)
                    if article:
                        products.append({"article": article, "quantity": quantity})
                        logging.info(f"✅ Найден товар: SKU {sku} -> артикул {article}")
                    else:
                        logging.warning(f"❌ SKU {sku} не найден в таблице артикулов!")
                else:
                    logging.warning(f"❌ SKU отсутствует в товаре: {item}")
            except Exception as e:
                logging.error("Ошибка при обработке товара: %s", e)

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "delivery_address": address,
            "comment": comment,
            "products": json.dumps(products, ensure_ascii=False)
        }

        logging.info("📦 Отправляем заказ в FrontPad: %s", payload)
        response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)

        logging.info("📤 Статус ответа от FrontPad: %s", response.status_code)
        logging.info("📤 Тело ответа от FrontPad (text): %s", response.text)
        try:
            response_json = response.json()
            logging.info("✅ Ответ от FrontPad (json): %s", response_json)
        except Exception as e:
            logging.error("❌ Не удалось распарсить ответ как JSON: %s", e)

    return "ok"

@app.route('/', methods=['GET'])
def index():
    return "👋 Бот работает."

