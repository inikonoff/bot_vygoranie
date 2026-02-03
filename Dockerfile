# Используем легкий образ Python 3.11
FROM python:3.11-slim

# Отключаем создание .pyc файлов и буферизацию вывода (чтобы логи летели сразу)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости включая Rust
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    pkg-config \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && export PATH="/root/.cargo/bin:$PATH" \
    && rm -rf /var/lib/apt/lists/*

# Добавляем cargo в PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем Python-библиотеки с предварительной сборкой некоторых пакетов
# Используем --no-build-isolation для maturin если будет нужно
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY . .

# Создаем папку data, если её нет (на всякий случай)
RUN mkdir -p data

# Эта команда будет выполняться по умолчанию, если не переопределить её в Render
# Но мы переопределим её в настройках Render для надежности
CMD ["python", "main.py"]
