import sqlite3
import json
from flask import Flask, Response, request

from requests_tg import *

app = Flask(__name__)


def write_json(data, filename='answer.json'):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_inline_keyboard():
    keyboard = [[{'text': 'Добавить еще район.⤴️', 'callback_data': 'add'},
                 {'text': 'Готово!✅', 'callback_data': 'ok'}]]
    return {'inline_keyboard': keyboard}


def check_name(r, name):
    if name in r['message']['chat'][name]:
        return name
    else:
        return ''


class DB():
    """ Класс для запросов в бд """

    def __init__(self):
        self.conn = sqlite3.connect('contacts.db')
        self.cur = self.conn.cursor()
        self.cur.execute("""CREATE TABLE IF NOT EXIST main(
            district TEXT,
            username TEXT,
            chat_id INTEGER,
            full_name TEXT);
        """)

    def __del__(self):
        self.conn.close()

    def insert_new_district_with_user(self, district, username, chat_id, name):
        conn = sqlite3.connect('contacts.db')
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO main(district, username, chat_id, full_name)
            VALUES(?, ?, ?, ?); """, [district, username, chat_id, name])
        conn.close()

    def update_district(self, district, chat_id):
        self.cur.execute(
            """UPDATE main SET district= ? WHERE district= ? AND chat_id= ?""",
            [district, '', chat_id])

    def get_districts_of_user(self, chat_id):
        """ Выбираем районы пользователя из БД """
        districts = ''.join(self.cur.execute(
            """SELECT district FROM main WHERE chat_id LIKE(?)""", (chat_id,)))
        return districts


def command_start(chat_id, username, full_name):
    """Команда / start """
    db = DB()
    dis = db.get_districts_of_user(chat_id)
    if dis == '':
        send_message(
            chat_id,
            'Введите один район. Важно указать название района так же,'
            ' как пишет Диспетчерская:', {'force_reply': True})
        db.insert_new_district_with_user('', username, chat_id, full_name)
        send_message(
            '286032878', 'Новый пользователь: @' + username + ' ' + full_name)
    else:
        m = 'Ваши районы: ' + dis
        send_message(chat_id, m, get_inline_keyboard())
    return Response('Ok', status=200)


def callback_query(r):
    """ Ответ на callback query клавиатуры """
    conn = sqlite3.connect('contacts.db')
    cur = conn.cursor()
    if r['callback_query']['data'] == 'add':
        username = check_name(r['callback_query'], 'username')
        first_name = check_name(r['callback_query'], 'first_name')
        last_name = check_name(r['callback_query'], 'last_name')
        insert_new_district_with_user_in_db(
            '', username, r['message']['chat']['id'],
            first_name + ' ' + last_name)
        deleteMessageReplyMarkup(r['callback_query']['message']['chat']['id'],
                                 r['callback_query']['message']['message_id'])
        send_message(r['callback_query']['message']['chat']['id'],
                     'Пришлите один район. Важно указать название '
                     'района так же, как пишет Диспетчерская!',
                     {'force_reply': True})
    elif r['callback_query']['data'] == 'ok':
        dis = ''
        for title in cur.execute('SELECT district FROM main WHERE chat_id LIKE ?',
                                 [r['callback_query']['message']['chat']['id']]):
            dis += title[0] + ' '
        deleteMessageReplyMarkup(r['callback_query']['message']['chat']['id'],
                                 r['callback_query']['message']['message_id'])
        send_message(r['callback_query']['message']
                     ['chat']['id'], 'Ваши районы: ' + dis)
        send_message(r['callback_query']['message']['chat']['id'], 'Бот будет присылать вам '
                     'сообщения с заявками ваших районов. Можно выключить звук чата с '
                     'Диспетчером.\nДля добавления районов запустите'
                     ' бота заного, командой /start\nПо вопросам пишите @tizerof')
    else:
        return Response('Ok', status=200)
    conn.commit()
    conn.close()
    return Response('Ok', status=200)


def req_text(r):
    """ Ответы на текст """
    db = DB()
    # Добавление района пользователю
    if r['message'].get('reply_to_message')['data'] == 'ok':
        district = r['message']['text']
        chat_id = r['message']['chat']['id']
        db.update_district(district=district, chat_id=chat_id)
        send_message(
            chat_id, f'Район {district} добавлен.', get_inline_keyboard())
        print('Новый район у', r['message']
              ['chat']['id'], r['message']['text'])
    return Response('Ok', status=200)


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        r = request.get_json()
        write_json(r)
        try:
            chat_id = r['message']['chat']['id']
            username = r['message']["chat"]["username"]
            full_name = r['message']["chat"].get(
                "first_name") + ' ' + r['message']["chat"].get('last_name')
            if r.get('callback_query'):
                return callback_query(r)
            elif r['message']['chat']['type'] == 'private':
                if r['message']['text'] == '/start':
                    command_start(chat_id, username, full_name)
                else:
                    req_text(r)
            # Пересылка заявок пользователям
            elif (r['message']['chat']['type'] == 'group' or
                  r['message']['chat']['type'] == 'supergroup'):
                if ('reply_to_message' in r['message'] or
                        'forward_from' in r['message']):
                    return Response('Ok', status=200)
                else:
                    if 'text' in r['message']:
                        r_text = r['message']['text']
                        if 'Номер заявки:' in r_text:
                            district = r_text.split('\n')[6][7:]
                            type_request = r_text.split('\n')[9][12:]
                            adress = r_text.split('\n')[4][15:]
                            conn = sqlite3.connect('contacts.db')
                            cur = conn.cursor()
                            for title in cur.execute("""SELECT chat_id
                            FROM main WHERE district LIKE ?""", [district]):
                                send_message(
                                    title[0], adress + '\n' + type_request)
                            conn.commit()
                            conn.close()
            else:
                return Response('Ok', status=200)
        except KeyError:
            return Response('Ok', status=200)
        return Response('Ok', status=200)
    else:
        return '<h1>Бот для ГУП СППМ (ВАО)</h1>'


if __name__ == '__main__':
    app.run()
