from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# 🔐 Константы
CONFIRMATION_TOKEN = 'f4256a8f'  # строка подтверждения сервера VK
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")  # ключ API FrontPad
VK_SECRET = os.getenv("VK_SECRET")  # секрет из VK Callback API

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("📥 Запрос от VK:\n", json.dumps(data, ensure_ascii=False, indent=2))

    # 🔐 Проверка секрета
    if 'secret' in data and data['secret'] != VK_SECRET:
        print("⛔ Неверный секрет!")
        return 'access denied', 403

    # 🔄 Подтверждение сервера
    if data.get('type') == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    # 📦 Новый заказ
    if data.get('type') == 'market_order_new':
        order = data['object']
        recipient = order.get('recipient', {})
        delivery = order.get('delivery', {})
        items = order.get('preview_order_items', [])

        # Данные клиента
        phone = recipient.get('phone', '').replace('+', '').replace(' ', '')
        name = recipient.get('name', 'Клиент ВК')
        comment = order.get('comment', '')

        # Сбор товаров
        item_fields = {}
        for idx, item in enumerate(items):
            sku = item.get('item', {}).get('sku')
            quantity = item.get('quantity', 1)
            if sku:
                item_fields[f'items[{idx}][id]'] = sku
                item_fields[f'items[{idx}][quantity]'] = quantity

        # Основной payload
        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'phone': phone,
            'name': name,
            'comment': comment,
            'source': 'VK',
            'street': delivery.get('address', '')
        }
        payload.update(item_fields)

        print("📦 Отправляем в FrontPad:\n", payload)

        try:
            response = requests.post('https://app.frontpad.ru/api/index.php', data=payload, timeout=10)
            print("✅ Ответ от FrontPad:", response.text)
        except Exception as e:
            print("❌ Ошибка при отправке в FrontPad:", str(e))
        return 'ok'

    print("⚠️ Необработанный тип:", data.get('type'))
    return 'unsupported'
