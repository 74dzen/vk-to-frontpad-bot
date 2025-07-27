from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# Конфигурация
CONFIRMATION_TOKEN = 'f4256a8f'
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("📨 Входящий запрос от ВК:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # Проверка секрета
    if 'secret' in data and data['secret'] != VK_SECRET:
        print("⛔ Неверный секрет")
        return 'access denied', 403

    # Подтверждение сервера
    if data['type'] == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    # Обработка заказа
    elif data['type'] == 'market_order_new':
        order = data['object']
        phone = order.get('recipient', {}).get('phone', '79999999999')
        name = order.get('recipient', {}).get('name', 'Клиент ВК')
        items = order.get('preview_order_items', [])

        item_fields = {}
        for idx, item in enumerate(items):
            sku = item.get('item', {}).get('sku')  # ← вот он, артикул!
            quantity = item.get('quantity', 1)

            if sku:
                item_fields[f'items[{idx}][id]'] = sku
                item_fields[f'items[{idx}][quantity]'] = quantity
            else:
                print(f"⚠️ Пропущен товар без SKU: {item}")

        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'secret': FRONTPAD_SECRET,
            'phone': phone,
            'name': name,
            'source': 'VK'
        }
        payload.update(item_fields)

        print("📦 Отправляем в FrontPad:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
        print("🟢 Ответ от FrontPad:", response.text)

        return 'ok'

    print(f"⚠️ Необработанный тип события: {data.get('type')}")
    return 'unsupported'
