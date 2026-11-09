"""
live_ccxt_paper.py - Ejecutor de Paper Trading con Datos Reales de Mercado en Vivo (CCXT)
Se conecta a los libros de órdenes y velas en tiempo real de Binance / Bybit / Kraken sin necesidad de API keys.
Permite evaluar cada tick de mercado en vivo usando The Reflex y la Capa de Riesgo Determinista.
"""

from __future__ import annotations
import time
import sys
import ccxt
from core.types import Candle, OrderBookSnapshot
from simulation.paper_engine import PaperTradingHarness

def run_live_paper_trading(
    symbol: str = "BTC/USDT",
    exchange_id: str = "binance",
    max_ticks: int = 25,
    interval_sec: float = 2.0
):
    print("=" * 90)
    print(f"  PAPER TRADING EN TIEMPO REAL (DATOS PÚBLICOS EN VIVO): {exchange_id.upper()} - {symbol}")
    print("=" * 90)

    # Inicializar exchange con fallback
    exchange = None
    exchanges_to_try = [exchange_id, "bybit", "kraken", "okx"]
    for ex_name in exchanges_to_try:
        try:
            ex_cls = getattr(ccxt, ex_name)
            candidate = ex_cls({"enableRateLimit": True, "timeout": 10000})
            candidate.load_markets()
            exchange = candidate
            exchange_id = ex_name
            print(f"[CONEXIÓN EXITOSA]: Conectado al API público de {exchange_id.upper()}")
            break
        except Exception as e:
            continue

    if exchange is None:
        print("[ERROR]: No se pudo conectar a los servidores públicos de los exchanges.")
        print("[NOTA]: Verifica que tu terminal cuente con acceso a internet hacia api.binance.com / bybit.com.")
        return

    harness = PaperTradingHarness(
        symbol=symbol,
        initial_balance=100_000.0,
        taker_fee_bps=4.0,  # 0.04% comisión de taker
        slippage_bps=2.0    # 0.02% deslizamiento
    )

    print(f"[DESCARGA]: Obteniendo histórico de las últimas 30 velas (1m) de {symbol}...")
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1m", limit=30)
    except Exception as e:
        print(f"[ERROR]: Fallo al obtener velas iniciales: {e}")
        return

    candles = [
        Candle(
            timestamp=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5])
        )
        for row in ohlcv
    ]
    precio_actual = candles[-1].close
    print(f"[MERCADO REAL]: {len(candles)} velas cargadas. Precio spot actual: ${precio_actual:,.2f}")
    print("\nIniciando evaluación continua de ticks reales (Sub-100ms)...")
    print("-" * 90)
    print(f"{'HORA':<10} | {'PRECIO SPOT':<13} | {'SPREAD':<9} | {'REFLEJO':<16} | {'CONF':<6} | {'COMPUERTA':<10} | {'PATRIMONIO':<12}")
    print("-" * 90)

    for tick_num in range(1, max_ticks + 1):
        try:
            # Obtener profundidad L2 del libro de órdenes
            ob = exchange.fetch_order_book(symbol, limit=5)
            book = OrderBookSnapshot(
                timestamp=ob["timestamp"] or int(time.time() * 1000),
                bids=[(float(p), float(s)) for p, s in ob["bids"][:5]],
                asks=[(float(p), float(s)) for p, s in ob["asks"][:5]]
            )

            mid = (book.bids[0][0] + book.asks[0][0]) / 2.0
            last_c = candles[-1]
            candles[-1] = Candle(
                timestamp=last_c.timestamp,
                open=last_c.open,
                high=max(last_c.high, mid),
                low=min(last_c.low, mid),
                close=mid,
                volume=last_c.volume + 0.05
            )

            res = harness.process_tick(book, candles)
            dec = res["decision"]
            spread_bps = ((book.asks[0][0] - book.bids[0][0]) / mid) * 10000.0

            dir_es = "LARGO" if dec.direction.value == "long" else ("CORTO" if dec.direction.value == "short" else "NEUTRAL")
            dir_str = f"{dir_es} (Q{dec.setup_quality})"
            gate_status = "SUPERADA" if res["gate_passed"] else "DENEGADA"
            ts_str = time.strftime('%H:%M:%S', time.localtime())

            print(f"{ts_str:<10} | ${mid:<12,.2f} | {spread_bps:<6.2f} bp | {dir_str:<16} | {dec.confidence:<6.2f} | {gate_status:<10} | ${res['equity']:<11,.2f}")

            if res["order"]:
                ord_info = res["order"]
                lado = "COMPRA" if ord_info['side'] == "buy" else "VENTA"
                print(f"  >>> [ORDEN EJECUTADA]: {lado} {ord_info['qty']:.4f} BTC @ ${ord_info['fill_price']:,.2f} | Comisión: ${ord_info['fee']:.2f}")

            time.sleep(interval_sec)

        except KeyboardInterrupt:
            print("\n[INFO]: Sesión detenida por el usuario.")
            break
        except Exception as e:
            print(f"[ERROR]: {e}")
            break

    # Auditoría final
    print("\n" + "=" * 90)
    print("                AUDITORÍA DE LA SESIÓN EN VIVO & PUNTAJE DE BRIER")
    print("=" * 90)
    report = harness.brain_engine.nightly_post_mortem()
    for k, v in report.items():
        k_clean = k.replace('_', ' ').capitalize()
        print(f"  * {k_clean:<34}: {v}")
    print("=" * 90)

if __name__ == "__main__":
    ex = "binance"
    ticks = 25
    if len(sys.argv) > 1:
        ex = sys.argv[1]
    run_live_paper_trading(exchange_id=ex, max_ticks=ticks)
