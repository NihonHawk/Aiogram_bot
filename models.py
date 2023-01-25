from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Date
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, relationship, scoped_session
import datetime


Base = declarative_base()

engine = create_engine('sqlite:///bot_db.sqlite?check_same_thread=False')
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
session = Session()


class Server(Base):
    __tablename__ = "server"

    id = Column(Integer, primary_key=True)                  # уникальный ID чата
    date = Column(Date, default=datetime.datetime.now().date() -
                  datetime.timedelta(days=1))               # текущая дата -1  (при смене должны обновляться колонки статуса)
    users = relationship("User", cascade="all, delete")     # связь сервера и пользователей этого сервера


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)      # уникальный ID пользователя tg
    name = Column(String)                       # имя пользователя в чате tg
    nick = Column(String)                       # nickname пользователя
    count = Column(Integer, default=0)          # количество дней
    status = Column(Boolean, default=False)     # статус для сегодняшнего дня
    server_id = Column(Integer, ForeignKey("server.id", ondelete="cascade"))


Base.metadata.create_all(engine)
