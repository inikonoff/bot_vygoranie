import os
import logging
from dotenv import load_dotenv

# load_dotenv работает локально (из .env файла).
# На Render переменные уже в окружении — load_dotenv их не перезапишет.
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
        val = os.environ.get("GROQ_API_KEY")
        if not val:
            logger.warning("⚠️ GROQ_API_KEY не задан — LLM-функции недоступны")
            return ""
        return val


config = Config()
