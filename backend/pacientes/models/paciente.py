from django.db import models


class Paciente(models.Model):
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    edad = models.IntegerField()
    sexo = models.CharField(max_length=20)
    peso = models.DecimalField(max_digits=5, decimal_places=2)
    altura = models.DecimalField(max_digits=3, decimal_places=2)
    imc = models.DecimalField(max_digits=5, decimal_places=2, db_column='IMC')
    presion_sistolica = models.IntegerField()
    presion_diastolica = models.IntegerField()
    frecuencia_cardiaca = models.IntegerField()
    saturacion_oxigeno = models.DecimalField(max_digits=5, decimal_places=2)
    temperatura = models.DecimalField(max_digits=4, decimal_places=2)
    glucosa = models.DecimalField(max_digits=6, decimal_places=2)
    colesterol = models.DecimalField(max_digits=6, decimal_places=2)
    antecedentes_familiares = models.BooleanField(default=False)
    fumador = models.BooleanField(default=False)
    consumo_alcohol = models.BooleanField(default=False)
    actividad_fisica = models.CharField(max_length=50)
    diagnostico_preliminar = models.CharField(max_length=150)
    riesgo_enfermedad = models.CharField(max_length=50)
    fecha_consulta = models.DateField()

    # ============================
    # Fase 2 (sin campos persistidos)
    # ============================

    def _get_numeric(self, value, default=0):
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default


    @property
    def motivos_critico(self):
        motivos = []

        if self.presion_sistolica is not None and self.presion_sistolica > 180:
            motivos.append('presion_sistolica_alta')
        if self.presion_diastolica is not None and self.presion_diastolica > 120:
            motivos.append('presion_diastolica_alta')
        if self.saturacion_oxigeno is not None and self.saturacion_oxigeno < 85:
            motivos.append('saturacion_oxigeno_baja')
        if self.glucosa is not None and self.glucosa > 300:
            motivos.append('glucosa_alta')
        if self.frecuencia_cardiaca is not None and (self.frecuencia_cardiaca > 130 or self.frecuencia_cardiaca < 40):
            motivos.append('frecuencia_cardiaca_alta_baja')
        if self.temperatura is not None and (self.temperatura > 39.5 or self.temperatura < 35):
            motivos.append('temperatura_alta_baja')

        return motivos

    @property
    def critico(self):
        # Señal clínica peligrosa pero plausible (según umbrales del plan)
        return len(self.motivos_critico) > 0

    @property
    def motivos_sospecha(self):
        motivos = []

        # Inconsistencia interna
        if self.presion_sistolica is not None and self.presion_diastolica is not None:
            if self.presion_diastolica >= self.presion_sistolica:
                motivos.append('diastolica_mayor_igual_sistolica')

        # Rangos fisiológicos / plausibilidad (no descartan, solo marcan sospecha)
        # Saturación: [0, 100]
        if self.saturacion_oxigeno is not None:
            so = self._get_numeric(self.saturacion_oxigeno)
            if so < 0 or so > 100:
                motivos.append('saturacion_fuera_rango')

        # Presiones: límites amplios (plausibles)
        ps = self._get_numeric(self.presion_sistolica)
        pd = self._get_numeric(self.presion_diastolica)
        if ps <= 0 or ps > 280:
            motivos.append('presion_sistolica_fuera_rango')
        if pd <= 0 or pd > 200:
            motivos.append('presion_diastolica_fuera_rango')

        # FC: [20, 240]
        fc = self._get_numeric(self.frecuencia_cardiaca)
        if fc <= 0 or fc < 20 or fc > 240:
            motivos.append('frecuencia_cardiaca_fuera_rango')

        # Glucosa: [20, 700] (para plausibilidad), y además > 0
        gl = self._get_numeric(self.glucosa)
        if gl <= 0 or gl < 20 or gl > 1000:
            motivos.append('glucosa_fuera_rango')

        # Temperatura: [30, 43] (plausibilidad)
        t = self._get_numeric(self.temperatura)
        if t < 25 or t > 45:
            motivos.append('temperatura_fuera_rango')

        # IMC: rango razonable (para sospecha de inconsistencias)
        imc = self._get_numeric(self.imc)
        if imc > 0 and (imc < 10 or imc > 80):
            motivos.append('imc_fuera_rango')

        # IMC vs peso/altura (si existen)
        try:
            altura = self._get_numeric(self.altura)
            peso = self._get_numeric(self.peso)
            if altura > 0 and peso > 0:
                imc_calc = peso / (altura ** 2)
                if imc > 0:
                    # tolerancia razonable
                    if abs(imc_calc - imc) / max(imc, 0.01) > 0.15:
                        motivos.append('imc_inconsistente_con_peso_altura')
        except Exception:
            # si no se puede evaluar, no rompe
            pass

        return motivos

    @property
    def sospechoso(self):
        return len(self.motivos_sospecha) > 0

    @property
    def nivel_riesgo_calculado(self):
        """Heurística simple basada en signos vitales (y critico => Alto)."""
        if self.critico:
            return 'Alto'

        # Medio si hay alteraciones moderadas o sospecha de rangos clínicos
        # (sin caer en valores imposibles)
        ps = self._get_numeric(self.presion_sistolica)
        pd = self._get_numeric(self.presion_diastolica)
        so = self._get_numeric(self.saturacion_oxigeno)
        fc = self._get_numeric(self.frecuencia_cardiaca)
        gl = self._get_numeric(self.glucosa)
        t = self._get_numeric(self.temperatura)

        alteracion_moderada = (
            (ps >= 140 and ps <= 180) or
            (pd >= 90 and pd <= 120) or
            (so >= 85 and so < 95) or
            (fc >= 90 and fc <= 130) or
            (gl >= 150 and gl <= 300) or
            (t >= 37.5 and t <= 39.5)
        )

        if alteracion_moderada or self.sospechoso:
            return 'Medio'

        return 'Bajo'

    @property
    def motivos_riesgo_inconsistente(self):
        motivos = []
        try:
            riesgo_asignado = str(self.riesgo_enfermedad).strip().capitalize()
        except Exception:
            riesgo_asignado = 'Bajo'

        riesgo_calc = self.nivel_riesgo_calculado
        if riesgo_asignado != riesgo_calc:
            motivos.append('riesgo_asignado_no_coincide_con_riesgo_calculado')
        return motivos

    @property
    def riesgo_inconsistente(self):
        return len(self.motivos_riesgo_inconsistente) > 0

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"