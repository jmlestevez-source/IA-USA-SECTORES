import os
import asyncio
from telegram import Bot
from inercia import calcular_inercia_mensual, formato_mensaje, backtest_completo

async def send_results(include_backtest=True):
    """
    Envía los resultados por Telegram.
    
    Args:
        include_backtest: Si True, envía también el backtest. Default: True
    """
    
    token = os.environ.get('TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    # Variable de entorno para controlar backtest
    skip_backtest = os.environ.get('SKIP_BACKTEST', '0') == '1'
    if skip_backtest:
        include_backtest = False
    
    if not token:
        print("❌ Error: Variable TOKEN no configurada")
        return False
    
    if not chat_id:
        print("❌ Error: Variable CHAT_ID no configurada")
        return False
    
    try:
        bot = Bot(token=token)
        
        # === 1. ENVIAR INERCIA ACTUAL ===
        print("🔄 Calculando inercia actual...")
        resultados = calcular_inercia_mensual()
        mensaje_inercia = formato_mensaje(resultados)
        
        print("📤 Enviando inercia a Telegram...")
        await bot.send_message(
            chat_id=chat_id,
            text=mensaje_inercia,
            parse_mode='Markdown'
        )
        print("✅ Inercia enviada!")
        
        # === 2. ENVIAR BACKTEST (opcional) ===
        if include_backtest:
            print("\n🔄 Ejecutando backtest...")
            backtest_res = backtest_completo()
            
            if backtest_res and 'top2' in backtest_res and 'top3' in backtest_res:
                mensaje_backtest = formato_backtest(backtest_res)
                
                print("📤 Enviando backtest a Telegram...")
                await bot.send_message(
                    chat_id=chat_id,
                    text=mensaje_backtest,
                    parse_mode='Markdown'
                )
                print("✅ Backtest enviado!")
            else:
                print("⚠️ No se pudo generar el backtest")
        else:
            print("⏭️ Backtest omitido (SKIP_BACKTEST=1)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def formato_backtest(resultados):
    """Formatea los resultados del backtest para Telegram."""
    
    top2 = resultados['top2']
    top3 = resultados['top3']
    bench = top2['benchmark']
    
    años = top2['años']
    fecha_inicio = top2['resultados_df'].index[0].strftime('%Y-%m')
    fecha_fin = top2['resultados_df'].index[-1].strftime('%Y-%m')
    
    lineas = [
        "📈 *BACKTEST INERCIA ALCISTA*",
        f"📅 Período: {fecha_inicio} → {fecha_fin}",
        f"⏱️ Duración: {años:.1f} años",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "*🥇 ESTRATEGIA TOP 2*",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"💰 Valor Final: ${top2['portfolio']['valor_final']:.2f}",
        f"📊 CAGR: {top2['portfolio']['cagr']:+.2f}%",
        f"📉 Max Drawdown: {top2['portfolio']['max_dd']:.2f}%",
        f"⚖️ Sharpe Ratio: {top2['portfolio']['sharpe']:.2f}",
        f"🔄 Trades: {top2['trades']}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "*🥈 ESTRATEGIA TOP 3*",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"💰 Valor Final: ${top3['portfolio']['valor_final']:.2f}",
        f"📊 CAGR: {top3['portfolio']['cagr']:+.2f}%",
        f"📉 Max Drawdown: {top3['portfolio']['max_dd']:.2f}%",
        f"⚖️ Sharpe Ratio: {top3['portfolio']['sharpe']:.2f}",
        f"🔄 Trades: {top3['trades']}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "*📌 BENCHMARK (SPY B&H)*",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"💰 Valor Final: ${bench['valor_final']:.2f}",
        f"📊 CAGR: {bench['cagr']:+.2f}%",
        f"📉 Max Drawdown: {bench['max_dd']:.2f}%",
        f"⚖️ Sharpe Ratio: {bench['sharpe']:.2f}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "*📊 COMPARATIVA*",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    
    # Comparar TOP 2 vs SPY
    diff_cagr_2 = top2['portfolio']['cagr'] - bench['cagr']
    if diff_cagr_2 > 0:
        lineas.append(f"✅ TOP 2 supera SPY en {diff_cagr_2:.2f}%/año")
    else:
        lineas.append(f"❌ TOP 2 inferior a SPY en {abs(diff_cagr_2):.2f}%/año")
    
    # Comparar TOP 3 vs SPY
    diff_cagr_3 = top3['portfolio']['cagr'] - bench['cagr']
    if diff_cagr_3 > 0:
        lineas.append(f"✅ TOP 3 supera SPY en {diff_cagr_3:.2f}%/año")
    else:
        lineas.append(f"❌ TOP 3 inferior a SPY en {abs(diff_cagr_3):.2f}%/año")
    
    # Mejor estrategia
    lineas.append("")
    if top2['portfolio']['sharpe'] > top3['portfolio']['sharpe']:
        lineas.append("🏆 _Mejor riesgo/retorno: TOP 2_")
    else:
        lineas.append("🏆 _Mejor riesgo/retorno: TOP 3_")
    
    return "\n".join(lineas)


if __name__ == "__main__":
    asyncio.run(send_results())
