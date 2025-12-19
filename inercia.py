import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

ETFS = ["XLK", "XLV", "XLF", "XLY", "XLC", "XLI", "XLP", "XLE", "XLU", "XLRE", "XLB", "IEF"]


def calcular_atr(high, low, close, period=14):
    """Calcula el Average True Range estándar."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def calcular_inercia_mensual():
    """
    Calcula el índice de Inercia Alcista para cada ETF.
    Replica exactamente el indicador de ProRealTime en escala mensual.
    
    Fórmula PRT:
    Ind1 = (CLOSE-CLOSE[8])/CLOSE[8]       # ROC 8 meses
    Ind2 = (CLOSE-CLOSE[10])/CLOSE[10]     # ROC 10 meses
    Ind3 = AverageTrueRange[14](close)     # ATR 14 meses
    Ind4 = Average[14](close)              # SMA 14 meses
    Ind5 = Ind3/Ind4
    F = (Ind1*0.4 + Ind2*0.2) / (Ind5*0.4) * 100
    """
    resultados = []
    
    for ticker in ETFS:
        try:
            # Descargar 3 años de datos con auto_adjust=True
            df = yf.download(
                ticker, 
                period="3y", 
                interval="1d", 
                progress=False,
                auto_adjust=True  # ← Precios ajustados por splits/dividendos
            )
            
            if df.empty:
                print(f"⚠️ {ticker}: Sin datos")
                continue
            
            # Manejar MultiIndex de yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(1, axis=1)
            
            # === RESAMPLEAR A MENSUAL ===
            df_monthly = df.resample('ME').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            # === ELIMINAR MES ACTUAL SI NO ESTÁ CERRADO ===
            hoy = datetime.now()
            ultimo_mes = df_monthly.index[-1]
            
            # Si el último mes es el mes actual, eliminarlo (vela no cerrada)
            if ultimo_mes.month == hoy.month and ultimo_mes.year == hoy.year:
                df_monthly = df_monthly.iloc[:-1]
                print(f"📅 {ticker}: Usando datos hasta {df_monthly.index[-1].strftime('%Y-%m')} (mes actual excluido)")
            
            # Necesitamos al menos 15 meses (14 para ATR + 1 actual)
            if len(df_monthly) < 15:
                print(f"⚠️ {ticker}: Datos mensuales insuficientes ({len(df_monthly)} meses)")
                continue
            
            close = df_monthly['Close']
            high = df_monthly['High']
            low = df_monthly['Low']
            
            # === CÁLCULOS SEGÚN PROREALTIME ===
            
            # Ind1 = (CLOSE - CLOSE[8]) / CLOSE[8]  → ROC 8 meses
            ind1 = (close - close.shift(8)) / close.shift(8)
            
            # Ind2 = (CLOSE - CLOSE[10]) / CLOSE[10]  → ROC 10 meses
            ind2 = (close - close.shift(10)) / close.shift(10)
            
            # Ind3 = AverageTrueRange[14](close)  → ATR 14 meses
            ind3 = calcular_atr(high, low, close, period=14)
            
            # Ind4 = Average[14](close)  → SMA 14 meses
            ind4 = close.rolling(window=14).mean()
            
            # Ind5 = Ind3 / Ind4  → Volatilidad relativa
            ind5 = ind3 / ind4
            
            # F = (Ind1*0.4 + Ind2*0.2) / (Ind5*0.4) * 100
            fuerza_alcista = ((ind1 * 0.4 + ind2 * 0.2) / (ind5 * 0.4)) * 100
            
            # Obtener el último valor (último mes cerrado)
            fa_actual = fuerza_alcista.iloc[-1]
            
            if pd.isna(fa_actual):
                print(f"⚠️ {ticker}: Valor NaN")
                continue
            
            resultados.append({
                'ticker': ticker,
                'inercia': round(float(fa_actual), 2),
                'roc8': round(float(ind1.iloc[-1] * 100), 2),
                'roc10': round(float(ind2.iloc[-1] * 100), 2),
                'volatilidad': round(float(ind5.iloc[-1] * 100), 4),
                'precio': round(float(close.iloc[-1]), 2),
                'mes': df_monthly.index[-1].strftime('%Y-%m')
            })
            
            print(f"✅ {ticker}: Fuerza Alcista = {fa_actual:.2f}")
            
        except Exception as e:
            print(f"❌ Error {ticker}: {e}")
    
    # Ordenar por inercia descendente
    return sorted(resultados, key=lambda x: x['inercia'], reverse=True)


def formato_mensaje(resultados):
    """Formatea los resultados para Telegram."""
    if not resultados:
        return "⚠️ No se pudieron calcular resultados"
    
    fecha = datetime.now().strftime("%d/%m/%Y")
    mes_datos = resultados[0]['mes'] if resultados else "N/A"
    
    lineas = [
        "📊 *INERCIA ALCISTA - SECTORES USA*",
        f"📅 Calculado: {fecha}",
        f"📆 Datos hasta: {mes_datos}",
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
        lineas.append(
            f"{emoji} *{r['ticker']}*: {signo}{r['inercia']:.2f}"
        )
    
    # Separador y detalles de los top 3
    lineas.append("")
    lineas.append("📈 *Detalles Top 3:*")
    for r in resultados[:3]:
        lineas.append(
            f"  • {r['ticker']}: ROC8={r['roc8']}% | ROC10={r['roc10']}%"
        )
    
    lineas.append("")
    lineas.append(f"_Recomendados: {', '.join(r['ticker'] for r in resultados[:3])}_")
    
    return "\n".join(lineas)


if __name__ == "__main__":
    print("🔄 Calculando Inercia Alcista (mensual)...\n")
    resultados = calcular_inercia_mensual()
    print("\n" + "=" * 50)
    print(formato_mensaje(resultados))
