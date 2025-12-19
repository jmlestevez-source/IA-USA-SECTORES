import os
import asyncio
from telegram import Bot
from inercia import calcular_inercia_mensual, formato_mensaje

async def send_results():
    """Envía los resultados por Telegram."""
    
    token = os.environ.get('TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token:
        print("❌ Error: Variable TOKEN no configurada")
        return False
    
    if not chat_id:
        print("❌ Error: Variable CHAT_ID no configurada")
        return False
    
    print("🔄 Calculando inercia...")
    resultados = calcular_inercia_mensual()
    
    print("📤 Enviando a Telegram...")
    mensaje = formato_mensaje(resultados)
    
    try:
        bot = Bot(token=token)
        await bot.send_message(
            chat_id=chat_id,
            text=mensaje,
            parse_mode='Markdown'
        )
        print("✅ Mensaje enviado correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(send_results())
