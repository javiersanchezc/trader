# 📘 MANUAL DE USO — Sistema de Trading Cuantitativo `d:\trader`

> **Para qué sirve:** convertir una alerta (TradingView o tu propio análisis) en un **plan de ejecución cerrado** —3 órdenes límite, Stop Loss, Take Profits y pérdida máxima en dólares— **antes** de entrar, para operar por estrategia y no por susto.

---

## Índice
1. [Requisitos y preparación](#1-requisitos-y-preparación)
2. [Uso diario en 5 pasos (lo esencial)](#2-uso-diario-en-5-pasos-lo-esencial)
3. [El generador de planes: todos los comandos](#3-el-generador-de-planes-todos-los-comandos)
4. [Cómo leer el plan generado](#4-cómo-leer-el-plan-generado)
5. [Cómo poner el plan en el exchange](#5-cómo-poner-el-plan-en-el-exchange)
6. [Gestión durante la operación](#6-gestión-durante-la-operación)
7. [Semáforo de seguridad (cuándo NO operar)](#7-semáforo-de-seguridad-cuándo-no-operar)
8. [Herramientas complementarias](#8-herramientas-complementarias)
9. [Vigilante directo de Binance](#9-vigilante-directo-de-binance-recomendado-sin-tradingview-ni-webhook)
10. [Webhook (alternativa)](#10-recepción-automática-de-alertas-webhook-alternativa)
11. [Arquitectura interna](#11-arquitectura-interna-para-entender-el-sistema)
12. [Pruebas y mantenimiento](#12-pruebas-y-mantenimiento)
13. [Reglas de oro y limitaciones](#13-reglas-de-oro-y-limitaciones-conocidas)
14. [Solución de problemas](#14-solución-de-problemas)

---

## 1. Requisitos y preparación

| Elemento | Valor |
|---|---|
| Python | 3.13 — `C:\Users\javie\AppData\Local\Programs\Python\Python313\python.exe` |
| Librerías | `ccxt`, `pandas`, `fastapi`, `uvicorn`, `ta`, `pydantic` (ya instaladas) |
| Carpeta | `d:\trader` |

Abre PowerShell en la carpeta:
```powershell
cd d:\trader
```

> 💡 Si `python` no se reconoce, usa la ruta completa:
> ```powershell
> & "C:\Users\javie\AppData\Local\Programs\Python\Python313\python.exe" generador_plan_alerta.py ...
> ```
> En este manual se escribe `python` para abreviar.

---

## 2. Uso diario en 5 pasos (lo esencial)

```
ALERTA  ──►  VALIDAR  ──►  GENERAR PLAN  ──►  PONER ÓRDENES  ──►  CERRAR GRÁFICA
```

### Paso 1 — Llega la alerta
Tu indicador en TradingView (Divergencia RSI 4H + CHoCH 5m) dispara una señal de compra, o tú detectas el setup.

### Paso 2 — Valida en el gráfico (30 segundos)
Comprueba 3 cosas:
- ✅ **Precio actual** (ej. `127.35`).
- ✅ **Soporte real / mínimo de la mecha** del impulso (ej. `121.88`). Es el punto que, si se rompe, invalida la idea.
- ✅ **No estás comprando en Premium** (por encima del 50% del rango de 4H) ni en caída libre.

### Paso 3 — Genera el plan
```powershell
python generador_plan_alerta.py MSTR 127.35 500 3 121.88 --max-risk 15
```
| Posición | Significado | Ejemplo |
|---|---|---|
| 1 | Activo | `MSTR`, `BTC`, `ETH`, `SOL`, `XRP`... |
| 2 | Precio de la alerta | `127.35` |
| 3 | Capital de la cuenta (USDT) | `500` |
| 4 | Apalancamiento máximo | `3` |
| 5 | Soporte real del gráfico (opcional, **recomendado**) | `121.88` |
| `--max-risk` | Pérdida máxima permitida en USDT | `15` (por defecto `20`) |

### Paso 4 — Pon las órdenes en el exchange
3 órdenes **Limit Buy** + 1 **Stop Market** + 2 **Take Profit** (ver [sección 5](#5-cómo-poner-el-plan-en-el-exchange)).

### Paso 5 — Cierra la gráfica
El plan ya está decidido. Los retrocesos **llenan tus órdenes**, no son una amenaza. La pérdida máxima ya la aceptaste antes de entrar.

---

## 3. El generador de planes: todos los comandos

Archivo: [`generador_plan_alerta.py`](generador_plan_alerta.py)

### 3.1 Con soporte del gráfico (modo recomendado)
```powershell
python generador_plan_alerta.py MSTR 127.35 500 3 121.88
python generador_plan_alerta.py MSTR 127.35 500 3 --low 121.88      # equivalente
```
Las órdenes se colocan sobre el impulso real `soporte → precio`.

### 3.2 Con tope de pérdida personalizado
```powershell
python generador_plan_alerta.py MSTR 127.35 500 3 121.88 --max-risk 10
python generador_plan_alerta.py BTC 74200 500 3 72900 --max-risk 15
```

### 3.3 Rápido, sin soporte (volatilidad calibrada por activo)
```powershell
python generador_plan_alerta.py BTC 74200 500 3
python generador_plan_alerta.py SOL 185.20 500 3
```
Usa el rango típico del activo (`VOLATILIDAD_PRESETS`):

| Activo | Rango intradía | Motivo |
|---|---|---|
| BTC | 0.90% | El más líquido y pesado |
| ETH | 1.15% | Algo más rápido que BTC |
| SOL | 1.45% | Mechas más profundas |
| MSTR | 1.85% | Alta beta: se mueve ~2× BTC |
| Otros | 1.10% | Valor por defecto |

> ⚠️ Este modo es una aproximación. En días de noticias (FED, apertura de Wall Street) la volatilidad real puede triplicarse. **Siempre que puedas, pasa el soporte real.**

### 3.4 Simular escenarios peligrosos
```powershell
python generador_plan_alerta.py MSTR 127.35 500 3 --crash      # simula caída del 9.5% → BLOQUEO
python generador_plan_alerta.py MSTR 127.35 500 3 --illiquid   # simula spread 45 bps → BLOQUEO
```

### 3.5 Dónde queda guardado
Cada plan se guarda en **`ULTIMO_PLAN_DE_ACCION.txt`** (se sobrescribe con cada ejecución). Cópialo a otra carpeta si quieres llevar un diario.

---

## 4. Cómo leer el plan generado

Ejemplo real: `MSTR 127.35 500 3 121.88 --max-risk 15`

### 4.1 Cabecera
```
Modo Estructura: ANCLADO A SOPORTE REAL EN GRAFICA ($121.880 | Rango: 4.30%)
```
Indica si el plan se basa en tu soporte real o en la volatilidad calibrada.

### 4.2 Semáforo
`[VERDE - SEGURO]` → se puede operar. `AMARILLO` / `ROJO` → **no se generan órdenes** (ver [sección 7](#7-semáforo-de-seguridad-cuándo-no-operar)).

### 4.3 Guardián de riesgo (si aparece)
```
Si entraras con 3.0x completo ($1,500.00), arriesgarias -$35.59 USDT.
Se reduce automaticamente la exposicion a 1.26x efectivo
(Nocional: $632.25 | Margen Usado: $210.75 USDT)
```
El soporte está lejos, así que el sistema **reduce el tamaño** para que nunca pierdas más de tu `--max-risk`. **Los precios no cambian; solo la cantidad.**

### 4.4 Las 3 órdenes (Scale-In 30/30/40)

| Orden | Peso | Nivel | Por qué ahí |
|---|---|---|---|
| 1 | 30% | Retroceso 38.2% del impulso | Retesteo del techo roto: el antiguo máximo pasa a ser soporte |
| 2 | 30% | Retroceso 50% (OTE / equilibrio) | Zona de descuento donde suelen recomprar las manos fuertes |
| 3 | 40% | Retroceso 75% (Order Block / mecha) | Barrido de liquidez: la carga más grande, al mejor precio |

**Por qué 40% en la última:** si el precio llega hasta ahí, tu promedio baja de forma significativa y el Stop queda cerca.

### 4.5 Salidas
| Concepto | Fórmula |
|---|---|
| **Stop Loss** | 0.35% por debajo del soporte (colchón contra mechas) |
| **TP1** (50% de la posición) | Promedio + 1.8 × distancia al SL |
| **TP2** (50% restante) | Promedio + 3.2 × distancia al SL |
| **Riesgo máximo** | Incluye deslizamiento del SL (8 bps) + comisión taker (4 bps) |

### 4.6 Escenarios
- **Llenado 3/3:** las tres órdenes entran → mejor promedio, máximo beneficio y máximo riesgo (= tu `--max-risk`).
- **Llenado parcial (solo Orden 1):** el precio no retrocede tanto y sube → ganas menos, pero arriesgaste menos. **No persigas el precio.**

---

## 5. Cómo poner el plan en el exchange

Ejemplo con Binance Futures (perpetuo `MSTRUSDT`):

1. **Modo de margen:** *Aislado (Isolated)*. Así una operación no puede comerse el resto de la cuenta.
2. **Apalancamiento:** pon el que indicaste (`3x`).
3. **Órdenes de entrada:** 3 × *Limit* → *Buy/Long*.
   - Escribe la **CANTIDAD en monedas/acciones** del plan (ej. `1.514`, `1.522`, `2.052`), **no el margen**. Así el riesgo cuadra exactamente aunque el exchange muestre otro margen.
4. **Stop Loss:** *Stop Market*, precio de activación = SL del plan, marcado como **Reduce-Only**, cantidad = total de las 3 órdenes.
5. **Take Profits:** 2 × *Limit Sell* **Reduce-Only**, 50% de la cantidad total en cada TP.

> ⚠️ Si al principio solo se llena la Orden 1, ajusta la cantidad del SL y de los TP a lo que realmente está abierto (o usa la función TP/SL "de posición" del exchange, que se ajusta sola).

---

## 6. Gestión durante la operación

| Situación | Qué hacer |
|---|---|
| El precio retrocede hacia tus órdenes | Nada. Es el plan funcionando. |
| Solo entra la Orden 1 y el precio sube | **No añadas más arriba.** Cancela las órdenes 2 y 3 cuando toque TP1. |
| Toca TP1 | Se cierra el 50%. **Mueve el SL del resto a Break-Even** (tu precio promedio). Desde aquí no puedes perder. |
| Toca TP2 | Operación cerrada. Anótala. |
| Toca el Stop Loss | Pierdes lo calculado (ej. −\$15). **No re-entres por venganza.** Espera la siguiente alerta. |
| Quieres "promediar" por debajo del SL | **Prohibido.** Eso es justo el "promediado por susto" que este sistema elimina. |
| Pasan muchas horas sin llenarse | Si el precio se va sin llenar ninguna orden, cancela: el setup ya no es válido. |

---

## 7. Semáforo de seguridad (cuándo NO operar)

Módulo: [`core/toxicity_detector.py`](core/toxicity_detector.py)

| Estado | Condición | Acción del sistema |
|---|---|---|
| 🟢 **VERDE** | Caída < 7% en 4H, spread ≤ 25 bps, volumen ≥ \$5M | Genera el plan |
| 🟡 **AMARILLO** | Spread > 25 bps o volumen < \$5M (activo ilíquido) | **Bloquea**: el slippage se comería el beneficio |
| 🔴 **ROJO** | Caída ≥ 7% en 4H (cuchillo cayendo) | **Bloquea**: espera suelo + divergencia en 4H |

> ⚠️ **Importante:** desde la línea de comandos (CLI), el semáforo **no lee el mercado en vivo**: asume spread de 2 bps y caída del 0%. **Tú debes comprobar en el gráfico** que no hay caída violenta. Vía webhook sí puedes enviarle `drop_pct`, `spread_bps` y `volume_24h` reales.

---

## 8. Herramientas complementarias

| Script | Para qué sirve | Comando |
|---|---|---|
| [`vision_mercado.py`](vision_mercado.py) | Panel multi-temporal: sesgo 1D, rango 4H (Premium/Discount), gatillo 15m | `python vision_mercado.py 74300` |
| [`gestor_escalamiento.py`](gestor_escalamiento.py) | Calculadora 30/30/40 entre dos precios que tú eliges | `python gestor_escalamiento.py 500 3 73500 72800` *(margen, apalancamiento, zona alta, zona baja)* |
| [`estrategia_choch_4h_5m.py`](estrategia_choch_4h_5m.py) | Detecta Divergencia RSI 4H + CHoCH 5m. Compara entrada a mercado vs escalonada | `python estrategia_choch_4h_5m.py 500 3` · en vivo: `... --live` |
| [`simulador_estrategia_completa.py`](simulador_estrategia_completa.py) | 4 escenarios (éxito, llenado parcial, stop, barrido) | `python simulador_estrategia_completa.py 500 3` |
| [`simulador_volatilidad_intradia.py`](simulador_volatilidad_intradia.py) | Prueba el plan con movimientos de \$1,000–\$2,000 en BTC | `python simulador_volatilidad_intradia.py 500` |
| [`analisis_caida_80k_74k.py`](analisis_caida_80k_74k.py) | Análisis forense de la caída de BTC de 80k a 74k (entrada en 76k) | `python analisis_caida_80k_74k.py 500` |
| [`main.py`](main.py) | Demostración completa de la arquitectura Brain/Reflex | `python main.py` |
| [`run_simulation.py`](run_simulation.py) | Paper trading simulado tick a tick | `python run_simulation.py 200` |
| [`live_ccxt_paper.py`](live_ccxt_paper.py) | Paper trading con datos **reales** del exchange (necesita internet) | `python live_ccxt_paper.py binance` |

> Los modos `--live` y `live_ccxt_paper.py` necesitan conexión a internet. **Ninguno envía órdenes reales**: todo es en papel.

---

## 9. Vigilante directo de Binance (recomendado, sin TradingView ni webhook)

Archivo: [`vigilante_binance.py`](vigilante_binance.py). Lee **directamente** la API pública de Binance Futuros. **No necesita API key** y **nunca envía órdenes**.

```powershell
# Foto instantánea con datos reales + envío directo a Telegram
python vigilante_binance.py MSTR --ahora --max-risk 15 --telegram

# Vigilar varios activos 24/7 (avisa por Telegram y pita al confirmarse Div 4H + CHoCH 5m)
python vigilante_binance.py MSTR BTC SOL --max-risk 15 --capital 500 --lev 3 --intervalo 30

# Probar que el bot de Telegram responde a tu móvil
python vigilante_binance.py --test-telegram
```

Calcula por sí mismo: RSI 4H y divergencia, CHoCH 5m, **spread real**, **volumen 24h real**, **caída real en 4H** y **soporte del impulso** (mínimo de las últimas 2 h de velas de 5m). Solo usa velas **cerradas**, así que no repinta. Los planes se guardan en `planes/AAAAMMDD_HHMMSS_ACTIVO_SENAL.txt`.
Cada alerta envía al chat de Telegram:
1. Mensaje resumido con los precios clave (Orden 1, 2, 3, Stop Loss y Take Profits).
2. El archivo `.txt` del plan completo adjunto como documento.

> El PC tiene que estar encendido y con el script abierto. Para 24/7 real, ejecútalo en un VPS.

---

## 10. Recepción automática de alertas (webhook, alternativa)

### 9.1 Arrancar el receptor
```powershell
python generador_plan_alerta.py --webhook
```
Queda escuchando en `http://127.0.0.1:8000/webhook`. Cada alerta recibida imprime el plan en consola y lo guarda en `ULTIMO_PLAN_DE_ACCION.txt`.

### 9.2 Mensaje JSON para la alerta de TradingView
```json
{
  "ticker": "{{ticker}}",
  "price": {{close}},
  "swing_low": {{low}},
  "capital": 500,
  "leverage": 3,
  "max_risk_usdt": 15
}
```
Campos opcionales para alimentar el semáforo: `drop_pct`, `spread_bps`, `volume_24h`.

> ⚠️ `{{low}}` es el mínimo de **la vela de la alerta**, no necesariamente el soporte estructural. Lo ideal es que tu Pine Script envíe el mínimo del impulso (el swing low) en una variable propia.

### 9.3 Probarlo en local
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/webhook -Method Post -ContentType "application/json" -Body '{"ticker":"MSTRUSDT","price":127.35,"swing_low":121.88,"max_risk_usdt":15}'
```

> ℹ️ TradingView solo envía webhooks a URLs públicas (puertos 80/443). Para recibirlos en tu PC necesitas un túnel (ngrok, Cloudflare Tunnel) o un servidor. **Nunca expongas un puerto que tenga acceso a claves de exchange.**

---

## 11. Arquitectura interna (para entender el sistema)

```
             ┌───────────────────── THE BRAIN (lento, reflexivo) ─────────────────────┐
             │  core/brain.py: tesis macro, invalidación, post-mortem nocturno, Brier │
             └───────────────────────────────▲────────────────────────────────────────┘
                                             │ escala si confianza < 0.60 o crisis
 Mercado ─► core/state_engine.py ─► core/reflex.py ─► core/risk_layer.py ─► Orden / Plan
 (libro,     estado numérico         decisión tipada    compuertas en código duro
  velas)     < 400 tokens, causal    < 1 ms             Kelly/4, DD 15%, kill-switch
```

| Módulo | Función |
|---|---|
| `core/types.py` | Contratos de datos: `MarketState`, `DecisionSchema`, `Order`, `RiskParameters` |
| `core/state_engine.py` | Mid, spread, desbalance del libro, volatilidad realizada, drawdown (sin mirar el futuro) |
| `core/smc_quant.py` | Swings, Order Blocks, rupturas reales vs falsas, barridos de liquidez |
| `core/multi_timeframe.py` | Sesgo 1D, rango 4H Premium/Discount, gatillo 15m |
| `core/choch_rsi_strategy.py` | RSI de Wilder, divergencia alcista 4H (< 35), CHoCH de cuerpo en 5m |
| `core/position_scaling.py` | Escalonado 30/30/40 y precio promedio |
| `core/toxicity_detector.py` | Cuchillo cayendo y liquidez tóxica |
| `core/reflex.py` | Decide `long/short/neutral` con confianza y calidad 0–3 |
| `core/risk_layer.py` | Opera solo si calidad ≥ 2, confianza > 0.80 y riesgo = `safe`; DD máx 15%, pérdida diaria máx 3% |
| `core/brain.py` | Revisión nocturna: aciertos, oportunidades perdidas, calibración Brier |
| `simulation/paper_engine.py` | Simulador con comisiones (4 bps) y slippage |

**Principio clave:** el modelo **solo juzga**. Tamaños, límites y kill-switch los decide **código fijo** que ningún modelo puede saltarse.

---

## 12. Pruebas y mantenimiento

Ejecutar todas las pruebas (deben salir 37 `ok`):
```powershell
python -m unittest discover -s tests -v
```
Hazlo **siempre** después de cambiar cualquier parámetro o archivo de `core/`.

### Parámetros que puedes ajustar
| Qué | Dónde | Valor actual |
|---|---|---|
| Rango por activo | `VOLATILIDAD_PRESETS` en `generador_plan_alerta.py` | BTC 0.90 / ETH 1.15 / SOL 1.45 / MSTR 1.85 |
| Riesgo máximo por defecto | `max_riesgo_usdt` en `calcular_y_generar_plan` | 20 USDT |
| Slippage y comisión del SL | `slippage_sl_bps`, `taker_fee_bps` | 8 y 4 bps |
| Umbral de cuchillo cayendo | `max_caida_veloz_pct` en `toxicity_detector.py` | 7% |
| Spread máximo | `max_spread_bps` | 25 bps |
| Drawdown máx / pérdida diaria | `RiskParameters` en `core/types.py` | 15% / 3% |

---

## 13. Reglas de oro y limitaciones conocidas

### Reglas de oro
1. **Nunca entres sin generar el plan.** Sin plan no hay operación.
2. **Riesgo por operación: 2–3% de la cuenta** (\$10–\$15 con \$500).
3. **El Stop Loss se pone al mismo tiempo que las entradas**, nunca después.
4. **Nunca muevas el SL hacia abajo.** Solo hacia arriba (Break-Even en TP1).
5. **Nunca promedies por debajo del plan.**
6. **Semáforo rojo = no operar**, aunque la señal "se vea buenísima".
7. **Máximo 3 pérdidas seguidas por día** → apaga y vuelve mañana.
8. **Anota cada operación** (plan, resultado, emoción). Es la base de la revisión nocturna.

### Limitaciones honestas
- **No es una garantía de ganancias.** Los niveles 38.2/50/75 son una regla estructural, no una predicción. El *edge* real solo se confirma con un historial largo de operaciones registradas.
- **Selección adversa:** en las operaciones buenas a menudo solo se llena la Orden 1; en las malas se llenan las tres. Por eso se limita el riesgo con el llenado completo.
- **Gaps y noticias:** el Stop Market puede ejecutarse peor de lo calculado en movimientos bruscos. Esto pesa especialmente en MSTR, que es menos líquido y depende de noticias de Wall Street.
- **Funding:** mantener perpetuos varios días paga (o cobra) funding cada 8 h. El plan no lo incluye.
- **El semáforo por CLI no lee datos en vivo.** Compruébalo tú en el gráfico.
- **El sistema no envía órdenes reales.** Tú las colocas: esa es tu última compuerta de seguridad.

---

## 14. Solución de problemas

| Problema | Solución |
|---|---|
| `python` no se reconoce | Usa la ruta completa del ejecutable (sección 1) |
| Caracteres raros (`Ca�da`) en consola | Es solo cómo muestra PowerShell los acentos. Ejecuta antes `chcp 65001` o abre `ULTIMO_PLAN_DE_ACCION.txt` |
| `UnicodeEncodeError` | Ejecuta `$env:PYTHONIOENCODING="utf-8"` antes del comando |
| El soporte que paso se ignora | Debe ser **menor** que el precio de la alerta y mayor que 0 |
| Margen asignado muy pequeño | El soporte está lejos: el guardián reduce el tamaño para respetar tu riesgo. Es lo correcto. Si te parece poco, el setup tiene mala relación riesgo/tamaño |
| `--live` da error de conexión | Sin internet o exchange bloqueado: el script vuelve solo al modo simulación |
| El webhook no recibe alertas de TradingView | `127.0.0.1` no es pública: necesitas un túnel o servidor (sección 9) |
| Falla un test | No operes con cambios sin probar. Revierte el último cambio y vuelve a lanzar los tests |

---

### Chuleta rápida

```powershell
cd d:\trader

# Plan con soporte real y riesgo de $15  (USO HABITUAL)
python generador_plan_alerta.py MSTR 127.35 500 3 121.88 --max-risk 15

# Plan rápido sin soporte
python generador_plan_alerta.py BTC 74200 500 3

# Probar bloqueos de seguridad
python generador_plan_alerta.py BTC 74200 500 3 --crash

# Receptor de alertas
python generador_plan_alerta.py --webhook

# Verificar que todo funciona
python -m unittest discover -s tests -v
```

> **Opera el plan, no la emoción.** La pérdida se decide antes de entrar; después solo queda ejecutar.
