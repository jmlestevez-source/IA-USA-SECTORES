import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

ETFS = ["XLK", "XLV", "XLF", "XLY", "XLC", "XLI", "XLP", "XLE", "XLU", "XLRE", "XLB", "IEF"]
BENCHMARK = "SPY"


def calcular_atr(high, low, close, period=14):
    """Calcula el Average True Range estándar."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def descargar_datos_mensuales(ticker, start="2000-01-01", end=None):
    """
    Descarga datos y resamplea a mensual.
    Incluye el mes en curso (vela abierta) para cálculos en tiempo real.
    """
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")
    
    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval="1d",
            progress=False,
            auto_adjust=True
        )
        
        if df.empty:
            return None
        
        # Manejar MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
        
        # Resamplear a mensual (incluye mes en curso)
        df_monthly = df.resample('ME').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        return df_monthly
        
    except Exception as e:
        print(f"❌ Error descargando {ticker}: {e}")
        return None


def calcular_fuerza_alcista(df_monthly):
    """
    Calcula la Fuerza Alcista para cada mes.
    
    Fórmula PRT:
    Ind1 = (CLOSE-CLOSE[8])/CLOSE[8]
    Ind2 = (CLOSE-CLOSE[10])/CLOSE[10]
    Ind3 = AverageTrueRange[14](close)
    Ind4 = Average[14](close)
    Ind5 = Ind3/Ind4
    F = (Ind1*0.4 + Ind2*0.2) / (Ind5*0.4) * 100
    """
    close = df_monthly['Close']
    high = df_monthly['High']
    low = df_monthly['Low']
    
    # Ind1 = ROC 8 meses
    ind1 = (close - close.shift(8)) / close.shift(8)
    
    # Ind2 = ROC 10 meses
    ind2 = (close - close.shift(10)) / close.shift(10)
    
    # Ind3 = ATR 14 meses
    ind3 = calcular_atr(high, low, close, period=14)
    
    # Ind4 = SMA 14 meses
    ind4 = close.rolling(window=14).mean()
    
    # Ind5 = Volatilidad relativa
    ind5 = ind3 / ind4
    
    # Fuerza Alcista
    fuerza = ((ind1 * 0.4 + ind2 * 0.2) / (ind5 * 0.4)) * 100
    
    return fuerza


def calcular_inercia_mensual():
    """
    Calcula la Inercia Alcista actual para cada ETF.
    Incluye el mes en curso (como si hoy fuera fin de mes).
    """
    resultados = []
    
    print("📅 Calculando con datos hasta HOY (incluye mes en curso)\n")
    
    for ticker in ETFS:
        try:
            df_monthly = descargar_datos_mensuales(ticker, start="2020-01-01")
            
            if df_monthly is None or len(df_monthly) < 15:
                print(f"⚠️ {ticker}: Datos insuficientes")
                continue
            
            fuerza = calcular_fuerza_alcista(df_monthly)
            fa_actual = fuerza.iloc[-1]
            
            if pd.isna(fa_actual):
                print(f"⚠️ {ticker}: Valor NaN")
                continue
            
            close = df_monthly['Close']
            roc8 = ((close.iloc[-1] - close.iloc[-9]) / close.iloc[-9]) * 100 if len(close) > 9 else 0
            roc10 = ((close.iloc[-1] - close.iloc[-11]) / close.iloc[-11]) * 100 if len(close) > 11 else 0
            
            resultados.append({
                'ticker': ticker,
                'inercia': round(float(fa_actual), 2),
                'roc8': round(float(roc8), 2),
                'roc10': round(float(roc10), 2),
                'precio': round(float(close.iloc[-1]), 2),
                'fecha': df_monthly.index[-1].strftime('%Y-%m-%d')
            })
            
            print(f"✅ {ticker}: Fuerza Alcista = {fa_actual:.2f}")
            
        except Exception as e:
            print(f"❌ Error {ticker}: {e}")
    
    return sorted(resultados, key=lambda x: x['inercia'], reverse=True)


def formato_mensaje(resultados):
    """Formatea los resultados para Telegram."""
    if not resultados:
        return "⚠️ No se pudieron calcular resultados"
    
    fecha = datetime.now().strftime("%d/%m/%Y")
    
    lineas = [
        "📊 *INERCIA ALCISTA - SECTORES USA*",
        f"📅 {fecha} (incluye mes en curso)",
        ""
    ]
    
    for i, r in enumerate(resultados, 1):
        if i == 1:
            emoji = "🥇"
        elif i == 2:
            emoji = "🥈"
        elif i == 3:
            emoji = "🥉"
        else:
            emoji = "▪️"
        
        signo = "+" if r['inercia'] >= 0 else ""
        lineas.append(f"{emoji} *{r['ticker']}*: {signo}{r['inercia']:.2f}")
    
    lineas.append("")
    lineas.append("📈 *Detalles Top 3:*")
    for r in resultados[:3]:
        lineas.append(f"  • {r['ticker']}: ROC8={r['roc8']}% | ROC10={r['roc10']}%")
    
    lineas.append("")
    lineas.append(f"_Recomendados: {', '.join(r['ticker'] for r in resultados[:3])}_")
    
    return "\n".join(lineas)


# ============================================================
# BACKTEST ROTACIONAL
# ============================================================

def ejecutar_backtest(top_n=2, start_date="2000-01-01"):
    """
    Backtest rotacional mensual.
    
    - Cada fin de mes calcula Fuerza Alcista de todos los ETFs disponibles
    - Compra los top_n ETFs con mayor fuerza
    - Mantiene posición si el ETF sigue en el top (no vende para recomprar)
    - Compara con SPY como benchmark
    """
    print(f"\n{'='*60}")
    print(f"📈 BACKTEST ROTACIONAL TOP {top_n}")
    print(f"{'='*60}")
    print(f"📅 Período: {start_date} - Hoy")
    print(f"🔄 Rebalanceo: Mensual")
    print(f"📊 ETFs: {', '.join(ETFS)}")
    print()
    
    # Descargar todos los datos
    print("⏳ Descargando datos históricos...")
    datos = {}
    for ticker in ETFS + [BENCHMARK]:
        df = descargar_datos_mensuales(ticker, start=start_date)
        if df is not None and len(df) > 0:
            datos[ticker] = df
            print(f"  ✅ {ticker}: {len(df)} meses desde {df.index[0].strftime('%Y-%m')}")
        else:
            print(f"  ⚠️ {ticker}: Sin datos")
    
    if BENCHMARK not in datos:
        print(f"❌ Error: No se pudo descargar {BENCHMARK}")
        return None
    
    # Obtener fechas comunes
    benchmark_df = datos[BENCHMARK]
    fechas = benchmark_df.index[14:]  # Necesitamos 14 meses de historia para ATR
    
    # Calcular Fuerza Alcista para cada ETF en cada fecha
    print("\n⏳ Calculando Fuerza Alcista histórica...")
    fuerza_historica = {}
    returns_historico = {}
    
    for ticker in ETFS:
        if ticker not in datos:
            continue
        
        df = datos[ticker]
        fuerza = calcular_fuerza_alcista(df)
        returns_m = df['Close'].pct_change()
        
        fuerza_historica[ticker] = fuerza
        returns_historico[ticker] = returns_m
    
    # Simular estrategia
    print("⏳ Ejecutando simulación...")
    
    portfolio_value = [100.0]  # Empezamos con 100
    benchmark_value = [100.0]
    posiciones_actuales = set()
    trades_log = []
    
    fechas_validas = []
    
    for i, fecha in enumerate(fechas[:-1]):  # Hasta penúltimo mes
        fecha_siguiente = fechas[i + 1]
        
        # Obtener rankings de este mes
        rankings = []
        for ticker in ETFS:
            if ticker not in fuerza_historica:
                continue
            
            fuerza = fuerza_historica[ticker]
            if fecha not in fuerza.index:
                continue
            
            valor = fuerza.loc[fecha]
            if pd.notna(valor):
                rankings.append((ticker, valor))
        
        if len(rankings) < top_n:
            continue  # No hay suficientes ETFs elegibles
        
        fechas_validas.append(fecha_siguiente)
        
        # Ordenar por fuerza alcista
        rankings.sort(key=lambda x: x[1], reverse=True)
        nuevos_top = set([r[0] for r in rankings[:top_n]])
        
        # Log de cambios
        entradas = nuevos_top - posiciones_actuales
        salidas = posiciones_actuales - nuevos_top
        
        if entradas or salidas:
            trades_log.append({
                'fecha': fecha_siguiente,
                'entradas': list(entradas),
                'salidas': list(salidas),
                'cartera': list(nuevos_top)
            })
        
        posiciones_actuales = nuevos_top
        
        # Calcular retorno del mes siguiente
        retornos_mes = []
        for ticker in posiciones_actuales:
            if ticker in returns_historico:
                ret = returns_historico[ticker]
                if fecha_siguiente in ret.index:
                    r = ret.loc[fecha_siguiente]
                    if pd.notna(r):
                        retornos_mes.append(r)
        
        if retornos_mes:
            ret_portfolio = np.mean(retornos_mes)  # Equiponderado
        else:
            ret_portfolio = 0
        
        # Retorno del benchmark
        ret_bench = benchmark_df['Close'].pct_change().loc[fecha_siguiente]
        if pd.isna(ret_bench):
            ret_bench = 0
        
        # Actualizar valores
        portfolio_value.append(portfolio_value[-1] * (1 + ret_portfolio))
        benchmark_value.append(benchmark_value[-1] * (1 + ret_bench))
    
    # Crear DataFrames de resultados
    if not fechas_validas:
        print("❌ No hay suficientes datos para el backtest")
        return None
    
    resultados = pd.DataFrame({
        'Fecha': fechas_validas,
        'Portfolio': portfolio_value[1:len(fechas_validas)+1],
        'Benchmark': benchmark_value[1:len(fechas_validas)+1]
    }).set_index('Fecha')
    
    # Calcular métricas
    metricas = calcular_metricas(resultados, trades_log, top_n)
    
    return metricas


def calcular_metricas(resultados, trades_log, top_n):
    """Calcula CAGR, Max Drawdown y Sharpe Ratio."""
    
    # Años totales
    años = (resultados.index[-1] - resultados.index[0]).days / 365.25
    
    # === PORTFOLIO ===
    valor_inicial_p = resultados['Portfolio'].iloc[0]
    valor_final_p = resultados['Portfolio'].iloc[-1]
    
    # CAGR
    cagr_p = ((valor_final_p / valor_inicial_p) ** (1 / años) - 1) * 100
    
    # Max Drawdown
    rolling_max_p = resultados['Portfolio'].cummax()
    drawdown_p = (resultados['Portfolio'] - rolling_max_p) / rolling_max_p
    max_dd_p = drawdown_p.min() * 100
    
    # Sharpe Ratio (asumiendo rf = 0 para simplificar)
    returns_p = resultados['Portfolio'].pct_change().dropna()
    sharpe_p = (returns_p.mean() / returns_p.std()) * np.sqrt(12)  # Anualizado
    
    # === BENCHMARK ===
    valor_inicial_b = resultados['Benchmark'].iloc[0]
    valor_final_b = resultados['Benchmark'].iloc[-1]
    
    cagr_b = ((valor_final_b / valor_inicial_b) ** (1 / años) - 1) * 100
    
    rolling_max_b = resultados['Benchmark'].cummax()
    drawdown_b = (resultados['Benchmark'] - rolling_max_b) / rolling_max_b
    max_dd_b = drawdown_b.min() * 100
    
    returns_b = resultados['Benchmark'].pct_change().dropna()
    sharpe_b = (returns_b.mean() / returns_b.std()) * np.sqrt(12)
    
    # Imprimir resultados
    print(f"\n{'='*60}")
    print(f"📊 RESULTADOS BACKTEST TOP {top_n}")
    print(f"{'='*60}")
    print(f"📅 Período: {resultados.index[0].strftime('%Y-%m')} a {resultados.index[-1].strftime('%Y-%m')}")
    print(f"⏱️  Duración: {años:.1f} años")
    print(f"🔄 Trades totales: {len(trades_log)}")
    print()
    
    print(f"┌{'─'*28}┬{'─'*14}┬{'─'*14}┐")
    print(f"│ {'Métrica':<26} │ {'Estrategia':^12} │ {'SPY (B&H)':^12} │")
    print(f"├{'─'*28}┼{'─'*14}┼{'─'*14}┤")
    print(f"│ {'Valor Final ($100 ini)':<26} │ {valor_final_p:>11.2f}$ │ {valor_final_b:>11.2f}$ │")
    print(f"│ {'CAGR':<26} │ {cagr_p:>+11.2f}% │ {cagr_b:>+11.2f}% │")
    print(f"│ {'Max Drawdown':<26} │ {max_dd_p:>11.2f}% │ {max_dd_b:>11.2f}% │")
    print(f"│ {'Sharpe Ratio':<26} │ {sharpe_p:>12.2f} │ {sharpe_b:>12.2f} │")
    print(f"└{'─'*28}┴{'─'*14}┴{'─'*14}┘")
    
    # Comparación
    print()
    if cagr_p > cagr_b:
        print(f"✅ Estrategia SUPERA al benchmark en {cagr_p - cagr_b:.2f}% anual")
    else:
        print(f"❌ Estrategia INFERIOR al benchmark en {cagr_b - cagr_p:.2f}% anual")
    
    if max_dd_p > max_dd_b:
        print(f"✅ Menor drawdown que el benchmark ({abs(max_dd_p):.2f}% vs {abs(max_dd_b):.2f}%)")
    else:
        print(f"⚠️ Mayor drawdown que el benchmark ({abs(max_dd_p):.2f}% vs {abs(max_dd_b):.2f}%)")
    
    return {
        'top_n': top_n,
        'años': años,
        'portfolio': {
            'valor_final': valor_final_p,
            'cagr': cagr_p,
            'max_dd': max_dd_p,
            'sharpe': sharpe_p
        },
        'benchmark': {
            'valor_final': valor_final_b,
            'cagr': cagr_b,
            'max_dd': max_dd_b,
            'sharpe': sharpe_b
        },
        'trades': len(trades_log),
        'resultados_df': resultados
    }


def backtest_completo():
    """Ejecuta backtest para TOP 2 y TOP 3."""
    print("\n" + "="*70)
    print("🚀 BACKTEST ROTACIONAL - INERCIA ALCISTA")
    print("="*70)
    
    resultados = {}
    
    # Backtest TOP 2
    res_top2 = ejecutar_backtest(top_n=2, start_date="2000-01-01")
    if res_top2:
        resultados['top2'] = res_top2
    
    # Backtest TOP 3
    res_top3 = ejecutar_backtest(top_n=3, start_date="2000-01-01")
    if res_top3:
        resultados['top3'] = res_top3
    
    # Resumen comparativo
    if 'top2' in resultados and 'top3' in resultados:
        print(f"\n{'='*70}")
        print("📊 RESUMEN COMPARATIVO")
        print(f"{'='*70}")
        print()
        print(f"┌{'─'*20}┬{'─'*14}┬{'─'*14}┬{'─'*14}┐")
        print(f"│ {'Estrategia':<18} │ {'CAGR':^12} │ {'Max DD':^12} │ {'Sharpe':^12} │")
        print(f"├{'─'*20}┼{'─'*14}┼{'─'*14}┼{'─'*14}┤")
        print(f"│ {'TOP 2':<18} │ {resultados['top2']['portfolio']['cagr']:>+11.2f}% │ {resultados['top2']['portfolio']['max_dd']:>11.2f}% │ {resultados['top2']['portfolio']['sharpe']:>12.2f} │")
        print(f"│ {'TOP 3':<18} │ {resultados['top3']['portfolio']['cagr']:>+11.2f}% │ {resultados['top3']['portfolio']['max_dd']:>11.2f}% │ {resultados['top3']['portfolio']['sharpe']:>12.2f} │")
        print(f"│ {'SPY (Buy & Hold)':<18} │ {resultados['top2']['benchmark']['cagr']:>+11.2f}% │ {resultados['top2']['benchmark']['max_dd']:>11.2f}% │ {resultados['top2']['benchmark']['sharpe']:>12.2f} │")
        print(f"└{'─'*20}┴{'─'*14}┴{'─'*14}┴{'─'*14}┘")
    
    return resultados


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "backtest":
        # Ejecutar backtest
        backtest_completo()
    else:
        # Cálculo normal
        print("🔄 Calculando Inercia Alcista...\n")
        resultados = calcular_inercia_mensual()
        print("\n" + "=" * 50)
        print(formato_mensaje(resultados))
        print("\n💡 Para ejecutar backtest: python inercia.py backtest")
