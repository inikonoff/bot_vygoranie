# Используем slim версию 3.11 (она меньше и стабильнее)
FROM python:3.11-slim

# Переменные для python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем системные библиотеки (gcc нужен на всякий случай, но Rust скорее всего не понадобится)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем и ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем папки (если их нет в репозитории)
RUN mkdir -p data src/database src/services src/keyboards src/handlers

# ВАЖНО: generate_audio.py лучше запускать ПРИ ЗАПУСКЕ контейнера, а не при сборке.
# Если он генерирует файлы на основе внешних данных, сборка может упасть.
# Но если файлы статичны, можно раскомментировать строку ниже:
# RUN python generate_audio.py

# Запуск
CMD ["python", "main.py"]
