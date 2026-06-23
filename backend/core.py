"""
backend/core.py — Motor de cálculo del Sistema de Cobro Musical (sin Streamlit).

Contiene la MISMA lógica de negocio que la versión original en `app.py`
(clase MusicianPaymentSystem). La matemática y el flujo de los cálculos se han
mantenido idénticos byte a byte.

Cambios respecto a la versión Streamlit (solo capa de presentación/estado):
  - El estado que vivía en `st.session_state` (original_weights, editing_weights,
    band_retention_config) ahora son atributos de instancia.
  - Los mensajes `st.error/warning/info/success` se acumulan en `self.messages`
    (lista de dicts {level, text}) en vez de pintarse en pantalla.
  - Las llamadas de presentación (st.metric, st.dataframe, ...) se han eliminado:
    esos datos los devuelven los métodos para que el frontend los renderice.

Las fórmulas de reparto, penalizaciones, retención de banda y los pasos de
`process_payments` son idénticas al original.
"""

import pandas as pd
import numpy as np


class MusicianPaymentSystem:
    def __init__(self, data_path=None):
        self.data_path = data_path
        self.asistencia_df = None
        self.presupuesto_df = None
        self.configuracion_df = None
        self.band_retention_df = None

        # Estado que antes vivía en st.session_state
        self.original_weights = None
        self.editing_weights = None
        self.band_retention_config = None

        # Mensajes acumulados (sustituyen a st.error/warning/info/success)
        self.messages = []

        # Cache del último procesamiento (para la descarga de Excel)
        self.last_results = None

    # ------------------------------------------------------------------
    # Utilidades de mensajes (sustituyen st.error / st.warning / ...)
    # ------------------------------------------------------------------
    def _msg(self, level, text):
        self.messages.append({"level": level, "text": str(text)})

    def reset_messages(self):
        self.messages = []

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------
    def load_from_uploaded_file(self, uploaded_file):
        """Carga datos desde un Excel subido, con detección dinámica de hojas.

        `uploaded_file` puede ser una ruta o un buffer (BytesIO).
        """
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            available_sheets = excel_file.sheet_names

            self._msg("info", f"📋 Hojas encontradas en el archivo: {', '.join(available_sheets)}")

            asistencia_sheet = self._find_sheet_by_patterns(available_sheets, ["Asistencia", "asistencia", "Attendance", "attendance"])
            presupuesto_sheet = self._find_sheet_by_patterns(available_sheets, ["Presupuesto", "presupuesto", "Budget", "budget"])
            configuracion_sheet = self._find_sheet_by_patterns(available_sheets, ["Configuracion_Precios", "configuracion_precios", "Configuracion", "configuracion", "Prices", "prices", "Config", "config"])

            if not asistencia_sheet:
                self._msg("error", "❌ No se encontró hoja de Asistencia. Nombres esperados: Asistencia, asistencia, Attendance, attendance")
                return False

            if not presupuesto_sheet:
                self._msg("error", "❌ No se encontró hoja de Presupuesto. Nombres esperados: Presupuesto, presupuesto, Budget, budget")
                return False

            if not configuracion_sheet:
                self._msg("error", "❌ No se encontró hoja de Configuración de Precios. Nombres esperados: Configuracion_Precios, Configuracion, Config, etc.")
                return False

            self._msg("success", f"✅ Hojas identificadas: {asistencia_sheet}, {presupuesto_sheet}, {configuracion_sheet}")

            self.asistencia_df = pd.read_excel(uploaded_file, sheet_name=asistencia_sheet)
            self.presupuesto_df = pd.read_excel(uploaded_file, sheet_name=presupuesto_sheet)
            self.configuracion_df = pd.read_excel(uploaded_file, sheet_name=configuracion_sheet)

            if not self._validate_and_clean_data_structure():
                return False

            self._validate_data_consistency()

            # Actualizar pesos originales (antes: st.session_state.original_weights)
            self.original_weights = self.configuracion_df.copy()

            # Inicializar pesos de edición (antes se hacía perezosamente en la página)
            self.editing_weights = self.configuracion_df.copy()
            for col in ['A', 'B', 'C', 'D', 'E']:
                if col in self.editing_weights.columns:
                    self.editing_weights[col] = self.editing_weights[col].astype(float)

            # Inicializar datos de retención de banda
            self._initialize_band_retention()

            return True

        except Exception as e:
            self._msg("error", f"Error loading uploaded file: {str(e)}")
            return False

    def _find_sheet_by_patterns(self, available_sheets, patterns):
        """Find sheet name that matches any of the given patterns"""
        for pattern in patterns:
            for sheet in available_sheets:
                if pattern.lower() in sheet.lower():
                    return sheet
        return None

    def _validate_and_clean_data_structure(self):
        """Validate and clean the structure of loaded data"""
        try:
            required_asistencia_cols = ['Nombre', 'Apellidos', 'Instrumento', 'Categoria']
            missing_cols = [col for col in required_asistencia_cols if col not in self.asistencia_df.columns]

            if missing_cols:
                self._msg("error", f"❌ Columnas faltantes en hoja de Asistencia: {missing_cols}")
                self._msg("info", "💡 Columnas requeridas: Nombre, Apellidos, Instrumento, Categoria")
                return False

            if 'ACTES' not in self.presupuesto_df.columns:
                self._msg("error", "❌ Columna 'ACTES' faltante en hoja de Presupuesto")
                return False

            budget_cols = []
            for col in self.presupuesto_df.columns:
                if any(word in col.upper() for word in ['REPARTIR', 'BUDGET', 'TOTAL', 'AMOUNT']):
                    budget_cols.append(col)

            if not budget_cols:
                possible_budget_cols = [col for col in self.presupuesto_df.columns if col.upper() in ['A REPARTIR', 'TOTAL', 'AMOUNT', 'BUDGET']]
                if not possible_budget_cols:
                    self._msg("error", "❌ No se encontró columna de presupuesto. Busque columnas como 'A REPARTIR', 'TOTAL', 'BUDGET'")
                    return False
                budget_cols = possible_budget_cols

            self._msg("info", f"💰 Columnas de presupuesto detectadas: {', '.join(budget_cols)}")

            if 'ACTES' not in self.configuracion_df.columns:
                self._msg("error", "❌ Columna 'ACTES' faltante en hoja de Configuración")
                return False

            category_cols = [col for col in self.configuracion_df.columns if col in ['A', 'B', 'C', 'D', 'E']]

            if len(category_cols) == 0:
                self._msg("error", "❌ No se encontraron columnas de categorías (A, B, C, D, E) en la configuración")
                return False

            self._msg("info", f"🏷️ Categorías detectadas: {', '.join(category_cols)}")

            self._clean_data()

            return True

        except Exception as e:
            self._msg("error", f"Error validating data structure: {str(e)}")
            return False

    def _clean_data(self):
        """Clean and standardize the loaded data"""
        try:
            self.asistencia_df['Nombre'] = self.asistencia_df['Nombre'].astype(str).str.strip()
            self.asistencia_df['Apellidos'] = self.asistencia_df['Apellidos'].astype(str).str.strip()

            self.asistencia_df['Categoria'] = self.asistencia_df['Categoria'].astype(str).str.upper().str.strip()

            if 'ACTES' in self.presupuesto_df.columns:
                self.presupuesto_df['ACTES'] = self.presupuesto_df['ACTES'].astype(str).str.strip()

            if 'ACTES' in self.configuracion_df.columns:
                self.configuracion_df['ACTES'] = self.configuracion_df['ACTES'].astype(str).str.strip()

            event_columns = self.get_events_list()
            for event in event_columns:
                self.asistencia_df[event] = pd.to_numeric(self.asistencia_df[event], errors='coerce').fillna(0)
                self.asistencia_df[event] = self.asistencia_df[event].apply(lambda x: 1 if x > 0 else 0)

            self._msg("success", "✅ Datos limpiados y estandarizados")

        except Exception as e:
            self._msg("warning", f"⚠️ Advertencia en limpieza de datos: {str(e)}")

    def get_data_summary(self):
        """Devuelve el resumen de los datos cargados (antes _show_data_summary)."""
        try:
            total_budget = self.presupuesto_df.select_dtypes(include=[np.number]).sum().sum()
            events = self.get_events_list()
            category_counts = self.asistencia_df['Categoria'].value_counts()
            return {
                "total_musicos": int(len(self.asistencia_df)),
                "total_actos": int(len(events)),
                "presupuesto_total": float(total_budget),
                "categorias": {str(k): int(v) for k, v in category_counts.to_dict().items()},
                "primeros_actos": events[:10],
                "actos_restantes": max(0, len(events) - 10),
            }
        except Exception as e:
            self._msg("warning", f"Error mostrando resumen: {str(e)}")
            return {}

    def _validate_data_consistency(self):
        """Validate that all sheets have consistent event data"""
        try:
            asistencia_events = set(self.get_events_list())
            presupuesto_events = set(self.presupuesto_df['ACTES'].values)
            configuracion_events = set(self.configuracion_df['ACTES'].values)

            missing_in_presupuesto = asistencia_events - presupuesto_events
            missing_in_configuracion = asistencia_events - configuracion_events
            extra_in_presupuesto = presupuesto_events - asistencia_events
            extra_in_configuracion = configuracion_events - asistencia_events

            if missing_in_presupuesto:
                self._msg("warning", f"⚠️ Eventos en Asistencia pero faltantes en Presupuesto: {missing_in_presupuesto}")

            if missing_in_configuracion:
                self._msg("warning", f"⚠️ Eventos en Asistencia pero faltantes en Configuracion_Precios: {missing_in_configuracion}")

            if extra_in_presupuesto:
                self._msg("warning", f"⚠️ Eventos en Presupuesto pero faltantes en Asistencia: {extra_in_presupuesto}")

            if extra_in_configuracion:
                self._msg("warning", f"⚠️ Eventos en Configuracion_Precios pero faltantes en Asistencia: {extra_in_configuracion}")

            if not (missing_in_presupuesto or missing_in_configuracion or extra_in_presupuesto or extra_in_configuracion):
                self._msg("success", f"✅ Datos consistentes: {len(asistencia_events)} eventos encontrados en todas las hojas")

        except Exception as e:
            self._msg("error", f"Error validating data consistency: {str(e)}")

    def get_events_list(self):
        """Get list of events from attendance data"""
        if self.asistencia_df is None:
            return []
        return [col for col in self.asistencia_df.columns if col not in ['Nombre', 'Apellidos', 'Instrumento', 'Categoria']]

    def _initialize_band_retention(self):
        """Initialize band retention data structure"""
        try:
            events = self.get_events_list()
            if events:
                self.band_retention_df = pd.DataFrame({
                    'ACTES': events,
                    'BANDA_PORCENTAJE': [0.0] * len(events),
                    'DESCRIPCION': ['Sin retención'] * len(events)
                })

                if self.band_retention_config is None:
                    self.band_retention_config = self.band_retention_df.copy()
                else:
                    existing_events = set(self.band_retention_config['ACTES'].values)
                    new_events = [e for e in events if e not in existing_events]
                    if new_events:
                        new_rows = pd.DataFrame({
                            'ACTES': new_events,
                            'BANDA_PORCENTAJE': [0.0] * len(new_events),
                            'DESCRIPCION': ['Sin retención'] * len(new_events)
                        })
                        self.band_retention_config = pd.concat([
                            self.band_retention_config, new_rows
                        ], ignore_index=True)

                    self.band_retention_df = self.band_retention_config.copy()

            else:
                self.band_retention_df = pd.DataFrame(columns=['ACTES', 'BANDA_PORCENTAJE', 'DESCRIPCION'])

        except Exception as e:
            self._msg("warning", f"Error inicializando configuración de retención: {str(e)}")
            self.band_retention_df = pd.DataFrame(columns=['ACTES', 'BANDA_PORCENTAJE', 'DESCRIPCION'])

    def get_band_retention_for_event(self, event_name):
        """Get band retention percentage for a specific event"""
        if self.band_retention_df is None or self.band_retention_df.empty:
            return 0.0

        retention_row = self.band_retention_df[self.band_retention_df['ACTES'] == event_name]
        if not retention_row.empty:
            return float(retention_row.iloc[0]['BANDA_PORCENTAJE'])
        return 0.0

    def get_musicians_by_category(self, event):
        """Get count and names of musicians by category for an event"""
        if self.asistencia_df is None or event not in self.asistencia_df.columns:
            return pd.DataFrame()
        attended = self.asistencia_df[self.asistencia_df[event] == 1]
        category_counts = attended.groupby('Categoria').agg({
            'Nombre': 'count',
            'Apellidos': lambda x: list(zip(attended.loc[x.index, 'Nombre'], attended.loc[x.index, 'Apellidos']))
        }).rename(columns={'Nombre': 'Count', 'Apellidos': 'Musicians'})
        return category_counts

    def calculate_budget_difference(self):
        """Calculate difference between budget and distributed amount in real time"""
        try:
            if self.asistencia_df is None or self.presupuesto_df is None or self.configuracion_df is None:
                return 0, 0, 0

            # Pesos actuales (antes: st.session_state.get('editing_weights', ...))
            current_weights = self.editing_weights
            if current_weights is None:
                current_weights = self.configuracion_df if self.configuracion_df is not None else self.original_weights
            if current_weights is None or current_weights.empty:
                return 0, 0, 0

            total_budget = self.presupuesto_df['A REPARTIR'].sum()

            total_distributed = 0

            for _, event_row in self.presupuesto_df.iterrows():
                event_name = event_row['ACTES']
                if event_name in self.asistencia_df.columns:
                    event_attendees = self.asistencia_df[self.asistencia_df[event_name] == 1]
                    total_attendees = len(event_attendees)

                    if total_attendees > 0:
                        original_amount = event_row['A REPARTIR']
                        retention_percentage = self.get_band_retention_for_event(event_name)
                        net_amount = original_amount * (1 - retention_percentage / 100)

                        weight_row = current_weights[current_weights['ACTES'] == event_name]
                        if not weight_row.empty:
                            weight_row = weight_row.iloc[0]

                            for _, attendee in event_attendees.iterrows():
                                category = attendee['Categoria']
                                if category in weight_row:
                                    ponderacion = weight_row[category]
                                    payment = (net_amount / total_attendees) * ponderacion
                                    total_distributed += payment

            difference = total_budget - total_distributed
            return total_budget, total_distributed, difference

        except Exception as e:
            self._msg("error", f"Error calculating budget difference: {str(e)}")
            return 0, 0, 0

    def process_payments(self, penalty_criteria="manual", fixed_penalty_amount=0, category_penalties=None):
        """Process all payment calculations according to requirements"""
        if self.asistencia_df is None or self.presupuesto_df is None or self.configuracion_df is None:
            self._msg("error", "No hay datos cargados. Por favor, carga un archivo Excel primero.")
            return None
        try:
            # 1. Transform attendance table to long format
            id_vars = ['Nombre', 'Apellidos', 'Instrumento', 'Categoria']
            attendance_long = pd.melt(
                self.asistencia_df,
                id_vars=id_vars,
                var_name='Acto',
                value_name='Asistencia'
            )

            # 2. Normalize column names and values
            attendance_long['Musico'] = attendance_long['Nombre'] + ' ' + attendance_long['Apellidos']

            # 3. Join with budget - ENSURE ALL EVENTS ARE PROCESSED
            attendance_budget = attendance_long.merge(
                self.presupuesto_df,
                left_on='Acto',
                right_on='ACTES',
                how='left'
            )

            events_without_budget = attendance_budget[attendance_budget['ACTES'].isna()]['Acto'].unique()
            if len(events_without_budget) > 0:
                print(f"WARNING: Events without budget data: {events_without_budget}")

            # 4. Join with weights - ENSURE ALL EVENTS ARE PROCESSED
            attendance_weights = attendance_budget.merge(
                self.configuracion_df,
                left_on='Acto',
                right_on='ACTES',
                how='left',
                suffixes=('', '_config')
            )

            events_without_config = attendance_weights[attendance_weights['ACTES_config'].isna()]['Acto'].unique()
            if len(events_without_config) > 0:
                print(f"WARNING: Events without configuration data: {events_without_config}")

            events_with_complete_data = []
            events_with_missing_data = []

            for event_name in self.get_events_list():
                has_budget = event_name in self.presupuesto_df['ACTES'].values
                has_config = event_name in self.configuracion_df['ACTES'].values

                if has_budget and has_config:
                    events_with_complete_data.append(event_name)
                else:
                    events_with_missing_data.append({
                        'event': event_name,
                        'has_budget': has_budget,
                        'has_config': has_config
                    })

            if events_with_missing_data:
                print(f"Events with incomplete data (will be skipped from payment calculations):")
                for item in events_with_missing_data:
                    print(f"  - {item['event']}: Budget={item['has_budget']}, Config={item['has_config']}")

            print(f"Events with complete data for processing: {len(events_with_complete_data)}")

            # Only keep rows with complete data for payment calculation
            attendance_weights = attendance_weights.dropna(subset=['A REPARTIR', 'A', 'B', 'C', 'D', 'E'])

            # 5. Filter attendees only
            attendees = attendance_weights[attendance_weights['Asistencia'] == 1].copy()

            # 6. Calculate total attendees per event
            attendees_per_event = attendees.groupby('Acto')['Musico'].count().reset_index()
            attendees_per_event.columns = ['Acto', 'total_asistentes']

            attendees = attendees.merge(attendees_per_event, on='Acto')

            # 7. Get ponderacion based on category - FIXED FORMULA
            def get_ponderacion(row):
                category = row['Categoria']
                if category in ['A', 'B', 'C', 'D', 'E']:
                    return row[category]
                return 1.0

            attendees['ponderacion'] = attendees.apply(get_ponderacion, axis=1)

            # 8. Apply band retention before calculating individual payments
            def apply_band_retention(row):
                event_name = row['Acto']
                original_amount = row['A REPARTIR']
                retention_percentage = self.get_band_retention_for_event(event_name)
                net_amount = original_amount * (1 - retention_percentage / 100)
                return net_amount

            attendees['A_REPARTIR_NETO'] = attendees.apply(apply_band_retention, axis=1)
            attendees['BANDA_RETENCION_PCT'] = attendees['Acto'].apply(lambda x: self.get_band_retention_for_event(x))
            attendees['BANDA_RETENCION_AMOUNT'] = attendees['A REPARTIR'] - attendees['A_REPARTIR_NETO']

            # 9. Calculate individual payment using net amount after band retention
            attendees['Importe_Individual'] = (attendees['A_REPARTIR_NETO'] / attendees['total_asistentes']) * attendees['ponderacion']

            # 10. Generate total summary per musician
            musician_summary = attendees.groupby('Musico').agg({
                'Importe_Individual': 'sum',
                'Categoria': 'first',
                'Instrumento': 'first',
                'Nombre': 'first',
                'Apellidos': 'first'
            }).reset_index()

            # 11. Create payment pivot by event
            payment_pivot = attendees.pivot_table(
                index='Musico',
                columns='Acto',
                values='Importe_Individual',
                fill_value=0
            )

            original_events_order = self.get_events_list()

            for event in original_events_order:
                if event not in payment_pivot.columns:
                    payment_pivot[event] = 0.0

            payment_pivot = payment_pivot.reindex(columns=original_events_order)

            # 12. Create attendance pivot by event
            attendance_pivot = self.asistencia_df.set_index(['Nombre', 'Apellidos', 'Instrumento', 'Categoria'])

            # 13. Detect official events (those with "OFICIAL" in name)
            official_events = [col for col in self.get_events_list() if 'OFICIAL' in col.upper()]

            # 14. Count missed official events per musician - FIXED INDEX ISSUE
            musician_summary = musician_summary.reset_index(drop=True)

            if official_events:
                missed_counts = {}
                for _, row in self.asistencia_df.iterrows():
                    full_name = f"{row['Nombre']} {row['Apellidos']}"
                    missed_count = sum(row[event] == 0 for event in official_events if event in row.index)
                    missed_counts[full_name] = missed_count

                musician_summary['Actos_Oficiales_No_Asistidos'] = musician_summary['Musico'].map(missed_counts).fillna(0)
            else:
                musician_summary['Actos_Oficiales_No_Asistidos'] = 0

            # 15. Apply penalty for missed official events
            if penalty_criteria != "manual":
                musician_summary = self._apply_official_event_penalties(
                    musician_summary, penalty_criteria, fixed_penalty_amount, category_penalties
                )

            # 16. Filter musicians with earnings > 0
            musician_summary = musician_summary[musician_summary['Importe_Individual'] > 0]

            # 17. Calculate actual distributed amount per event
            actual_distributed = attendees.groupby('Acto')['Importe_Individual'].sum().reset_index()
            actual_distributed.columns = ['Acto', 'Distribuido_Real']

            # 18. Compare budget vs actual distribution (including band retention)
            budget_comparison = self.presupuesto_df.merge(actual_distributed, left_on='ACTES', right_on='Acto', how='left')
            budget_comparison['Distribuido_Real'] = budget_comparison['Distribuido_Real'].fillna(0)

            budget_comparison['Banda_Retencion_PCT'] = budget_comparison['ACTES'].apply(lambda x: self.get_band_retention_for_event(x))
            budget_comparison['Banda_Retencion_Amount'] = budget_comparison['A REPARTIR'] * (budget_comparison['Banda_Retencion_PCT'] / 100)
            budget_comparison['Neto_Para_Musicos'] = budget_comparison['A REPARTIR'] - budget_comparison['Banda_Retencion_Amount']
            budget_comparison['Diferencia'] = budget_comparison['Neto_Para_Musicos'] - budget_comparison['Distribuido_Real']

            # 19. Count musicians by category and event
            musicians_by_category = attendees.groupby(['Acto', 'Categoria']).size().reset_index(name='Cantidad_Musicos')

            # 20. Calculate total band retention summary
            total_band_retention = attendees['BANDA_RETENCION_AMOUNT'].sum() if not attendees.empty else 0

            return {
                'musician_summary': musician_summary,
                'payment_pivot': payment_pivot,
                'attendance_pivot': attendance_pivot,
                'budget_comparison': budget_comparison,
                'musicians_by_category': musicians_by_category,
                'attendees_detail': attendees,
                'total_band_retention': total_band_retention
            }

        except Exception as e:
            self._msg("error", f"Error processing payments: {str(e)}")
            return None

    def _apply_official_event_penalties(self, musician_summary, penalty_criteria, fixed_penalty_amount, category_penalties=None):
        """Apply penalties for missed official events"""
        try:
            result_summary = musician_summary.copy()

            result_summary['Penalizacion_Total'] = 0.0
            result_summary['Importe_Final'] = result_summary['Importe_Individual']

            for idx, musician in result_summary.iterrows():
                missed_official_events = musician['Actos_Oficiales_No_Asistidos']

                if missed_official_events > 0:
                    if penalty_criteria == "fixed":
                        if category_penalties and musician['Categoria'] in category_penalties:
                            penalty = missed_official_events * category_penalties[musician['Categoria']]
                        else:
                            penalty = missed_official_events * fixed_penalty_amount

                    elif penalty_criteria == "average":
                        musician_name = musician['Musico']

                        attended_events = 0
                        for event in self.get_events_list():
                            if event in self.asistencia_df.columns:
                                musician_row = self.asistencia_df[
                                    (self.asistencia_df['Nombre'] + ' ' + self.asistencia_df['Apellidos']) == musician_name
                                ]
                                if not musician_row.empty and musician_row.iloc[0][event] == 1:
                                    attended_events += 1

                        if attended_events > 0:
                            average_per_event = musician['Importe_Individual'] / attended_events
                            penalty = missed_official_events * average_per_event
                        else:
                            penalty = 0
                    else:
                        penalty = 0

                    result_summary.at[idx, 'Penalizacion_Total'] = penalty
                    result_summary.at[idx, 'Importe_Final'] = max(0, musician['Importe_Individual'] - penalty)
                else:
                    result_summary.at[idx, 'Importe_Final'] = musician['Importe_Individual']

            return result_summary

        except Exception as e:
            self._msg("error", f"Error applying penalties: {str(e)}")
            return musician_summary

    # ------------------------------------------------------------------
    # Operaciones que en Streamlit vivían en la capa de UI (mismo cálculo)
    # ------------------------------------------------------------------
    def set_weights(self, rows):
        """Actualiza editing_weights desde filas editadas en el frontend.

        `rows`: lista de dicts con ACTES, A, B, C, D, E. Mantiene el orden y
        los ACTES existentes (igual que el data_editor con num_rows='fixed').
        """
        df = self.editing_weights.copy()
        by_acto = {r['ACTES']: r for r in rows}
        for col in ['A', 'B', 'C', 'D', 'E']:
            if col in df.columns:
                df[col] = df.apply(
                    lambda row: float(by_acto.get(row['ACTES'], {}).get(col, row[col]))
                    if row['ACTES'] in by_acto else float(row[col]),
                    axis=1,
                )
        self.editing_weights = df.copy()
        self.configuracion_df = df.copy()
        return df

    def save_weights(self):
        self.configuracion_df = self.editing_weights.copy()

    def restore_weights(self):
        self.editing_weights = self.original_weights.copy()
        for col in ['A', 'B', 'C', 'D', 'E']:
            if col in self.editing_weights.columns:
                self.editing_weights[col] = self.editing_weights[col].astype(float)
        self.configuracion_df = self.original_weights.copy()

    def apply_auto_ponderacion(self, eventos_a_recalcular, decimales=4):
        """Recalcula la ponderación A automáticamente (idéntico a _aplicar_auto_pond).

        Devuelve (cambios, saltados).
        """
        from Igualar_Precios import calcular_ponderaciones_automaticas

        cat_cols = ['A', 'B', 'C', 'D', 'E']
        df_pond_idx = self.editing_weights.copy().set_index('ACTES')
        resultados = calcular_ponderaciones_automaticas(
            df_asistencia=self.asistencia_df,
            df_ponderaciones=df_pond_idx,
            eventos=eventos_a_recalcular,
            categoria_col="Categoria",
            decimales=decimales,
        )

        cambios = []
        saltados = []
        df_new = self.editing_weights.copy()
        for evento, info in resultados.items():
            if info.get("skipped"):
                saltados.append({"Acto": evento, "Motivo": info.get("reason", "")})
                continue
            mask = df_new['ACTES'] == evento
            if mask.any():
                df_new.loc[mask, 'A'] = info["A_nuevo"]
                df_new.loc[mask, 'B'] = info["B"]
                df_new.loc[mask, 'C'] = info["C"]
                df_new.loc[mask, 'D'] = info["D"]
                df_new.loc[mask, 'E'] = info["E"]

                a_repartir = 0.0
                bp_row = self.presupuesto_df[self.presupuesto_df['ACTES'] == evento]
                if not bp_row.empty:
                    a_repartir = float(bp_row.iloc[0]['A REPARTIR'])
                retention_pct = self.get_band_retention_for_event(evento)
                neto = a_repartir * (1 - retention_pct / 100)

                suma_pond = (
                    info["n_A"] * info["A_nuevo"]
                    + info["n_B"] * info["B"]
                    + info["n_C"] * info["C"]
                    + info["n_D"] * info["D"]
                    + info["n_E"] * info["E"]
                )
                total_repartido = (neto / info["N_total"]) * suma_pond if info["N_total"] else 0.0
                diff_eur = neto - total_repartido

                cambios.append({
                    "Acto": evento,
                    "A anterior": info["A_anterior"],
                    "A nuevo": info["A_nuevo"],
                    "B": info["B"],
                    "Asistentes": info["N_total"],
                    "Neto (€)": neto,
                    "Total Repartido (€)": total_repartido,
                    "Diff (€)": diff_eur,
                })

        for c in cat_cols:
            df_new[c] = df_new[c].astype(float)
        self.editing_weights = df_new
        self.configuracion_df = df_new.copy()
        return cambios, saltados

    def get_non_official_events(self):
        """Actos no oficiales según la suma de ponderaciones (igual que la UI)."""
        weights_df = self.editing_weights
        cat_cols = ['A', 'B', 'C', 'D', 'E']
        non_official_mask = (weights_df[cat_cols].fillna(0).sum(axis=1) > 0)
        return weights_df.loc[non_official_mask, 'ACTES'].tolist()

    def apply_equalize_budgets(self, selected_events, target_total_budget):
        """Iguala presupuestos (idéntico al bloque de la pestaña de igualar)."""
        from Igualar_Precios import calcular_presupuestos_iguales

        df_pond_for_calc = self.editing_weights.copy()
        if 'ACTES' in df_pond_for_calc.columns:
            df_pond_for_calc.set_index('ACTES', inplace=True)

        new_budgets, valor_unitario = calcular_presupuestos_iguales(
            df_asistencia=self.asistencia_df,
            df_ponderaciones=df_pond_for_calc,
            eventos=selected_events,
            categorias=['A', 'B', 'C', 'D', 'E'],
            presupuesto_total_max=target_total_budget,
            categoria_col="Categoria",
        )

        changes_log = []
        for event, new_amount in new_budgets.items():
            mask = self.presupuesto_df['ACTES'] == event
            if mask.any():
                old_amount = self.presupuesto_df.loc[mask, 'A REPARTIR'].values[0]
                self.presupuesto_df.loc[mask, 'A REPARTIR'] = new_amount
                changes_log.append({
                    "Acto": event,
                    "Anterior": float(old_amount),
                    "Nuevo": float(new_amount),
                    "Cambio": float(new_amount - old_amount),
                })

        return changes_log, float(valor_unitario)

    def get_default_budget_sum(self, selected_events):
        if not selected_events:
            return 0.0
        current_budgets = self.presupuesto_df[self.presupuesto_df['ACTES'].isin(selected_events)]
        return float(current_budgets['A REPARTIR'].sum())

    def compute_budget_comparison_preview(self):
        """Comparación presupuestaria en tiempo real (idéntica a la vista previa)."""
        budget_comparison_df = self.presupuesto_df.copy()
        budget_comparison_df['Banda_Retencion_PCT'] = 0.0
        budget_comparison_df['Banda_Retencion_Amount'] = 0.0
        budget_comparison_df['Neto_Para_Musicos'] = budget_comparison_df['A REPARTIR']
        budget_comparison_df['Total Repartido'] = 0.0

        current_weights = self.editing_weights
        for idx, row in budget_comparison_df.iterrows():
            event_name = row['ACTES']
            retention_percentage = self.get_band_retention_for_event(event_name)
            retention_amount = row['A REPARTIR'] * (retention_percentage / 100)
            net_amount = row['A REPARTIR'] - retention_amount

            budget_comparison_df.at[idx, 'Banda_Retencion_PCT'] = retention_percentage
            budget_comparison_df.at[idx, 'Banda_Retencion_Amount'] = retention_amount
            budget_comparison_df.at[idx, 'Neto_Para_Musicos'] = net_amount

            if event_name in self.asistencia_df.columns:
                event_attendees = self.asistencia_df[self.asistencia_df[event_name] == 1]
                total_attendees = len(event_attendees)
                if total_attendees > 0:
                    weight_row = current_weights[current_weights['ACTES'] == event_name]
                    if not weight_row.empty:
                        weight_row = weight_row.iloc[0]
                        total_event_payment = 0
                        for _, attendee in event_attendees.iterrows():
                            category = attendee['Categoria']
                            if category in ['A', 'B', 'C', 'D', 'E'] and category in weight_row:
                                ponderacion = weight_row[category]
                                payment = (net_amount / total_attendees) * ponderacion
                                total_event_payment += payment
                        budget_comparison_df.at[idx, 'Total Repartido'] = total_event_payment

        budget_comparison_df['Diferencia_Neto'] = (
            budget_comparison_df['Neto_Para_Musicos'] - budget_comparison_df['Total Repartido']
        )
        return budget_comparison_df

    def compute_earnings_by_category(self):
        """Ganancias por categoría (idéntico a la pestaña de la vista previa)."""
        earnings_data = []
        current_weights = self.editing_weights

        for _, event_row in self.presupuesto_df.iterrows():
            event_name = event_row['ACTES']
            retention_percentage = self.get_band_retention_for_event(event_name)
            original_amount = event_row['A REPARTIR']
            net_amount = original_amount * (1 - retention_percentage / 100)

            if event_name in self.asistencia_df.columns:
                event_attendees = self.asistencia_df[self.asistencia_df[event_name] == 1]
                total_attendees = len(event_attendees)
                weight_row = current_weights[current_weights['ACTES'] == event_name]

                if not weight_row.empty:
                    weight_row = weight_row.iloc[0]
                    event_earnings = {
                        'Acto': event_name,
                        'Original': original_amount,
                        'Retención %': retention_percentage,
                        'Neto': net_amount,
                    }
                    for category in ['A', 'B', 'C', 'D', 'E']:
                        if category in weight_row and total_attendees > 0:
                            ponderacion = float(weight_row[category])
                            event_earnings[category] = (net_amount / total_attendees) * ponderacion
                        else:
                            event_earnings[category] = 0.0
                    earnings_data.append(event_earnings)

        return earnings_data

    # ------------------------------------------------------------------
    # Retención de banda (página de configuración)
    # ------------------------------------------------------------------
    def set_band_retention(self, rows):
        """Actualiza la config de retención desde filas editadas en el frontend."""
        df = self.band_retention_config.copy()
        by_acto = {r['ACTES']: r for r in rows}
        for idx, row in df.iterrows():
            acto = row['ACTES']
            if acto in by_acto:
                if 'BANDA_PORCENTAJE' in by_acto[acto]:
                    df.at[idx, 'BANDA_PORCENTAJE'] = float(by_acto[acto]['BANDA_PORCENTAJE'])
                if 'DESCRIPCION' in by_acto[acto]:
                    df.at[idx, 'DESCRIPCION'] = str(by_acto[acto]['DESCRIPCION'])
        self.band_retention_config = df.copy()
        self.band_retention_df = df.copy()
        return df

    def save_band_retention(self):
        self.band_retention_df = self.band_retention_config.copy()

    def reset_band_retention(self):
        reset_config = self.band_retention_config.copy()
        reset_config['BANDA_PORCENTAJE'] = 0.0
        reset_config['DESCRIPCION'] = 'Sin retención'
        self.band_retention_config = reset_config
        self.band_retention_df = reset_config.copy()

    def apply_band_retention_template(self):
        template_config = self.band_retention_config.copy()
        for idx, row in template_config.iterrows():
            if 'OFICIAL' in row['ACTES'].upper():
                template_config.at[idx, 'BANDA_PORCENTAJE'] = 0.0
                template_config.at[idx, 'DESCRIPCION'] = 'Acto oficial - Sin retención'
            elif any(word in row['ACTES'].upper() for word in ['NAVIDAD', 'CHRISTMAS', 'CONCIERTO']):
                template_config.at[idx, 'BANDA_PORCENTAJE'] = 15.0
                template_config.at[idx, 'DESCRIPCION'] = 'Fondo de instrumentos'
            else:
                template_config.at[idx, 'BANDA_PORCENTAJE'] = 10.0
                template_config.at[idx, 'DESCRIPCION'] = 'Gastos generales'

        self.band_retention_config = template_config
        self.band_retention_df = template_config.copy()

    def compute_retention_impact(self):
        """Impacto financiero de la retención (idéntico a la página)."""
        total_retention = 0.0
        total_budget = 0.0
        retention_breakdown = []

        current_retention = self.band_retention_config

        for _, budget_row in self.presupuesto_df.iterrows():
            event_name = budget_row['ACTES']
            budget_amount = budget_row['A REPARTIR']
            total_budget += budget_amount

            retention_row = current_retention[current_retention['ACTES'] == event_name]
            if not retention_row.empty:
                retention_pct = retention_row.iloc[0]['BANDA_PORCENTAJE']
                retention_amount = budget_amount * (retention_pct / 100)
                total_retention += retention_amount

                if retention_pct > 0:
                    retention_breakdown.append({
                        'Acto': event_name,
                        'Presupuesto': float(budget_amount),
                        'Retención %': float(retention_pct),
                        'Retención €': float(retention_amount),
                        'Neto Músicos': float(budget_amount - retention_amount),
                    })

        return {
            "total_budget": float(total_budget),
            "total_retention": float(total_retention),
            "net_for_musicians": float(total_budget - total_retention),
            "breakdown": retention_breakdown,
        }

    # ------------------------------------------------------------------
    # Dashboard / análisis
    # ------------------------------------------------------------------
    def dashboard_data(self):
        total_budget, total_distributed, difference = self.calculate_budget_difference()
        category_counts = self.asistencia_df['Categoria'].value_counts()
        budget_by_event = self.presupuesto_df.head(10)[['ACTES', 'A REPARTIR']]
        return {
            "total_budget": float(total_budget),
            "total_distributed": float(total_distributed),
            "difference": float(difference),
            "category_counts": {str(k): int(v) for k, v in category_counts.to_dict().items()},
            "budget_by_event": [
                {"ACTES": str(r['ACTES']), "A REPARTIR": float(r['A REPARTIR'])}
                for _, r in budget_by_event.iterrows()
            ],
        }

    def event_analysis(self, selected_event):
        """Datos de la página Análisis por Actos."""
        result = {"categorias": [], "presupuesto": None}
        category_data = self.get_musicians_by_category(selected_event)
        if not category_data.empty:
            result["categorias"] = [
                {
                    "Categoria": str(cat),
                    "Count": int(category_data.loc[cat, 'Count']),
                    "Musicians": [f"{n} {a}" for (n, a) in category_data.loc[cat, 'Musicians']],
                }
                for cat in category_data.index
            ]

        budget_info = self.presupuesto_df[self.presupuesto_df['ACTES'] == selected_event]
        if not budget_info.empty:
            budget_row = budget_info.iloc[0]
            result["presupuesto"] = {
                "COBRAT": float(budget_row['COBRAT']) if 'COBRAT' in budget_row else None,
                "LLOGATS": float(budget_row['LLOGATS']) if 'LLOGATS' in budget_row else None,
                "TRANSPORT": float(budget_row['TRANSPORT']) if 'TRANSPORT' in budget_row else None,
                "A REPARTIR": float(budget_row['A REPARTIR']) if 'A REPARTIR' in budget_row else None,
            }
        return result
