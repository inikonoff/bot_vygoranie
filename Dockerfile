# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CARGO_HOME=/tmp/cargo
ENV RUSTUP_HOME=/tmp/rustup

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Rust (КРИТИЧЕСКИ ВАЖНО!)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable

# Добавляем Rust в PATH
ENV PATH="/tmp/cargo/bin:${PATH}"

# Проверяем установку
RUN rustc --version && cargo --version

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    # Сначала устанавливаем простые зависимости
    pip install --no-cache-dir \
        aiogram==3.3.0 \
        aiohttp \
        supabase==2.3.0 \
        python-dotenv==1.0.0 \
        groq==0.4.0 \
        edge-tts==6.1.9 && \
    # Потом устанавливаем sentence-transformers с флагами
    pip install --no-cache-dir \
        --no-build-isolation \
        sentence-transformers==2.3.1

# Копируем весь проект
COPY . .

# Создаем необходимые папки
RUN mkdir -p data src/database src/services src/keyboards src/handlers

# Запускаем скрипт генерации аудио
RUN python generate_audio.py

# Команда запуска
CMD ["python", "main.py"]
