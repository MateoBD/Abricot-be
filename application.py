from dotenv import load_dotenv

from app import create_app

# Call the application factory function to construct a Flask application
# instance using the development configuration
load_dotenv()

# loop = asyncio.get_event_loop()

application = create_app()


if __name__ == "__main__":
    port = int(application.config.get("PORT", 5000))
    application.run(port=port)
