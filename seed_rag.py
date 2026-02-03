# seed_rag.py
import os
from supabase import create_client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# 1. Setup
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)
model = SentenceTransformer('all-MiniLM-L6-v2') # Бесплатная легкая модель

# 2. Текст из методичек (пример)
chunks = [
    "Эмоциональное выгорание — это состояние истощения...",
    "Техника заземления 5-4-3-2-1 помогает при острой тревоге...",
    "Деперсонализация проявляется в цинизме и безразличии к коллегам..."
]

# 3. Process
for text in chunks:
    vector = model.encode(text).tolist()
    data = {
        "content": text,
        "embedding": vector,
        "metadata": {"source": "manual"}
    }
    supabase.table("knowledge_base").insert(data).execute()
    print(f"Inserted: {text[:20]}...")
