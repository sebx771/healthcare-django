from ..models import MetricasModelos


class MetricasDefaultService:
    @classmethod
    def set_default_model(cls, model_id: int) -> MetricasModelos:
        model = MetricasModelos.objects.get(pk=model_id)
        model.default = True
        model.save()  # lógica en model.save desactiva los demás
        return model

