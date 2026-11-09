"""
run_simulation.py - Arnés de Simulación Interactiva y Replay de Mercado
Permite probar el sistema completo con diferentes escenarios de mercado,
auditar las decisiones del Reflejo, comprobar las compuertas de riesgo
y ver la calibración estadística final en español.
"""

from __future__ import annotations
import sys
import time
import random
from core.types import Candle, OrderBookSnapshot, Regime
from core.brain import MacroResearchThesis
from simulation.paper_engine import PaperTradingHarness

def generate_market_scenario(num_ticks: int = 15):
    """
    Genera una secuencia dinámica de ticks y velas con eventos de mercado:
    - Retesteo de Order Block alcista
    - Expansión de precio en beneficio
    - Libro ilíquido / Spread tóxico (> 25 bps)
    - Barrido de liquidez superior (Trampa de Toros / Fake Breakout)
    """
    base_price = 89000.0
    current_price = base_price
    candles = []
    
    # 1. Semilla inicial de velas causales
    for i in range(15):
        ts = 1700000000000 + i * 60000
        p = base_price + (i * 15.0) + random.uniform(-10, 10)
        c = Candle(
            timestamp=ts,
            open=p,
            high=p + 35,
            low=p - 30,
            close=p + 10,
            volume=10.0 + random.uniform(0, 5)
        )
        candles.append(c)

    # 2. Generar Order Block alcista previo
    ts_ob = candles[-1].timestamp + 60000
    ob_low = current_price - 50.0
    ob_high = current_price + 30.0
    candles.append(Candle(ts_ob, current_price + 20, ob_high, ob_low, current_price - 30, volume=12.0))
    ts_exp = ts_ob + 60000
    candles.append(Candle(ts_exp, current_price - 20, current_price + 450, current_price - 25, current_price + 420, volume=45.0))
    current_price += 420

    events = []
    
    for step in range(num_ticks):
        step_ts = ts_exp + (step + 1) * 60000

        # Ticks 0 a 3: Retesteo controlado de Order Block [ob_low, ob_high]
        if step < 4:
            current_price = ob_high - (step * 8.0)
            c = Candle(step_ts, current_price + 20, current_price + 30, current_price - 10, current_price, volume=15.0)
            candles.append(c)
            book = OrderBookSnapshot(
                timestamp=step_ts,
                bids=[(current_price - 1.0, 5.0), (current_price - 3.0, 4.0), (current_price - 5.0, 6.0)],
                asks=[(current_price + 1.0, 1.2), (current_price + 3.0, 1.0), (current_price + 5.0, 1.5)]
            )
            desc = f"Tick {step+1:02d}: Retesteo de Order Block Alcista"

        # Ticks 4 a 7: Rebote y expansión alcista
        elif step < 8:
            current_price += random.uniform(80, 140)
            c = Candle(step_ts, current_price - 60, current_price + 40, current_price - 70, current_price, volume=22.0)
            candles.append(c)
            book = OrderBookSnapshot(
                timestamp=step_ts,
                bids=[(current_price - 2.0, 2.5)],
                asks=[(current_price + 2.0, 2.0)]
            )
            desc = f"Tick {step+1:02d}: Expansión alcista en beneficio"

        # Ticks 8 a 10: Libro ilíquido / Spread tóxico (> 25 bps)
        elif step < 11:
            current_price += 20.0
            c = Candle(step_ts, current_price - 10, current_price + 15, current_price - 10, current_price, volume=8.0)
            candles.append(c)
            book = OrderBookSnapshot(
                timestamp=step_ts,
                bids=[(current_price - 120.0, 1.0)],
                asks=[(current_price + 130.0, 1.0)]
            )
            desc = f"Tick {step+1:02d}: Libro ilíquido / Spread tóxico"

        # Ticks 11+: Barrido de liquidez superior (Trampa de Toros)
        else:
            swing_high_prior = max(c.high for c in candles[-10:-1])
            c = Candle(step_ts, swing_high_prior - 10, swing_high_prior + 90, swing_high_prior - 20, swing_high_prior - 5, volume=55.0)
            candles.append(c)
            current_price = c.close
            book = OrderBookSnapshot(
                timestamp=step_ts,
                bids=[(current_price - 2.0, 1.0), (current_price - 4.0, 1.0)],
                asks=[(current_price + 2.0, 6.0), (current_price + 4.0, 8.0)]
            )
            desc = f"Tick {step+1:02d}: Barrido de liquidez (Trampa)"

        events.append((book, list(candles), desc))

    return events

def run_interactive_simulation(ticks_count: int = 15):
    print("=" * 96)
    print("      SIMULADOR INSTITUCIONAL 24/7 - PAPER TRADING REPLAY & COMPUERTAS DE RIESGO")
    print("=" * 96)

    symbol = "BTC/USDT"
    harness = PaperTradingHarness(
        symbol=symbol,
        initial_balance=100_000.0,
        taker_fee_bps=4.0,
        slippage_bps=2.0
    )

    thesis = MacroResearchThesis(
        asset=symbol,
        macro_regime=Regime.TRENDING,
        funding_rate_bps=1.5,
        stablecoin_liquidity_flow="expanding",
        on_chain_fundamental_score=8.5,
        bull_catalyst="Crecimiento neto de liquidez en stablecoins + acumulación institucional spot",
        bear_case_thesis="Pérdida del soporte semanal en $85,000 por shock de rendimiento de bonos",
        invalidation_level=85000.0
    )
    harness.brain_engine.register_macro_thesis(thesis)

    print(f"\n[EL CEREBRO - Tesis Activa]:")
    print(f"  * Activo: {symbol} | Régimen: {thesis.macro_regime.value.upper()} | Financiación: +{thesis.funding_rate_bps} bps")
    print(f"  * Catalizador: {thesis.bull_catalyst}")
    print(f"  * Nivel de invalidación: ${thesis.invalidation_level:,.2f}")
    print("-" * 96)

    scenario = generate_market_scenario(ticks_count)
    
    print(f"{'PASO':<30} | {'REFLEJO':<16} | {'CONF':<6} | {'COMPUERTA':<10} | {'ACCIÓN':<20} | {'PATRIMONIO':<12}")
    print("-" * 96)

    for book, candles, desc in scenario:
        res = harness.process_tick(book, candles)
        dec = res["decision"]
        action_str = "ESPERA (HOLD)"
        
        if res["order"]:
            ord_info = res["order"]
            lado = "COMPRA" if ord_info['side'] == "buy" else "VENTA"
            action_str = f"{lado} {ord_info['qty']:.3f} BTC"
        elif not res["gate_passed"]:
            short_reason = res["gate_reason"]
            if ":" in short_reason:
                short_reason = short_reason.split(":")[0]
            action_str = f"BLOQUEO ({short_reason[:12]})"

        gate_status = "SUPERADA" if res["gate_passed"] else "DENEGADA"
        dir_es = "LARGO" if dec.direction.value == "long" else ("CORTO" if dec.direction.value == "short" else "NEUTRAL")
        dir_str = f"{dir_es} (Q{dec.setup_quality})"

        print(f"{desc:<30} | {dir_str:<16} | {dec.confidence:<6.2f} | {gate_status:<10} | {action_str:<20} | ${res['equity']:<11,.2f}")

    print("\n" + "=" * 96)
    print("                AUDITORÍA NOCTURNA POST-MORTEM & PUNTAJE DE BRIER")
    print("=" * 96)
    report = harness.brain_engine.nightly_post_mortem()
    for k, v in report.items():
        k_clean = k.replace('_', ' ').capitalize()
        print(f"  * {k_clean:<34}: {v}")

    print("=" * 96)
    print("\n[VERIFICACIÓN COMPLETADA CON ÉXITO EN ESPAÑOL]\n")

if __name__ == "__main__":
    count = 15
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            count = 15
    run_interactive_simulation(count)
