# Используем легкий образ Python 3.11
FROM python:3.11-slim

# Отключаем создание .pyc файлов и буферизацию вывода
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# КРИТИЧЕСКИ ВАЖНО: Устанавливаем переменные окружения для Cargo
ENV CARGO_HOME=/tmp/cargo
ENV RUSTUP_HOME=/tmp/rustup

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Rust с временными путями
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable \
    && export PATH="/tmp/cargo/bin:$PATH" \
    && rustc --version

# Добавляем cargo в PATH
ENV PATH="/tmp/cargo/bin:${PATH}"

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем Python-библиотеки с принудительной установкой wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    # Сначала устанавливаем пакеты без Rust зависимостей
    pip install --no-cache-dir \
        aiogram==3.3.0 \
        aiohttp \
        supabase==2.3.0 \
        python-dotenv==1.0.0 \
        groq==0.4.0 \
        edge-tts==6.1.9 && \
    # Затем пытаемся установить sentence-transformers с флагами
    pip install --no-cache-dir --no-build-isolation sentence-transformers==2.3.1

# Копируем весь код проекта в контейнер
COPY . .

# Создаем папку data
RUN mkdir -p data

CMD ["python", "main.py"]
