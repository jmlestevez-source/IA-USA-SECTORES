import yfinance as yf, pandas as pd

ETFS = ["XLK","XLV","XLF","XLY","XLC","XLI","XLP","XLE","XLU","XLRE","XLB","IEF"]
N, M = 8, 10

def calcular_inercia_mensual():
    res = []
    for t in ETFS:
        try:
            d = yf.download(t, period="6mo", interval="1mo", progress=False)
            if len(d) < 20: continue
            c = d['Close']
            roc3 = c.pct_change(N).iloc[-1] * 0.4
            roc4 = c.pct_change(M).iloc[-1] * 0.2
            f1 = roc3 + roc4
            atr14 = (c - c.shift(1)).abs().rolling(14).mean().iloc[-1]
            sma14 = c.rolling(14).mean().iloc[-1]
            f2 = (atr14 / sma14) * 0.4
            ia   = f1 / f2 if f2 else 0
            res.append((t, ia))
        except Exception as e:
            print(f"Error {t}: {e}")
    return sorted(res, key=lambda x: x[1], reverse=True)
