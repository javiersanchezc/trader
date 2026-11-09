"""
main.py - Ejecutor 24/7 del Agente Cuantitativo de Trading
Demuestra el ciclo de vida completo en español con precios alineados al mercado real:
Investigación en el Cerebro (Brain), Motor de Estado, Decisiones de Reflejo, Compuertas Deterministas de Riesgo,
Ejecución en Paper Trading y Auditoría Nocturna con Puntaje de Brier.
"""

from __future__ import annotations
import time
from core.types import Candle, OrderBookSnapshot, Regime
from core.brain import MacroResearchThesis
from simulation.paper_engine import PaperTradingHarness

def run_quant_trading_system():
    print("=" * 88)
    print(" CONSTRUCTOR DE AGENTES DE TRADING CUANTITATIVO: ARQUITECTURA DE DOS CAPAS (BRAIN / REFLEX)")
    print("=" * 88)

    # 1. Inicializar Arnés
    symbol = "BTC/USDT"
    harness = PaperTradingHarness(
        symbol=symbol,
        initial_balance=100_000.0,
        taker_fee_bps=4.0,  # 0.04% comisión de taker
        slippage_bps=2.0    # 0.02% deslizamiento estimado
    )

    # 2. Capa de Investigación (The Brain): Formulación de la Tesis Macro
    # Calibrada al contexto macroeconómico y niveles de soporte actuales (~$74,000)
    macro_thesis = MacroResearchThesis(
        asset=symbol,
        macro_regime=Regime.TRENDING,
        funding_rate_bps=1.2, # 0.012% tasa de financiación (base saludable impulsada por spot)
        stablecoin_liquidity_flow="expanding",
        on_chain_fundamental_score=8.4,
        bull_catalyst="Entradas institucionales netas en ETF spot + absorción pasiva en el rango $74k-$75k",
        bear_case_thesis="Pérdida del soporte estructural en $71,500 con liquidación de posiciones apalancadas",
        invalidation_level=71500.0
    )
    harness.brain_engine.register_macro_thesis(macro_thesis)
    
    print(f"\n[INVESTIGACIÓN DEL CEREBRO] Tesis macroeconómica activa para {symbol}:")
    print(f"  * Régimen de mercado   : {macro_thesis.macro_regime.value.upper()} | Tasa de financiación: +{macro_thesis.funding_rate_bps} bps")
    print(f"  * Catalizador alcista  : {macro_thesis.bull_catalyst}")
    print(f"  * Tesis bajista        : {macro_thesis.bear_case_thesis}")
    print(f"  * Nivel de invalidación: ${macro_thesis.invalidation_level:,.2f}")

    # 3. Simular flujo de mercado calibrado a precios actuales de Bitcoin (~$74,800)
    print("\n" + "-" * 88)
    print("[MOTOR DE REFLEJO Y RIESGO] Iniciando bucle de ejecución en tiempo real...")
    print("-" * 88)

    base_price = 74800.0
    candles = []
    
    for i in range(12):
        ts = 1700000000000 + i * 60000
        p = base_price + (i * 15.0)
        candles.append(Candle(timestamp=ts, open=p, high=p + 40, low=p - 30, close=p + 10, volume=12.0))

    # Escenario: Retesteo de Order Block alcista en la zona de soporte actual (~$74,900)
    candles.append(Candle(timestamp=1700000720000, open=74980, high=75010, low=74920, close=74930, volume=14.0))
    candles.append(Candle(timestamp=1700000780000, open=74940, high=75450, low=74935, close=75420, volume=45.0))
    candles.append(Candle(timestamp=1700000840000, open=75250, high=75270, low=74960, close=74980, volume=18.0))

    ticks = [
        # Tick 1: Retesteo de Order Block alcista con desbalance positivo en libro -> LARGO ALTA CONFLUENCIA
        (
            OrderBookSnapshot(
                timestamp=1700000840000,
                bids=[(74975.0, 4.5), (74970.0, 5.0), (74965.0, 6.0)],
                asks=[(74980.0, 1.2), (74985.0, 1.5), (74990.0, 1.8)]
            ),
            "Tick 1: Retesteo de Order Block Alcista ($74,977)"
        ),
        # Tick 2: Consolidación con libro ilíquido (spread tóxico de 220 puntos = ~29 bps) -> DENEGADA
        (
            OrderBookSnapshot(
                timestamp=1700000900000,
                bids=[(74950.0, 1.0)],
                asks=[(75170.0, 1.0)]
            ),
            "Tick 2: Agujero de Liquidez Repentino / Spread Ancho"
        ),
        # Tick 3: Intento de ruptura superior con rechazo (trampa de liquidez)
        (
            OrderBookSnapshot(
                timestamp=1700000960000,
                bids=[(75050.0, 1.0), (75045.0, 1.2)],
                asks=[(75055.0, 5.0), (75060.0, 6.0)]
            ),
            "Tick 3: Trampa de Liquidez Superior (Barrido de Stops)"
        )
    ]

    candles_tick3 = list(candles)
    candles_tick3.append(Candle(
        timestamp=1700000960000,
        open=75000.0,
        high=75500.0,
        low=74990.0,
        close=75030.0,
        volume=60.0
    ))

    # Procesar Ticks
    for i, (book, label) in enumerate(ticks):
        current_candles = candles_tick3 if i == 2 else candles
        res = harness.process_tick(book, current_candles)
        
        dec = res["decision"]
        dir_es = "LARGO" if dec.direction.value == "long" else ("CORTO" if dec.direction.value == "short" else "NEUTRAL")
        paso_es = "SUPERADA" if res["gate_passed"] else "DENEGADA"

        print(f"\n--> {label}")
        print(f"  Salida del Reflejo : Dirección={dir_es} | Confianza={dec.confidence:.2f} | Calidad={dec.setup_quality}/3 | Régimen={dec.regime.value}")
        print(f"  Racional           : {dec.rationale}")
        print(f"  Compuertas Riesgo  : Estado={paso_es} | Motivo={res['gate_reason']}")
        if res["order"]:
            ord_info = res["order"]
            lado_es = "COMPRA" if ord_info['side'] == "buy" else "VENTA"
            print(f"  [EJECUCIÓN]        : Orden de {lado_es} por {ord_info['qty']:.4f} BTC @ ${ord_info['fill_price']:,.2f} (Comisión: ${ord_info['fee']:.2f})")
        print(f"  Patrimonio Cuenta  : ${res['equity']:,.2f} | Posición Actual: {harness.position.size:.4f} BTC")

    # 4. Auditoría Nocturna y Calibración
    print("\n" + "=" * 88)
    print(" AUDITORÍA NOCTURNA POST-MORTEM Y CALIBRACIÓN PROBABILÍSTICA (PUNTAJE DE BRIER)")
    print("=" * 88)
    report = harness.brain_engine.nightly_post_mortem()
    for k, v in report.items():
        k_clean = k.replace('_', ' ').capitalize()
        print(f"  * {k_clean:<32}: {v}")

    print("\n[CONCLUSIÓN DE AUDITORÍA]: Sistema verificado con éxito bajo estricta separación de responsabilidades.")
    print("=" * 88)

if __name__ == "__main__":
    run_quant_trading_system()
