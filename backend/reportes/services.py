import io
from typing import Iterator
from django.http import StreamingHttpResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pandas as pd

COLUMNAS_EXPORT = [
    'nombres', 'apellidos', 'edad', 'sexo',
    'peso', 'altura', 'imc', 'presion_sistolica', 'presion_diastolica',
    'frecuencia_cardiaca', 'saturacion_oxigeno', 'temperatura', 'glucosa',
    'colesterol', 'antecedentes_familiares', 'fumador', 'consumo_alcohol',
    'actividad_fisica', 'diagnostico_preliminar', 'riesgo_enfermedad',
    'fecha_consulta', 'critico'
]

HEADERS_ES = {
    'nombres': 'Nombres', 'apellidos': 'Apellidos', 'edad': 'Ed', 'sexo': 'Sx',
    'peso': 'W(kg)', 'altura': 'H(m)', 'imc': 'IMC', 'presion_sistolica': 'PAS', 'presion_diastolica': 'PAD',
    'frecuencia_cardiaca': 'FC', 'saturacion_oxigeno': 'Sat%', 'temperatura': 'T(°C)', 'glucosa': 'Glu',
    'colesterol': 'Col', 'antecedentes_familiares': 'Antc', 'fumador': 'Fum', 'consumo_alcohol': 'Alc',
    'actividad_fisica': 'Act.Física', 'diagnostico_preliminar': 'Diagnóstico Preliminar', 
    'riesgo_enfermedad': 'Riesgo', 'fecha_consulta': 'Fecha', 'critico': 'Crít'
}

class ReportesService:
    
    @staticmethod
    def generar_filas_csv(pacientes_qs) -> Iterator[str]:
        yield ";".join(HEADERS_ES.values()) + "\n"
        
        for p in pacientes_qs:
            fila = [
                f'"{p.nombres}"',
                f'"{p.apellidos}"',
                str(p.edad),
                str(p.sexo),
                str(float(p.peso)),
                str(float(p.altura)),
                str(float(p.imc)),
                str(p.presion_sistolica),
                str(p.presion_diastolica),
                str(p.frecuencia_cardiaca),
                str(float(p.saturacion_oxigeno)),
                str(float(p.temperatura)),
                str(float(p.glucosa)),
                str(float(p.colesterol)),
                'SÍ' if p.antecedentes_familiares else 'NO',
                'SÍ' if p.fumador else 'NO',
                'SÍ' if p.consumo_alcohol else 'NO',
                str(p.actividad_fisica),
                f'"{p.diagnostico_preliminar}"',
                str(p.riesgo_enfermedad),
                p.fecha_consulta.strftime('%Y-%m-%d') if p.fecha_consulta else '',
                'SÍ' if p.critico else 'NO'
            ]
            yield ";".join(fila) + "\n"

    @staticmethod
    def get_dataframe(pacientes_qs) -> pd.DataFrame:
        datos = []
        for p in pacientes_qs:
            datos.append({
                'nombres': p.nombres, 'apellidos': p.apellidos, 'edad': p.edad, 'sexo': p.sexo,
                'peso': float(p.peso), 'altura': float(p.altura), 'imc': float(p.imc), 'presion_sistolica': p.presion_sistolica,
                'presion_diastolica': p.presion_diastolica, 'frecuencia_cardiaca': p.frecuencia_cardiaca,
                'saturacion_oxigeno': float(p.saturacion_oxigeno), 'temperatura': float(p.temperatura), 'glucosa': float(p.glucosa),
                'colesterol': float(p.colesterol), 'antecedentes_familiares': 'SÍ' if p.antecedentes_familiares else 'NO',
                'fumador': 'SÍ' if p.fumador else 'NO', 'consumo_alcohol': 'SÍ' if p.consumo_alcohol else 'NO',
                'actividad_fisica': p.actividad_fisica, 'diagnostico_preliminar': p.diagnostico_preliminar,
                'riesgo_enfermedad': p.riesgo_enfermedad, 'fecha_consulta': p.fecha_consulta.strftime('%Y-%m-%d') if p.fecha_consulta else '',
                'critico': 'SÍ' if p.critico else 'NO'
            })
        return pd.DataFrame(datos, columns=COLUMNAS_EXPORT).rename(columns=HEADERS_ES)

    @staticmethod
    def export_csv(pacientes_qs) -> StreamingHttpResponse:
        response = StreamingHttpResponse(
            ReportesService.generar_filas_csv(pacientes_qs),
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
        response = StreamingHttpResponse(iter([buffer.getvalue()]), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="pacientes.xlsx"'
        return response

    @staticmethod
    def export_pdf(pacientes_qs) -> StreamingHttpResponse:
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=15, leftMargin=15, topMargin=20, bottomMargin=20
        )
        
        styles = getSampleStyleSheet()
        
        style_title = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=16, textColor=colors.HexColor('#1A365D'), alignment=1)
        style_cell = ParagraphStyle('CellStyle', fontName='Helvetica', fontSize=5, leading=6, alignment=1)
        style_header_cell = ParagraphStyle('HeaderStyle', fontName='Helvetica-Bold', fontSize=5.5, leading=7, textColor=colors.whitesmoke, alignment=1)

        elementos = []
        elementos.append(Paragraph('HealthAnalytics IPS - Reporte Clínico Consolidado', style_title))
        elementos.append(Spacer(1, 10))

        data = [[Paragraph(h, style_header_cell) for h in HEADERS_ES.values()]]
        
        for p in pacientes_qs:
            data.append([
                Paragraph(p.nombres, style_cell),
                Paragraph(p.apellidos, style_cell),
                Paragraph(str(p.edad), style_cell),
                Paragraph(p.sexo, style_cell),
                Paragraph(str(float(p.peso)), style_cell),
                Paragraph(str(float(p.altura)), style_cell),
                Paragraph(str(float(p.imc)), style_cell),
                Paragraph(str(p.presion_sistolica), style_cell),
                Paragraph(str(p.presion_diastolica), style_cell),
                Paragraph(str(p.frecuencia_cardiaca), style_cell),
                Paragraph(str(float(p.saturacion_oxigeno)), style_cell),
                Paragraph(str(float(p.temperatura)), style_cell),
                Paragraph(str(float(p.glucosa)), style_cell),
                Paragraph(str(float(p.colesterol)), style_cell),
                Paragraph('SÍ' if p.antecedentes_familiares else 'NO', style_cell),
                Paragraph('SÍ' if p.fumador else 'NO', style_cell),
                Paragraph('SÍ' if p.consumo_alcohol else 'NO', style_cell),
                Paragraph(p.actividad_fisica, style_cell),
                Paragraph(p.diagnostico_preliminar, style_cell),
                Paragraph(p.riesgo_enfermedad, style_cell),
                Paragraph(p.fecha_consulta.strftime('%Y-%m-%d') if p.fecha_consulta else '', style_cell),
                Paragraph('SÍ' if p.critico else 'NO', style_cell)
            ])

        col_widths = [43, 43, 14, 12, 24, 24, 20, 20, 20, 16, 22, 22, 20, 20, 20, 18, 18, 35, 105, 33, 38, 17]
        
        tabla = Table(data, colWidths=col_widths, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A365D')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')])
        ]))
        
        elementos.append(tabla)
        doc.build(elementos)
        
        buffer.seek(0)
        response = StreamingHttpResponse(iter([buffer.getvalue()]), content_type='application/pdf')
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