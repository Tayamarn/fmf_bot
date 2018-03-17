#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sqlite3
import time

import telepot
from telepot.loop import MessageLoop
from command_parser import CommandParser

OWN_NAME = 'fmf_robot'

NO_NICKNAME_MSG = '''К сожалению, этот бот может работать только с людьми, у которых заполнен никнейм в профиле. 🙁
Заполни его и приходи еще раз!
'''

HELP_MESSAGE = '''Этот бот предназначен для поиска сексуальных партнёров среди ваших друзей.
Доступные команды:
{0}
Удачи в поисках!
'''

command_parser = CommandParser()


class FmfBotCommand():
    ADD = 1
    REMOVE = 2
    LIST = 3
    MATCHES = 4
    HELP = 5


def init_command_parser():
    global command_parser
    command_parser.registerCommand(
        FmfBotCommand.ADD,
        ['a', 'add', 'like'],
        'Добавить в список симпатичных вам людей одного или нескольких человек',
        nargs='*',
        arg_name='name')
    command_parser.registerCommand(
        FmfBotCommand.REMOVE,
        ['rm', 'remove'],
        'Удалить из списка симпатичных вам людей одного или нескольких человек',
        nargs='*',
        arg_name='name')
    command_parser.registerCommand(
        FmfBotCommand.LIST,
        ['l', 'list'],
        'Показать список симпатичных вам людей')
    command_parser.registerCommand(
        FmfBotCommand.MATCHES,
        ['m', 'matches'],
        'Показать список людей, с которыми у вас появилась взаимность')
    command_parser.registerCommand(
        FmfBotCommand.HELP,
        ['h', 'help', 'start'],
        'Выводит это сообщение')


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
    likes = [l.encode('utf8') for l in member_likes(connection, member_id)]
    if not likes:
        return 'Вы пока никого не добавили в список.'
    return 'Ваш список: {}'.format(', '.join(sorted(likes)))


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
    matches = [m.encode('utf8') for m in member_matches(connection, member_id)]
    if matches:
        return 'У вас взаимный интерес с этими людьми: {}'.format(
            ', '.join(sorted(matches)))
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


def show_help(chat_id):
    bot.sendMessage(chat_id, HELP_MESSAGE.format(command_parser.getHelp()))


def handle_add_command(params, connection, member_id, chat_id):
    if OWN_NAME in params:
        bot.sendMessage(chat_id, 'Это так неожиданно! 😘')
    for match_name in params:
        add_match(connection, member_id, match_name)
    check_new_matches(connection, member_id, params)
    bot.sendMessage(chat_id, likes_message(connection, member_id))


def handle_remove_command(params, connection, member_id, chat_id):
    for name in params:
        remove_match(connection, member_id, name)
    bot.sendMessage(chat_id, likes_message(connection, member_id))


def handle_command(command, connection, member_id, chat_id):
    if not command or command.id == FmfBotCommand.HELP:
        show_help(chat_id)
    elif command.id == FmfBotCommand.ADD:
        handle_add_command(command.params, connection, member_id, chat_id)
    elif command.id == FmfBotCommand.REMOVE:
        handle_remove_command(command.params, connection, member_id, chat_id)
    elif command.id == FmfBotCommand.LIST:
        bot.sendMessage(chat_id, likes_message(connection, member_id))
    elif command.id == FmfBotCommand.MATCHES:
        bot.sendMessage(chat_id, matches_message(connection, member_id))
    else:
        bot.sendMessage(chat_id, 'Команда ещё не реализована, потерпите немного.')
        show_help(chat_id)


def handle(msg):
    chat_id = msg['chat']['id']
    try:
        member_name = msg['from']['username']
    except KeyError:
        bot.sendMessage(chat_id, NO_NICKNAME_MSG)
    command = command_parser.parse(msg['text'])
    member_id = msg['from']['id']
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           'fmf.db')
    connection = sqlite3.connect(db_path)

    if not member_in_db(connection, member_id):
        add_member(connection, member_id, member_name, chat_id)
    elif member_changed_name(connection, member_id, member_name):
        update_name(connection, member_id, member_name)

    handle_command(command, connection, member_id, chat_id)


if __name__ == '__main__':
    init_command_parser()

    with open('/root/fmf_bot_token', 'r') as f:
        token = f.read().strip()
    bot = telepot.Bot(token)

    MessageLoop(bot, handle).run_as_thread()
    while 1:
        time.sleep(10)
