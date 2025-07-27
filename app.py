from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# 🔐 Константы
CONFIRMATION_TOKEN = 'f4256a8f'
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("🟡 Входящий запрос от VK:\n", json.dumps(data, ensure_ascii=False, indent=2))

    # Проверка секрета
    if 'secret' in data and data['secret'] != VK_SECRET:
        print("⛔ Неверный секрет!")
        return 'access denied', 403

    # Подтверждение сервера
    if data['type'] == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    # Обработка заказа из маркета
    elif data['type'] == 'market_order_new':
        order = data['object']
        phone = order.get('phone', '79999999999')
        name = order.get('user_name', 'Клиент VK')
        items = order.get('items', [])

        # Связка: ВК item_id → артикул во FrontPad
        mapped_items = {
            '10001': '123'  # ← здесь 10001 — это ID товара во ВК, а 123 — артикул в FrontPad
        }

        item_fields = {}
        for idx, item in enumerate(items):
            vk_id = str(item['item_id'])
            fp_id = mapped_items.get(vk_id)
            if fp_id:
                item_fields[f'items[{idx}][id]'] = fp_id
                item_fields[f'items[{idx}][quantity]'] = item['quantity']
            else:
                print(f"⚠️ Неизвестный товар VK ID: {vk_id}")
        
        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'secret': FRONTPAD_SECRET,
            'phone': phone,
            'name': name,
            'source': 'VK'
        }
        payload.update(item_fields)

        print("📦 Отправляем в FrontPad:\n", payload)
        response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
        print("🟢 Ответ от FrontPad:", response.text)
        return 'ok'

    print("⚠️ Необработанный тип события:", data['type'])
    return 'unsupported'
