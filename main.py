import os
import re
import sys
from getpass import getpass
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
DEFAULT_LIMIT = 5

def load_config() -> dict[str, Optional[str]]:
    load_dotenv()

    config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }

    if not all(config.values()):
        print("Не найдены переменные окружения. Введите данные вручную:")
        config["host"] = input("Хост (по умолчанию localhost): ") or "localhost"
        config["port"] = input("Порт (по умолчанию 5432): ") or "5432"
        config["dbname"] = input("Имя БД: ")
        config["user"] = input("Пользователь: ")
        config["password"] = getpass("Пароль: ")

    return config
def is_select_only(query: str) -> bool:
    query_upper = query.strip().upper()
    statements = [stmt.strip() for stmt in query_upper.split(';') if stmt.strip()]
    if not statements:
        return False

    dangerous_keywords = [
        "DELETE", "UPDATE", "INSERT", "ALTER", "DROP", "CREATE", 
        "TRUNCATE", "MERGE", "REPLACE", "WITH"
    ]
    
    for statement in statements:
        if not statement.startswith("SELECT"):
            return False
        for keyword in dangerous_keywords:
            if re.search(rf"\b{keyword}\b", statement):
                return False      
    return True
def add_limit_if_missing(query: str) -> str:
    stripped_query = query.strip()
    query_upper = stripped_query.upper()
    if "LIMIT" in query_upper:
        return query

    if stripped_query.endswith(";"):
        return f"{stripped_query[:-1]} LIMIT {DEFAULT_LIMIT};"
    
    return f"{query} LIMIT {DEFAULT_LIMIT}"


def execute_query(conn, query: str) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        if cur.description:
            return cur.fetchall()
        return []


def print_table(results: list[dict]) -> None:
    if not results:
        print("Запрос выполнен, но результат пуст.")
        return

    columns = results[0].keys()
    col_widths = {
        col: max(len(str(col)), max((len(str(row[col])) for row in results), default=0)) 
        for col in columns
    }
    total_width = sum(col_widths.values()) + len(columns) * 3 + 1

    print("-" * total_width)
    header = "| " + " | ".join(f"{col:<{col_widths[col]}}" for col in columns) + " |"
    print(header)
    print("-" * total_width)

    for row in results:
        line = "| " + " | ".join(f"{str(row[col]):<{col_widths[col]}}" for col in columns) + " |"
        print(line)
    print("-" * total_width)
    print(f"Всего строк: {len(results)}")

def main():
    config = load_config()
    try:
        with psycopg2.connect(**config) as conn:
            print("Подключение к PostgreSQL установлено.")
            while True:
                query = input("\nВведите SQL-запрос (или 'exit' для выхода):\n> ").strip()
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
                    print("\nРезультат:")
                    print_table(results)
                except Exception as e:
                    print(f"Ошибка выполнения запроса: {e}")   
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        sys.exit(1)
    print("\n Соединение закрыто.")

if __name__ == "__main__":
    main()
