from flask import Flask, request
import requests
import os

app = Flask(__name__)

# 🔐 Конфигурация
CONFIRMATION_TOKEN = 'e31f246c'  # <-- вставлен токен подтверждения из VK
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
VK_SECRET = os.getenv("VK_SECRET")

# Проверка переменных окружения
if not FRONTPAD_API_KEY:
    raise ValueError("FRONTPAD_API_KEY is not set")
if not VK_SECRET:
    raise ValueError("VK_SECRET is not set")

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("📩 Входящий JSON от VK:", data)

    # Проверка VK_SECRET
    if 'secret' in data and data['secret'] != VK_SECRET:
        print("❌ Неверный VK_SECRET")
        return 'access denied', 403

    # Подтверждение сервера VK
    if data.get('type') == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    # Обработка редактирования заказа
    elif data.get('type') == 'order_edit':
        order = data['object']
        phone = '79999999999'  # Тестовый номер
        name = 'Клиент VK'
        items = order.get('items', [])

        # Маппинг ID товаров VK → FrontPad
        mapped_items = {
            '10001': '123',
            '10002': '124'
        }

        item_fields = {}
        for idx, item in enumerate(items):
            vk_id = str(item['item_id'])
            fp_id = mapped_items.get(vk_id)
            if fp_id:
                item_fields[f'items[{idx}][id]'] = fp_id
                item_fields[f'items[{idx}][quantity]'] = item['quantity']
            else:
                print(f"⚠️ Неизвестный item_id: {vk_id}")

        # Сбор payload для FrontPad
        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'phone': phone,
            'name': name,
            'city': order.get('address', {}).get('city', ''),
            'street': order.get('address', {}).get('street', ''),
            'house': order.get('address', {}).get('house', ''),
            'flat': order.get('address', {}).get('apartment', '')
        }
        payload.update(item_fields)

        # Отправка заказа в FrontPad
        try:
            response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
            print("📦 Ответ от FrontPad:", response.text)
            return 'ok'
        except Exception as e:
            print("🔥 Ошибка при отправке в FrontPad:", e)
            return 'internal error', 500

    # Если пришёл неизвестный тип события
    print("❓ Неподдерживаемый тип события:", data.get('type'))
    return 'unsupported'
