import yfinance as yf
import pandas as pd

ETFS = ["XLK", "XLV", "XLF", "XLY", "XLC", "XLI", "XLP", "XLE", "XLU", "XLRE", "XLB", "IEF"]

# Períodos para ROC (en días)
ROC_FAST = 63    # ~3 meses
ROC_SLOW = 126   # ~6 meses
ATR_PERIOD = 14

def calcular_inercia_mensual():
    """
    Calcula el índice de inercia para cada ETF.
    Usa datos diarios de 1 año para tener suficiente historia.
    """
    resultados = []
    
    for ticker in ETFS:
        try:
            # Descargar 1 año de datos diarios
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            
            if df.empty:
                print(f"⚠️ {ticker}: Sin datos")
                continue
                
            if len(df) < ROC_SLOW + 10:
                print(f"⚠️ {ticker}: Datos insuficientes ({len(df)} filas)")
                continue
            
            # Obtener serie de cierre (manejar MultiIndex si existe)
            if isinstance(df.columns, pd.MultiIndex):
                close = df['Close'][ticker]
            else:
                close = df['Close']
            
            # Factor 1: Momentum (ROC ponderado)
            roc_fast = close.pct_change(ROC_FAST).iloc[-1]  # ROC 3 meses
            roc_slow = close.pct_change(ROC_SLOW).iloc[-1]  # ROC 6 meses
            factor_momentum = (roc_fast * 0.6) + (roc_slow * 0.4)
            
            # Factor 2: Volatilidad (ATR / SMA)
            high = df['High'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['High']
            low = df['Low'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Low']
            
            tr = pd.concat([
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs()
            ], axis=1).max(axis=1)
            
            atr = tr.rolling(ATR_PERIOD).mean().iloc[-1]
            sma = close.rolling(ATR_PERIOD).mean().iloc[-1]
            factor_volatilidad = atr / sma if sma != 0 else 0
            
            # Índice de Inercia = Momentum / Volatilidad
            if factor_volatilidad > 0:
                inercia = factor_momentum / factor_volatilidad
            else:
                inercia = 0
            
            resultados.append({
                'ticker': ticker,
                'inercia': round(inercia, 4),
                'momentum': round(factor_momentum * 100, 2),
                'volatilidad': round(factor_volatilidad * 100, 2),
                'precio': round(close.iloc[-1], 2)
            })
            
            print(f"✅ {ticker}: Inercia={inercia:.4f}")
            
        except Exception as e:
            print(f"❌ Error {ticker}: {e}")
    
    # Ordenar por inercia descendente
    resultados = sorted(resultados, key=lambda x: x['inercia'], reverse=True)
    
    return resultados


def formato_mensaje(resultados):
    """Formatea los resultados para Telegram."""
    if not resultados:
        return "⚠️ No se pudieron calcular resultados"
    
    lineas = ["📊 *INERCIA MENSUAL - SECTORES*", ""]
    
    for i, r in enumerate(resultados, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▪️"
        lineas.append(
            f"{emoji} *{r['ticker']}*: {r['inercia']:.2f} "
            f"(Mom: {r['momentum']}% | Vol: {r['volatilidad']}%)"
        )
    
    lineas.append("")
    lineas.append(f"_Top 3 recomendados: {', '.join(r['ticker'] for r in resultados[:3])}_")
    
    return "\n".join(lineas)


if __name__ == "__main__":
    print("🔄 Calculando inercia mensual...\n")
    resultados = calcular_inercia_mensual()
    print("\n" + "=" * 50)
    print(formato_mensaje(resultados))
