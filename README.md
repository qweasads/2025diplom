Веб-сервис для учёта заявок и обработки обращений в службу поддержки

## Установка и запуск проекта

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/qweasads/2025diplom.git
cd 2025diplom
```

### 2. Создайте и активируйте виртуальное окружение
```bash
python -m venv venv

venv\Scripts\activate
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

### 4. Настройте подключение к MySQL
В файле `support_project/settings.py` укажите параметры вашей базы данных MySQL:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 5. Примените миграции
```bash
python manage.py migrate
```

### 6. Создайте суперпользователя (админа)
```bash
python manage.py createsuperuser
```

### 7. Запустите сервер
```bash
python manage.py runserver
```

Откройте [http://127.0.0.1:8000/](http://127.0.0.1:8000/) в браузере.

---

