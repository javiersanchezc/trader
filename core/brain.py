"""
brain.py - The Brain (Capa Asíncrona de Macroinvestigación & Calibración Estadística)
Realiza investigación estructural profunda, invalidación de tesis y auditoría nocturna
post-mortem con calibración por Puntaje de Brier.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import math
from core.types import Regime

@dataclass
class TradeAuditRecord:
    timestamp: int
    symbol: str
    direction: str
    confidence: float
    setup_quality: int
    executed: bool
    rejection_reason: Optional[str]
    actual_return_bps: float
    outcome_positive: bool  # 1 si el retorno fue positivo / predicción correcta, 0 en caso contrario

@dataclass
class MacroResearchThesis:
    asset: str
    macro_regime: Regime
    funding_rate_bps: float
    stablecoin_liquidity_flow: str # "expanding" | "contracting"
    on_chain_fundamental_score: float # 0 a 10
    bull_catalyst: str
    bear_case_thesis: str
    invalidation_level: float
    active: bool = True

class BrainEngine:
    def __init__(self):
        self.theses: Dict[str, MacroResearchThesis] = {}
        self.audit_log: List[TradeAuditRecord] = []

    def register_macro_thesis(self, thesis: MacroResearchThesis) -> None:
        self.theses[thesis.asset] = thesis

    def log_decision_and_outcome(
        self,
        timestamp: int,
        symbol: str,
        direction: str,
        confidence: float,
        setup_quality: int,
        executed: bool,
        rejection_reason: Optional[str],
        actual_return_bps: float
    ) -> None:
        outcome_positive = actual_return_bps > 0.0
        record = TradeAuditRecord(
            timestamp=timestamp,
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            setup_quality=setup_quality,
            executed=executed,
            rejection_reason=rejection_reason,
            actual_return_bps=actual_return_bps,
            outcome_positive=outcome_positive
        )
        self.audit_log.append(record)

    def compute_brier_score(self) -> float:
        """
        El Puntaje de Brier mide la precisión de las probabilidades pronosticadas:
        BS = (1/N) * sum((probabilidad_pronosticada - resultado_real)^2)
        Un valor de 0 indica calibración perfecta; 0.25 equivale al azar (lanzamiento de moneda).
        """
        if not self.audit_log:
            return 0.0

        squared_errors = []
        for r in self.audit_log:
            y = 1.0 if r.outcome_positive else 0.0
            p = r.confidence
            squared_errors.append((p - y) ** 2)

        return sum(squared_errors) / len(squared_errors)

    def nightly_post_mortem(self) -> Dict[str, Any]:
        """
        Auditoría Nocturna de todas las ejecuciones (fills) y oportunidades descartadas (misses),
        análisis de calibración probabilística y recomendaciones de recalibración de umbrales.
        """
        total_evaluations = len(self.audit_log)
        fills = [r for r in self.audit_log if r.executed]
        misses = [r for r in self.audit_log if not r.executed]

        profitable_fills = [r for r in fills if r.outcome_positive]
        win_rate = len(profitable_fills) / len(fills) if fills else 0.0
        avg_pnl_bps = sum(r.actual_return_bps for r in fills) / len(fills) if fills else 0.0
        
        brier_score = self.compute_brier_score()

        # Oportunidades descartadas que habrían sido grandes ganadoras (> 50 bps)
        missed_winners = [m for m in misses if m.actual_return_bps > 50.0]

        # Evaluación según Puntaje de Brier
        if brier_score > 0.22:
            recommended_action = "DISMINUIR_RIESGO_Y_ELEVAR_UMBRAL_DE_CONFIANZA_A_0.85"
            calibration_status = "DERIVA_SOBRECONFIADA"
        elif brier_score < 0.14:
            recommended_action = "MANTENER_COMPUERTAS_CALIBRACION_OPTIMA"
            calibration_status = "ALTA_CALIBRACION"
        else:
            recommended_action = "OPERACION_ESTANDAR"
            calibration_status = "CALIBRACION_MODERADA"

        report = {
            "total_evaluaciones": total_evaluations,
            "total_ejecuciones": len(fills),
            "total_descartes": len(misses),
            "tasa_de_acierto": round(win_rate, 4),
            "pnl_promedio_bps": round(avg_pnl_bps, 2),
            "puntaje_de_brier": round(brier_score, 4),
            "estado_calibracion_brier": calibration_status,
            "ganadoras_descartadas": len(missed_winners),
            "accion_recomendada": recommended_action
        }
        return report
