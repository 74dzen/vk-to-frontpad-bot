from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# 🔐 Переменные окружения
CONFIRMATION_TOKEN = 'f4256a8f'  # VK → Callback API → строка подтверждения
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
VK_SECRET = os.getenv("VK_SECRET")

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("📥 Запрос от VK:\n", json.dumps(data, ensure_ascii=False, indent=2))

    # Проверка секрета
    if 'secret' in data and data['secret'] != VK_SECRET:
        print("⛔ Неверный секрет!")
        return 'access denied', 403

    # Подтверждение сервера
    if data['type'] == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    # Обработка заказа
    elif data['type'] == 'market_order_new':
        order = data['object']
        phone = order.get('recipient', {}).get('phone', '79999999999')
        name = order.get('recipient', {}).get('name', 'Клиент VK')
        items = order.get('items') or order.get('preview_order_items', [])

        item_fields = {}
        for idx, item in enumerate(items):
            # В preview_order_items артикул — это item['item']['sku']
            sku = item.get('item', {}).get('sku')
            quantity = item.get('quantity', 1)

            if not sku:
                print(f"⚠️ Пропущен товар без артикула: {item}")
                continue

            item_fields[f'items[{idx}][id]'] = sku
            item_fields[f'items[{idx}][quantity]'] = quantity

        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'phone': phone,
            'name': name,
            'source': 'VK'
        }
        payload.update(item_fields)

        print("📦 Отправляем в FrontPad:\n", payload)
        response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
        print("🟢 Ответ от FrontPad:", response.text)
        return 'ok'

    print("⚠️ Необработанный тип:", data['type'])
    return 'unsupported'
