@app.route('/', methods=['POST'])
def vk_callback():
    data = request.get_json()
    print("🟡 Входящий запрос от VK:\n", json.dumps(data, ensure_ascii=False, indent=2))

    if 'secret' in data and data['secret'] != VK_SECRET:
        print("⛔ Неверный секрет!")
        return 'access denied', 403

    if data['type'] == 'confirmation':
        print("✅ Подтверждение сервера")
        return CONFIRMATION_TOKEN

    elif data['type'] == 'order_edit':
        order = data['object']
        phone = order.get('phone', '79999999999')
        name = order.get('user_name', 'Клиент VK')
        items = order.get('items', [])

        mapped_items = {
            '10001': '123',  # Убедись, что это ID из VK
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
                print(f"⚠️ Не найден артикул во FrontPad для VK ID {vk_id}")

        if not item_fields:
            print("⛔ Ни один товар не сопоставлен — заказ не отправляется")
            return 'no items', 400

        payload = {
            'request': 'add_order',
            'key': FRONTPAD_API_KEY,
            'phone': phone,
            'name': name,
            'city': order.get('address', {}).get('city', ''),
            'street': order.get('address', {}).get('street', ''),
            'house': order.get('address', {}).get('house', ''),
            'flat': order.get('address', {}).get('apartment', ''),
            'delivery_type': 1,  # обязательно, даже если самовывоз
            'source': 'VK',
            'date': '2025-07-27',  # лучше ставить актуальную дату через datetime
            'time': '23:55'
        }
        payload.update(item_fields)

        print("📦 Отправляем в FrontPad:\n", json.dumps(payload, ensure_ascii=False, indent=2))

        try:
            response = requests.post('https://app.frontpad.ru/api/index.php', data=payload)
            print(f"🟢 Статус ответа: {response.status_code}")
            print("🟢 Тело ответа:", response.text)
        except Exception as e:
            print("⛔ Ошибка при отправке запроса:", e)
            return 'error', 500

        return 'ok'

    print("⚠️ Тип события не поддерживается:", data['type'])
    return 'unsupported'
