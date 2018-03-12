#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import telepot
from telepot.loop import MessageLoop

OWN_NAME = 'tayamarn_reactor_bot'
members_by_id = {}
members_by_name = {}
chat_by_id = {}
matches = {}


def add_member(member_id, member_name):
    members_by_id[member_id] = member_name
    members_by_name[member_name] = member_id
    matches[member_id] = set([])


def list_message(member_id):
    if not matches[member_id]:
        return 'Вы пока никого не добавили в список.'
    return 'Ваш список: {}'.format(
        ', '.join(sorted(matches[member_id])))


def is_match(member_id, name):
    if name not in members_by_name:
        return False
    return members_by_id[member_id] in matches[members_by_name[name]]


def list_matches(member_id):
    my_matches = []
    for name in matches[member_id]:
        if is_match(member_id, name):
            my_matches.append(name)
    if my_matches:
        return 'У вас взаимный интерес с этими людьми: {}'.format(
            ', '.join(sorted(my_matches)))
    else:
        return 'Пока у вас нет взаимного интереса ни с кем, но не сдавайтесь!'


def handle(msg):
    chat_id = msg['chat']['id']
    command = msg['text']
    member_id = msg['from']['id']
    member_name = msg['from']['username']

    if member_id not in members_by_id:
        add_member(member_id, member_name)

    if command.startswith('/add '):
        if OWN_NAME in command[len('/add '):].split(' '):
            bot.sendMessage(chat_id, 'Это так неожиданно! 😘')
        matches[member_id].update(command[len('/add '):].split(' '))
        bot.sendMessage(chat_id, list_message(member_id))
    elif command.startswith('/remove '):
        for name in command[len('/remove '):].split(' '):
            matches[member_id].discard(name)
        bot.sendMessage(chat_id, list_message(member_id))
    elif command.startswith('/list'):
        bot.sendMessage(chat_id, list_message(member_id))
    elif command.startswith('/matches'):
        bot.sendMessage(chat_id, list_matches(member_id))
    else:
        bot.sendMessage(chat_id, 'Я не знаю такой команды')

if __name__ == '__main__':
    with open('/root/fmf_bot_token', 'r') as f:
        token = f.read()
    bot = telepot.Bot(token)

    MessageLoop(bot, handle).run_as_thread()
    while 1:
        time.sleep(10)
