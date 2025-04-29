# main.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, status
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Import your bot's handlers and settings
from config import bot_config
from telegram_bot import (
    start,
    handle_sheet_selection,
    handle_revision_callback,
    cancel,
    error_handler,
    SELECTING_SHEET,
    CONFIRM_REVISION,
)

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Global Application instance ---
# Initialize application later in lifespan event
ptb_application: Application | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown logic."""
    global ptb_application
    logger.info("Application startup...")

    if not bot_config.telegram_bot_token:
        logger.error("FATAL: Telegram Bot Token not configured.")
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set.")

    if not bot_config.webhook_url:
        logger.error("FATAL: Webhook URL not configured.")
        raise RuntimeError("WEBHOOK_URL environment variable is not set.")

    # Create the Application instance
    ptb_application = (
        Application.builder().token(bot_config.telegram_bot_token).build()
    )

    # --- Add Handlers (Same as in your original polling setup) ---
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_SHEET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sheet_selection)
            ],
            CONFIRM_REVISION: [CallbackQueryHandler(handle_revision_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        # Optional: Configure persistence if needed across restarts
    )
    ptb_application.add_handler(conv_handler)
    ptb_application.add_error_handler(error_handler)

    # --- Webhook Setup ---
    # Drop pending updates from previous runs (optional but recommended)
    await ptb_application.initialize() # Required before calling bot methods
    await ptb_application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Attempting to set webhook...")
    try:
        webhook_set = await ptb_application.bot.set_webhook(
            url=bot_config.webhook_url,
            allowed_updates=Update.ALL_TYPES,
            secret_token=bot_config.webhook_secret_token # Pass None if not set
        )
        if not webhook_set:
            logger.error("Webhook setup failed!")
            raise RuntimeError("Failed to set Telegram webhook.")
        logger.info(f"Webhook successfully set to {bot_config.webhook_url}")
        # Important: PTB Application must be initialized *before* processing updates
        await ptb_application.start()

    except Exception as e:
        logger.error(f"Error setting webhook: {e}", exc_info=True)
        raise # Re-raise after logging

    yield # Application runs here

    # --- Shutdown Logic ---
    logger.info("Application shutdown...")
    if ptb_application:
        await ptb_application.stop()
        # Optionally delete the webhook on shutdown
        # try:
        #     await ptb_application.bot.delete_webhook()
        #     logger.info("Webhook deleted.")
        # except Exception as e:
        #     logger.warning(f"Could not delete webhook during shutdown: {e}")
        await ptb_application.shutdown()
    logger.info("Shutdown complete.")


# Create FastAPI app with lifespan manager
app = FastAPI(lifespan=lifespan)

@app.post("/") # Root path often used for health checks
async def root():
    return {"status": "ok"}

@app.post("/webhook") # Endpoint Telegram will send updates to
async def telegram_webhook(request: Request):
    """Handles incoming Telegram updates."""
    if not ptb_application:
         logger.error("PTB application not initialized during webhook call.")
         raise HTTPException(status_code=500, detail="Bot not ready")

    # Verify secret token if configured
    if bot_config.webhook_secret_token:
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_token != bot_config.webhook_secret_token:
            logger.warning("Invalid secret token received.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    try:
        # Get request body as bytes for PTB processing
        update_data = await request.json()
        update = Update.de_json(data=update_data, bot=ptb_application.bot)
        logger.debug(f"Processing update: {update.update_id}")

        # Process the update using PTB's internal queue and handlers
        # run_sync ensures compatibility with PTB's async structure
        await ptb_application.process_update(update)

        # Return 200 OK to Telegram quickly
        return Response(status_code=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        # Avoid sending detailed errors back to Telegram for security
        raise HTTPException(status_code=500, detail="Internal server error processing update")

# --- Optional: Run locally with Uvicorn (for development) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for local development...")
    # Note: For local dev, you'd typically use polling or ngrok for webhooks
    # This run command assumes you have Uvicorn installed (`pip install uvicorn[standard]`)
    # Running this directly won't work easily with webhooks unless using a tunneling service like ngrok.
    # Deployment via Docker/Cloud Run is the primary target for this setup.
    uvicorn.run(app, host="0.0.0.0", port=8000)