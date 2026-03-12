import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class TelegramAPI:
    """Interacts with the Telegram Bot API."""
    def __init__(self, token, parser, crew):
        self.token = token
        self.parser = parser
        self.crew = crew
        self.app = ApplicationBuilder().token(self.token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self._start_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._message_handler))

    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Hello! I am JARVIS. Send me a command and I will execute it.")

    async def _message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text = update.message.text
        chat_id = update.effective_chat.id
        
        print(f"[JARVIS-API] Received from Telegram: {message_text}")
        await update.message.reply_text("🧠 Processing...")

        try:
            # We must run the parsing and execution in a separate thread since telegram is asyncio
            # but crew execution is completely synchronous and can block for a long time.
            intent = await asyncio.to_thread(self.parser.parse, message_text)
            
            # Setup a screenshot sender callback (sync -> async bridge)
            # Since crew.execute is synchronous, it needs a synchronous callback function.
            def sync_send_photo(file_path):
                # Schedule the async call in the running event loop
                asyncio.run_coroutine_threadsafe(
                    context.bot.send_photo(chat_id=chat_id, photo=open(file_path, 'rb')),
                    asyncio.get_running_loop()
                )
                
            self.crew.whatsapp_sender = sync_send_photo  # Reusing the existing attribute name
            
            result = await asyncio.to_thread(self.crew.execute, intent)
            response = self._format_response(result)
        except Exception as e:
            response = f"❌ Error: {e}"

        await update.message.reply_text(response)

    def _format_response(self, result: dict) -> str:
        """Format agent result into a Telegram-friendly message."""
        if not result:
            return "✅ Done."
        status = result.get("status", "unknown")
        message = result.get("message", "")
        data = result.get("data", "")

        if status == "success":
            return f"✅ {message}\n{data}".strip()
        elif status == "error":
            return f"❌ {message}"
        else:
            return str(message or result)

    def start(self):
        """Starts the Telegram bot listening for messages."""
        print("[JARVIS-API] 🚀 Telegram API Server started.")
        # run_polling connects to Telegram and handles the event loop properly
        self.app.run_polling()
