"""
Загрузка data/knowledge.txt в таблицу knowledge_base (полнотекстовый поиск).
Сначала выполните migrations/001_persistence_digest_rag.sql. Запуск: python seed_rag.py
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SOURCE = "knowledge.txt"


def seed():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("❌ Не заданы SUPABASE_URL или SUPABASE_KEY")
        return

    file_path = os.path.join("data", SOURCE)
    if not os.path.exists(file_path):
        print(f"❌ Файл {file_path} не найден.")
        return
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    if not chunks:
        print("⚠️ Файл пуст. Пропускаем.")
        return
    print(f"Найдено {len(chunks)} фрагментов.")

    supabase = create_client(url, key)
    # перезаливка без дублей
    supabase.table("knowledge_base").delete().eq("metadata->>source", SOURCE).execute()
    rows = [{"content": c, "metadata": {"source": SOURCE}} for c in chunks]
    supabase.table("knowledge_base").insert(rows).execute()
    print(f"🎉 Загружено {len(rows)} фрагментов.")


if __name__ == "__main__":
    seed()
