import os
import re
import sys
from getpass import getpass

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import RealDictCursor


def load_config():
    """Загружает конфигурацию из .env или запрашивает ввод."""
    load_dotenv()

    config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }

    # Если переменные не заданы — запрашиваем интерактивно
    if not all(config.values()):
        print("Не найдены переменные окружения. Введите данные вручную:")
        config["host"] = input("Хост (по умолчанию localhost): ") or "localhost"
        config["port"] = input("Порт (по умолчанию 5432): ") or "5432"
        config["dbname"] = input("Имя БД: ")
        config["user"] = input("Пользователь: ")
        config["password"] = getpass("Пароль: ")

    return config


def is_select_only(query: str) -> bool:
    """Проверяет, что запрос начинается с SELECT и не содержит опасных конструкций."""
    query_upper = query.strip().upper()

    # Базовый чек: начинается ли с SELECT
    if not query_upper.startswith("SELECT"):
        return False

    # Чёрный список ключевых слов, которые могут изменить данные
    dangerous_keywords = [
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "DROP",
        "CREATE",
        "TRUNCATE",
        "MERGE",
        "REPLACE",
    ]
    for keyword in dangerous_keywords:
        # Ищем целые слова, чтобы не задеть подстроки
        if re.search(rf"\b{keyword}\b", query_upper):
            return False

    return True


def add_limit_if_missing(query: str) -> str:
    """Добавляет LIMIT 5, если его нет и запрос — SELECT."""
    query_upper = query.strip().upper()
    if "LIMIT" not in query_upper:
        # Добавляем в конец, учитывая точку с запятой
        if query.strip().endswith(";"):
            query = query.rstrip(";") + " LIMIT 5;"
        else:
            query = query + " LIMIT 5"
    return query


def execute_query(conn, query: str):
    """Выполняет запрос и возвращает результат."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        if cur.description:
            return cur.fetchall()
        return []


def print_table(results):
    """Выводит результат в виде таблицы."""
    if not results:
        print("Запрос выполнен, но результат пуст.")
        return

    columns = results[0].keys()
    col_widths = {col: max(len(str(col)), max((len(str(row[col])) for row in results), default=0)) for col in columns}
    total_width = sum(col_widths.values()) + len(columns) * 3 + 1

    # Шапка
    print("-" * total_width)
    header = "| " + " | ".join(f"{col:<{col_widths[col]}}" for col in columns) + " |"
    print(header)
    print("-" * total_width)

    # Строки
    for row in results:
        line = "| " + " | ".join(f"{str(row[col]):<{col_widths[col]}}" for col in columns) + " |"
        print(line)
    print("-" * total_width)
    print(f"Всего строк: {len(results)}")


def main():
    config = load_config()

    try:
        conn = psycopg2.connect(**config)
        print("Подключение к PostgreSQL установлено.")
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        sys.exit(1)

    try:
        while True:
            query = input("\n Введите SQL-запрос (или 'exit' для выхода):\n> ").strip()
            if query.lower() in ("exit", "quit", "q"):
                break
            if not query:
                continue

            if not is_select_only(query):
                print("Ошибка: разрешены только SELECT-запросы")
                continue

            query = add_limit_if_missing(query)
            print(f"Выполняется запрос:\n{query}")

            try:
                results = execute_query(conn, query)
                print("\n Результат:")
                print_table(results)
            except Exception as e:
                print(f"Ошибка выполнения запроса: {e}")

    finally:
        conn.close()
        print("\n Соединение закрыто.")


if __name__ == "__main__":
    main()