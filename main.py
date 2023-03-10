import numpy as np
import datetime

import logging
from sqlalchemy import update
from aiogram import Bot, Dispatcher, executor, types

from models import User, Server, session


API_TOKEN = ""
PROXY_URL = ""

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, proxy=PROXY_URL)
dp = Dispatcher(bot)

def get_name(message):
    with open("names.txt", "r", encoding="utf-8") as text:
        text = text.read().split(", ")
    while True:
        nick = np.random.choice(text)
        if not bool(session.query(User).filter_by(nick=nick, server_id=message.chat.id).first()):
            return nick

def server(message):
    if not bool(session.query(Server).filter_by(id=message.chat.id).first()):
        session.add(Server(id=message.chat.id))
    session.commit()

### BOT COMMANDS
@dp.message_handler(commands=['start', 'help'])
async def start(message: types.Message):
    """ Вывод команд бота """

    server(message)
    await message.reply("Регистрация - /reg;\
        \nВыбор счастливчика дня - /play;\
        \nПросмотр участников - /players;\
        \nСтатистика - /stats;\
        \nСмена ника - /change;\
    ")

@dp.message_handler(commands=['reg'])
async def reg(message: types.Message):
    """ Регистрация нового пользователя """

    if bool(session.query(User).filter_by(user_id=message.from_user.id, server_id=message.chat.id).first()):
        user = session.query(User).filter_by(user_id=message.from_user.id, server_id=message.chat.id).one()
        await message.reply(f"<b>{user.nick}</b> - ({user.name}) уже в игре.", parse_mode="HTML")
    else:
        nick = get_name(message)
        session.add(User(
            user_id = message.from_user.id,
            name = message.from_user.first_name,
            nick = nick,
            server_id = message.chat.id
        ))
        session.commit()
        await message.reply(f"Добро пожаловать \n<b>{nick}</b> - ({message.from_user.first_name}).", parse_mode="HTML")
        server(message)

@dp.message_handler(commands=['change'])
async def change(message: types.Message):
    """ Изменение никнейма """

    if bool(session.query(User).filter_by(user_id=message.from_user.id, server_id=message.chat.id).first()):
        nick = get_name(message)
        session.execute(
            update(User)
            .where(User.user_id == message.from_user.id, User.server_id == message.chat.id)
            .values(nick=nick)
        )
        session.commit()
        await message.reply(f"Твой новый ник - <i>{nick}</i>", parse_mode="HTML")
    else:
        await message.reply("Ты не зарегистрирован!")

@dp.message_handler(commands=['play'])
async def play(message: types.Message):
    """ Выбор случайного пользователя из списка участников """

    if not bool(session.query(Server).filter_by(id=message.chat.id).first()) or not bool(session.query(User).filter_by(user_id=message.from_user.id, server_id=message.chat.id).first()):
        await message.reply("Перед использованием необходимо зарегистрироваться.\nИспользуйте команду /reg")
    else:
        # Часовой регион сервера МСК+3часа
        if session.query(Server).filter_by(id=message.chat.id).one().date.month != (datetime.datetime.now() + datetime.timedelta(hours=3)).month:
            await message.answer("Выбираю счастливчика прошлого месяца...")
            query = session.query(User).filter_by(server_id=message.chat.id).order_by(User.count.desc()).first()
            await message.answer(f"Наш победитель: {query.nick} ({query.name}) - {query.count} раз(а)")
            session.execute(
                update(User)
                .where(User.server_id == message.chat.id)
                .values(count=0, status=False)
            ) # обнуление статистики
            session.execute(
                update(Server)
                .where(Server.id == message.chat.id)
                .values(date=datetime.datetime.now().date() + datetime.timedelta(days=1))
            ) # изменение даты
            session.commit()
        else:
            await message.answer(pick_player(message))

def pick_player(message):
    if session.query(Server).filter_by(id=message.chat.id).one().date != (datetime.datetime.now() + datetime.timedelta(hours=3)).date():
        # выбираем нового
        names = []
        for _ in session.query(User.name, User.nick).filter_by(server_id=message.chat.id).order_by(User.name.asc()).all():
            names.append(f"{_.nick} - {_.name}")
        names = np.random.choice(names)
        
        session.execute(
                update(User)
                .where(User.status==True, User.server_id==message.chat.id)
                .values(status=False)
        )# удаления статуса прошлого игрока
        session.execute(
                update(User)
                .where(User.nick==names.split(" - ")[0], User.name==names.split(" - ")[1], User.server_id==message.chat.id)
                .values(status=True, count=User.count+1)
        )# добавление статуса нового игрока
        session.execute(
                update(Server)
                .where(Server.id == message.chat.id)
                .values(date=datetime.datetime.now().date())
        )# обновление даты 
        session.commit()
        return f"Счастливчик дня: \n{names}"
    else:
        # выводим текущего
        query = session.query(User).filter_by(server_id=message.chat.id, status=True).one()
        return f"Счастливчик не изменился: \n{query.nick} - {query.name}"

@dp.message_handler(commands=['players'])
async def players(message: types.Message):
    """ Отображение зарегситрированных пользователей """

    if not bool(session.query(Server).filter_by(id=message.chat.id).first()) or session.query(User).filter_by(server_id=message.chat.id).count() == 0:
        await message.answer("Игроков не обнаруженно" + "\n" + "Для регистрации используйте /reg")
    else:
        text = "Список участников игры:\n\n"
        for _ in session.query(User).filter_by(server_id=message.chat.id):
            text += f"{_.nick} ({_.name})\n"
        await message.answer(text)

@dp.message_handler(commands=['stats'])
async def stats(message: types.Message):
    """ Вывод статистики """

    if bool(session.query(Server).filter_by(id=message.chat.id).first()) and bool(session.query(User).filter_by(user_id=message.from_user.id, server_id=message.chat.id).first()):
        query = session.query(User).filter_by(server_id=message.chat.id).order_by(User.count.desc())
        text = "Статистика:\n\n"
        count = 1
        for _ in query:
            text += f"{count}. {_.nick} ({_.name}) - {_.count} раз(а).\n"
            count += 1
        await message.answer(text)
    else:
        await message.answer("Необходимо зарегистрироваться или сыграть")

### MESSAGE TYPE HANDLERS
all_content_types = ["text", "audio", "document", "photo", "sticker", "video", \
    "video_note", "location", "contact", "new_chat_title", "new_chat_photo", \
    "delete_chat_photo", "group_chat_created", "supergroup_chat_created", \
    "channel_chat_created", "migrate_to_chat_id", "migrate_from_chat_id", "pinned_message", "web_app_data"]

@dp.message_handler(content_types=all_content_types)
async def unknown_message(message: types.Message):
    """ Принудительная регистрация """
    
    if not bool(session.query(User).filter_by(user_id=message.from_user.id, server_id=message.chat.id).first()):
        session.add(User(
            user_id = message.from_user.id,
            name = message.from_user.first_name,
            nick = get_name(message),
            server_id = message.chat.id,
            count = 1
        )) # все активные пользователи будут зарегистрированы по сообщению
        server(message)
    text = message.text.lower()

@dp.message_handler(content_types=["voice"])
async def audio_messages(message: types.Message):
    """ Приватные настройки для личной группы """
    
    # Удаление голосовых сообщений 
    SERVER_ID = ""
    if message.chat.id == int(SERVER_ID):
        await message.reply_photo(r"https://www.meme-arsenal.com/memes/ef41b7cf3e39a517dff3e91188725a41.jpg")
        await message.delete()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
