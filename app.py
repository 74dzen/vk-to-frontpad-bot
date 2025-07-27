from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# 🔐 Подтверждение сервера от VK
CONFIRMATION_TOKEN = 'f4256a8f'

# 🔑 Ключ и секрет для FrontPad
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# 🔐 Секрет для проверки входящих запросов от VK
VK_SECRET = os.getenv("VK_SECRET")

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("📥 Запрос от VK:\n", json.dumps(data, ensure_ascii=False, indent=2))

    # Проверка секрета VK
    if 'secret' in data and data['secret'] != VK_SECRET:
        print("⛔ Неверный секрет от VK!")
        return 'access denied', 403

    # Подтверждение сервера VK
    if data['type'] == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    # Обработка нового заказа из VK Market
    if data['type'] == 'market_order_new':
        order = data['object']

        phone = order.get('recipient', {}).get('phone', '79999999999')
        name = order.get('recipient', {}).get('name', 'Клиент VK')
        comment = order.get('comment', '')
        delivery = order.get('delivery', {})
        items = order.get('preview_order_items', [])

        # Формируем позиции для заказа
        item_fields = {}
        for idx, item in enumerate(items):
            quantity = item.get('quantity', 1)
            sku = item.get('item', {}).get('sku')  # артикул = sku
            if sku:
                item_fields[f'items[{idx}][id]'] = sku
                item_fields[f'items[{idx}][quantity]'] = quantity

        # Формируем тело запроса
        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'secret': FRONTPAD_SECRET,  # 🔥 ОБЯЗАТЕЛЬНО!
            'phone': phone,
            'name': name,
            'comment': comment,
            'source': 'VK',
            'street': delivery.get('address', '')
        }
        payload.update(item_fields)

        print("📦 Отправляем в FrontPad:\n", payload)

        response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
        print("✅ Ответ от FrontPad:", response.text)
        return 'ok'

    print("⚠️ Необработанный тип:", data['type'])
    return 'unsupported'
