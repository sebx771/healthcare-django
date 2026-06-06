import io
from typing import Iterator, List, Dict, Any
from django.http import StreamingHttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd

COLUMNAS_EXPORT = [
    'id_paciente', 'nombres', 'apellidos', 'edad', 'sexo',
    'peso', 'altura', 'imc', 'presion_sistolica', 'presion_diastolica',
    'frecuencia_cardiaca', 'saturacion_oxigeno', 'temperatura', 'glucosa',
    'colesterol', 'antecedentes_familiares', 'fumador', 'consumo_alcohol',
    'actividad_fisica', 'diagnostico_preliminar', 'riesgo_enfermedad',
    'fecha_consulta', 'critico'
]

HEADERS_ES = {
    'id_paciente': 'ID Paciente',
    'nombres': 'Nombres',
    'apellidos': 'Apellidos',
    'edad': 'Edad',
    'sexo': 'Sexo',
    'peso': 'Peso (kg)',
    'altura': 'Altura (m)',
    'imc': 'IMC',
    'presion_sistolica': 'Presión Sistólica',
    'presion_diastolica': 'Presión Diastólica',
    'frecuencia_cardiaca': 'Frecuencia Cardíaca',
    'saturacion_oxigeno': 'Saturación (%)',
    'temperatura': 'Temperatura (°C)',
    'glucosa': 'Glucosa (mg/dL)',
    'colesterol': 'Colesterol (mg/dL)',
    'antecedentes_familiares': 'Antecedentes',
    'fumador': 'Fumador',
    'consumo_alcohol': 'Consumo Alcohol',
    'actividad_fisica': 'Actividad Física',
    'diagnostico_preliminar': 'Diagnóstico',
    'riesgo_enfermedad': 'Riesgo',
    'fecha_consulta': 'Fecha Consulta',
    'critico': 'Crítico'
}

class ReportesService:
    @staticmethod
    def get_dataframe(pacientes_qs) -> pd.DataFrame:
        datos: List[Dict[str, Any]] = []
        for p in pacientes_qs:
            registro = {
                'id_paciente': p.id_paciente,
                'nombres': p.nombres,
                'apellidos': p.apellidos,
                'edad': p.edad,
                'sexo': p.sexo,
                'peso': float(p.peso),
                'altura': float(p.altura),
                'imc': float(p.imc),
                'presion_sistolica': p.presion_sistolica,
                'presion_diastolica': p.presion_diastolica,
                'frecuencia_cardiaca': p.frecuencia_cardiaca,
                'saturacion_oxigeno': float(p.saturacion_oxigeno),
                'temperatura': float(p.temperatura),
                'glucosa': float(p.glucosa),
                'colesterol': float(p.colesterol),
                'antecedentes_familiares': 'SÍ' if p.antecedentes_familiares else 'NO',
                'fumador': 'SÍ' if p.fumador else 'NO',
                'consumo_alcohol': 'SÍ' if p.consumo_alcohol else 'NO',
                'actividad_fisica': p.actividad_fisica,
                'diagnostico_preliminar': p.diagnostico_preliminar,
                'riesgo_enfermedad': p.riesgo_enfermedad,
                'fecha_consulta': p.fecha_consulta.strftime('%Y-%m-%d') if p.fecha_consulta else '',
                'critico': 'SÍ' if p.critico else 'NO'
            }
            datos.append(registro)
        return pd.DataFrame(datos, columns=COLUMNAS_EXPORT)

    @staticmethod
    def export_csv(pacientes_qs) -> StreamingHttpResponse:
        buffer = io.StringIO()
        df = ReportesService.get_dataframe(pacientes_qs)
        df.to_csv(buffer, index=False, sep=';', encoding='utf-8-sig')
        buffer.seek(0)
        response = StreamingHttpResponse(
            iter([buffer.getvalue()]),
            content_type='text/csv'
        )
        response['Content-Disposition'] = 'attachment; filename="pacientes.csv"'
        return response

    @staticmethod
    def export_excel(pacientes_qs) -> StreamingHttpResponse:
        buffer = io.BytesIO()
        df = ReportesService.get_dataframe(pacientes_qs)
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Pacientes Clínicos', index=False)
        buffer.seek(0)
        response = StreamingHttpResponse(
            iter([buffer.getvalue()]),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="pacientes.xlsx"'
        return response

    @staticmethod
    def export_pdf(pacientes_qs) -> StreamingHttpResponse:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        styles = getSampleStyleSheet()
        style_header = styles['Heading1']
        style_header.alignment = 1

        elementos = []
        elementos.append(Paragraph('Reporte Clínico de Pacientes', style_header))
        elementos.append(Spacer(1, 20))

        df = ReportesService.get_dataframe(pacientes_qs)
        data = [list(HEADERS_ES.values())]
        for _, row in df.iterrows():
            data.append([str(row[col]) for col in COLUMNAS_EXPORT])

        col_widths = [30, 60, 60, 25, 20, 35, 35, 30, 45, 45, 45, 40, 35, 40, 45, 35, 35, 35, 45, 60, 35, 40, 25]
        tabla = Table(data, colWidths=col_widths, repeatRows=1)

        estilo = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A365D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 1), 6),
            ('FONTSIZE', (5, 1), (-5, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
        ])
        tabla.setStyle(estilo)
        elementos.append(tabla)

        doc.build(elementos)
        buffer.seek(0)
        response = StreamingHttpResponse(
            iter([buffer.getvalue()]),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = 'attachment; filename="pacientes.pdf"'
        return response

    @classmethod
    def crear_reporte(cls, formato: str, pacientes_qs) -> StreamingHttpResponse:
        fabrica = {
            'csv': cls.export_csv,
            'excel': cls.export_excel,
            'pdf': cls.export_pdf
        }
        return fabrica[formato](pacientes_qs)