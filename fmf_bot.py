#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import re
import sqlite3
import time

import telepot
from telepot.loop import MessageLoop
from command_parser import CommandParser

OWN_NAME = 'fmf_robot'

HELP_MESSAGE = '''Этот бот предназначен для поиска сексуальных партнёров среди ваших друзей.
Доступные команды:
{0}
В качестве name в командах выступает ник пользователя. Например, ник этого бота – @fmf_robot, его можно узнать, нажав на полосу с краткой информацией в верхней части экрана.
Удачи в поисках!
'''
WORKDIR = os.path.abspath(os.path.dirname(__file__))

command_parser = CommandParser()


class FmfBotCommand():
    ADD = 1
    REMOVE = 2
    LIST = 3
    MATCHES = 4
    HELP = 5
    ADD_BY_ID = 6


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
    command_parser.registerCommand(
        FmfBotCommand.ADD_BY_ID,
        ['add_by_id'],
        'Добавить в список симпатичных вам людей или нескольких человек по идентификатору',
        nargs='*',
        arg_name='id')


def generate_user_name(nick=None, id=None, name=None):
    if nick is not None:
        return nick if nick.startswith('@') else '@' + nick
    if name is not None:
        return name
    if id is not None:
        return 'id:' + str(id)
    return 'неизвестный утконос'


def member_in_db(connection, member_id):
    cur = connection.cursor()
    cur.execute('SELECT COUNT(*) FROM members WHERE id=?', (member_id,))
    return cur.fetchone()[0] > 0


def add_member(connection, member_id, member_name, chat_id, full_name):
    cur = connection.cursor()
    cur.execute('INSERT INTO members (id, name, chat, full_name) VALUES (?, ?, ?, ?)',
                (member_id, member_name, chat_id, full_name))
    connection.commit()


def member_changed_name(connection, member_id, member_name, full_name):
    cur = connection.cursor()
    cur.execute('SELECT COUNT(*) FROM members WHERE id=? AND name=? AND full_name=?',
                (member_id, member_name, full_name))
    return cur.fetchone()[0] == 0


def update_name(connection, member_id, member_name, full_name):
    cur = connection.cursor()
    cur.execute('UPDATE members SET name=?, full_name=? WHERE id=?',
                (member_name, full_name, member_id))
    connection.commit()


def member_likes(connection, member_id):
    cur = connection.cursor()
    cur.execute('SELECT match_name, match_id FROM matches WHERE member_id=?',
                (member_id,))
    return [{'nick': c[0], 'id': c[1]} for c in cur.fetchall()]


def likes_message(connection, member_id):
    likes = [generate_user_name(nick=l['nick'], id=l['id']).encode('utf8') for l in member_likes(connection, member_id)]
    if not likes:
        return 'Вы пока никого не добавили в список.'
    return 'Ваш список: {}'.format(', '.join(sorted(likes)))


def invalid_nicks_message(invalid_nicks):
    return 'Это - не имена пользователей! Повнимательнее :)\n{}'.format(
        ', '.join([n.encode('utf8') for n in invalid_nicks]))


def invalid_ids_message(invalid_ids):
    return 'Это - не идентификаторы пользователей! Повнимательнее :)\n{}'.format(
        ', '.join([n.encode('utf8') for n in invalid_ids]))


def member_matches(connection, member_id):
    cur = connection.cursor()
    cur.execute('''
        SELECT m1.match_name, m1.match_id FROM matches AS m1
        JOIN members as mem1 ON m1.member_id = mem1.id
        JOIN matches as m2 ON (mem1.name = m2.match_name OR mem1.id = m2.match_id)
        JOIN members as mem2 ON m2.member_id = mem2.id
        WHERE m1.member_id=? AND (m1.match_name = mem2.name OR m1.match_id = mem2.id)''',
                (member_id,))
    return [{'nick': c[0], 'id': c[1]} for c in cur.fetchall()]


def get_ids_by_nicks(connection, nicks):
    cur = connection.cursor()
    sql = 'SELECT id FROM members WHERE name IN ({})'.format(', '.join(['?']*len(nicks)))
    cur.execute(sql, nicks)
    return [c[0] for c in cur.fetchall()]


def matches_message(connection, member_id):
    matches = [generate_user_name(nick=m['nick'], id=m['id']).encode('utf8') for m in member_matches(connection, member_id)]
    if matches:
        return 'У вас взаимный интерес с этими людьми: {}'.format(
            ', '.join(sorted(matches)))
    else:
        return 'Пока у вас нет взаимного интереса ни с кем, но не сдавайтесь!'


def add_match(connection, member_id, match_name=None, match_id=None):
    cur = connection.cursor()
    cur.execute('INSERT INTO matches (member_id, match_name, match_id) VALUES (?, ?, ?)',
                (member_id, match_name, match_id))
    connection.commit()


def remove_match(connection, member_id, match_name):
    cur = connection.cursor()
    cur.execute('DELETE FROM matches WHERE member_id=? AND match_name=?',
                (member_id, match_name))
    connection.commit()


def congratulations_messages(connection, member_id, match_id):
    cur = connection.cursor()
    cur.execute('SELECT name, chat FROM members WHERE id=?',
                (member_id,))
    nick_1, chat_id_1 = cur.fetchone()
    cur.execute('SELECT name, chat FROM members WHERE id=?',
                (match_id,))
    nick_2, chat_id_2 = cur.fetchone()
    bot.sendMessage(chat_id_1, 'У вас совпадение с {}. Удачи!'.format(
        generate_user_name(nick=nick_1, id=member_id).encode('utf8')))
    bot.sendMessage(chat_id_2, 'У вас совпадение с {}. Удачи!'.format(
        generate_user_name(nick=nick_2, id=match_id).encode('utf8')))


def check_new_matches(connection, member_id, new_matches):
    matches = [m['id'] for m in member_matches(connection, member_id)]
    for match_id in new_matches:
        if match_id in matches:
            congratulations_messages(connection, member_id, match_id)


def show_help(chat_id):
    bot.sendMessage(chat_id, HELP_MESSAGE.format(command_parser.getHelp()))


def handle_add_command(params, connection, member_id, chat_id):
    if OWN_NAME in params:
        bot.sendMessage(chat_id, 'Это так неожиданно! 😘')
    valid_nick_pattern = re.compile('^\@?[A-Za-z]\w{4}\w*$')
    invalid_nicks = []
    for match_name in params:
        if not valid_nick_pattern.match(match_name):
            invalid_nicks.append(match_name)
            continue
        if not match_name.startswith('@'):
            match_name = '@' + match_name
        add_match(connection, member_id, match_name)
    new_ids = get_ids_by_nicks(connection, params)
    check_new_matches(connection, member_id, new_ids)
    msg = likes_message(connection, member_id)
    if invalid_nicks:
        msg = '\n'.join([msg, invalid_nicks_message(invalid_nicks)])
    bot.sendMessage(chat_id, msg)


def handle_add_by_id_command(params, connection, member_id, chat_id):
    valid_id_pattern = re.compile('^\d+$')
    invalid_ids = []
    for match_id in params:
        if not valid_id_pattern.match(match_id):
            invalid_ids.append(match_id)
            continue
        add_match(connection, member_id, match_id=match_id)
    check_new_matches(connection, member_id, params)
    msg = likes_message(connection, member_id)
    if invalid_ids:
        msg = '\n'.join([msg, invalid_ids_message(invalid_ids)])
    bot.sendMessage(chat_id, msg)


def handle_remove_command(params, connection, member_id, chat_id):
    for name in params:
        if not name.startswith('@'):
            name = '@' + name
        remove_match(connection, member_id, name)
    bot.sendMessage(chat_id, likes_message(connection, member_id))


def handle_command(command, connection, member_id, chat_id):
    if not command or command.id == FmfBotCommand.HELP:
        show_help(chat_id)
    elif command.id == FmfBotCommand.ADD:
        handle_add_command(command.params, connection, member_id, chat_id)
    elif command.id == FmfBotCommand.ADD_BY_ID:
        handle_add_by_id_command(command.params, connection, member_id, chat_id)
    elif command.id == FmfBotCommand.REMOVE:
        handle_remove_command(command.params, connection, member_id, chat_id)
    elif command.id == FmfBotCommand.LIST:
        bot.sendMessage(chat_id, likes_message(connection, member_id))
    elif command.id == FmfBotCommand.MATCHES:
        bot.sendMessage(chat_id, matches_message(connection, member_id))
    else:
        bot.sendMessage(chat_id, 'Команда ещё не реализована, потерпите немного.')
        show_help(chat_id)


def generate_command_by_contact(contact):
    return '/add_by_id {}'.format(contact['user_id'])


def generate_full_name(data):
    name_parts = [data[key] for key in ('first_name', 'last_name') if key in data]
    return ' '.join(name_parts)


def handle(msg):
    chat_id = msg['chat']['id']
    member_nick = '@' + msg['from']['username'] if 'username' in msg['from'] else None
    text = msg['text'] if 'text' in msg else generate_command_by_contact(msg['contact'])
    member_full_name = generate_full_name(msg['from'])
    command = command_parser.parse(text)
    member_id = msg['from']['id']
    db_path = os.path.join(WORKDIR, 'fmf.db')
    connection = sqlite3.connect(db_path)

    if not member_in_db(connection, member_id):
        add_member(connection, member_id, member_nick, chat_id, member_full_name)
    elif member_changed_name(connection, member_id, member_nick, member_full_name):
        update_name(connection, member_id, member_nick, member_full_name)
    handle_command(command, connection, member_id, chat_id)


def read_token():
    token_file_name = os.path.join(WORKDIR, 'fmf_bot_token')
    if not os.path.isfile(token_file_name):
        token_file_name = '/root/fmf_bot_token'
    with open(token_file_name, 'r') as f:
        return f.read().strip()


if __name__ == '__main__':
    init_command_parser()
    bot = telepot.Bot(read_token())

    MessageLoop(bot, handle).run_as_thread()
    while 1:
        time.sleep(10)
