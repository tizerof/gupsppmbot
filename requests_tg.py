import requests

from settings import token  # Токен бота

URL = 'https://api.telegram.org/bot' + token + '/'


def send_message(chat_id, text, reply_markup=''):
    url = URL + 'sendMessage'
    answer = {'chat_id': chat_id, 'text': text, 'reply_markup': reply_markup}
    r = requests.post(url, json=answer)
    return r


def deleteMessageReplyMarkup(chat_id, message_id):
    url = URL + 'editMessageReplyMarkup'
    answer = {'chat_id': chat_id,
              'message_id': message_id, 'reply_markup': [[]]}
    r = requests.post(url, json=answer)
    return r


def forward_message(chat_id, from_chat_id, message_id):
    url = URL + 'forwardMessage'
    answer = {'chat_id': chat_id,
              'from_chat_id': from_chat_id, 'message_id': message_id}
    r = requests.post(url, json=answer)
    return r
