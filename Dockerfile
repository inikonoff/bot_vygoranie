# Используем slim версию 3.11 (она меньше и стабильнее)
FROM python:3.11-slim

# Переменные для python: отключаем буферизацию и создание .pyc
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем системные библиотеки
# build-essential нужен для gcc, если вдруг придется что-то собирать
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# ВАЖНО: Обновляем pip и ставим зависимости с флагом --prefer-binary
# Это ИСПРАВЛЯЕТ ошибку "maturin failed", заставляя pip качать готовые wheel-файлы,
# вместо того чтобы пытаться компилировать Rust-код на сервере.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Копируем весь код проекта
COPY . .

# Создаем структуру папок (на случай, если git их не сохранил пустыми)
RUN mkdir -p data src/database src/services src/keyboards src/handlers

# Команда запуска по умолчанию
# Примечание: В настройках Render в поле "Start Command" это будет переопределено 
# на "python generate_audio.py && python main.py", но этот CMD нужен как база.
CMD ["python", "main.py"]
