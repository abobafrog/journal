import gspread
from google.oauth2.service_account import Credentials

# Подключаемся к API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
client = gspread.authorize(creds)

# Открываем таблицу по имени
spreadsheet = client.open("Название_твоей_таблицы")
sheet = spreadsheet.sheet1  # первый лист

# Читаем данные
data = sheet.get_all_records()
print(data)