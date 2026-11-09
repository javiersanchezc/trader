# Quant Trading Agent Builder: Institutional Two-Layer Autonomous System

Sistema institucional de trading cuantitativo y algorítmico 24/7 en criptoactivos con desacoplamiento estricto de dos capas (**The Brain** / **The Reflex**) y compuertas deterministas de riesgo.

---

## 1. Arquitectura de Dos Capas

```
┌────────────────────────────────────────────────────────────────────────┐
│                   THE BRAIN (Cerebro Asíncrono)                         │
│  - Diagnóstico Macro & Régimen (BTC/ETH, Funding Rates, Liquidez)     │
│  - Formulación de Tesis, Bear Case & Puntos de Invalidación            │
│  - Post-Mortem Nocturno y Calibración Probabilística (Brier Score)    │
│  - Recalibración Dinámica de Umbrales                                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Directrices & Políticas de Riesgo
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   THE REFLEX (Motor Sub-100ms)                         │
│  - Consumo de Estado Numérico Compacto (< 400 tokens)                 │
│  - Evaluación de Microestructura (Order Book Imbalance, Spreads)       │
│  - Detección Cuantitativa de SMC (Order Blocks, Sweeps, Breakouts)     │
│  - Emisión de Esquema Tipado (Direction, Confidence, Setup Quality)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Juicio Probabilístico (Sin efectos secundarios)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              CAPA DE RIESGO DETERMINISTA (Código Duro)                 │
│  - Compuertas de Ejecución Inmutables:                                 │
│      * Setup Quality >= 2                                              │
│      * Confianza > 0.80                                                │
│      * Risk State == "safe"                                            │
│      * Spread <= 25 bps                                                │
│  - Dimensionamiento de Posición: Quarter-Kelly (1/4 Kelly conservador) │
│  - Circuit Breakers: Drawdown Máximo <= 15%, Pérdida Diaria <= 3%      │
│  - Kill-Switch de Emergencia y Escalado al Brain ante Crisis           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Órdenes Validadas
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   MOTOR DE EJECUCIÓN / PAPER TRADING                   │
│  - Modelado de Slippage Realista & Comisiones de Exchange (Taker/Maker)│
│  - Contabilidad Mark-to-Market & Registro Continuo de Auditoría        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Traducción de Heurísticas Minoristas (SMC) a Microestructura Cuantitativa

| Concepto Visual (Infografía) | Interpretación Minorista / Discrecional | Formulación Matemática Cuantitativa (Código Nativo) |
|---|---|---|
| **Support & Resistance** | Líneas subjetivas trazadas en gráficos | Puntos de pivote causales ($SwingHigh_t, SwingLow_t$) libres de sesgo retrospectivo (*lookahead bias*). |
| **Order Block (OB)** | "Zonas institucionales de compra/venta" | Vela contraria precedente a un impulso volumétrico con ratio de desplazamiento $\ge 1.5\times$ el rango medio y volumen $\ge 1.5\times$, testeada sin invalidación previa del mínimo/máximo. |
| **Fake Breakout / Traps** | "Trampas para engañar traders" | Barrido de liquidez de stops (*Liquidity Sweep*): $High_t > SwingHigh$ pero $Close_t \le SwingHigh$ con mecha superior $\ge 40\%$ del rango y absorción de delta en el libro. |
| **Real Breakout** | "Ruptura que continúa" | $Close_t > SwingHigh$ con cuerpo de vela $\ge 55\%$ del rango total, confirmada por desbalance positivo en el libro de órdenes ($Imbalance > 0.25$). |

---

## 3. Estructura del Código

```
d:\trader\
├── core/
│   ├── types.py            # Enums, MarketState (<400 tokens), DecisionSchema, Position, RiskParams
│   ├── smc_quant.py        # Algoritmos cuantitativos para Order Blocks, Sweeps y Breakouts
│   ├── state_engine.py     # Compilador causal de microestructura (Mid, Spread, Imbalance, Vol)
│   ├── reflex.py           # Evaluador sub-100ms con emisión de probabilidades calibradas
│   ├── risk_layer.py       # Compuertas inmutables, Quarter-Kelly y Kill-switch
│   └── brain.py            # Tesis macro, bear case, invalidación y post-mortem con Brier Score
├── simulation/
│   └── paper_engine.py     # Arnés de paper trading 24/7 con comisiones y slippage
├── tests/
│   ├── test_state_engine.py
│   ├── test_smc_quant.py
│   ├── test_risk_layer.py
│   ├── test_reflex_gates.py
│   ├── test_brain_postmortem.py
│   └── test_paper_engine.py
└── main.py                 # Orquestador del ciclo completo de ejecución
```

---

## 4. Ejecución y Verificación

### Ejecución de Pruebas Unitarias e Integración (TDD)
```powershell
python -m unittest discover -s tests -v
```

### Ejecución del Sistema en Tiempo Real (Paper Trading)
```powershell
python main.py
```
