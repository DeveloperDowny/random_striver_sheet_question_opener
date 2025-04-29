# /bot/telegram_bot.py

import logging
import os
import requests
from typing import Dict, Any, Optional, List, cast

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import telegramify_markdown

from pydantic import (
    BaseModel,
    Field,
)  # Using Pydantic for request validation might be good practice

# --- Configuration ---
# It's highly recommended to use environment variables for sensitive info
from config import bot_config
TELEGRAM_BOT_TOKEN = bot_config.telegram_bot_token
SERVER_BASE_URL = bot_config.server_base_url

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- Pydantic Models (Optional but recommended for request bodies) ---
class SheetSelectionRequest(BaseModel):
    filter_text: Optional[str] = None
    selected_index: Optional[int] = None
    random_selection: bool = False


class RevisionRequest(BaseModel):
    sheet_type: str
    topic_id: str


# --- Conversation States ---
SELECTING_SHEET, CONFIRM_REVISION = range(2)


# --- Helper Functions ---
async def fetch_sheet_types(context: ContextTypes.DEFAULT_TYPE) -> List[str]:
    """Fetches the list of available sheet types from the server."""
    try:
        response = requests.get(f"{SERVER_BASE_URL}/sheet-types")
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        sheet_types = data.get("sheet_types", [])
        context.user_data["sheet_types"] = sheet_types  # Store for later use
        return sheet_types
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch sheet types: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching sheet types: {e}")
        return []


async def select_topic_from_server(
    selection: SheetSelectionRequest, context: ContextTypes.DEFAULT_TYPE
) -> Optional[Dict[str, Any]]:
    """Selects a topic using the server API."""
    try:
        # Use .model_dump() for Pydantic v2, .dict() for v1
        # Filter out None values to match server expectations if needed
        payload = selection.model_dump(exclude_none=True)
        logger.info(f"Sending selection request to server: {payload}")

        response = requests.post(f"{SERVER_BASE_URL}/select-topic", json=payload)
        response.raise_for_status()
        topic_data = response.json()
        # Store necessary details for the revision step
        context.user_data["current_topic"] = {
            "sheet_type": topic_data.get("sheet_type"),
            "topic_id": topic_data.get("topic_id"),
        }
        return topic_data
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Failed to select topic: {e} - Status Code: {e.response.status_code if e.response else 'N/A'} - Response: {e.response.text if e.response else 'N/A'}"
        )
        await context.bot.send_message(
            chat_id=context.user_data.get(
                "chat_id", "default_chat_id"
            ),  # Ensure chat_id is stored or handle error
            text=(
                f"Error selecting topic: {e.response.json().get('detail', str(e))}"
                if e.response
                else str(e)
            ),
        )
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while selecting topic: {e}")
        await context.bot.send_message(
            chat_id=context.user_data.get("chat_id", "default_chat_id"),
            text=f"An unexpected error occurred: {str(e)}",
        )
        return None


async def mark_topic_for_revision(
    revision_details: RevisionRequest, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Marks a topic for revision using the server API."""
    try:
        payload = revision_details.model_dump()  # Use .model_dump() for Pydantic v2
        response = requests.post(f"{SERVER_BASE_URL}/mark-revision", json=payload)
        response.raise_for_status()
        logger.info(
            f"Successfully marked topic {revision_details.topic_id} for revision."
        )
        return True
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Failed to mark topic for revision: {e} - Response: {e.response.text if e.response else 'N/A'}"
        )
        await context.bot.send_message(
            chat_id=context.user_data.get("chat_id", "default_chat_id"),
            text=(
                f"Error marking for revision: {e.response.json().get('detail', str(e))}"
                if e.response
                else str(e)
            ),
        )
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while marking for revision: {e}")
        await context.bot.send_message(
            chat_id=context.user_data.get("chat_id", "default_chat_id"),
            text=f"An unexpected error occurred: {str(e)}",
        )
        return False


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and displays sheet types."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    context.user_data["chat_id"] = chat_id  # Store chat_id

    logger.info(
        f"User {user.username} (ID: {user.id}) started the bot in chat {chat_id}."
    )

    await update.message.reply_html(
        f"Hi {user.mention_html()}! 👋\n"
        "I can help you select a random topic from various sheets.\n"
        "Fetching available sheet types..."
    )

    sheet_types = await fetch_sheet_types(context)

    if not sheet_types:
        await update.message.reply_text(
            "Could not fetch sheet types from the server. Please try again later or contact the administrator."
        )
        return ConversationHandler.END

    # Format the list for display
    sheet_list_text = "Available sheet types:\n"
    for i, sheet in enumerate(sheet_types):
        sheet_list_text += f"  {i}: `{sheet}`\n"  # Use backticks for monospace

    sheet_list_text += (
        "\n"
        "Enter:\n"
        "➡️ A number (e.g., `8`) to select one.\n"
        "➡️ Text (e.g., `dsa`) to filter by name.\n"
        "➡️ `random` to pick a random sheet and topic."
    )

    converted = telegramify_markdown.standardize(sheet_list_text)

    await update.message.reply_text(converted, parse_mode="MarkdownV2")

    return SELECTING_SHEET


# --- Message Handlers ---
async def handle_sheet_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles user input for sheet selection (number, text, or 'random')."""
    user_input = update.message.text.strip()
    chat_id = update.effective_chat.id
    context.user_data["chat_id"] = chat_id  # Ensure chat_id is stored

    sheet_types = context.user_data.get("sheet_types")
    if not sheet_types:
        await update.message.reply_text(
            "Sheet types not loaded. Please use /start again."
        )
        return ConversationHandler.END

    selection_request = None
    selected_sheet_name_for_log = "N/A"  # For logging purposes

    if user_input.lower() == "random":
        selection_request = SheetSelectionRequest(random_selection=True)
        selected_sheet_name_for_log = "Random"
    elif user_input.isdigit():
        try:
            index = int(user_input)
            if 0 <= index < len(sheet_types):
                # Important: The server expects the index relative to the *potentially filtered* list.
                # However, our current server implementation handles filtering internally
                # if filter_text is provided OR picks from the full list if selected_index is used without filter text.
                # Let's assume the user provides the index based on the full list shown initially.
                selection_request = SheetSelectionRequest(selected_index=index)
                selected_sheet_name_for_log = sheet_types[index]  # For logging only
            else:
                await update.message.reply_text(
                    f"Invalid index. Please enter a number between 0 and {len(sheet_types) - 1}."
                )
                return SELECTING_SHEET  # Stay in the same state
        except ValueError:
            await update.message.reply_text(
                "Invalid input. Please enter a number, text, or 'random'."
            )
            return SELECTING_SHEET
    else:  # Treat as filter text
        # The server endpoint /select-topic can handle filter_text directly
        selection_request = SheetSelectionRequest(filter_text=user_input)
        selected_sheet_name_for_log = f"Filtered by '{user_input}'"

    if selection_request:
        logger.info(
            f"User {update.effective_user.username} selected: {selected_sheet_name_for_log}"
        )
        await update.message.reply_text("Processing your selection...")

        topic_data = await select_topic_from_server(selection_request, context)

        if topic_data:
            # Format the response
            title = topic_data.get("title", "N/A")
            link = topic_data.get("link", "#")
            sheet_type = topic_data.get("sheet_type", "N/A")
            topic_id = topic_data.get("topic_id", "N/A")
            # details = topic_data.get('details', {}) # Contains the raw topic data

            response_text = (
                f"Selected from sheet: `{sheet_type}`\n\n"
                f"*Topic:* {title}\n"
                f"*ID:* `{topic_id}`\n\n"
                # Escape markdown characters in the link if necessary, but requests should handle URL encoding
                f"[Search Link]({link})"
            )

            # Ask for revision with Inline Keyboard
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Yes, Mark for Revision", callback_data="mark_revision_yes"
                    ),
                    InlineKeyboardButton("No", callback_data="mark_revision_no"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                response_text,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2",
                disable_web_page_preview=True,
            )
            return CONFIRM_REVISION  # Move to revision confirmation state
        else:
            # Error message already sent by select_topic_from_server
            await update.message.reply_text(
                "Failed to get a topic. Please try again or use /start."
            )
            # Decide whether to end conversation or allow retry
            return SELECTING_SHEET  # Allow user to try again

    else:
        await update.message.reply_text(
            "Invalid selection. Please enter a number, text, or 'random'."
        )
        return SELECTING_SHEET  # Stay in the same state


# --- Callback Query Handler ---
async def handle_revision_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the 'Yes'/'No' response for marking revision."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    user_choice = query.data

    current_topic = context.user_data.get("current_topic")
    if not current_topic:
        await query.edit_message_text(
            text="Sorry, I lost track of the topic. Please start again with /start."
        )
        return ConversationHandler.END

    if user_choice == "mark_revision_yes":
        logger.info(
            f"User {update.effective_user.username} chose to mark topic {current_topic['topic_id']} for revision."
        )
        revision_request = RevisionRequest(
            sheet_type=current_topic["sheet_type"], topic_id=current_topic["topic_id"]
        )
        success = await mark_topic_for_revision(revision_request, context)
        if success:
            await query.edit_message_text(
                text=f"✅ Topic `{current_topic['topic_id']}` marked for revision."
            )
        else:
            # Error message sent by mark_topic_for_revision
            await query.edit_message_text(text="⚠️ Failed to mark topic for revision.")

    elif user_choice == "mark_revision_no":
        logger.info(
            f"User {update.effective_user.username} chose *not* to mark topic {current_topic['topic_id']} for revision."
        )
        await query.edit_message_text(text="Okay, topic not marked for revision.")

    # Clean up topic data for this round
    del context.user_data["current_topic"]

    # Ask if the user wants another topic
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="You can start again with /start to get another topic.",
    )

    return ConversationHandler.END  # End the conversation here


# --- Fallback and Error Handlers ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.effective_user
    logger.info(f"User {user.first_name} canceled the conversation.")
    await update.message.reply_text("Okay, conversation canceled. Use /start anytime!")
    # Clean up user data if needed
    context.user_data.clear()
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")
    # Optionally send a message to the user
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="An internal error occurred. Please try again later.",
            )
        except Exception as e:
            logger.error(
                f"Failed to send error message to chat {update.effective_chat.id}: {e}"
            )


# --- Main Application Setup ---
def main() -> None:
    """Run the bot."""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "FATAL: Telegram Bot Token not configured. Set the TELEGRAM_BOT_TOKEN environment variable."
        )
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler setup
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_SHEET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sheet_selection)
            ],
            CONFIRM_REVISION: [CallbackQueryHandler(handle_revision_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
