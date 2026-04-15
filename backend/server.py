import os
import json
from flask import Flask, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# Пути к файлам
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'service_account.json')
TABLE_ID_FILE = os.path.join(os.path.dirname(__file__), 'table_id')

# Инициализация Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Фиксированные имена листов
SHEET_NAMES = {
    'menu': 'Меню',
    'mon': 'ПН',
    'tue': 'ВТ',
    'wed': 'СР',
    'thu': 'ЧТ',
    'fri': 'ПТ',
    'users': 'Логины/Пароли',
    'feedback': 'Обратная связь',
    'weeks': 'Недели'
}


# CORS поддержка
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


def get_sheets_service():
    """Создает и возвращает сервис для работы с Google Sheets"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    return service


def read_table_id():
    """Читает ID таблицы из файла"""
    with open(TABLE_ID_FILE, 'r', encoding='utf-8') as f:
        return f.read().strip()


def find_sheet_by_name(service, spreadsheet_id, sheet_name):
    """Находит лист по имени и возвращает его свойства
    
    Args:
        service: Сервис Google Sheets
        spreadsheet_id: ID таблицы
        sheet_name: Имя листа для поиска
    
    Returns:
        Словарь с свойствами листа {'title': '...', 'sheetId': ...} или None, если не найден
    """
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']
        
        return None
    except Exception as e:
        raise Exception(f"Ошибка при поиске листа '{sheet_name}': {str(e)}")


def get_weeks():
    """Читает список недель из листа 'Недели' Google Sheets
    
    Returns:
        Словарь вида {
            'current': 'текст из B1', 
            'next': 'текст из B2',
            'week1_enabled': True/False,  # True если C1 = 1
            'week2_enabled': True/False    # True если C2 = 1
        }
    """
    try:
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        sheet_name = SHEET_NAMES['weeks']
        
        # Проверяем существование листа
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            raise Exception(f"Лист '{sheet_name}' не найден")
        
        # Читаем ячейки B1, B2, C1, C2
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!B1:C2"
        ).execute()
        
        values = result.get('values', [])
        current_week = values[0][0].strip() if len(values) > 0 and len(values[0]) > 0 else ''
        next_week = values[1][0].strip() if len(values) > 1 and len(values[1]) > 0 else ''
        
        # Читаем значения доступности из C1 и C2
        week1_enabled = True  # По умолчанию доступна
        week2_enabled = True   # По умолчанию доступна
        
        if len(values) > 0 and len(values[0]) > 1:
            c1_value = values[0][1].strip() if len(values[0]) > 1 else ''
            week1_enabled = c1_value == '1'
        
        if len(values) > 1 and len(values[1]) > 1:
            c2_value = values[1][1].strip() if len(values[1]) > 1 else ''
            week2_enabled = c2_value == '1'
        
        return {
            'current': current_week,
            'next': next_week,
            'week1_enabled': week1_enabled,
            'week2_enabled': week2_enabled
        }
    except Exception as e:
        raise Exception(f"Ошибка при чтении недель из Google Sheets: {str(e)}")


def get_menu_data(sheet_type='rus'):
    """Читает данные меню из Google Sheets
    
    Args:
        sheet_type: Тип меню ('rus' для русского, 'eng' для английского) - не используется, всегда читаем из 'Меню'
    """
    try:
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        # Всегда используем лист 'Меню'
        sheet_name = 'Меню'
        
        # Проверяем существование листа
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            raise Exception(f"Лист '{sheet_name}' не найден")
        
        # Читаем все данные с указанного листа
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A:Z"  # Читаем все столбцы от A до Z с указанного листа
        ).execute()
        
        values = result.get('values', [])
        return values
    except Exception as e:
        raise Exception(f"Ошибка при чтении данных из Google Sheets: {str(e)}")


def get_users():
    """Читает пользователей с листа "Логины/Пароли" Google Sheets
    
    Returns:
        Словарь вида { login: {"password": "...", "note": "...", "active": True/False} }
        где login - логин пользователя из колонки B,
        password - пароль из колонки C,
        note - примечание из колонки D,
        active - True если все поля заполнены, False иначе
    """
    try:
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        # Получаем имя листа
        sheet_name = SHEET_NAMES['users']
        
        # Проверяем существование листа
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            raise Exception(f"Лист '{sheet_name}' не найден")
        
        # Читаем данные с листа (колонки B, C, D)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!B:D"
        ).execute()
        
        values = result.get('values', [])
        users = {}
        
        # Пропускаем первую строку (заголовки), если они есть
        start_row = 1 if len(values) > 0 and values[0] else 0
        
        for i in range(start_row, len(values)):
            row = values[i]
            if len(row) >= 1 and row[0]:  # Проверяем, что есть логин (столбец B)
                login = str(row[0]).strip()  # Столбец B
                password = str(row[1]).strip() if len(row) > 1 and row[1] else ""  # Столбец C
                note = str(row[2]).strip() if len(row) > 2 and row[2] else ""  # Столбец D
                
                # active = True если логин и пароль заполнены
                active = bool(login and password)
                
                users[login] = {
                    "password": password,
                    "note": note,
                    "active": active
                }
        
        return users
    except Exception as e:
        raise Exception(f"Ошибка при чтении пользователей из Google Sheets: {str(e)}")


def verify_login(login):
    """Проверяет существование и активность логина
    
    Args:
        login: Логин пользователя для проверки
    
    Returns:
        Кортеж (is_valid, error_code, error_message):
        - is_valid: True если логин существует и активен, False иначе
        - error_code: HTTP код ошибки (401 если логин не существует, 403 если неактивен)
        - error_message: Текст ошибки
    """
    if not login or not login.strip():
        return (False, 401, 'Логин не указан')
    
    login = login.strip()
    
    try:
        users = get_users()
        
        # Проверяем существование логина
        if login not in users:
            return (False, 401, 'Логин не найден в системе')
        
        # Проверяем активность
        if not users[login].get('active', False):
            return (False, 403, 'Пользователь неактивен')
        
        return (True, None, None)
    except Exception as e:
        # При ошибке чтения пользователей считаем проверку неудачной
        return (False, 401, f'Ошибка при проверке логина: {str(e)}')


@app.route('/health', methods=['GET'])
def health():
    return 'OK', 200


@app.route('/login', methods=['POST', 'OPTIONS'])
def login():
    """Авторизация пользователя
    
    Тело запроса (JSON):
    {
        "login": "логин пользователя",
        "password": "пароль пользователя"
    }
    
    Успешный ответ (200):
    {
        "status": "ok",
        "login": "логин пользователя",
        "note": "примечание"
    }
    
    Ошибка (401):
    {
        "status": "error",
        "message": "Неверный логин или пароль"
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Неверный логин или пароль'
            }), 401
        
        login_input = data.get('login', '').strip()
        password_input = data.get('password', '').strip()
        
        if not login_input or not password_input:
            return jsonify({
                'status': 'error',
                'message': 'Неверный логин или пароль'
            }), 401
        
        # Получаем список пользователей
        users = get_users()
        
        # Проверяем логин и пароль
        if login_input in users:
            user = users[login_input]
            if user['password'] == password_input and user['active']:
                return jsonify({
                    'status': 'ok',
                    'login': login_input,
                    'note': user['note']
                }), 200
        
        # Если логин не найден или пароль неверный
        return jsonify({
            'status': 'error',
            'message': 'Неверный логин или пароль'
        }), 401
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка при авторизации: {str(e)}'
        }), 500


@app.route('/weeks', methods=['GET', 'OPTIONS'])
def weeks():
    """Возвращает список недель в формате JSON"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        weeks_data = get_weeks()
        return jsonify(weeks_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def check_menu_enabled():
    """Проверяет значение ячейки A1 листа 'Меню'
    
    Returns:
        True если A1 = '1', False если A1 = '0' или пусто
    """
    try:
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        sheet_name = 'Меню'
        
        # Проверяем существование листа
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            # Если лист не найден, считаем что меню доступно
            return True
        
        # Читаем значение ячейки A1
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A1"
        ).execute()
        
        values = result.get('values', [])
        if len(values) > 0 and len(values[0]) > 0:
            a1_value = str(values[0][0]).strip()
            return a1_value == '1'
        
        # Если ячейка пустая, считаем что меню доступно
        return True
    except Exception as e:
        # При ошибке считаем что меню доступно
        return True


@app.route('/menu', methods=['GET', 'OPTIONS'])
def menu():
    """Возвращает меню в формате JSON
    
    Параметры:
        sheet: тип меню ('rus' для русского, 'eng' для английского, по умолчанию 'rus')
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Получаем тип меню из параметра запроса (по умолчанию 'rus')
        sheet_type = request.args.get('sheet', default='rus', type=str)
        if sheet_type not in ['rus', 'eng']:
            sheet_type = 'rus'  # По умолчанию русское меню
        
        data = get_menu_data(sheet_type)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/menu_enabled', methods=['GET', 'OPTIONS'])
def menu_enabled():
    """Проверяет доступность меню (значение A1 листа 'Меню')
    
    Успешный ответ (200):
    {
        "enabled": true/false
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        enabled = check_menu_enabled()
        return jsonify({'enabled': enabled}), 200
    except Exception as e:
        # При ошибке считаем что меню доступно
        return jsonify({'enabled': True}), 200


def get_sheet_name_by_day(day):
    """Возвращает имя листа для дня недели
    
    Args:
        day: День недели (mon, tue, wed, thu, fri)
    
    Returns:
        Имя листа: mon='ПН', tue='ВТ', wed='СР', thu='ЧТ', fri='ПТ'
    """
    day_to_prefix = {
        'mon': 'ПН',
        'tue': 'ВТ',
        'wed': 'СР',
        'thu': 'ЧТ',
        'fri': 'ПТ'
    }
    prefix = day_to_prefix.get(day.lower(), 'ПН')
    sheet_name = prefix
    print(f"DEBUG: День '{day}' -> Лист '{sheet_name}'")  # Логирование для отладки
    return sheet_name


def save_selections(sheet_name, day, selections, login=''):
    """Сохраняет выбранные блюда в Google Sheets
    
    Args:
        sheet_name: Имя листа (например, 'ПН', 'ВТ', и т.д.)
        day: День недели (mon, tue, wed, thu, fri)
        selections: Словарь с выбранными блюдами {category: dish_name}
        login: Логин пользователя (сохраняется в столбец B, столбец A пропускается)
    """
    try:
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        # Проверяем существование листа
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            raise Exception(f"Лист '{sheet_name}' не найден")
        
        # Маппинг категорий на столбцы (A=0 пропускаем, B=1, C=2, D=3, E=4, F=5, G=6, H=7)
        category_to_column = {
            'breakfast': 2,  # Столбец C (было B)
            'soup': 3,       # Столбец D (было C)
            'hot': 4,        # Столбец E (было D)
            'side': 5,       # Столбец F (было E)
            'salad': 6,      # Столбец G (было F)
            'dessert': 7     # Столбец H (было G)
        }
        
        # Подготавливаем данные для записи
        # Структура: [логин, завтрак, суп, горячее, гарнир, салат, десерт] для диапазона B:H
        row_data = [login]  # Столбец B - логин
        for i in range(2, 8):  # Столбцы C-H
            category = None
            for cat, col in category_to_column.items():
                if col == i:
                    category = cat
                    break
            
            value = selections.get(category, '') if category else ''
            row_data.append(value)
        
        # Читаем все данные листа для поиска существующей строки
        result_read = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!B:H"  # Читаем все столбцы B-H (A пропускаем)
        ).execute()
        
        existing_rows = result_read.get('values', [])
        print(f"DEBUG SAVE: Лист '{sheet_name}', существующих строк: {len(existing_rows)}")  # Логирование
        
        # Ищем существующую строку с логином пользователя
        # Пропускаем заголовки (индекс 0), ищем с начала, чтобы найти первую запись
        row_to_update = None
        for i in range(1, len(existing_rows)):  # Пропускаем заголовки (индекс 0)
            row = existing_rows[i]
            # Логин теперь в столбце B (индекс 0 в массиве, так как читаем с B)
            if len(row) > 0 and str(row[0]).strip() == login:
                row_to_update = i + 1  # +1 потому что строки в Sheets начинаются с 1
                print(f"DEBUG SAVE: Найдена существующая строка {row_to_update} для логина '{login}'")  # Логирование
                break
        
        if row_to_update:
            # Обновляем существующую строку
            range_name = f"'{sheet_name}'!B{row_to_update}:H{row_to_update}"
            body = {
                'values': [row_data]
            }
            
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            print(f"DEBUG SAVE: Обновлена строка {row_to_update}, данные: {row_data}")  # Логирование
        else:
            # Строка не найдена - добавляем новую строку в конец
            if len(existing_rows) <= 1:
                # Лист пустой или только заголовки - записываем в строку 2
                next_row = 2
            else:
                # Есть данные - добавляем после последней строки
                next_row = len(existing_rows) + 1
            
            print(f"DEBUG SAVE: Добавлена новая строка {next_row}, данные: {row_data}")  # Логирование
            
            range_name = f"'{sheet_name}'!B{next_row}:H{next_row}"
            body = {
                'values': [row_data]
            }
            
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
        
        return result
    except Exception as e:
        raise Exception(f"Ошибка при сохранении данных в Google Sheets: {str(e)}")


def get_user_selections(sheet_name, login=''):
    """Получает сохраненные выборы пользователя из Google Sheets
    
    Args:
        sheet_name: Имя листа (например, 'ПН', 'ВТ', и т.д.)
        login: Логин пользователя
    
    Returns:
        Словарь с выбранными блюдами {category: dish_name} или None, если выборы не найдены
    """
    try:
        if not login:
            return None
        
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        # Проверяем существование листа
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            raise Exception(f"Лист '{sheet_name}' не найден")
        
        # Читаем все данные с листа
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!B:H"  # Читаем столбцы B-H (A пропускаем)
        ).execute()
        
        values = result.get('values', [])
        
        # Маппинг столбцов на категории (читаем с B, поэтому B=0 (логин), C=1, D=2, E=3, F=4, G=5, H=6)
        column_to_category = {
            1: 'breakfast',  # Столбец C (индекс 1 в массиве)
            2: 'soup',       # Столбец D (индекс 2 в массиве)
            3: 'hot',        # Столбец E (индекс 3 в массиве)
            4: 'side',       # Столбец F (индекс 4 в массиве)
            5: 'salad',      # Столбец G (индекс 5 в массиве)
            6: 'dessert'     # Столбец H (индекс 6 в массиве)
        }
        
        # Ищем строку с логином пользователя (ищем с конца, чтобы получить последнюю запись)
        for i in range(len(values) - 1, 0, -1):  # Пропускаем заголовки (индекс 0)
            row = values[i]
            # Логин теперь в столбце B (индекс 0 в массиве, так как читаем с B)
            if len(row) > 0 and str(row[0]).strip() == login:
                # Нашли строку с логином пользователя
                selections = {}
                for col_index, category in column_to_category.items():
                    if col_index < len(row):
                        dish_name = str(row[col_index]).strip()
                        if dish_name:
                            selections[category] = dish_name
                        else:
                            selections[category] = ''
                    else:
                        selections[category] = ''
                return selections
        
        # Выборы не найдены
        return None
    except Exception as e:
        raise Exception(f"Ошибка при чтении сохраненных выборов из Google Sheets: {str(e)}")


def delete_selections(sheet_name, day, selections, login=''):
    """Удаляет строку с выбранными блюдами из Google Sheets по логину пользователя
    
    Args:
        sheet_name: Имя листа (например, 'ПН', 'ВТ', и т.д.)
        day: День недели (mon, tue, wed, thu, fri)
        selections: Словарь с выбранными блюдами (не используется для поиска, только для совместимости)
        login: Логин пользователя (используется для поиска строки в столбце B, столбец A пропускается)
    """
    try:
        if not login:
            return {'deleted': False, 'message': 'Логин не указан'}
        
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        # Проверяем существование листа и получаем его ID
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            raise Exception(f"Лист '{sheet_name}' не найден")
        
        sheet_id = sheet_props['sheetId']
        
        # Читаем все данные с листа
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!B:H"  # Читаем столбцы B-H (A пропускаем)
        ).execute()
        
        values = result.get('values', [])
        print(f"DEBUG: Лист '{sheet_name}', найдено строк: {len(values)}")  # Логирование
        
        # Если нет данных (только заголовки), нечего удалять
        if len(values) <= 1:
            return {'deleted': False, 'message': 'Нет данных для удаления'}
        
        # Ищем строку с логином пользователя (ищем с конца, чтобы получить последнюю запись)
        row_to_delete = None
        for i in range(len(values) - 1, 0, -1):  # Пропускаем заголовки (индекс 0)
            row = values[i]
            # Логин теперь в столбце B (индекс 0 в массиве, так как читаем с B)
            if len(row) > 0 and str(row[0]).strip() == login:
                row_to_delete = i + 1  # +1 потому что строки в Sheets начинаются с 1
                print(f"DEBUG DELETE: Найдена строка для удаления: строка {row_to_delete}, логин: {login}")  # Логирование
                break
        
        if row_to_delete is None:
            return {
                'deleted': False, 
                'message': 'Строка с указанным логином не найдена',
                'debug': {
                    'sheet_name': sheet_name,
                    'total_rows': len(values),
                    'login': login
                }
            }
        
        # Удаляем строку через batchUpdate
        requests = [{
            'deleteDimension': {
                'range': {
                    'sheetId': sheet_id,
                    'dimension': 'ROWS',
                    'startIndex': row_to_delete - 1,  # Индекс начинается с 0
                    'endIndex': row_to_delete
                }
            }
        }]
        
        body = {
            'requests': requests
        }
        
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        return {'deleted': True, 'row': row_to_delete}
    except Exception as e:
        raise Exception(f"Ошибка при удалении данных из Google Sheets: {str(e)}")


@app.route('/save', methods=['POST', 'OPTIONS'])
def save():
    """Сохраняет выбранные блюда пользователя
    
    Тело запроса (JSON):
    {
        "day": "mon",  # день недели: mon, tue, wed, thu, fri
        "selections": {
            "breakfast": "название блюда",
            "soup": "название блюда",
            "hot": "название блюда",
            "side": "название блюда",
            "salad": "название блюда",
            "dessert": "название блюда"
        },
        "login": "логин пользователя"  # обязательный, должен существовать в 8-м листе
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных в запросе'}), 400
        
        day = data.get('day', '')
        selections = data.get('selections', {})
        login = data.get('login', '').strip()
        
        if not day:
            return jsonify({'error': 'Не указан день недели'}), 400
        
        # Проверяем логин (существование и активность)
        is_valid, error_code, error_message = verify_login(login)
        if not is_valid:
            print(f"WARNING SAVE: Попытка сохранения с невалидным логином '{login}'. День: {day}, ошибка: {error_message}")
            return jsonify({'error': error_message}), error_code
        
        # Определяем имя листа по дню недели (всегда используем лист 1)
        sheet_name = get_sheet_name_by_day(day)
        save_selections(sheet_name, day, selections, login)
        
        print(f"INFO SAVE: Успешное сохранение для логина '{login}', день: {day}")
        return jsonify({'success': True, 'message': 'Данные успешно сохранены'}), 200
    except Exception as e:
        print(f"ERROR SAVE: Ошибка при сохранении: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/delete', methods=['POST', 'OPTIONS'])
def delete():
    """Удаляет строку с выбранными блюдами пользователя по логину
    
    Тело запроса (JSON):
    {
        "day": "mon",  # день недели: mon, tue, wed, thu, fri
        "login": "логин пользователя"  # обязательный, используется для поиска строки
        # selections больше не используется для поиска, можно не передавать
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных в запросе'}), 400
        
        day = data.get('day', '')
        login = data.get('login', '').strip()
        selections = data.get('selections', {})  # Оставляем для совместимости, но не используем
        
        if not day:
            return jsonify({'error': 'Не указан день недели'}), 400
        
        # Проверяем логин (существование и активность)
        is_valid, error_code, error_message = verify_login(login)
        if not is_valid:
            print(f"WARNING DELETE: Попытка удаления с невалидным логином '{login}'. День: {day}, ошибка: {error_message}")
            return jsonify({'error': error_message}), error_code
        
        # Определяем имя листа по дню недели (всегда используем лист 1)
        sheet_name = get_sheet_name_by_day(day)
        result = delete_selections(sheet_name, day, selections, login)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def save_feedback(login='', rating=0, feedback_text=''):
    """Сохраняет фидбэк в Google Sheets на лист "Обратная связь"
    
    Args:
        login: Логин пользователя (колонка A)
        rating: Количество звёзд (колонка B)
        feedback_text: Текстовый отзыв (колонка C)
    """
    try:
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        # Получаем имя листа
        sheet_name = SHEET_NAMES['feedback']
        
        # Проверяем существование листа
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            raise Exception(f"Лист '{sheet_name}' не найден")
        
        # Подготавливаем данные для записи
        row_data = [login, str(rating), feedback_text]
        
        # Читаем текущие данные, чтобы найти следующую свободную строку
        result_read = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A:A"
        ).execute()
        
        existing_rows = result_read.get('values', [])
        
        # Если есть только заголовки или лист пустой, начинаем со строки 2
        if len(existing_rows) <= 1:
            next_row = 2
        else:
            next_row = len(existing_rows) + 1
        
        # Записываем данные
        range_name = f"'{sheet_name}'!A{next_row}:C{next_row}"
        body = {
            'values': [row_data]
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return result
    except Exception as e:
        raise Exception(f"Ошибка при сохранении фидбэка в Google Sheets: {str(e)}")


def get_user_feedback(login=''):
    """Получает фидбэк пользователя из Google Sheets (лист "Обратная связь")
    
    Args:
        login: Логин пользователя
    
    Returns:
        Словарь с фидбэком {'rating': int, 'feedback_text': str} или None, если не найден
    """
    try:
        if not login:
            return None
        
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        # Получаем имя листа
        sheet_name = SHEET_NAMES['feedback']
        
        # Проверяем существование листа
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            return None
        
        # Читаем все данные с листа
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A:C"
        ).execute()
        
        values = result.get('values', [])
        
        # Ищем строку с логином пользователя (ищем с конца, чтобы получить последнюю запись)
        for i in range(len(values) - 1, 0, -1):  # Пропускаем заголовки (индекс 0)
            row = values[i]
            if len(row) > 0 and str(row[0]).strip() == login:
                # Нашли строку с логином пользователя
                rating = int(row[1]) if len(row) > 1 and row[1] else 0
                feedback_text = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                return {
                    'rating': rating,
                    'feedback_text': feedback_text
                }
        
        # Фидбэк не найден
        return None
    except Exception as e:
        raise Exception(f"Ошибка при чтении фидбэка из Google Sheets: {str(e)}")


def delete_feedback(login=''):
    """Удаляет фидбэк пользователя из Google Sheets (лист "Обратная связь")
    
    Args:
        login: Логин пользователя
    """
    try:
        if not login:
            return {'deleted': False, 'message': 'Логин не указан'}
        
        service = get_sheets_service()
        spreadsheet_id = read_table_id()
        
        # Получаем имя листа
        sheet_name = SHEET_NAMES['feedback']
        
        # Проверяем существование листа и получаем его ID
        sheet_props = find_sheet_by_name(service, spreadsheet_id, sheet_name)
        if not sheet_props:
            return {'deleted': False, 'message': f"Лист '{sheet_name}' не найден"}
        
        sheet_id = sheet_props['sheetId']
        
        # Читаем все данные с листа
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A:C"
        ).execute()
        
        values = result.get('values', [])
        
        # Если нет данных (только заголовки), нечего удалять
        if len(values) <= 1:
            return {'deleted': False, 'message': 'Нет данных для удаления'}
        
        # Ищем строку с логином пользователя (ищем с конца, чтобы удалить последнюю запись)
        row_to_delete = None
        for i in range(len(values) - 1, 0, -1):  # Пропускаем заголовки (индекс 0)
            row = values[i]
            if len(row) > 0 and str(row[0]).strip() == login:
                row_to_delete = i + 1  # +1 потому что строки в Sheets начинаются с 1
                break
        
        if row_to_delete is None:
            return {'deleted': False, 'message': 'Фидбэк не найден'}
        
        # Удаляем строку через batchUpdate
        requests = [{
            'deleteDimension': {
                'range': {
                    'sheetId': sheet_id,
                    'dimension': 'ROWS',
                    'startIndex': row_to_delete - 1,  # Индекс начинается с 0
                    'endIndex': row_to_delete
                }
            }
        }]
        
        body = {
            'requests': requests
        }
        
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        return {'deleted': True, 'row': row_to_delete}
    except Exception as e:
        raise Exception(f"Ошибка при удалении фидбэка из Google Sheets: {str(e)}")


@app.route('/save_feedback', methods=['POST', 'OPTIONS'])
def save_feedback_endpoint():
    """Сохраняет фидбэк пользователя
    
    Тело запроса (JSON):
    {
        "login": "логин пользователя",
        "rating": 5,  # количество звёзд (1-5)
        "feedback_text": "текст отзыва"
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных в запросе'}), 400
        
        login = data.get('login', '').strip()
        rating = data.get('rating', 0)
        feedback_text = data.get('feedback_text', '').strip()
        
        # Проверяем логин (существование и активность)
        is_valid, error_code, error_message = verify_login(login)
        if not is_valid:
            print(f"WARNING SAVE_FEEDBACK: Попытка сохранения фидбэка с невалидным логином '{login}', ошибка: {error_message}")
            return jsonify({'error': error_message}), error_code
        
        if not rating or rating < 1 or rating > 5:
            return jsonify({'error': 'Рейтинг должен быть от 1 до 5'}), 400
        
        if not feedback_text:
            return jsonify({'error': 'Текст отзыва не может быть пустым'}), 400
        
        save_feedback(login, rating, feedback_text)
        
        return jsonify({'success': True, 'message': 'Фидбэк успешно сохранён'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_feedback', methods=['POST', 'OPTIONS'])
def get_feedback():
    """Получает фидбэк пользователя
    
    Тело запроса (JSON):
    {
        "login": "логин пользователя"
    }
    
    Успешный ответ (200):
    {
        "feedback": {
            "rating": 5,
            "feedback_text": "текст отзыва"
        }
    }
    
    Если фидбэк не найден:
    {
        "feedback": null
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных в запросе'}), 400
        
        login = data.get('login', '').strip()
        
        # Проверяем логин (существование и активность)
        is_valid, error_code, error_message = verify_login(login)
        if not is_valid:
            print(f"WARNING GET_FEEDBACK: Попытка получения фидбэка с невалидным логином '{login}', ошибка: {error_message}")
            return jsonify({'error': error_message}), error_code
        
        feedback = get_user_feedback(login)
        
        return jsonify({'feedback': feedback}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/delete_feedback', methods=['POST', 'OPTIONS'])
def delete_feedback_endpoint():
    """Удаляет фидбэк пользователя
    
    Тело запроса (JSON):
    {
        "login": "логин пользователя"
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных в запросе'}), 400
        
        login = data.get('login', '').strip()
        
        # Проверяем логин (существование и активность)
        is_valid, error_code, error_message = verify_login(login)
        if not is_valid:
            print(f"WARNING DELETE_FEEDBACK: Попытка удаления фидбэка с невалидным логином '{login}', ошибка: {error_message}")
            return jsonify({'error': error_message}), error_code
        
        result = delete_feedback(login)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_selections', methods=['POST', 'OPTIONS'])
def get_selections():
    """Получает сохраненные выборы пользователя для указанного дня
    
    Тело запроса (JSON):
    {
        "day": "mon",  # день недели: mon, tue, wed, thu, fri
        "login": "логин пользователя"
    }
    
    Успешный ответ (200):
    {
        "selections": {
            "breakfast": "название блюда",
            "soup": "название блюда",
            "hot": "название блюда",
            "side": "название блюда",
            "salad": "название блюда",
            "dessert": "название блюда"
        }
    }
    
    Если выборы не найдены:
    {
        "selections": null
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных в запросе'}), 400
        
        day = data.get('day', '')
        login = data.get('login', '')
        
        if not day:
            return jsonify({'error': 'Не указан день недели'}), 400
        
        # Проверяем логин (существование и активность)
        is_valid, error_code, error_message = verify_login(login)
        if not is_valid:
            print(f"WARNING GET_SELECTIONS: Попытка получения выборов с невалидным логином '{login}'. День: {day}, ошибка: {error_message}")
            return jsonify({'error': error_message}), error_code
        
        # Определяем имя листа по дню недели (всегда используем лист 1)
        sheet_name = get_sheet_name_by_day(day)
        selections = get_user_selections(sheet_name, login)
        
        return jsonify({'selections': selections}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)

