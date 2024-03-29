#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import re
import sqlite3
import time

import aiohttp
import asyncio
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.utils.exceptions import MessageTextIsEmpty

from command_parser import CommandParser


OWN_NAME = re.compile('@?fmf_robot')

NO_NICKNAME_MSG = '''К сожалению, этот бот может работать только с людьми, у которых заполнено имя пользователя в профиле. 🙁

Сделать это можно здесь:
≡ - Settings - Username или ≡ - Settings - Edit profile - Username
≡ - Настройки - Имя пользователя или ≡ - Настройки - Изменить профиль - Имя пользователя

Заполни его и приходи!
'''

HELP_MESSAGE = '''Этот бот предназначен для поиска сексуальных партнёров среди ваших друзей.

Логика работы бота такая: вы указываете людей, которым готовы сказать "я хочу секса с тобой, давай об этом поговорим". Если вы указали кого-то, а этот человек указал вас, то бот сообщит вам обоим, что ваш интерес взаимен. Сообщит он это вам и тому второму человеку фразой "У вас совпадение с @username". А дальше - пишите человеку в личку и разговаривайте!

Доступные команды:
{0}
В качестве name в командах выступает ник пользователя. Например, ник этого бота – @fmf_robot, его можно узнать, нажав на полосу с краткой информацией в верхней части экрана.

Чтобы узнать имя пользователя заинтересовавшего вас человека, находящегося рядом с вами, может пригодиться вот эта опция:
≡ - Contacts - Find People Nearby - Make Myself visible
≡ - Контакты - Найти людей рядом - Показать меня

Удачи в поисках!
'''
WORKDIR = os.path.abspath(os.path.dirname(__file__))


class NoNickname(Exception):
    pass


def read_token():
    token_file_name = os.path.join(WORKDIR, 'fmf_bot_token')
    if not os.path.isfile(token_file_name):
        token_file_name = '/root/fmf_bot_token'
    with open(token_file_name, 'r') as f:
        return f.read().strip()


bot = Bot(token=read_token())
dp = Dispatcher(bot)


command_parser = CommandParser(dp)


def member_in_db(connection, member_id):
    cur = connection.cursor()
    cur.execute('SELECT COUNT(*) FROM members WHERE id=?', (member_id,))
    return cur.fetchone()[0] > 0


def add_member_to_db(connection, member_id, member_name, chat_id):
    cur = connection.cursor()
    # member_id and chat_id are the same, so it's just a historical issue.
    cur.execute('INSERT INTO members (id, name, chat) VALUES (?, ?, ?)',
                (member_id, member_name, chat_id))
    connection.commit()


def member_changed_name(connection, member_id, member_name):
    cur = connection.cursor()
    cur.execute('SELECT COUNT(*) FROM members WHERE id=? AND name=?',
                (member_id, member_name))
    return cur.fetchone()[0] == 0


def update_name(connection, member_id, member_name):
    cur = connection.cursor()
    cur.execute('SELECT NAME FROM members WHERE id=?', (member_id,))
    prev_name = cur.fetchone()[0]
    cur.execute('UPDATE members SET name=?, previous_name=? WHERE id=?',
                (member_name, prev_name, member_id))
    connection.commit()


def add_match(connection, member_id, match_name):
    cur = connection.cursor()
    cur.execute('DELETE FROM matches WHERE member_id=? AND LOWER(match_name)=?',
                (member_id, match_name.lower()))
    cur.execute('INSERT INTO matches (member_id, match_name) VALUES (?, ?)',
                (member_id, match_name))
    connection.commit()


async def check_new_matches(connection, member_id, new_matches):
    matches = member_matches(connection, member_id)
    new_matches = ['@' + n if not n.startswith('@') else n for n in new_matches]
    for match in new_matches:
        if match in matches:
            await congratulations_messages(connection, member_id, match)


def member_likes(connection, member_id):
    cur = connection.cursor()
    cur.execute('SELECT match_name FROM matches WHERE member_id=?',
                (member_id,))
    return [c[0] for c in cur.fetchall()]


def likes_message(connection, member_id):
    likes = member_likes(connection, member_id)
    if not likes:
        return 'Вы пока никого не добавили в список.'
    return 'Ваш список: {}'.format(', '.join(sorted(likes, key=lambda x: x.lower())))


def invalid_nicks_message(invalid_nicks):
    return 'Это - не имена пользователей! Повнимательнее :)\n{}'.format(', '.join(invalid_nicks))


def member_matches(connection, member_id):
    cur = connection.cursor()
    cur.execute('''
        SELECT DISTINCT(m1.match_name) FROM matches as m1
        JOIN members as mem1 on m1.member_id = mem1.id
        JOIN matches as m2 ON LOWER(mem1.name) = LOWER(m2.match_name)
        JOIN members as mem2 on m2.member_id = mem2.id
        WHERE m1.member_id=? AND LOWER(m1.match_name) = LOWER(mem2.name)''',
                (member_id,))
    return [c[0] for c in cur.fetchall()]


def is_match(connection, member_id, name):
    return name in member_matches(connection, member_id)


def matches_message(connection, member_id):
    matches = member_matches(connection, member_id)
    if matches:
        return 'У вас взаимный интерес с этими людьми: {}'.format(
            ', '.join(sorted(matches, key=lambda x: x.lower())))
    else:
        return 'Пока у вас нет взаимного интереса ни с кем, но не сдавайтесь!'


def remove_match(connection, member_id, match_name):
    cur = connection.cursor()
    cur.execute('DELETE FROM matches WHERE member_id=? AND LOWER(match_name)=?',
                (member_id, match_name.lower()))
    connection.commit()


async def congratulations_messages(connection, member_id, match):
    cur = connection.cursor()
    cur.execute('SELECT name, chat FROM members WHERE id=?',
                (member_id,))
    name, chat_id = cur.fetchone()
    await bot.send_message(chat_id, 'У вас совпадение с {}. Удачи!'.format(match))
    cur.execute('SELECT chat FROM members WHERE LOWER(name)=LOWER(?)',
                (match,))
    chat_id = cur.fetchone()[0]
    await bot.send_message(chat_id, 'У вас совпадение с {}. Удачи!'.format(name))


def get_db():
    db_path = os.path.join(WORKDIR, 'fmf.db')
    connection = sqlite3.connect(db_path)
    return connection


async def handle_nickname(message):
    if message.from_user.username is None:
        await message.reply(NO_NICKNAME_MSG)
        raise NoNickname
    member_name = '@' + message.from_user.username
    member_id = message.from_user.id
    connection = get_db()
    if not member_in_db(connection, member_id):
        add_member_to_db(connection, member_id, member_name, member_id)
    elif member_changed_name(connection, member_id, member_name):
        update_name(connection, member_id, member_name)
    return member_name, member_id


async def add_command(message: types.Message):
    try:
        member_name, member_id = await handle_nickname(message)
    except NoNickname:
        return
    params = message.get_args().split()
    if any((OWN_NAME.match(p) for p in params)):
        await bot.send_message(message.from_user.id, 'Это так неожиданно! 😘')
    valid_nick_pattern = re.compile(r'^\@?[A-Za-z]\w{4}\w*$')
    invalid_nicks = []
    connection = get_db()
    for match_name in params:
        if not valid_nick_pattern.match(match_name):
            invalid_nicks.append(match_name)
            continue
        if not match_name.startswith('@'):
            match_name = '@' + match_name
        add_match(connection, member_id, match_name)
    await check_new_matches(connection, member_id, params)
    msg = likes_message(connection, member_id)
    if invalid_nicks:
        msg = '\n'.join([msg, invalid_nicks_message(invalid_nicks)])
    await message.reply(msg)


async def remove_command(message: types.Message):
    try:
        member_name, member_id = await handle_nickname(message)
    except NoNickname:
        return
    params = message.get_args().split()
    connection = get_db()
    for name in params:
        if not name.startswith('@'):
            name = '@' + name
        remove_match(connection, member_id, name)
    await message.reply(likes_message(connection, member_id))


async def list_command(message: types.Message):
    try:
        member_name, member_id = await handle_nickname(message)
    except NoNickname:
        return
    params = message.get_args().split()
    connection = get_db()
    await message.reply(likes_message(connection, member_id))


async def match_command(message: types.Message):
    try:
        member_name, member_id = await handle_nickname(message)
    except NoNickname:
        return
    params = message.get_args().split()
    connection = get_db()
    await message.reply(matches_message(connection, member_id))


async def rename_command(message: types.Message):
    try:
        member_name, member_id = await handle_nickname(message)
    except NoNickname:
        return
    connection = get_db()
    cur = connection.cursor()
    cur.execute('SELECT name, previous_name FROM members WHERE id=?',
                (member_id,))
    name, previous_name = cur.fetchone()
    if previous_name is not None:
        cur.execute('UPDATE matches SET match_name=? WHERE match_name=?',
                    (name, previous_name))
        connection.commit()
    await message.reply('OK')


async def help_message(message: types.Message):
    await message.reply(HELP_MESSAGE.format(command_parser.getHelp()))


async def unknown_command(message: types.Message):
    await message.reply('Команда ещё не реализована, потерпите немного.')
    await message.reply(HELP_MESSAGE.format(command_parser.getHelp()))


class FmfBotCommand():
    ADD = 1
    REMOVE = 2
    LIST = 3
    MATCHES = 4
    HELP = 5
    RENAME = 6


def init_command_parser():
    global command_parser
    command_parser.registerCommand(
        FmfBotCommand.ADD,
        add_command,
        ['a', 'add', 'like'],
        'Добавить в список симпатичных вам людей одного или нескольких человек',
        nargs='*',
        arg_name='name')
    command_parser.registerCommand(
        FmfBotCommand.REMOVE,
        remove_command,
        ['rm', 'remove'],
        'Удалить из списка симпатичных вам людей одного или нескольких человек',
        nargs='*',
        arg_name='name')
    command_parser.registerCommand(
        FmfBotCommand.LIST,
        list_command,
        ['l', 'list'],
        'Показать список симпатичных вам людей')
    command_parser.registerCommand(
        FmfBotCommand.MATCHES,
        match_command,
        ['m', 'matches'],
        'Показать список людей, с которыми у вас появилась взаимность')
    command_parser.registerCommand(
        FmfBotCommand.HELP,
        help_message,
        ['h', 'help', 'start'],
        'Выводит это сообщение')
    command_parser.registerCommand(
        FmfBotCommand.RENAME,
        rename_command,
        ['rename'],
        'Если у вас изменился ник – обновляет его у всех, кому вы симпатичны.')
    dp.register_message_handler(unknown_command)


if __name__ == '__main__':
    init_command_parser()
    executor.start_polling(dp)
