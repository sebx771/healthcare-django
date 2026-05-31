import os
from datetime import datetime
import logging
import joblib
import pandas as pd
import numpy as np
from django.conf import settings
from sklearn.model_selection import KFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from pacientes.models import Paciente
from ..models import MetricasModelos

logger = logging.getLogger('ml_logger')

class MLTrainerService:

    @classmethod
    def extraer_datos_orm(cls):
        """
        Fase 1: Extracción y Preprocesamiento.
        Trae los datos limpios por el ETL desde SQLite y los adapta numéricamente.
        """
        logger.info(" Iniciando la extracción de registros clínicos desde el ORM...")
   
        # 🛠️ CAMBIO: Se agrega 'actividad_fisica' a la extracción del ORM
        queryset = Paciente.objects.all().values(
            'edad', 'sexo', 'peso', 'altura', 'imc', 
            'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca', 
            'glucosa', 'colesterol', 'saturacion_oxigeno', 'temperatura',
            'antecedentes_familiares', 'fumador', 'consumo_alcohol',
            'actividad_fisica', 'riesgo_enfermedad' 
        )
        
        if not queryset.exists():
            logger.error("❌ ERROR CRÍTICO: La tabla de pacientes está vacía. Es obligatorio correr el ETL primero.")
            raise ValueError("No hay datos en la base de datos para entrenar el modelo.")
            
        df = pd.DataFrame(list(queryset))
        logger.info(f"📊 Dataset cargado en memoria exitosamente: {len(df)} registros para preprocesar.")
        
        # --- PREPROCESAMIENTO OBLIGATORIO ---
        df['sexo'] = df['sexo'].map({'M': 1, 'F': 0}).fillna(0).astype(int)
        df['antecedentes_familiares'] = df['antecedentes_familiares'].astype(int)
        df['fumador'] = df['fumador'].astype(int)
        df['consumo_alcohol'] = df['consumo_alcohol'].astype(int)
        
        # 🛠️ CAMBIO: Mapeo numérico estricto para codificar la columna 'actividad_fisica'
        mapeo_actividad = {'Sedentario': 0, 'Moderado': 1, 'Activo': 2}
        df['actividad_fisica'] = df['actividad_fisica'].map(mapeo_actividad).fillna(0).astype(int)
        
        # --- MAPEO DEL TARGET COMPLETAMENTE ALINEADO ---
        s_target_limpio = (
            df['riesgo_enfermedad'].astype(str)
            .str.strip()
            .str.lower()
            .str.replace('ítico', 'itico', regex=False)
        )
        
        mapeo_riesgo = {
            'bajo': 0,
            'medio': 1,
            'alto': 2,
            'critico': 3
        }
        
        df['target'] = s_target_limpio.map(mapeo_riesgo)
        
        valores_nulos = df['target'].isna().sum()
        if valores_nulos > 0:
            logger.warning(f"⚠️ Alerta: Se detectaron {valores_nulos} registros con riesgo no reconocido. Imputando con la moda.")
            df['target'] = df['target'].fillna(df['target'].mode()[0])
            
        df['target'] = df['target'].astype(int)

        # CAMBIO: Al dropear las columnas del target, 'actividad_fisica' ahora se preserva en X como float
        X = df.drop(columns=['riesgo_enfermedad', 'target']).astype(float)
        y = df['target']
        
        logger.info("✅ Preprocesamiento completado de forma limpia. Variables codificadas numéricamente.")
        return X, y

    @classmethod
    def ejecutar_kfold_y_entrenar(cls):
        """
        Fase 2: Evaluación científica por K-Fold y serialización binaria del Bosque.
        """
        try:
            X, y = cls.extraer_datos_orm()
            
            logger.info("🚀 Iniciando Validación Cruzada K-Fold (K=5 pliegues)...")
            kf = KFold(n_splits=5, shuffle=True, random_state=42)
            
            acc_list, prec_list, rec_list, f1_list = [], [], [], []
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            
            for iteracion, (train_idx, test_idx) in enumerate(kf.split(X), 1):
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
                
                model.fit(X_train, y_train)
                preds = model.predict(X_test)
                
                acc = accuracy_score(y_test, preds)
                prec = precision_score(y_test, preds, average='weighted', zero_division=0)
                rec = recall_score(y_test, preds, average='weighted', zero_division=0)
                f1 = f1_score(y_test, preds, average='weighted', zero_division=0)
                
                acc_list.append(acc)
                prec_list.append(prec)
                rec_list.append(rec)
                f1_list.append(f1)
                
                logger.info(f"🌲 Pliegue {iteracion}/5 completado -> Acc: {acc:.4f} | Recall: {rec:.4f}")
            
            final_acc = float(np.mean(acc_list))
            final_prec = float(np.mean(prec_list))
            final_rec = float(np.mean(rec_list))
            final_f1 = float(np.mean(f1_list))
            
            logger.info("📊 --- PROMEDIOS FINALES DEL K-FOLD VALIDADOS ---")
            logger.info(f"Accuracy: {final_acc:.4f} | Precision: {final_prec:.4f} | Recall: {final_rec:.4f} | F1-Score: {final_f1:.4f}")
            
            logger.info("🎯 Entrenando modelo definitivo con el 100% de la data clínica persistida...")
            model.fit(X, y)
            preds_totales = model.predict(X)
            matriz = confusion_matrix(y, preds_totales)
            
            dir_modelos = os.path.join(settings.BASE_DIR, 'ml', 'saved_models')
            os.makedirs(dir_modelos, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_versionado = f"modelo_riesgo_rf_{timestamp}.joblib"
            ruta_final_joblib = os.path.join(dir_modelos, nombre_versionado)
            
            joblib.dump(model, ruta_final_joblib)
            logger.info(f"💾 Archivo binario serializado con éxito en: {ruta_final_joblib}")
            
            logger.info("🗄️ Almacenando informe analítico e histórico de métricas en la base de datos...")
            MetricasModelos.objects.create(
                nombre_modelo=f"RandomForestClassifier (K-Fold=5) {timestamp}",
                accuracy=final_acc,
                precision=final_prec,
                recall=final_rec,
                f1_score=final_f1,
                matriz_confusion=np.array2string(matriz),
                ruta_archivo_joblib=ruta_final_joblib
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ ERROR CRÍTICO EN EL MOTOR DE MACHINE LEARNING: {str(e)}", exc_info=True)
            return False