from flask import Flask
from flask import request
from flask import Response
import requests
import json
import sqlite3
import re

app = Flask(__name__)
token = 0 # Токен бота
URL = f"https://api.telegram.org/bot{token}/"

def chek_name(r,name):
    if name in r['message']['chat'][name]:
        return name
    else:
        return ''

# Команда /start
def command_start(r):
    #выбираем районы из БД, при отсутствии записываем нового пользователя
    conn = sqlite3.connect('contacts.db')
    cur = conn.cursor()
    dis = ''
    for title in cur.execute("SELECT district FROM main WHERE idtg LIKE ?",
        [r['message']['chat']['id']]):
        dis += title[0] + ' '
    if dis == '':
        send_message(r['message']['chat']['id'], 'Введите один район. '
                                'Важно указать название района так же,'
                                            ' как пишет Диспетчерская:',
        {"force_reply": True})
        username = chek_name(r,'username')
        first_name = chek_name(r,'first_name')
        last_name = chek_name(r,'last_name')
        cur.execute("INSERT INTO main (district, username, idtg, name) "
                                                   "VALUES(?, ?, ?, ?);",
                          ['', username, r['message']['chat']['id'],
                          first_name+' '+ last_name])
        send_message('286032878','Новый пользователь: @'+
                        username + ' ' + first_name +' ' + last_name)
    else:
        m = 'Ваши районы: ' + dis
        send_message(r['message']['chat']['id'], m, get_inline_keyboard())
    conn.commit()
    conn.close()
    return Response('Ok', status=200)

# Ответ на callback query клавиатуры
def callback_query(r):
    conn = sqlite3.connect('contacts.db')
    cur = conn.cursor()
    if r['callback_query']['data'] == 'add':
        username = chek_name(r['callback_query'],'username')
        first_name = chek_name(r['callback_query'],'first_name')
        last_name = chek_name(r['callback_query'],'last_name')
        cur.execute("INSERT INTO main (district, username, idtg, name) "
                                                       "VALUES(?, ?, ?, ?);",
                              ['', username,
                              r['callback_query']['message']['chat']['id'],
                                                first_name+' '+last_name])
        deleteMessageReplyMarkup(r['callback_query']['message']['chat']['id'],
                                    r['callback_query']['message']['message_id'])
        send_message(r['callback_query']['message']['chat']['id'],
                                'Пришлите один район. Важно указать название '
                                'района так же, как пишет Диспетчерская!',
        {"force_reply": True})
    elif r['callback_query']['data'] == 'ok':
        dis = ''
        for title in cur.execute("SELECT district FROM main WHERE idtg LIKE ?",
            [r['callback_query']['message']['chat']['id']]):
            dis += title[0] + ' '
        deleteMessageReplyMarkup(r['callback_query']['message']['chat']['id'],
                                    r['callback_query']['message']['message_id'])
        send_message(r['callback_query']['message']['chat']['id'], 'Ваши районы: ' + dis)
        send_message(r['callback_query']['message']['chat']['id'], 'Бот будет присылать вам '
        'сообщения с заявками ваших районов. Можно выключить звук чата с '
        'Диспетчером.\nДля добавления районов запустите'
        ' бота заного, командой /start\nПо вопросам пишите @tizerof')
    else:
        return Response('Ok', status=200)
    conn.commit()
    conn.close()
    return Response('Ok', status=200)
# Ответы на текст
def req_text(r):
    # Добавление района пользователю
    if 'reply_to_message' in r['message']:

        conn = sqlite3.connect('contacts.db')
        cur = conn.cursor()
        dis = ''
        for title in cur.execute("SELECT district FROM main WHERE idtg LIKE ?",
                                                    [r['message']['chat']['id']]):
            dis = title

        if dis != '':
            cur.execute("UPDATE main SET district = ? WHERE district = ? AND idtg = ?;",
                            [r['message']['text'], "",r['message']['chat']['id']])
            send_message(r['message']['chat']['id'], 'Район '+r['message']['text']+
            ' добавлен.', get_inline_keyboard())
            print('Новый район у', r['message']['chat']['id'], r['message']['text'])
        conn.commit()
        conn.close()
    return Response('Ok', status=200)

def get_inline_keyboard():
    keyboard = [[{'text': 'Добавить еще район.⤴️', 'callback_data': 'add'},
                 {'text': 'Готово!✅', 'callback_data': 'ok'}]]
    return {'inline_keyboard': keyboard}
def write_json(data, filename="answer.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_message(chat_id, text, reply_markup=''):
    url = URL +"sendMessage"
    answer = {'chat_id': chat_id, 'text': text, 'reply_markup': reply_markup}
    r = requests.post(url, json=answer)
    return r

def deleteMessageReplyMarkup(chat_id, message_id):
    url = URL +"editMessageReplyMarkup"
    answer = {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': [[]]}
    r = requests.post(url, json=answer)
    return r

def forward_message(chat_id, from_chat_id, message_id):
    url = URL +"forwardMessage"
    answer = {'chat_id': chat_id, 'from_chat_id': from_chat_id, 'message_id': message_id}
    r = requests.post(url, json=answer)
    return r

@app.route("/", methods=['POST','GET'])
def index():
    if request.method == 'POST':
        r = request.get_json()
        write_json(r)
        try:
            if 'callback_query' in r:
                return callback_query(r)
            elif r['message']['chat']['type'] == "private":
                if r['message']['text'] == "/start":
                    command_start(r)
                else:
                    req_text(r)

            # Пересылка заявок пользователям
            elif r['message']['chat']['type'] == "group"  or r['message']['chat']['type'] == "supergroup":
                if 'reply_to_message' in r['message'] or 'forward_from' in r['message']:
                    return Response('Ok', status=200)
                else:
                    if 'text' in r['message']:
                        r_text = r['message']['text']
                        if 'Номер заявки:' in r_text:
                            if re.search(r'Номер заявки: ', r_text):
                                split_message =
                                district = r_text.split('\n')[6][7:]
                                type_request = r_text.split('\n')[9][12:]
                                adress = r_text.split('\n')[4][15:]
                                conn = sqlite3.connect('contacts.db')
                                cur = conn.cursor()
                                for title in cur.execute("SELECT idtg FROM main WHERE district LIKE ?", [district]):
                                    send_message(title[0], adress +'\n'+ type_request)
                                conn.commit()
                                conn.close()
            else:
                return Response('Ok', status=200)
        except KeyError:
            return Response('Ok', status=200)
        return Response('Ok', status=200)
    else:
        return "<h1>Бот для ГУП СППМ (ВАО)</h1>"
if __name__ == "__main__":
    app.run()
