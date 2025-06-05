import mysql.connector
from mysql.connector import Error

def reset_database():
    try:
        # Подключение к БД
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="7878"
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            cursor.execute("DROP DATABASE IF EXISTS support_system")
            
            cursor.execute("CREATE DATABASE support_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            print("База данных успешно пересоздана")
            
    except Error as e:
        print(f"Ошибка при работе с MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Соединение с MySQL закрыто")

if __name__ == "__main__":
    reset_database() 