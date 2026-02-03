# Используем легкий образ Python 3.11
FROM python:3.11-slim

# Отключаем создание .pyc файлов и буферизацию вывода (чтобы логи летели сразу)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (gcc нужен для сборки некоторых lib)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем Python-библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY . .

# Создаем папку data, если её нет (на всякий случай)
RUN mkdir -p data

# Эта команда будет выполняться по умолчанию, если не переопределить её в Render
# Но мы переопределим её в настройках Render для надежности
CMD ["python", "main.py"]
