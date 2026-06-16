from typing import Any, Dict, List
from django.utils import timezone

from ..models import MetricasModelos


class MetricasModelosService:
    @classmethod
    def listar_metricas(cls) -> List[Dict[str, Any]]:
        queryset = MetricasModelos.objects.all().order_by("-trained_at")

        modelos: List[Dict[str, Any]] = []
        for m in queryset:
            modelos.append(
                {
                    "id": m.id,
                    "nombre_modelo": m.nombre_modelo,
                    "trained_at": m.trained_at.isoformat() if m.trained_at else None,
                    "default": m.default,
                    "ruta_archivo_joblib": m.ruta_archivo_joblib,
                    "metricas": {
                        "accuracy": m.accuracy,
                        "precision": m.precision,
                        "recall": m.recall,
                        "f1_score": m.f1_score,
                    },
                    "matriz_confusion": m.matriz_confusion,
                }
            )

        return modelos

