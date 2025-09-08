import json, asyncio
from telegram import Bot
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from inercia import calcular_inercia_mensual

CONFIG_FILE = "config.json"

# ---------- lógica de envío ----------
async def send_results(chat_id: str = None):
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    bot = Bot(cfg["token"])
    if chat_id is None:
        chat_id = cfg["chat_id"]

    rank = calcular_inercia_mensual()
    msg  = "📊 *Inercia Alcista – último día mes*\n\n"
    for i, (t, s) in enumerate(rank, 1):
        if i <= 2:
            msg += f"🎯 *{i}. {t}: {s:.2f}* ← ELEGIBLE\n"
        else:
            msg += f"{i}. {t}: {s:.2f}\n"
    await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

# ---------- comando manual ----------
async def cmd_rank(update, context):
    await send_results(update.effective_chat.id)

# ---------- arranque ----------
async def start_bot():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    app = Application.builder().token(cfg["token"]).build()
    app.add_handler(CommandHandler("rank", cmd_rank))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_results, 'cron', day='last', hour=22, minute=0)
    scheduler.start()

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()  # forever
