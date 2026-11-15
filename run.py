import asyncio
import logging
import sys
import uvicorn
from app.config import settings
from app.database import init_db
from app.bot import create_bot_app
from app.web_app import app as fastapi_app

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("CalorieBot")

async def run_web_server(config: uvicorn.Config):
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    print("=" * 60)
    print("⚡ CALORIEBOT // HIGH PERFORMANCE NUTRITION TRACKER")
    print(f"🎯 User: {settings.USER_NAME} | 21M, 168cm | 89 kg ➔ 70 kg")
    print(f"🔥 Daily Budget: {settings.DAILY_CALORIE_BUDGET} kcal | Target Deficit: ~500 kcal/day")
    print("=" * 60)

    # 1. Initialize SQLite Database
    init_db()
    logger.info("Database initialized successfully.")

    # 2. Setup Uvicorn web server
    config = uvicorn.Config(
        app=fastapi_app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info",
        loop="asyncio"
    )

    tasks = []

    # 3. Setup Telegram Bot if token provided
    bot_app = create_bot_app()
    if bot_app:
        logger.info("Starting Telegram Bot with polling...")
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        print("🤖 Telegram Bot is ONLINE! Ready to receive messages.")
    else:
        print("\n⚠️ NOTICE: TELEGRAM_BOT_TOKEN not configured in .env.")
        print("👉 You can still use the Web Dashboard at: http://localhost:8000/dashboard")
        print("👉 To enable the Telegram Bot, add your token from @BotFather to your .env file.\n")

    # 4. Start web server
    print(f"🌐 Web Dashboard live at: http://localhost:{settings.PORT}/dashboard\n")
    server = uvicorn.Server(config)
    
    try:
        if bot_app:
            await asyncio.gather(
                server.serve(),
            )
        else:
            await server.serve()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        if bot_app:
            logger.info("Stopping Telegram Bot...")
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCalorieBot stopped.")
