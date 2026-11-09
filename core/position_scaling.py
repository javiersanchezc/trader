"""
position_scaling.py - Gestor de Escalamiento Institucional de Posiciones (Staged Scale-In)
Reemplaza el promediado emocional/pánico por una distribución matemática predefinida:
- Tranche 1 (30%): Entrada de confirmación en el borde del Order Block.
- Tranche 2 (30%): Entrada óptima (OTE / 61.8% - 70.5% Fibo).
- Tranche 3 (40%): Entrada de barrido de liquidez en el mínimo de la demanda.
- Stop Loss Inmutable que defiende todo el paquete con pérdida máxima calculada.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class TramoOrden:
    numero_tramo: int
    porcentaje_capital: float # e.g. 0.30
    margen_usdt: float        # e.g. 150 USDT
    apalancamiento: float     # e.g. 3.0
    nocional_usdt: float      # e.g. 450 USDT
    precio_orden: float       # Precio límite exacto
    cantidad_activo: float    # Cantidad en BTC
    tipo_zona: str            # "BORDE_DEMANDA", "ZONA_OPTIMA_OTE", "BARRIDO_LIQUIDEZ"

@dataclass
class PlanEscalamiento:
    simbolo: str
    margen_total_usdt: float
    apalancamiento: float
    nocional_total_usdt: float
    tramos: List[TramoOrden]
    precio_promedio_proyectado: float
    stop_loss_inmutable: float
    perdida_maxima_usdt: float
    perdida_maxima_pct: float
    take_profit_1: float
    take_profit_2: float
    ganancia_proyectada_tp1: float
    ganancia_proyectada_tp2: float
    ratio_riesgo_beneficio: float

class ScaleInManager:
    def __init__(self, symbol: str = "BTC/USDT"):
        self.symbol = symbol

    def calcular_plan_escalado(
        self,
        margen_total_usdt: float = 500.0,
        apalancamiento: float = 3.0,
        zona_alta_demanda: float = 73500.0,
        zona_baja_demanda: float = 72800.0,
        stop_loss_colchon_pct: float = 0.004 # 0.4% debajo del mínimo
    ) -> PlanEscalamiento:
        nocional_total = margen_total_usdt * apalancamiento
        rango_demanda = zona_alta_demanda - zona_baja_demanda

        # 1. Definición de niveles de precio basada en microestructura:
        # Nivel 1 (30%): Entrada inicial en el borde superior de la demanda
        p1 = zona_alta_demanda
        # Nivel 2 (30%): Zona óptima de retroceso (OTE 61.8% del rango de demanda)
        p2 = zona_alta_demanda - (rango_demanda * 0.50)
        # Nivel 3 (40%): Nivel de barrido de liquidez (cerca del mínimo del Order Block)
        p3 = zona_baja_demanda + (rango_demanda * 0.15)

        # 2. Stop Loss inmutable (fuera de toda la estructura de demanda)
        stop_loss = zona_baja_demanda * (1.0 - stop_loss_colchon_pct)

        # 3. Construir los 3 tramos (30% / 30% / 40%)
        distribucion = [
            (1, 0.30, p1, "1. Retesteo Borde Superior Demand Block"),
            (2, 0.30, p2, "2. Zona Óptima de Retroceso (50%-61.8% OTE)"),
            (3, 0.40, p3, "3. Barrido de Liquidez / Mecha de Manipulación")
        ]

        tramos: List[TramoOrden] = []
        suma_coste_ponderado = 0.0
        cantidad_total_btc = 0.0

        for num, pct, p_orden, desc in distribucion:
            margen_tramo = margen_total_usdt * pct
            nocional_tramo = margen_tramo * apalancamiento
            qty = nocional_tramo / p_orden
            
            tramos.append(TramoOrden(
                numero_tramo=num,
                porcentaje_capital=pct,
                margen_usdt=round(margen_tramo, 2),
                apalancamiento=apalancamiento,
                nocional_usdt=round(nocional_tramo, 2),
                precio_orden=round(p_orden, 2),
                cantidad_activo=round(qty, 4),
                tipo_zona=desc
            ))

            suma_coste_ponderado += (p_orden * qty)
            cantidad_total_btc += qty

        # 4. Precio promedio ponderado si entran todos los tramos
        precio_promedio = suma_coste_ponderado / cantidad_total_btc

        # 5. Cálculo de pérdida máxima en Stop Loss
        # Pérdida = cantidad_total * (precio_promedio - stop_loss)
        perdida_max_usdt = cantidad_total_btc * (precio_promedio - stop_loss)
        perdida_max_pct = (perdida_max_usdt / margen_total_usdt) * 100.0

        # 6. Take Profits (TP1 en equilibrio del rango de 4H, TP2 en máximos del rango)
        # Proyectamos TP1 a 1.5x la distancia del riesgo y TP2 a 3x
        distancia_riesgo = precio_promedio - stop_loss
        tp1 = precio_promedio + (distancia_riesgo * 1.8)
        tp2 = precio_promedio + (distancia_riesgo * 3.5)

        ganancia_tp1 = (cantidad_total_btc * 0.5) * (tp1 - precio_promedio)
        ganancia_tp2 = (cantidad_total_btc * 0.5) * (tp2 - precio_promedio)
        ganancia_total = ganancia_tp1 + ganancia_tp2
        rr_ratio = ganancia_total / perdida_max_usdt if perdida_max_usdt > 0 else 2.5

        return PlanEscalamiento(
            simbolo=self.symbol,
            margen_total_usdt=margen_total_usdt,
            apalancamiento=apalancamiento,
            nocional_total_usdt=nocional_total,
            tramos=tramos,
            precio_promedio_proyectado=round(precio_promedio, 2),
            stop_loss_inmutable=round(stop_loss, 2),
            perdida_maxima_usdt=round(perdida_max_usdt, 2),
            perdida_maxima_pct=round(perdida_max_pct, 2),
            take_profit_1=round(tp1, 2),
            take_profit_2=round(tp2, 2),
            ganancia_proyectada_tp1=round(ganancia_tp1, 2),
            ganancia_proyectada_tp2=round(ganancia_tp2, 2),
            ratio_riesgo_beneficio=round(rr_ratio, 2)
        )
