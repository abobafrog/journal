import telebot
from database import SessionLocal
from models import Student, Lesson, Mark
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Это электронный журнал.")

@bot.message_handler(commands=['students'])
def list_students(message):
    db = SessionLocal()
    students = db.query(Student).all()
    text = "\n".join([s.name for s in students])
    bot.send_message(message.chat.id, text)
    db.close()

bot.polling()
