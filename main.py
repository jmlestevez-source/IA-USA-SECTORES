### 📄 `main.py`
```python
import json, os, asyncio
from telegram_bot import start_bot

CONFIG_FILE = "config.json"

def init_config():
    if not os.path.exists(CONFIG_FILE):
        token  = input("Bot token de Telegram: ").strip()
        chat_id= input("Chat ID de Telegram: ").strip()
        with open(CONFIG_FILE, "w") as f:
            json.dump({"token": token, "chat_id": chat_id}, f)
        print("Configuración guardada.")
    else:
        print("Usando configuración existente.")

if __name__ == "__main__":
    init_config()
    asyncio.run(start_bot())
