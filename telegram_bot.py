import json, asyncio
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from inercia import calcular_inercia_mensual

CONFIG_FILE = "config.json"

async def send_results():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    bot = Bot(cfg["token"])
    rank = calcular_inercia_mensual()
    msg  = "📊 *Inercia Alcista – último día mes*\n\n"
    for i, (t, s) in enumerate(rank, 1):
        if i <= 2:
            msg += f"🎯 *{i}. {t}: {s:.2f}* ← ELEGIBLE\n"
        else:
            msg += f"{i}. {t}: {s:.2f}\n"
    await bot.send_message(chat_id=cfg["chat_id"], text=msg, parse_mode="Markdown")

async def start_bot():
    sched = AsyncIOScheduler()
    sched.add_job(send_results, 'cron', day='last', hour=18, minute=0)
    sched.start()
    print("Bot activo → envío el último día de cada mes a las 18:00 UTC.")
    await asyncio.Event().wait()   # forever
