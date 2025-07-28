import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

VK_SECRET = os.getenv("VK_SECRET")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

FRONTPAD_API_URL = "https://app.frontpad.ru/api/index.php?new_order"

@app.route("/", methods=["POST"])
def vk_webhook():
    data = request.get_json()

    if "type" not in data:
        return "ok"

    if data["type"] == "confirmation":
        return VK_SECRET

    elif data["type"] == "message_new":
        message = data["object"]["message"]["text"].strip().lower()
        user_id = data["object"]["message"]["from_id"]

        if "аляска" in message:
            send_order_to_frontpad()
            send_message(user_id, "Ваш заказ на ролл Аляска принят! Спасибо!")
        else:
            send_message(user_id, "Напишите \"Аляска\", чтобы сделать заказ")

    return "ok"

def send_order_to_frontpad():
    payload = {
        "secret": FRONTPAD_SECRET,
        "product[0]": "123",     # Артикул ролла "Аляска"
        "product_kol[0]": "1"
    }
    response = requests.post(FRONTPAD_API_URL, data=payload)
    print("FrontPad response:", response.text)

def send_message(user_id, text):
    url = "https://api.vk.com/method/messages.send"
    payload = {
        "user_id": user_id,
        "random_id": 0,
        "message": text,
        "access_token": VK_TOKEN,
        "v": "5.131"
    }
    requests.post(url, data=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
