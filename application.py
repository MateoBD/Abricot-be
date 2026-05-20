from dotenv import load_dotenv

# Load .env before importing app.config — ProductionConfig reads ALLOWED_ORIGINS at import time.
load_dotenv()

from app import create_app  # noqa: E402

# loop = asyncio.get_event_loop()

application = create_app()


if __name__ == "__main__":
    port = int(application.config.get("PORT", 5000))
    application.run(port=port)
