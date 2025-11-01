import telebot
from telebot import types
import gspread
from google.oauth2.service_account import Credentials
import os

# ========== Настройки ==========
BOT_TOKEN = "8463443445:AAGKv-OLXPBiVYvWFqoUv5-Fmiez2ECLspo"
SPREADSHEET_NAME = "журнал"  # точно как в Google Drive
SHEET_NAME = None  # None -> первый лист; или укажи "Sheet1"
CREDENTIALS_FILE = "credentials.json"  # файл сервиса-аккаунта

# ==============================
bot = telebot.TeleBot(BOT_TOKEN)

# Подключение к Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
gc = gspread.authorize(creds)
sh = gc.open(SPREADSHEET_NAME)
sheet = sh.sheet1 if SHEET_NAME is None else sh.worksheet(SHEET_NAME)

# ------------------------------
# Вспомогательные функции
# ------------------------------
def get_header():
    """Возвращает список заголовков первой строки (A1, B1, C1, ...)"""
    return sheet.row_values(1)

def get_dates():
    """Возвращает заголовки начиная со второго столбца (B..). Это наши даты."""
    header = get_header()
    return header[1:]

def get_students():
    """Возвращает значения первого столбца (A) без заголовка"""
    col = sheet.col_values(1)
    return col[1:]

def find_col_index_by_date(date_text):
    """Индекс столбца (1-based) по названию даты в шапке. Возвращает None, если не найдено."""
    header = get_header()
    try:
        idx = header.index(date_text) + 1
        return idx
    except ValueError:
        return None

def get_entries_by_date(date_text, only_yes=False):
    """Возвращает список строк для даты. Если only_yes=True — возвращает только строки со значением 'Да' (case-insensitive)."""
    col_idx = find_col_index_by_date(date_text)
    if col_idx is None:
        return None  # дата не найдена

    students = get_students()
    values = sheet.col_values(col_idx)[1:]  # без заголовка
    result = []
    for name, val in zip(students, values + [''] * max(0, len(students) - len(values))):
        v = val.strip()
        if only_yes:
            if v.lower() in ("да", "yes", "+", "1", "present"):
                result.append(f"{name}: {val if val else '—'}")
        else:
            result.append(f"{name}: {val if val else '—'}")
    return result

def set_mark(date_text, student_name, new_value):
    """Установить (записать) значение для заданного ученика и даты. Возвращает True при успехе."""
    col_idx = find_col_index_by_date(date_text)
    if col_idx is None:
        return False, "Дата не найдена."

    students = sheet.col_values(1)
    # ищем полное совпадение в столбце A (игнор регистра и пробелов по краям)
    target_row = None
    for i, s in enumerate(students):
        if s.strip().lower() == student_name.strip().lower():
            target_row = i + 1  # gspread row numbers 1-based
            break
    if target_row is None:
        return False, "Ученик не найден в первом столбце."

    sheet.update_cell(target_row, col_idx, new_value)
    return True, "Отметка обновлена."

# ------------------------------
# Телеграм-обработчики
# ------------------------------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    dates = get_dates()
    text = "Электронный журнал\n\nДоступные команды:\n" \
           "/start — показать это сообщение\n" \
           "/dates — показать список дат\n" \
           "/show <дата> — показать журнал за дату (пример: /show 01.11.2025)\n" \
           "/show_yes <дата> — показать только положительные отметки (Да)\n" \
           "/set <дата>;<ФИО>;<значение> — установить отметку (пример: /set 01.11.2025;Иванов И.;Да)\n\n" \
           "Или нажми на кнопку с датой ниже."
    bot.send_message(message.chat.id, text)

    # Кнопки с датами (inline)
    dates = get_dates()
    if dates:
        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = [types.InlineKeyboardButton(text=d, callback_data=f"show|{d}") for d in dates]
        # добавить кнопку фильтра "только Да"
        # складываем две группы в разметку
        for b in buttons:
            markup.add(b)
        bot.send_message(message.chat.id, "Выбери дату:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "В таблице пока нет дат в первой строке.")

@bot.message_handler(commands=['dates'])
def cmd_dates(message):
    dates = get_dates()
    if dates:
        bot.send_message(message.chat.id, "Доступные даты:\n" + "\n".join(dates))
    else:
        bot.send_message(message.chat.id, "Даты не найдены в таблице (первая строка пустая).")

@bot.message_handler(commands=['show'])
def cmd_show(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.reply_to(message, "Пожалуйста, укажи дату. Пример: /show 01.11.2025")
        return
    date_text = parts[1].strip()
    entries = get_entries_by_date(date_text, only_yes=False)
    if entries is None:
        bot.reply_to(message, "Дата не найдена в таблице.")
    else:
        bot.reply_to(message, "\n".join(entries))

@bot.message_handler(commands=['show_yes'])
def cmd_show_yes(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.reply_to(message, "Пожалуйста, укажи дату. Пример: /show_yes 01.11.2025")
        return
    date_text = parts[1].strip()
    entries = get_entries_by_date(date_text, only_yes=True)
    if entries is None:
        bot.reply_to(message, "Дата не найдена в таблице.")
    else:
        if not entries:
            bot.reply_to(message, "Нет положительных отметок за эту дату.")
        else:
            bot.reply_to(message, "\n".join(entries))

@bot.message_handler(commands=['set'])
def cmd_set(message):
    # формат: /set дата;ФИО;значение
    payload = message.text[len('/set'):].strip()
    if not payload:
        bot.reply_to(message, "Пример: /set 01.11.2025;Иванов И.;Да")
        return
    try:
        date_text, student, value = [p.strip() for p in payload.split(';', 2)]
    except ValueError:
        bot.reply_to(message, "Неверный формат. Используй: /set ДАТА;ФИО;ЗНАЧЕНИЕ")
        return
    ok, msg = set_mark(date_text, student, value)
    bot.reply_to(message, msg)

# Обработчик inline-кнопок (кнопки с датами)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if '|' not in call.data:
        bot.answer_callback_query(call.id, "Неизвестная команда.")
        return
    action, date_text = call.data.split('|', 1)
    if action == "show":
        entries = get_entries_by_date(date_text, only_yes=False)
        if entries is None:
            bot.answer_callback_query(call.id, "Дата не найдена.")
            return
        bot.send_message(call.message.chat.id, f"Журнал за {date_text}:\n" + "\n".join(entries))
    elif action == "show_yes":
        entries = get_entries_by_date(date_text, only_yes=True)
        if entries is None:
            bot.answer_callback_query(call.id, "Дата не найдена.")
            return
        if not entries:
            bot.send_message(call.message.chat.id, f"За {date_text} нет положительных отметок.")
        else:
            bot.send_message(call.message.chat.id, f"Положительные отметки за {date_text}:\n" + "\n".join(entries))
    else:
        bot.answer_callback_query(call.id, "Неизвестное действие.")

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)