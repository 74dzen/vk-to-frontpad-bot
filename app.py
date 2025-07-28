from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# 🔐 Конфигурация из переменных окружения
CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION_TOKEN")  # f4256a8f
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")

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

    # 🛒 Новый заказ из VK Маркета
    elif data['type'] == 'market_order_new':
        order = data['object']
        phone = order.get('recipient', {}).get('phone', '79999999999')
        name = order.get('recipient', {}).get('name', 'Клиент VK')
        items = order.get('preview_order_items', [])

        if not items:
            print("⚠️ В заказе нет товаров")
            return 'no items', 400

        # 🧾 Сбор товаров
        item_fields = {}
        for idx, item in enumerate(items):
            sku = item.get('item', {}).get('sku')
            quantity = item.get('quantity', 1)

            if not sku:
                print(f"⛔ Ошибка: у товара отсутствует sku (артикул). Полный item: {json.dumps(item, ensure_ascii=False)}")
                return 'missing sku', 400

            item_fields[f'items[{idx}][id]'] = sku
            item_fields[f'items[{idx}][quantity]'] = quantity

        # 📦 Формируем payload для FrontPad
        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'secret': FRONTPAD_SECRET,
            'phone': phone,
            'name': name,
            'source': 'VK'
        }
        payload.update(item_fields)

        print("📤 Отправляем в FrontPad:\n", json.dumps(payload, indent=2, ensure_ascii=False))

        # 📡 Запрос к FrontPad
        try:
            response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
            print("🟢 Ответ от FrontPad:", response.text)
            return 'ok'
        except Exception as e:
            print("⛔ Ошибка при запросе в FrontPad:", e)
            return 'frontpad error', 500

    # 🚫 Необработанный тип события
    print("⚠️ Необработанный тип:", data.get('type'))
    return 'unsupported', 400
