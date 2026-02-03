import os
from supabase import create_client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

def seed():
    # 1. Подключение
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Ошибка: Не заданы SUPABASE_URL или KEY в .env")
        return

    print("Подключаемся к Supabase...")
    supabase = create_client(url, key)
    
    # 2. Инициализация модели (скачается 1 раз)
    print("Загружаем модель эмбеддингов...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 3. Чтение файла
    file_path = "data/knowledge.txt"
    if not os.path.exists(file_path):
        print(f"❌ Файл {file_path} не найден.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        print("⚠️ Файл пуст. Пропускаем.")
        return

    # Разбиваем текст на кусочки (чанков) по пустым строкам
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    print(f"Найдено {len(chunks)} фрагментов текста.")

    # 4. Заливка
    for i, chunk in enumerate(chunks):
        # Превращаем текст в цифры
        vector = model.encode(chunk).tolist()
        
        data = {
            "content": chunk,
            "embedding": vector,
            "metadata": {"source": "knowledge.txt"}
        }
        
        try:
            supabase.table("knowledge_base").insert(data).execute()
            print(f"✅ Загружен фрагмент {i+1}/{len(chunks)}")
        except Exception as e:
            print(f"❌ Ошибка при загрузке фрагмента {i+1}: {e}")

    print("🎉 База знаний успешно обновлена!")

if __name__ == "__main__":
    seed()
