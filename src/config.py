import os
import logging
from dotenv import load_dotenv

# Загружаем .env файл если он есть (для локальной разработки)
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """
    Читает переменные окружения через свойства, а не при импорте.
    Это гарантирует, что значения берутся уже после того, как
    Render/Docker успел передать их в процесс.
    """

    @property
    def BOT_TOKEN(self) -> str:
        val = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
        if not val:
            logger.error("BOT_TOKEN not found in environment variables")
            logger.error(f"Available env vars: {list(os.environ.keys())}")
            raise RuntimeError("❌ BOT_TOKEN не задан в переменных окружения")
        return val

    @property
    def SUPABASE_URL(self) -> str:
        val = os.environ.get("SUPABASE_URL")
        if not val:
            logger.error("SUPABASE_URL not found in environment variables")
            raise RuntimeError("❌ SUPABASE_URL не задан в переменных окружения")
        return val

    @property
    def SUPABASE_KEY(self) -> str:
        val = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        if not val:
            logger.error("SUPABASE_KEY not found in environment variables")
            raise RuntimeError("❌ SUPABASE_KEY не задан в переменных окружения")
        return val

    @property
    def GROQ_API_KEY(self) -> str:
        # Пробуем разные возможные имена переменных
        val = (
            os.environ.get("GROQ_API_KEY") or 
            os.environ.get("GROQ_KEY") or 
            os.environ.get("GROQ_API_TOKEN")
        )
        
        if not val:
            logger.warning("⚠️ GROQ_API_KEY не задан — LLM-функции недоступны")
            logger.warning("Доступные переменные окружения: %s", list(os.environ.keys()))
            return ""
        
        # Очищаем ключ от возможных пробелов и кавычек
        val = val.strip().strip("'").strip('"')
        logger.info(f"✅ GROQ_API_KEY найден, длина: {len(val)}")
        logger.info(f"✅ Первые символы: {val[:8]}...")
        
        return val


config = Config()
