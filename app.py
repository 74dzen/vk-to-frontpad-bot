from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# 🔐 Настройки
CONFIRMATION_TOKEN = '38afba8f'
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")  # должен быть задан в Render
VK_SECRET = os.getenv("VK_SECRET")  # должен быть задан в Render

# 💥 Проверка, если ключи не заданы
if not FRONTPAD_API_KEY:
    raise ValueError("❌ FRONTPAD_API_KEY is not set")
if not VK_SECRET:
    raise ValueError("❌ VK_SECRET is not set")

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("🟡 Входящий запрос от VK:\n", json.dumps(data, ensure_ascii=False, indent=2))

    # 🔒 Проверка секрета
    if 'secret' in data and data['secret'] != VK_SECRET:
        print("⛔ Неверный секрет!")
        return 'access denied', 403

    # 🔁 Подтверждение сервера
    if data['type'] == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    # 🧾 Заказ
    elif data['type'] == 'order_edit':
        order = data['object']
        phone = order.get('phone', '79999999999')
        name = order.get('user_name', 'Клиент VK')
        items = order.get('items', [])

        # 🗺️ Сопоставление VK ID → FrontPad артикулов
        mapped_items = {
            '10001': '123'  # ← Убедись, что item_id в VK равен 10001 для артикула 123
        }

        # 🧩 Формируем структуру заказа
        item_fields = {}
        for idx, item in enumerate(items):
            vk_id = str(item['item_id'])
            fp_id = mapped_items.get(vk_id)
            if fp_id:
                item_fields[f'items[{idx}][id]'] = fp_id
                item_fields[f'items[{idx}][quantity]'] = item['quantity']
            else:
                print(f"⚠️ Не найден артикул во FrontPad для VK item_id={vk_id}")

        # 📨 Готовим payload
        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'phone': phone,
            'name': name,
            'city': order.get('address', {}).get('city', ''),
            'street': order.get('address', {}).get('street', ''),
            'house': order.get('address', {}).get('house', ''),
            'flat': order.get('address', {}).get('apartment', ''),
            'source': 'VK'
        }
        payload.update(item_fields)

        print("📦 Отправляем в FrontPad:\n", payload)

        response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
        print("🟢 Ответ от FrontPad:", response.text)
        return 'ok'

    # ⚠️ Другой тип события
    print("⚠️ Тип события не поддерживается:", data['type'])
    return 'unsupported'
