import os
import requests
from flask import Flask, request

app = Flask(__name__)

# Твои данные из Green API
ID_INSTANCE = "71072260715"
# ⚠️ ОБЯЗАТЕЛЬНО ВСТАВЬ СВОЙ ТОКЕН НИЖЕ (между кавычками):
API_TOKEN = "38c0a3003c22469cad11461cd9f72335793bd5303fe8450baf"


@app.route('/webhook', methods=['POST'])
def webhook():
  data = request.get_json(silent=True) or {}

  # Выводим входящий вебхук в логи Render для проверки
  print("Получен запрос:", data, flush=True)

  type_webhook = data.get('typeWebhook')

  # Обрабатываем только входящие сообщения
  if type_webhook == 'incomingMessageReceived':
    message_data = data.get('messageData', {})
    type_message = message_data.get('typeMessage')

    # Достаем текст сообщения
    text = ''
    if type_message == 'textMessage':
      text = message_data.get('textMessageData', {}).get('textMessage', '')
    elif type_message == 'extendedTextMessage':
      text = message_data.get('extendedTextMessageData', {}).get('text', '')

    sender = data.get('senderData', {}).get('chatId')

    # Проверяем команду !пинг (игнорируя пробелы и регистр)
    if text.strip().lower() == '!пинг':
      url = f'https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}'
      payload = {'chatId': sender, 'message': 'ПОНГ! 🏓 Бот работает!'}

      response = requests.post(url, json=payload)
      print(
          'Ответ от Green API:',
          response.status_code,
          response.text,
          flush=True,
      )

  return 'OK', 200


@app.route('/', methods=['GET'])
def home():
  return 'Бот активен и работает!', 200


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
    
