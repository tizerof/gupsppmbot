import json
import sqlite3

from flask import Flask, Response, request

from requests_tg import deleteMessageReplyMarkup, send_message

app = Flask(__name__)


def write_json(data, filename='answer.json'):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_inline_keyboard():
    keyboard = [[{'text': 'Добавить еще район.⤴️', 'callback_data': 'add'},
                 {'text': 'Готово!✅', 'callback_data': 'ok'}]]
    return {'inline_keyboard': keyboard}


class DB():
    """ Класс для запросов в бд """

    def __init__(self):
        self.conn = sqlite3.connect('contacts.db')
        self.cur = self.conn.cursor()
        self.cur.execute("""CREATE TABLE IF NOT EXISTS main(
            district TEXT,
            username TEXT,
            chat_id INTEGER,
            full_name TEXT);
        """)

    def __del__(self):
        self.conn.commit()
        self.conn.close()

    def insert_new_record(self, district, username, chat_id, name):
        """ Добавить новую запись в таблицу main """
        conn = sqlite3.connect('contacts.db')
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO main(district, username, chat_id, full_name)
            VALUES(?, ?, ?, ?); """, [district, username, chat_id, name])
        conn.close()

    def update_district(self, district, chat_id):
        """ Заполнить пустой район у юзера в таблице main"""
        self.cur.execute(
            """UPDATE main SET district= ? WHERE district= ? AND chat_id= ?""",
            [district, '', chat_id])

    def get_districts_of_user(self, chat_id):
        """ Выбираем районы пользователя """
        district = ''
        for dis in self.cur.execute(
                "SELECT district FROM main WHERE chat_id LIKE ?", [chat_id]):
            district += f'{dis[0]} '
        return district

    def get_users_with_district(self, district):
        """ Выбираем пользователей с данным районом """
        users = self.cur.execute("""SELECT chat_id
                    FROM main WHERE district LIKE ?""", [district]).fetchall()
        return users


def command_start(chat_id, username, full_name):
    """Команда /start """
    db = DB()
    dis = db.get_districts_of_user(chat_id)
    if dis == '':
        send_message(
            chat_id,
            'Введите один район. Важно указать название района так же,'
            ' как пишет Диспетчерская:', {'force_reply': True})
        db.insert_new_record('', username, chat_id, full_name)
        send_message(
            '286032878', 'Новый пользователь: @' + username + ' ' + full_name)
    else:
        m = 'Ваши районы: ' + dis
        send_message(chat_id, m, get_inline_keyboard())
    return Response('Ok', status=200)


def callback_query(r):
    """ Ответ на callback query клавиатуры """
    db = DB()
    chat_id = r['callback_query']['message']['chat']['id']
    deleteMessageReplyMarkup(
        chat_id,
        r['callback_query']['message']['message_id'])
    if r['callback_query']['data'] == 'add':
        username = r['callback_query'].get('username')
        first_name = r['callback_query'].get('first_name')
        last_name = r['callback_query'].get('last_name')
        full_name = ''
        if first_name:
            full_name += f'{first_name} '
        if last_name:
            full_name += f'{last_name} '
        db.insert_new_record(
            '', username, chat_id, full_name)
        send_message(
            chat_id,
            'Введите один район. Важно указать название района так же,'
            ' как пишет Диспетчерская:', {'force_reply': True})
    elif r['callback_query']['data'] == 'ok':
        dis = db.get_districts_of_user(chat_id)
        send_message(chat_id, 'Ваши районы: ' + dis)
        send_message(
            chat_id,
            'Бот будет присылать вам сообщения с заявками ваших районов. '
            'Можно выключить звук чата с Диспетчером.\n'
            'Для добавления районов запустите бота заново, командой /start\n'
            'По вопросам пишите @tizerof')
    return Response('Ok', status=200)


def req_text(r):
    """ Ответы на текст """
    # Добавление района пользователю
    if r['message'].get('reply_to_message').get('text')[:7] == 'Введите':
        db = DB()
        district = r['message']['text']
        chat_id = r['message']['chat']['id']
        db.update_district(district, chat_id)
        send_message(
            chat_id, f'Район {district} добавлен.', get_inline_keyboard())
        print('Новый район у', chat_id, district)
    return Response('Ok', status=200)


def group_messages(r):
    """ Обработка групповых сообщений """
    # Пересылка заявок пользователям
    if 'text' in r['message']:
        message_text = r['message']['text']
        if 'Номер заявки:' in message_text:
            db = DB()
            message_lines = message_text.split('\n')
            address = message_lines[4][15:]
            district = message_lines[6][7:]
            text = message_lines[7][13:]
            type_request = message_lines[9][12:]
            message = f'{address}\n + {type_request}\n {text}'
            for chat_id in db.get_users_with_district(district):
                send_message(chat_id[0], message)
    return Response('Ok', status=200)


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        r = request.get_json()
        write_json(r)
        try:
            if r.get('callback_query'):
                return callback_query(r)
            chat = r.get('message').get('chat')
            chat_id = chat.get('id')
            username = chat.get('username')
            first_name = chat.get('first_name')
            last_name = chat.get('last_name')
            full_name = ''
            if first_name:
                full_name += f'{first_name} '
            if last_name:
                full_name += f'{last_name} '
            chat_type = chat.get('type')
            if chat_type == 'private':
                if r['message']['text'] == '/start':
                    return command_start(chat_id, username, full_name)
                else:
                    return req_text(r)
            elif chat_type == 'group' or 'supergroup':
                return group_messages(r)
        except Exception as e:
            print(e)
        return Response('Ok', status=200)
    else:
        return '<h1>Бот для ГУП СППМ (ВАО)</h1>'


if __name__ == '__main__':
    app.run()
