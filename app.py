from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# 🔐 Данные из окружения
CONFIRMATION_TOKEN = 'f4256a8f'
VK_SECRET = os.getenv("VK_SECRET")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("🟡 Входящий запрос от VK:\n", json.dumps(data, ensure_ascii=False, indent=2))

    # 🔐 Проверка секрета
    if 'secret' in data and data['secret'] != VK_SECRET:
        print("⛔ Неверный секрет!")
        return 'access denied', 403

    # ✅ Подтверждение сервера
    if data['type'] == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    # 📦 Новый заказ из маркета
    elif data['type'] == 'market_order_new':
        try:
            order = data['object']
            phone = order.get('phone', '79999999999')
            name = order.get('user_name', 'Клиент VK')
            items = order.get('items', [])

            # Подготовка массивов товаров
            products = {}
            quantities = {}

            for idx, item in enumerate(items):
                products[f'product[{idx}]'] = item['item_id']
                quantities[f'product_kol[{idx}]'] = item['quantity']

            payload = {
                'secret': FRONTPAD_SECRET,
                'phone': phone,
                'name': name,
                'descr': f'Заказ из VK, ID заказа {order.get("id")}'
            }
            payload.update(products)
            payload.update(quantities)

            print("📤 Отправляем заказ в FrontPad:\n", payload)
            response = requests.post(
                'https://app.frontpad.ru/api/index.php?new_order',
                data=payload
            )
            print("✅ Ответ от FrontPad:", response.text)
            return 'ok'

        except Exception as e:
            print("🔥 Ошибка при обработке заказа:", str(e))
            return 'error', 500

    # 🟠 Необработанный тип запроса
    print("⚠️ Необработанный тип:", data['type'])
    return 'unsupported'

