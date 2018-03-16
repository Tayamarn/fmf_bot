#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sqlite3
import time

import telepot
from telepot.loop import MessageLoop

OWN_NAME = 'fmf_robot'

NO_NICKNAME_MSG = '''К сожалению, этот бот может работать только с людьми, у которых заполнен никнейм в профиле. 🙁
Заполни его и приходи еще раз!
'''

HELP_MESSAGE = '''Этот бот предназначен для поиска сексуальных партнёров среди ваших друзей.
Доступные команды:
/add <name1> <name2>... – добавить в список симпатичных вам людей одного или нескольких разделённых пробелами людей
/remove <name1> <name2>... – убрать людей из списка
/list – показывает список интересных вам людей
/matches – показывает список людей, с которыми у вас появилась взаимность
/help – выводит это сообщение
Удачи в поисках!
'''


def member_in_db(connection, member_id):
    cur = connection.cursor()
    cur.execute('SELECT COUNT(*) FROM members WHERE id=?', (member_id,))
    return cur.fetchone()[0] > 0


def add_member(connection, member_id, member_name, chat_id):
    cur = connection.cursor()
    cur.execute('INSERT INTO members VALUES (?, ?, ?)',
                (member_id, member_name, chat_id))
    connection.commit()


def member_changed_name(connection, member_id, member_name):
    cur = connection.cursor()
    cur.execute('SELECT COUNT(*) FROM members WHERE id=? AND name=?',
                (member_id, member_name))
    return cur.fetchone()[0] == 0


def update_name(connection, member_id, member_name):
    cur = connection.cursor()
    cur.execute('UPDATE members SET name=? WHERE id=?',
                (member_name, member_id))
    connection.commit()


def member_likes(connection, member_id):
    cur = connection.cursor()
    cur.execute('SELECT match_name FROM matches WHERE member_id=?',
                (member_id,))
    return [c[0] for c in cur.fetchall()]


def likes_message(connection, member_id):
    likes = member_likes(connection, member_id)
    if not likes:
        return 'Вы пока никого не добавили в список.'
    return 'Ваш список: {}'.format(', '.join(sorted(likes.encode('utf8'))))


def member_matches(connection, member_id):
    cur = connection.cursor()
    cur.execute('''
        SELECT m1.match_name FROM matches as m1
        JOIN members as mem1 on m1.member_id = mem1.id
        JOIN matches as m2 ON mem1.name = m2.match_name
        JOIN members as mem2 on m2.member_id = mem2.id
        WHERE m1.member_id=? AND m1.match_name = mem2.name''',
                (member_id,))
    return [c[0] for c in cur.fetchall()]


def is_match(connection, member_id, name):
    return name in member_matches(connection, member_id)


def matches_message(connection, member_id):
    matches = member_matches(connection, member_id)
    if matches:
        return 'У вас взаимный интерес с этими людьми: {}'.format(
            ', '.join(sorted(matches.encode('utf8'))))
    else:
        return 'Пока у вас нет взаимного интереса ни с кем, но не сдавайтесь!'


def add_match(connection, member_id, match_name):
    cur = connection.cursor()
    cur.execute('INSERT INTO matches (member_id, match_name) VALUES (?, ?)',
                (member_id, match_name))
    connection.commit()


def remove_match(connection, member_id, match_name):
    cur = connection.cursor()
    cur.execute('DELETE FROM matches WHERE member_id=? AND match_name=?',
                (member_id, match_name))
    connection.commit()


def congratulations_messages(connection, member_id, match):
    cur = connection.cursor()
    cur.execute('SELECT name, chat FROM members WHERE id=?',
                (member_id,))
    name, chat_id = cur.fetchone()
    bot.sendMessage(chat_id, 'У вас совпадение с {}. Удачи!'.format(match.encode('utf8')))
    cur.execute('SELECT chat FROM members WHERE name=?',
                (match,))
    chat_id = cur.fetchone()[0]
    bot.sendMessage(chat_id, 'У вас совпадение с {}. Удачи!'.format(name.encode('utf8')))


def check_new_matches(connection, member_id, new_matches):
    matches = member_matches(connection, member_id)
    for match in new_matches:
        if match in matches:
            congratulations_messages(connection, member_id, match)


def handle(msg):
    chat_id = msg['chat']['id']
    try:
        member_name = msg['from']['username']
    except KeyError:
        bot.sendMessage(chat_id, NO_NICKNAME_MSG)
    command = msg['text']
    member_id = msg['from']['id']
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           'fmf.db')
    connection = sqlite3.connect(db_path)

    if not member_in_db(connection, member_id):
        add_member(connection, member_id, member_name, chat_id)
    elif member_changed_name(connection, member_id, member_name):
        update_name(connection, member_id, member_name)

    if command.startswith('/add '):
        if OWN_NAME in command[len('/add '):].split(' '):
            bot.sendMessage(chat_id, 'Это так неожиданно! 😘')
        new_matches = command[len('/add '):].split(' ')
        for match_name in new_matches:
            add_match(connection, member_id, match_name)
        check_new_matches(connection, member_id, new_matches)
        bot.sendMessage(chat_id, likes_message(connection, member_id))
    elif command.startswith('/remove '):
        for name in command[len('/remove '):].split(' '):
            remove_match(connection, member_id, name)
        bot.sendMessage(chat_id, likes_message(connection, member_id))
    elif command.startswith('/list'):
        bot.sendMessage(chat_id, likes_message(connection, member_id))
    elif command.startswith('/matches'):
        bot.sendMessage(chat_id, matches_message(connection, member_id))
    elif command.startswith('/start') or command.startswith('/help'):
        bot.sendMessage(chat_id, HELP_MESSAGE)
    else:
        bot.sendMessage(chat_id, 'Я не знаю такой команды')

if __name__ == '__main__':
    with open('/root/fmf_bot_token', 'r') as f:
        token = f.read().strip()
    bot = telepot.Bot(token)

    MessageLoop(bot, handle).run_as_thread()
    while 1:
        time.sleep(10)
