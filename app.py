from flask import Flask, request
import requests
import os

app = Flask(__name__)

CONFIRMATION_TOKEN = '38afba8f'  # <- заменить, если токен VK изменится
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
VK_SECRET = os.getenv("VK_SECRET")

if not FRONTPAD_API_KEY:
    raise ValueError("FRONTPAD_API_KEY is not set in environment variables")

@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()

    # 🔐 Проверка VK-секрета
    if 'secret' in data and data['secret'] != VK_SECRET:
        return 'access denied', 403

    if data['type'] == 'confirmation':
        return CONFIRMATION_TOKEN
    elif data['type'] == 'order_edit':
        order = data['object']
        phone = '79999999999'
        name = 'Клиент VK'
        items = order['items']

        mapped_items = {
            '10001': '123',
            '10002': '124'
        }

        item_fields = {}
        for idx, item in enumerate(items):
            fp_id = mapped_items.get(str(item['item_id']))
            if fp_id:
                item_fields[f'items[{idx}][id]'] = fp_id
                item_fields[f'items[{idx}][quantity]'] = item['quantity']

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

        response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
        print('FrontPad response:', response.text)
        return 'ok'

    return 'unsupported'
