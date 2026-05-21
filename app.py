import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from Igualar_Precios import calcular_presupuestos_iguales, calcular_ponderaciones_automaticas

# Configure Streamlit page
st.set_page_config(
    page_title="Sistema de Cobro Musical",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #f7f7f7;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f4e79;
    }
</style>
""", unsafe_allow_html=True)

class MusicianPaymentSystem:
    def __init__(self, data_path=None):
        self.data_path = data_path
        self.asistencia_df = None
        self.presupuesto_df = None
        self.configuracion_df = None
        self.band_retention_df = None
        # Do not auto-load data - let user upload files
    
    def load_data(self):
        """Load data from Excel file"""
        if not self.data_path:
            return False
        try:
            # Load all sheets
            self.asistencia_df = pd.read_excel(self.data_path, sheet_name="Asistencia")
            self.presupuesto_df = pd.read_excel(self.data_path, sheet_name="Presupuesto")
            self.configuracion_df = pd.read_excel(self.data_path, sheet_name="Configuracion_Precios")
            
            # Validate data consistency
            self._validate_data_consistency()
            
            # Store original weights for reset functionality
            if 'original_weights' not in st.session_state:
                st.session_state.original_weights = self.configuracion_df.copy()
            
            # Initialize band retention data
            self._initialize_band_retention()
                
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return False
        return True
    
    def load_from_uploaded_file(self, uploaded_file):
        """Load data from uploaded Excel file with dynamic sheet detection"""
        try:
            # First, get all sheet names to validate structure
            excel_file = pd.ExcelFile(uploaded_file)
            available_sheets = excel_file.sheet_names
            
            st.info(f"📋 Hojas encontradas en el archivo: {', '.join(available_sheets)}")
            
            # Check for required sheets with flexible naming
            asistencia_sheet = self._find_sheet_by_patterns(available_sheets, ["Asistencia", "asistencia", "Attendance", "attendance"])
            presupuesto_sheet = self._find_sheet_by_patterns(available_sheets, ["Presupuesto", "presupuesto", "Budget", "budget"])
            configuracion_sheet = self._find_sheet_by_patterns(available_sheets, ["Configuracion_Precios", "configuracion_precios", "Configuracion", "configuracion", "Prices", "prices", "Config", "config"])
            
            if not asistencia_sheet:
                st.error("❌ No se encontró hoja de Asistencia. Nombres esperados: Asistencia, asistencia, Attendance, attendance")
                return False
            
            if not presupuesto_sheet:
                st.error("❌ No se encontró hoja de Presupuesto. Nombres esperados: Presupuesto, presupuesto, Budget, budget")
                return False
                
            if not configuracion_sheet:
                st.error("❌ No se encontró hoja de Configuración de Precios. Nombres esperados: Configuracion_Precios, Configuracion, Config, etc.")
                return False
            
            st.success(f"✅ Hojas identificadas: {asistencia_sheet}, {presupuesto_sheet}, {configuracion_sheet}")
            
            # Load sheets with identified names
            self.asistencia_df = pd.read_excel(uploaded_file, sheet_name=asistencia_sheet)
            self.presupuesto_df = pd.read_excel(uploaded_file, sheet_name=presupuesto_sheet)
            self.configuracion_df = pd.read_excel(uploaded_file, sheet_name=configuracion_sheet)
            
            # Validate and clean data structure
            if not self._validate_and_clean_data_structure():
                return False
            
            # Validate data consistency
            self._validate_data_consistency()
            
            # Update original weights
            st.session_state.original_weights = self.configuracion_df.copy()
            
            # Initialize band retention data
            self._initialize_band_retention()
            
            # Show data summary
            self._show_data_summary()
            
            return True
                
        except Exception as e:
            st.error(f"Error loading uploaded file: {str(e)}")
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
            # Validate Asistencia sheet
            required_asistencia_cols = ['Nombre', 'Apellidos', 'Instrumento', 'Categoria']
            missing_cols = [col for col in required_asistencia_cols if col not in self.asistencia_df.columns]
            
            if missing_cols:
                st.error(f"❌ Columnas faltantes en hoja de Asistencia: {missing_cols}")
                st.info("💡 Columnas requeridas: Nombre, Apellidos, Instrumento, Categoria")
                return False
            
            # Validate Presupuesto sheet - ensure ACTES column exists
            if 'ACTES' not in self.presupuesto_df.columns:
                st.error("❌ Columna 'ACTES' faltante en hoja de Presupuesto")
                return False
            
            # Look for budget columns with flexible naming
            budget_cols = []
            for col in self.presupuesto_df.columns:
                if any(word in col.upper() for word in ['REPARTIR', 'BUDGET', 'TOTAL', 'AMOUNT']):
                    budget_cols.append(col)
            
            if not budget_cols:
                # Try to find common budget column patterns
                possible_budget_cols = [col for col in self.presupuesto_df.columns if col.upper() in ['A REPARTIR', 'TOTAL', 'AMOUNT', 'BUDGET']]
                if not possible_budget_cols:
                    st.error("❌ No se encontró columna de presupuesto. Busque columnas como 'A REPARTIR', 'TOTAL', 'BUDGET'")
                    return False
                budget_cols = possible_budget_cols
            
            st.info(f"💰 Columnas de presupuesto detectadas: {', '.join(budget_cols)}")
            
            # Validate Configuracion sheet - ensure ACTES column exists
            if 'ACTES' not in self.configuracion_df.columns:
                st.error("❌ Columna 'ACTES' faltante en hoja de Configuración")
                return False
            
            category_cols = [col for col in self.configuracion_df.columns if col in ['A', 'B', 'C', 'D', 'E']]
            
            if len(category_cols) == 0:
                st.error("❌ No se encontraron columnas de categorías (A, B, C, D, E) en la configuración")
                return False
            
            st.info(f"🏷️ Categorías detectadas: {', '.join(category_cols)}")
            
            # Clean and standardize data
            self._clean_data()
            
            return True
            
        except Exception as e:
            st.error(f"Error validating data structure: {str(e)}")
            return False
    
    def _clean_data(self):
        """Clean and standardize the loaded data"""
        try:
            # Clean musician names
            self.asistencia_df['Nombre'] = self.asistencia_df['Nombre'].astype(str).str.strip()
            self.asistencia_df['Apellidos'] = self.asistencia_df['Apellidos'].astype(str).str.strip()
            
            # Ensure categories are uppercase
            self.asistencia_df['Categoria'] = self.asistencia_df['Categoria'].astype(str).str.upper().str.strip()
            
            # Clean event names in all sheets
            if 'ACTES' in self.presupuesto_df.columns:
                self.presupuesto_df['ACTES'] = self.presupuesto_df['ACTES'].astype(str).str.strip()
            
            if 'ACTES' in self.configuracion_df.columns:
                self.configuracion_df['ACTES'] = self.configuracion_df['ACTES'].astype(str).str.strip()
            
            # Clean attendance data - convert to numeric and fill NaN with 0
            event_columns = self.get_events_list()
            for event in event_columns:
                self.asistencia_df[event] = pd.to_numeric(self.asistencia_df[event], errors='coerce').fillna(0)
                # Ensure binary values (0 or 1)
                self.asistencia_df[event] = self.asistencia_df[event].apply(lambda x: 1 if x > 0 else 0)
            
            st.success("✅ Datos limpiados y estandarizados")
            
        except Exception as e:
            st.warning(f"⚠️ Advertencia en limpieza de datos: {str(e)}")
    
    def _show_data_summary(self):
        """Show summary of loaded data"""
        try:
            st.subheader("📊 Resumen de Datos Cargados")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Músicos", len(self.asistencia_df))
                
            with col2:
                events_count = len(self.get_events_list())
                st.metric("Total Actos", events_count)
                
            with col3:
                total_budget = self.presupuesto_df.select_dtypes(include=[np.number]).sum().sum()
                st.metric("Presupuesto Total", f"€{total_budget:,.2f}")
            
            # Show categories distribution
            st.write("**Distribución por Categorías:**")
            category_counts = self.asistencia_df['Categoria'].value_counts()
            st.write(category_counts.to_dict())
            
            # Show first few events
            events = self.get_events_list()[:10]  # Show first 10 events
            if events:
                st.write(f"**Primeros Actos:** {', '.join(events)}")
                if len(self.get_events_list()) > 10:
                    st.write(f"... y {len(self.get_events_list()) - 10} actos más")
            
        except Exception as e:
            st.warning(f"Error mostrando resumen: {str(e)}")
    
    def _validate_data_consistency(self):
        """Validate that all sheets have consistent event data"""
        try:
            # Get events from each sheet
            asistencia_events = set(self.get_events_list())
            presupuesto_events = set(self.presupuesto_df['ACTES'].values)
            configuracion_events = set(self.configuracion_df['ACTES'].values)
            
            # Find discrepancies
            missing_in_presupuesto = asistencia_events - presupuesto_events
            missing_in_configuracion = asistencia_events - configuracion_events
            extra_in_presupuesto = presupuesto_events - asistencia_events
            extra_in_configuracion = configuracion_events - asistencia_events
            
            # Report issues
            if missing_in_presupuesto:
                st.warning(f"⚠️ Eventos en Asistencia pero faltantes en Presupuesto: {missing_in_presupuesto}")
            
            if missing_in_configuracion:
                st.warning(f"⚠️ Eventos en Asistencia pero faltantes en Configuracion_Precios: {missing_in_configuracion}")
                
            if extra_in_presupuesto:
                st.warning(f"⚠️ Eventos en Presupuesto pero faltantes en Asistencia: {extra_in_presupuesto}")
                
            if extra_in_configuracion:
                st.warning(f"⚠️ Eventos en Configuracion_Precios pero faltantes en Asistencia: {extra_in_configuracion}")
            
            # Show success message if all consistent
            if not (missing_in_presupuesto or missing_in_configuracion or extra_in_presupuesto or extra_in_configuracion):
                st.success(f"✅ Datos consistentes: {len(asistencia_events)} eventos encontrados en todas las hojas")
                
        except Exception as e:
            st.error(f"Error validating data consistency: {str(e)}")
    
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
                # Create band retention dataframe with default 0% retention
                self.band_retention_df = pd.DataFrame({
                    'ACTES': events,
                    'BANDA_PORCENTAJE': [0.0] * len(events),
                    'DESCRIPCION': ['Sin retención'] * len(events)
                })
                
                # Store in session state for persistence
                if 'band_retention_config' not in st.session_state:
                    st.session_state.band_retention_config = self.band_retention_df.copy()
                else:
                    # Update existing config with new events if any
                    existing_events = set(st.session_state.band_retention_config['ACTES'].values)
                    new_events = [e for e in events if e not in existing_events]
                    if new_events:
                        new_rows = pd.DataFrame({
                            'ACTES': new_events,
                            'BANDA_PORCENTAJE': [0.0] * len(new_events),
                            'DESCRIPCION': ['Sin retención'] * len(new_events)
                        })
                        st.session_state.band_retention_config = pd.concat([
                            st.session_state.band_retention_config, new_rows
                        ], ignore_index=True)
                    
                    self.band_retention_df = st.session_state.band_retention_config.copy()
                    
            else:
                self.band_retention_df = pd.DataFrame(columns=['ACTES', 'BANDA_PORCENTAJE', 'DESCRIPCION'])
                
        except Exception as e:
            st.warning(f"Error inicializando configuración de retención: {str(e)}")
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
            # Check if data is loaded
            if self.asistencia_df is None or self.presupuesto_df is None or self.configuracion_df is None:
                return 0, 0, 0
                
            # Get current weights from session state (editing_weights) for real-time updates
            current_weights = st.session_state.get('editing_weights', getattr(self, 'configuracion_df', st.session_state.get('original_weights', pd.DataFrame())))
            
            if current_weights.empty:
                return 0, 0, 0
            
            total_budget = self.presupuesto_df['A REPARTIR'].sum()
            
            # Calculate what would be distributed with current weights
            total_distributed = 0
            
            for _, event_row in self.presupuesto_df.iterrows():
                event_name = event_row['ACTES']
                if event_name in self.asistencia_df.columns:
                    # Get attendees for this event
                    event_attendees = self.asistencia_df[self.asistencia_df[event_name] == 1]
                    total_attendees = len(event_attendees)
                    
                    if total_attendees > 0:
                        # Apply band retention first
                        original_amount = event_row['A REPARTIR']
                        retention_percentage = self.get_band_retention_for_event(event_name)
                        net_amount = original_amount * (1 - retention_percentage / 100)
                        
                        # Get weights for this event
                        weight_row = current_weights[current_weights['ACTES'] == event_name]
                        if not weight_row.empty:
                            weight_row = weight_row.iloc[0]
                            
                            # Calculate payment for each attendee using net amount
                            for _, attendee in event_attendees.iterrows():
                                category = attendee['Categoria']
                                if category in weight_row:
                                    ponderacion = weight_row[category]
                                    payment = (net_amount / total_attendees) * ponderacion
                                    total_distributed += payment
            
            difference = total_budget - total_distributed
            return total_budget, total_distributed, difference
            
        except Exception as e:
            st.error(f"Error calculating budget difference: {str(e)}")
            return 0, 0, 0

    def process_payments(self, penalty_criteria="manual", fixed_penalty_amount=0, category_penalties=None):
        """Process all payment calculations according to requirements"""
        if self.asistencia_df is None or self.presupuesto_df is None or self.configuracion_df is None:
            st.error("No hay datos cargados. Por favor, carga un archivo Excel primero.")
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
            
            # Check for events that didn't match in budget
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
            
            # Check for events that didn't match in configuration
            events_without_config = attendance_weights[attendance_weights['ACTES_config'].isna()]['Acto'].unique()
            if len(events_without_config) > 0:
                print(f"WARNING: Events without configuration data: {events_without_config}")
            
            # More robust handling of missing data
            # First, check what events have all required data
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
            # (row["A_REPARTIR_NETO"] / row["total_asistentes"]) * row["ponderacion"]
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
            
            # Get ALL events from original Excel in their original order
            original_events_order = self.get_events_list()
            
            # Add missing events (those without attendees) as columns with 0 values
            # This ensures ALL events appear in the final Excel, even if no one attended
            for event in original_events_order:
                if event not in payment_pivot.columns:
                    payment_pivot[event] = 0.0
            
            # Reorder ALL columns to match original Excel order
            payment_pivot = payment_pivot.reindex(columns=original_events_order)
            
            # 12. Create attendance pivot by event
            attendance_pivot = self.asistencia_df.set_index(['Nombre', 'Apellidos', 'Instrumento', 'Categoria'])
            
            # 13. Detect official events (those with "OFICIAL" in name)
            official_events = [col for col in self.get_events_list() if 'OFICIAL' in col.upper()]
            
            # 14. Count missed official events per musician - FIXED INDEX ISSUE
            musician_summary = musician_summary.reset_index(drop=True)
            
            if official_events:
                # Create a mapping from full name to missed events count
                missed_counts = {}
                for _, row in self.asistencia_df.iterrows():
                    full_name = f"{row['Nombre']} {row['Apellidos']}"
                    missed_count = sum(row[event] == 0 for event in official_events if event in row.index)
                    missed_counts[full_name] = missed_count
                
                # Add missed official events count to summary
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
            
            # Add band retention information
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
            st.error(f"Error processing payments: {str(e)}")
            return None
    
    def _apply_official_event_penalties(self, musician_summary, penalty_criteria, fixed_penalty_amount, category_penalties=None):
        """Apply penalties for missed official events"""
        try:
            # Create a copy to avoid modifying the original
            result_summary = musician_summary.copy()
            
            # Add penalty columns
            result_summary['Penalizacion_Total'] = 0.0
            result_summary['Importe_Final'] = result_summary['Importe_Individual']
            
            for idx, musician in result_summary.iterrows():
                missed_official_events = musician['Actos_Oficiales_No_Asistidos']
                
                if missed_official_events > 0:
                    if penalty_criteria == "fixed":
                        # Option 1: Fixed amount per missed official event (now supports per-category)
                        if category_penalties and musician['Categoria'] in category_penalties:
                            penalty = missed_official_events * category_penalties[musician['Categoria']]
                        else:
                            penalty = missed_official_events * fixed_penalty_amount
                        
                    elif penalty_criteria == "average":
                        # Option 2: Average of earnings per attended event
                        # Get total events attended by this musician
                        musician_name = musician['Musico']
                        
                        # Count attended events for this musician
                        attended_events = 0
                        for event in self.get_events_list():
                            if event in self.asistencia_df.columns:
                                # Find musician in attendance data
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
            st.error(f"Error applying penalties: {str(e)}")
            return musician_summary

def main():
    # Initialize system without loading data by default
    if 'payment_system' not in st.session_state:
        st.session_state.payment_system = MusicianPaymentSystem()
    
    system = st.session_state.payment_system
    
    # File upload in sidebar (moved to top)
    st.sidebar.subheader("📁 Cargar Archivo Excel")
    
    # Show instructions for file structure
    with st.sidebar.expander("📋 Estructura del Archivo", expanded=False):
        st.write("**Hojas requeridas:**")
        st.write("• **Asistencia**: Datos de asistencia de músicos a actos")
        st.write("• **Presupuesto**: Información presupuestaria por acto")
        st.write("• **Configuracion** (o Config/Prices): Ponderaciones por categoría")
        st.write("")
        st.write("**Columnas mínimas:**")
        st.write("• Asistencia: Nombre, Apellidos, Instrumento, Categoria + columnas de actos")
        st.write("• Presupuesto: ACTES + columnas de presupuesto")
        st.write("• Configuracion: ACTES, A, B, C, D, E")
    
    uploaded_file = st.sidebar.file_uploader(
        "Selecciona un archivo Excel:",
        type=['xlsx', 'xls'],
        help="El archivo se adaptará automáticamente a diferentes números de actos y nombres"
    )
    
    if uploaded_file is not None:
        # Show file info
        st.sidebar.info(f"📄 Archivo: {uploaded_file.name}")
        st.sidebar.info(f"📏 Tamaño: {uploaded_file.size / 1024:.1f} KB")
        
        if st.sidebar.button("🔄 Cargar y Procesar Archivo", use_container_width=True):
            with st.spinner("Analizando y cargando archivo..."):
                if system.load_from_uploaded_file(uploaded_file):
                    # Reset editing state when new file is loaded
                    if 'editing_weights' in st.session_state:
                        del st.session_state.editing_weights
                    st.success("✅ Archivo cargado y validado correctamente!")
                    st.balloons()  # Celebration effect
                    st.rerun()
                else:
                    st.error("❌ Error al cargar el archivo")
    else:
        st.sidebar.warning("⚠️ Selecciona un archivo Excel para comenzar")
    
    st.sidebar.markdown("---")
    
    # Sidebar navigation
    st.sidebar.subheader("🎵 Navegación")
    page = st.sidebar.selectbox(
        "Selecciona una página:",
        ["Dashboard Principal", "Editar Ponderaciones", "Configurar Retención Banda", "Análisis por Actos", "Procesar y Descargar"]
    )
    
    if page == "Dashboard Principal":
        show_dashboard(system)
    elif page == "Editar Ponderaciones":
        show_weights_editor(system)
    elif page == "Configurar Retención Banda":
        show_band_retention_page(system)
    elif page == "Análisis por Actos":
        show_event_analysis(system)
    elif page == "Procesar y Descargar":
        show_processing_page(system)

def show_dashboard(system):
    """Main dashboard page"""
    st.markdown('<h1 class="main-header">🎵 Sistema de Cobro Musical</h1>', unsafe_allow_html=True)
    
    # Check if data is loaded
    if system.asistencia_df is None or system.presupuesto_df is None or system.configuracion_df is None:
        st.warning("⚠️ No hay archivo cargado. Por favor, carga un archivo Excel usando el botón en la barra lateral.")
        
        # Show welcome message and instructions
        st.markdown("""
        ### 🎼 Bienvenido al Sistema de Cobro Musical
        
        Este sistema te permite:
        - ✅ **Cargar cualquier archivo Excel** con datos de asistencia y presupuestos
        - 🔄 **Adaptarse automáticamente** a diferentes números de actos y nombres
        - ⚖️ **Editar ponderaciones** por categoría en tiempo real
        - 📊 **Generar reportes completos** y exportar a Excel
        
        ### 📋 Para comenzar:
        1. **Prepara tu archivo Excel** con las hojas: Asistencia, Presupuesto, Configuración
        2. **Carga el archivo** usando el botón en la barra lateral
        3. **El sistema se adaptará automáticamente** al número de actos y sus nombres
        
        ### 🏗️ Flexible y Escalable:
        - Soporta cualquier número de actos (5, 10, 50, 100+)
        - Nombres de actos personalizables
        - Validación automática de estructura
        - Limpieza y estandarización de datos
        """)
        
        st.info("👈 Utiliza el botón 'Cargar y Procesar Archivo' en la barra lateral para comenzar.")
        return
    
    # Key metrics
    col1, col2, col3 = st.columns(3)
    
    total_budget, total_distributed, difference = system.calculate_budget_difference()
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total a Repartir", f"€{total_budget:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Distribuido", f"€{total_distributed:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Diferencia", f"€{difference:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Data overview
    st.subheader("📊 Resumen de Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Músicos por Categoría:**")
        category_counts = system.asistencia_df['Categoria'].value_counts()
        fig_pie = px.pie(values=category_counts.values, names=category_counts.index, title="Distribución por Categorías")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.write("**Presupuesto por Acto:**")
        fig_bar = px.bar(
            system.presupuesto_df.head(10), 
            x='A REPARTIR', 
            y='ACTES', 
            orientation='h',
            title="Top 10 Actos por Presupuesto"
        )
        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

def show_weights_editor(system):
    """Weights editing page"""
    st.header("⚖️ Editar Ponderaciones")
    
    # Check if data is loaded
    if system.asistencia_df is None or system.presupuesto_df is None or system.configuracion_df is None:
        st.warning("⚠️ No hay archivo cargado. Por favor, carga un archivo Excel usando el botón en la barra lateral.")
        st.info("👈 Utiliza el botón 'Cargar Archivo Excel' en la barra lateral para comenzar.")
        return
    
    st.subheader("⚖️ Ponderaciones por Categoría")
    st.write("Edita las ponderaciones por categoría para cada acto:")
    
    # Initialize editing state in session if not exists
    if 'editing_weights' not in st.session_state:
        st.session_state.editing_weights = system.configuracion_df.copy()
        # Ensure proper data types for all category columns
        for col in ['A', 'B', 'C', 'D', 'E']:
            if col in st.session_state.editing_weights.columns:
                st.session_state.editing_weights[col] = st.session_state.editing_weights[col].astype(float)
    
    # Create editable dataframe with custom column configuration
    column_config = {
        "ACTES": st.column_config.TextColumn("Acto", disabled=True),
        "A": st.column_config.NumberColumn("A", min_value=0.0, max_value=10.0, step=0.0001, format="%.4f"),
        "B": st.column_config.NumberColumn("B", min_value=0.0, max_value=10.0, step=0.001, format="%.3f"),
        "C": st.column_config.NumberColumn("C", min_value=0.0, max_value=10.0, step=0.001, format="%.3f"),
        "D": st.column_config.NumberColumn("D", min_value=0.0, max_value=10.0, step=0.001, format="%.3f"),
        "E": st.column_config.NumberColumn("E", min_value=0.0, max_value=10.0, step=0.001, format="%.3f")
    }
    
    # Use session state data for consistent editing experience
    edited_df = st.data_editor(
        st.session_state.editing_weights,
        use_container_width=True,
        num_rows="fixed",
        column_config=column_config,
        disabled=["ACTES"],
        key="ponderaciones_editor"
    )
    
    # Update session state immediately when data changes and force recalculation
    # Always update to ensure real-time functionality works correctly
    # Ensure proper data types before updating
    for col in ['A', 'B', 'C', 'D', 'E']:
        if col in edited_df.columns:
            edited_df[col] = edited_df[col].astype(float)
    
    st.session_state.editing_weights = edited_df.copy()
    # Force immediate update of the system configuration for real-time calculations
    system.configuracion_df = edited_df.copy()
    
    # Optional debug info (remove comment to debug)
    # st.write("🔍 DEBUG - Valores actuales guardados:")
    # debug_df = edited_df[['ACTES', 'A', 'B', 'C', 'D', 'E']].head(3)
    # st.dataframe(debug_df)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Guardar Cambios"):
            system.configuracion_df = st.session_state.editing_weights.copy()
            st.success("Ponderaciones actualizadas correctamente!")
            st.rerun()
    
    with col2:
        if st.button("🔄 Restaurar Original"):
            st.session_state.editing_weights = st.session_state.original_weights.copy()
            system.configuracion_df = st.session_state.original_weights.copy()
            st.success("Ponderaciones restauradas!")
            st.rerun()
    
    with col3:
            st.dataframe(st.session_state.editing_weights)
    
    # NEW: Equalize Prices Section
    st.divider()
    st.subheader("⚖️ Igualar Presupuestos")
    st.write("Calcula y ajusta los presupuestos automáticamente para que el *precio unitario ponderado* sea igual en los actos seleccionados.")
    
    with st.expander("🛠️ Configurar Igualación", expanded=False):
        # 1. Select events
        all_events = system.get_events_list()
        selected_events_eq = st.multiselect(
            "Selecciona los actos a igualar:",
            options=all_events,
            default=[] # Default to none to avoid accidental massive changes
        )
        
        # 2. Select Total Budget for these events
        # Default value: sum of current budgets for selected events
        default_budget_sum = 0.0
        if selected_events_eq:
            current_budgets = system.presupuesto_df[system.presupuesto_df['ACTES'].isin(selected_events_eq)]
            default_budget_sum = current_budgets['A REPARTIR'].sum()
        
        target_total_budget = st.number_input(
            "Presupuesto Total a repartir entre estos actos (€):",
            min_value=0.0,
            value=float(default_budget_sum),
            step=100.0,
            format="%.2f"
        )
        
        if st.button("🚀 Calcular y Aplicar Nuevos Presupuestos"):
            if not selected_events_eq:
                st.warning("⚠️ Selecciona al menos un acto.")
            else:
                try:
                    # Prepare arguments for calculation
                    # 1. df_asistencia: system.asistencia_df
                    # 2. df_ponderaciones: need ACTES as index
                    df_pond_for_calc = st.session_state.editing_weights.copy()
                    if 'ACTES' in df_pond_for_calc.columns:
                        df_pond_for_calc.set_index('ACTES', inplace=True)
                    
                    # 3. Categorias: A, B, C, D, E (columns present)
                    cats = ['A', 'B', 'C', 'D', 'E']
                    
                    # Run calculation
                    new_budgets, valor_unitario = calcular_presupuestos_iguales(
                        df_asistencia=system.asistencia_df,
                        df_ponderaciones=df_pond_for_calc,
                        eventos=selected_events_eq,
                        categorias=cats,
                        presupuesto_total_max=target_total_budget,
                        categoria_col="Categoria"
                    )
                    
                    # Update system.presupuesto_df
                    changes_log = []
                    for event, new_amount in new_budgets.items():
                        # Find row in budget df
                        mask = system.presupuesto_df['ACTES'] == event
                        if mask.any():
                            old_amount = system.presupuesto_df.loc[mask, 'A REPARTIR'].values[0]
                            system.presupuesto_df.loc[mask, 'A REPARTIR'] = new_amount
                            changes_log.append({
                                "Acto": event,
                                "Anterior": old_amount,
                                "Nuevo": new_amount,
                                "Cambio": new_amount - old_amount
                            })
                    
                    st.success(f"✅ Presupuestos actualizados con éxito! Valor unitario común: €{valor_unitario:.4f}")
                    
                    # Show changes
                    if changes_log:
                        st.write("Resumen de cambios:")
                        changes_df = pd.DataFrame(changes_log)
                        st.dataframe(changes_df.style.format({
                            "Anterior": "€{:.2f}", 
                            "Nuevo": "€{:.2f}", 
                            "Cambio": "€{:.2f}"
                        }))
                        
                except Exception as e:
                    st.error(f"Error al calcular: {str(e)}")

    # NEW: Automatic A weight calculation
    st.divider()
    st.subheader("🎯 Cálculo Automático de Ponderación A")
    st.write(
        "Calcula la ponderación **A** automáticamente para que "
        "**Total Repartido = Neto para Músicos** (diferencia ≥ 0 garantizada)."
    )
    st.caption(
        "Reglas: C=0.700, D=0.600, E=0.500 fijos · B se conserva · "
        "A se trunca hacia abajo a los decimales indicados · "
        "Actos oficiales (todo a 0) se omiten."
    )

    with st.expander("🛠️ Calcular A automáticamente", expanded=False):
        # Build event list (exclude official events: all 5 weights = 0)
        weights_df = st.session_state.editing_weights
        cat_cols = ['A', 'B', 'C', 'D', 'E']
        non_official_mask = (weights_df[cat_cols].fillna(0).sum(axis=1) > 0)
        non_official_events = weights_df.loc[non_official_mask, 'ACTES'].tolist()

        decimales_pond = st.slider(
            "Decimales de la ponderación A (más decimales = menor diferencia en €):",
            min_value=2, max_value=6, value=4, step=1,
            help=(
                "El truncamiento hacia abajo asegura que la diferencia (Neto − Total "
                "Repartido) sea ≥ 0. Con 4 decimales el margen suele ser < €0.10 por acto."
            ),
        )

        col_a, col_b = st.columns([2, 1])
        with col_a:
            evento_individual = st.selectbox(
                "Selecciona un acto para recalcular:",
                options=["— (ninguno) —"] + non_official_events,
                index=0,
                key="auto_pond_evento_individual",
            )
        with col_b:
            st.write("")
            st.write("")
            recalcular_uno = st.button(
                "🔧 Recalcular ESTE acto",
                use_container_width=True,
                disabled=(evento_individual == "— (ninguno) —"),
            )

        st.write("")
        recalcular_todos = st.button(
            "🚀 Recalcular A en TODOS los actos no oficiales",
            use_container_width=True,
            type="primary",
        )

        def _aplicar_auto_pond(eventos_a_recalcular):
            df_pond_idx = st.session_state.editing_weights.copy().set_index('ACTES')
            resultados = calcular_ponderaciones_automaticas(
                df_asistencia=system.asistencia_df,
                df_ponderaciones=df_pond_idx,
                eventos=eventos_a_recalcular,
                categoria_col="Categoria",
                decimales=decimales_pond,
            )

            cambios = []
            saltados = []
            df_new = st.session_state.editing_weights.copy()
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

                    # Calculate diff in € using current budget and band retention
                    a_repartir = 0.0
                    bp_row = system.presupuesto_df[system.presupuesto_df['ACTES'] == evento]
                    if not bp_row.empty:
                        a_repartir = float(bp_row.iloc[0]['A REPARTIR'])
                    retention_pct = system.get_band_retention_for_event(evento)
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
                        "A exacto (sin truncar)": info["A_exacto"],
                        "B": info["B"],
                        "Asistentes": info["N_total"],
                        "Neto (€)": neto,
                        "Total Repartido (€)": total_repartido,
                        "Diff (€)": diff_eur,
                    })

            # Persist
            for c in cat_cols:
                df_new[c] = df_new[c].astype(float)
            st.session_state.editing_weights = df_new
            system.configuracion_df = df_new.copy()
            return cambios, saltados

        fmt_pond = "{:." + str(decimales_pond) + "f}"
        tabla_fmt = {
            "A anterior": fmt_pond,
            "A nuevo": fmt_pond,
            "A exacto (sin truncar)": "{:.8f}",
            "B": "{:.4f}",
            "Neto (€)": "€{:,.2f}",
            "Total Repartido (€)": "€{:,.2f}",
            "Diff (€)": "€{:,.4f}",
        }

        if recalcular_uno and evento_individual != "— (ninguno) —":
            try:
                cambios, saltados = _aplicar_auto_pond([evento_individual])
                if cambios:
                    c = cambios[0]
                    st.success(
                        f"✅ Ponderación A recalculada para «{evento_individual}»: "
                        f"{c['A anterior']:.{decimales_pond}f} → "
                        f"{c['A nuevo']:.{decimales_pond}f} · "
                        f"Diff = €{c['Diff (€)']:.4f}"
                    )
                    st.dataframe(
                        pd.DataFrame(cambios).style.format(tabla_fmt),
                        use_container_width=True,
                    )
                if saltados:
                    st.warning("⚠️ Actos no procesados:")
                    st.dataframe(pd.DataFrame(saltados), use_container_width=True)
                st.rerun()
            except Exception as e:
                st.error(f"Error al recalcular: {str(e)}")

        if recalcular_todos:
            try:
                cambios, saltados = _aplicar_auto_pond(non_official_events)
                if cambios:
                    df_cambios = pd.DataFrame(cambios)
                    diff_total = df_cambios["Diff (€)"].sum()
                    diff_max = df_cambios["Diff (€)"].max()
                    st.success(
                        f"✅ Ponderación A recalculada en {len(cambios)} actos · "
                        f"Diff total = €{diff_total:,.2f} · Diff máx por acto = €{diff_max:,.4f}"
                    )
                    st.dataframe(
                        df_cambios.style.format(tabla_fmt),
                        use_container_width=True,
                    )
                if saltados:
                    st.warning(f"⚠️ {len(saltados)} acto(s) no procesado(s):")
                    st.dataframe(pd.DataFrame(saltados), use_container_width=True)
                st.rerun()
            except Exception as e:
                st.error(f"Error al recalcular: {str(e)}")

    # Budget comparison table
    st.divider()
    st.subheader("💰 Comparación Presupuestaria en Tiempo Real (Incluye Retención de Banda)")
    
    # Calculate budget comparison with current weights
    try:
        # Calculate distributed amounts using current weights from session state (with band retention)
        budget_comparison_df = system.presupuesto_df.copy()
        budget_comparison_df['Banda_Retencion_PCT'] = 0.0
        budget_comparison_df['Banda_Retencion_Amount'] = 0.0
        budget_comparison_df['Neto_Para_Musicos'] = budget_comparison_df['A REPARTIR']
        budget_comparison_df['Total Repartido'] = 0.0
        
        for idx, row in budget_comparison_df.iterrows():
            event_name = row['ACTES']
            
            # Apply band retention first
            retention_percentage = system.get_band_retention_for_event(event_name)
            retention_amount = row['A REPARTIR'] * (retention_percentage / 100)
            net_amount = row['A REPARTIR'] - retention_amount
            
            budget_comparison_df.at[idx, 'Banda_Retencion_PCT'] = retention_percentage
            budget_comparison_df.at[idx, 'Banda_Retencion_Amount'] = retention_amount
            budget_comparison_df.at[idx, 'Neto_Para_Musicos'] = net_amount
            
            if event_name in system.asistencia_df.columns:
                # Get attendees for this event
                event_attendees = system.asistencia_df[system.asistencia_df[event_name] == 1]
                total_attendees = len(event_attendees)
                
                if total_attendees > 0:
                    # Get weights for this event from session state
                    current_weights = st.session_state.editing_weights
                    weight_row = current_weights[current_weights['ACTES'] == event_name]
                    
                    # Optional debug (remove comment to debug)
                    # if not weight_row.empty:
                    #     st.write(f"🔍 DEBUG Tabla 1 - Evento: {event_name}")
                    #     st.write(f"   Pesos: A={weight_row.iloc[0]['A']}, B={weight_row.iloc[0]['B']}, C={weight_row.iloc[0]['C']}")
                    
                    if not weight_row.empty:
                        weight_row = weight_row.iloc[0]
                        total_event_payment = 0
                        
                        # Calculate payment for each attendee using NET amount after band retention
                        for _, attendee in event_attendees.iterrows():
                            category = attendee['Categoria']
                            if category in ['A', 'B', 'C', 'D', 'E'] and category in weight_row:
                                ponderacion = weight_row[category]
                                payment = (net_amount / total_attendees) * ponderacion
                                total_event_payment += payment
                        
                        budget_comparison_df.at[idx, 'Total Repartido'] = total_event_payment
        
        # Calculate difference using net amount
        budget_comparison_df['Diferencia_Neto'] = budget_comparison_df['Neto_Para_Musicos'] - budget_comparison_df['Total Repartido']
        
        # Display the comparison table with band retention info
        display_df = budget_comparison_df[[
            'ACTES', 'A REPARTIR', 'Banda_Retencion_PCT', 'Banda_Retencion_Amount', 
            'Neto_Para_Musicos', 'Total Repartido', 'Diferencia_Neto'
        ]].copy()
        
        # Round numeric columns
        for col in ['A REPARTIR', 'Banda_Retencion_Amount', 'Neto_Para_Musicos', 'Total Repartido', 'Diferencia_Neto']:
            display_df[col] = display_df[col].round(2)
        display_df['Banda_Retencion_PCT'] = display_df['Banda_Retencion_PCT'].round(1)
        
        # Rename columns for better display
        display_df.columns = [
            'Acto', 'Presupuesto Original', 'Retención %', 'Retención €', 
            'Neto para Músicos', 'Total Repartido', 'Diferencia'
        ]
        
        st.dataframe(display_df, use_container_width=True)
        
        # Summary metrics (with band retention)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_budget = budget_comparison_df['A REPARTIR'].sum()
            st.metric("Total Presupuesto", f"€{total_budget:,.2f}")
        
        with col2:
            total_retention = budget_comparison_df['Banda_Retencion_Amount'].sum()
            st.metric("Total Retención Banda", f"€{total_retention:,.2f}")
        
        with col3:
            total_net = budget_comparison_df['Neto_Para_Musicos'].sum()
            st.metric("Total Neto Músicos", f"€{total_net:,.2f}")
        
        with col4:
            total_difference = budget_comparison_df['Diferencia_Neto'].sum()
            st.metric("Diferencia", f"€{total_difference:,.2f}", delta=f"{total_difference:,.2f}")
            
    except Exception as e:
        st.error(f"Error calculando comparación presupuestaria: {str(e)}")
        st.write("Mostrando tabla básica de presupuesto:")
        st.dataframe(system.presupuesto_df)
    
    # Real-time earnings table by category and event
    st.divider()
    st.subheader("💵 Ganancias por Categoría y Acto (Tiempo Real - Después de Retención)")
    
    try:
        # Calculate earnings by category for each event - SHOW ALL EVENTS
        earnings_data = []
        current_weights = st.session_state.editing_weights
        
        for _, event_row in system.presupuesto_df.iterrows():
            event_name = event_row['ACTES']
            
            # Apply band retention first
            retention_percentage = system.get_band_retention_for_event(event_name)
            original_amount = event_row['A REPARTIR']
            net_amount = original_amount * (1 - retention_percentage / 100)
            
            if event_name in system.asistencia_df.columns:
                # Get attendees for this event by category
                event_attendees = system.asistencia_df[system.asistencia_df[event_name] == 1]
                total_attendees = len(event_attendees)
                
                # Get weights for this event
                weight_row = current_weights[current_weights['ACTES'] == event_name]
                
                # Optional debug (remove comment to debug)
                # if not weight_row.empty:
                #     st.write(f"🔍 DEBUG Tabla 2 - Evento: {event_name}")
                #     st.write(f"   Pesos: A={weight_row.iloc[0]['A']}, B={weight_row.iloc[0]['B']}, C={weight_row.iloc[0]['C']}")
                
                if not weight_row.empty:
                    weight_row = weight_row.iloc[0]
                    
                    # Calculate earnings for each category using NET amount - ALWAYS show, even if no attendees
                    event_earnings = {
                        'Acto': event_name,
                        'Original': f"€{original_amount:.2f}",
                        'Retención': f"{retention_percentage}%" if retention_percentage > 0 else "0%",
                        'Neto': f"€{net_amount:.2f}"
                    }
                    
                    for category in ['A', 'B', 'C', 'D', 'E']:
                        if category in weight_row:
                            if total_attendees > 0:
                                ponderacion = float(weight_row[category])
                                # Calculate individual payment for this category using NET amount
                                individual_payment = (net_amount / total_attendees) * ponderacion
                                event_earnings[category] = f"€{individual_payment:.2f}"
                            else:
                                # No attendees - show €0.00
                                event_earnings[category] = "€0.00"
                        else:
                            event_earnings[category] = "€0.00"
                    
                    earnings_data.append(event_earnings)
        
        if earnings_data:
            earnings_df = pd.DataFrame(earnings_data)
            
            # Display the earnings table with band retention info
            st.write("**Ganancias individuales por categoría (después de retención de banda)**")
            st.dataframe(earnings_df, use_container_width=True)
            
            # Show explanation
            st.info("💵 Las ganancias mostradas ya incluyen el descuento por retención de banda configurada para cada acto.")
        else:
            st.info("No hay datos de ganancias para mostrar")
            
    except Exception as e:
        st.error(f"Error calculando ganancias por categoría: {str(e)}")
        st.write("Detalle del error:", e)

def show_band_retention_page(system):
    """Band retention configuration page"""
    st.header("🏦 Configurar Retención de Banda")
    
    # Check if data is loaded
    if system.asistencia_df is None or system.presupuesto_df is None or system.configuracion_df is None:
        st.warning("⚠️ No hay archivo cargado. Por favor, carga un archivo Excel usando el botón en la barra lateral.")
        st.info("👈 Utiliza el botón 'Cargar Archivo Excel' en la barra lateral para comenzar.")
        return
    
    st.write("""
    Configura el porcentaje que la banda se quedará de cada acto **antes** de repartir el dinero entre los músicos.
    
    **📝 Ejemplo:**
    - A Repartir: €1,000
    - Retención Banda: 10%
    - Cantidad retenida: €100
    - **Cantidad neta para músicos: €900**
    """)
    
    # Initialize band retention if not exists
    if 'band_retention_config' not in st.session_state:
        system._initialize_band_retention()
    
    # Get current retention configuration
    current_config = st.session_state.band_retention_config.copy()
    
    st.subheader("📊 Configuración de Retención por Acto")
    
    # Create editable dataframe
    column_config = {
        "ACTES": st.column_config.TextColumn("Acto", disabled=True, width="large"),
        "BANDA_PORCENTAJE": st.column_config.NumberColumn(
            "Retención (%)", 
            min_value=0.0, 
            max_value=100.0, 
            step=0.5, 
            format="%.1f%%",
            help="Porcentaje que se queda la banda (0-100%)"
        ),
        "DESCRIPCION": st.column_config.TextColumn(
            "Descripción", 
            help="Descripción del motivo de la retención",
            width="medium"
        )
    }
    
    # Edit retention configuration
    edited_config = st.data_editor(
        current_config,
        use_container_width=True,
        num_rows="fixed",
        column_config=column_config,
        disabled=["ACTES"],
        key="band_retention_editor"
    )
    
    # Update session state when data changes
    if not edited_config.equals(current_config):
        st.session_state.band_retention_config = edited_config.copy()
        system.band_retention_df = edited_config.copy()
    
    # Control buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Guardar Configuración"):
            system.band_retention_df = st.session_state.band_retention_config.copy()
            st.success("Configuración de retención guardada!")
            st.rerun()
    
    with col2:
        if st.button("🔄 Resetear a 0%"):
            reset_config = current_config.copy()
            reset_config['BANDA_PORCENTAJE'] = 0.0
            reset_config['DESCRIPCION'] = 'Sin retención'
            st.session_state.band_retention_config = reset_config
            system.band_retention_df = reset_config.copy()
            st.success("Configuración reseteada a 0%!")
            st.rerun()
    
    with col3:
        if st.button("🕰️ Plantilla Rápida"):
            template_config = current_config.copy()
            # Set some common percentages
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
            
            st.session_state.band_retention_config = template_config
            system.band_retention_df = template_config.copy()
            st.success("Plantilla aplicada!")
            st.rerun()
    
    # Preview of financial impact
    st.divider()
    st.subheader("💰 Impacto Financiero")
    
    try:
        # Calculate total retention and net distribution
        total_retention = 0.0
        total_budget = 0.0
        retention_breakdown = []
        
        current_retention = st.session_state.band_retention_config
        
        for _, budget_row in system.presupuesto_df.iterrows():
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
                        'Presupuesto': budget_amount,
                        'Retención %': retention_pct,
                        'Retención €': retention_amount,
                        'Neto Músicos': budget_amount - retention_amount
                    })
        
        # Display summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Presupuesto", f"€{total_budget:,.2f}")
        
        with col2:
            st.metric("Total Retención Banda", f"€{total_retention:,.2f}")
        
        with col3:
            net_for_musicians = total_budget - total_retention
            st.metric("Neto para Músicos", f"€{net_for_musicians:,.2f}")
        
        # Show detailed breakdown if there are retentions
        if retention_breakdown:
            st.write("**Desglose de Retenciones:**")
            breakdown_df = pd.DataFrame(retention_breakdown)
            
            # Format the dataframe for display
            breakdown_df['Presupuesto'] = breakdown_df['Presupuesto'].apply(lambda x: f"€{x:,.2f}")
            breakdown_df['Retención %'] = breakdown_df['Retención %'].apply(lambda x: f"{x}%")
            breakdown_df['Retención €'] = breakdown_df['Retención €'].apply(lambda x: f"€{x:,.2f}")
            breakdown_df['Neto Músicos'] = breakdown_df['Neto Músicos'].apply(lambda x: f"€{x:,.2f}")
            
            st.dataframe(breakdown_df, use_container_width=True)
        else:
            st.info("💵 No hay retenciones configuradas - Todo el presupuesto se repartirá entre los músicos.")
            
    except Exception as e:
        st.error(f"Error calculando impacto financiero: {str(e)}")

def show_event_analysis(system):
    """Event analysis page"""
    st.header("🎭 Análisis por Actos")
    
    # Check if data is loaded
    if system.asistencia_df is None or system.presupuesto_df is None or system.configuracion_df is None:
        st.warning("⚠️ No hay archivo cargado. Por favor, carga un archivo Excel usando el botón en la barra lateral.")
        st.info("👈 Utiliza el botón 'Cargar Archivo Excel' en la barra lateral para comenzar.")
        return
    
    events = system.get_events_list()
    selected_event = st.selectbox("Selecciona un acto:", events)
    
    if selected_event:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👥 Músicos por Categoría")
            category_data = system.get_musicians_by_category(selected_event)
            
            if not category_data.empty:
                st.dataframe(category_data)
                
                # Visualization
                fig = px.bar(
                    x=category_data.index,
                    y=category_data['Count'],
                    title=f"Asistencia por Categoría - {selected_event}"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de asistencia para este acto")
        
        with col2:
            st.subheader("💰 Información Presupuestaria")
            budget_info = system.presupuesto_df[system.presupuesto_df['ACTES'] == selected_event]
            
            if not budget_info.empty:
                budget_row = budget_info.iloc[0]
                st.metric("Cobrado", f"€{budget_row['COBRAT']:,}")
                st.metric("Gastos Alquiler", f"€{budget_row['LLOGATS']:,}")
                st.metric("Transporte", f"€{budget_row['TRANSPORT']:,}")
                st.metric("A Repartir", f"€{budget_row['A REPARTIR']:,}")
            else:
                st.info("No hay información presupuestaria para este acto")

def show_processing_page(system):
    """Data processing and export page"""
    st.header("⚙️ Procesar y Descargar")
    
    # Check if data is loaded
    if system.asistencia_df is None or system.presupuesto_df is None or system.configuracion_df is None:
        st.warning("⚠️ No hay archivo cargado. Por favor, carga un archivo Excel usando el botón en la barra lateral.")
        st.info("👈 Utiliza el botón 'Cargar Archivo Excel' en la barra lateral para comenzar.")
        return
    
    st.write("Procesa todos los cálculos y genera el archivo Excel con los resultados detallados.")
    
    # Penalty configuration section
    st.subheader("💰 Configuración de Penalizaciones por Actos Oficiales")
    st.write("Selecciona cómo quieres manejar las penalizaciones por actos oficiales no asistidos:")
    
    penalty_criteria = st.radio(
        "Criterio de penalización:",
        options=["manual", "fixed", "average"],
        format_func=lambda x: {
            "manual": "3. Introducir manualmente después de descargar el Excel",
            "fixed": "1. Cantidad fija por acto oficial no asistido",
            "average": "2. Media de ganancias por acto asistido"
        }[x],
        help="Selecciona el método para calcular penalizaciones automáticamente o hazlo manualmente después"
    )
    
    fixed_penalty_amount = 0
    category_penalties = None
    
    if penalty_criteria == "fixed":
        penalty_type = st.radio(
            "Tipo de penalización fija:",
            options=["uniform", "by_category"],
            format_func=lambda x: {
                "uniform": "Cantidad igual para todas las categorías",
                "by_category": "Cantidad diferente por categoría"
            }[x],
            help="Elige si aplicar la misma cantidad a todos o diferente por categoría"
        )
        
        if penalty_type == "uniform":
            fixed_penalty_amount = st.number_input(
                "Cantidad a descontar por acto oficial no asistido (€):",
                min_value=0.0,
                value=50.0,
                step=5.0,
                help="Cantidad fija que se descontará por cada acto oficial al que no haya asistido el músico"
            )
        else:
            st.write("**Configurar penalización por categoría:**")
            category_penalties = {}
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                category_penalties['A'] = st.number_input(
                    "Categoría A (€):",
                    min_value=0.0,
                    value=60.0,
                    step=5.0,
                    key="penalty_A"
                )
            
            with col2:
                category_penalties['B'] = st.number_input(
                    "Categoría B (€):",
                    min_value=0.0,
                    value=55.0,
                    step=5.0,
                    key="penalty_B"
                )
            
            with col3:
                category_penalties['C'] = st.number_input(
                    "Categoría C (€):",
                    min_value=0.0,
                    value=50.0,
                    step=5.0,
                    key="penalty_C"
                )
            
            with col4:
                category_penalties['D'] = st.number_input(
                    "Categoría D (€):",
                    min_value=0.0,
                    value=45.0,
                    step=5.0,
                    key="penalty_D"
                )
            
            with col5:
                category_penalties['E'] = st.number_input(
                    "Categoría E (€):",
                    min_value=0.0,
                    value=40.0,
                    step=5.0,
                    key="penalty_E"
                )
            
            st.info(f"💡 Penalizaciones configuradas: A=€{category_penalties['A']}, B=€{category_penalties['B']}, C=€{category_penalties['C']}, D=€{category_penalties['D']}, E=€{category_penalties['E']}")
    elif penalty_criteria == "average":
        st.info("💡 Se calculará automáticamente la media de lo que ha ganado cada músico por acto asistido y se descontará esa cantidad por cada acto oficial no asistido.")
    else:
        st.info("💡 No se aplicarán penalizaciones automáticas. Podrás añadirlas manualmente en el Excel descargado.")
    
    st.divider()
    
    if st.button("🔄 Procesar Datos", type="primary"):
        with st.spinner("Procesando datos..."):
            results = system.process_payments(penalty_criteria, fixed_penalty_amount, category_penalties)
        
        if results:
            st.success("✅ Datos procesados correctamente!")
            
            # Show summary
            st.subheader("📋 Resumen de Resultados")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Músicos con Ganancias", len(results['musician_summary']))
            
            with col2:
                # Use final amount if penalties were applied, otherwise use individual amount
                if 'Importe_Final' in results['musician_summary'].columns:
                    total_distributed = results['musician_summary']['Importe_Final'].sum()
                    st.metric("Total Final", f"€{total_distributed:,.2f}")
                else:
                    total_distributed = results['musician_summary']['Importe_Individual'].sum()
                    st.metric("Total Distribuido", f"€{total_distributed:,.2f}")
            
            with col3:
                total_band_retention = results.get('total_band_retention', 0)
                st.metric("Retención Banda", f"€{total_band_retention:,.2f}")
            
            with col4:
                if 'Importe_Final' in results['musician_summary'].columns:
                    avg_payment = results['musician_summary']['Importe_Final'].mean()
                    st.metric("Pago Final Promedio", f"€{avg_payment:,.2f}")
                else:
                    avg_payment = results['musician_summary']['Importe_Individual'].mean()
                    st.metric("Pago Promedio", f"€{avg_payment:,.2f}")
            
            # Show penalty summary if penalties were applied
            if penalty_criteria != "manual" and 'Penalizacion_Total' in results['musician_summary'].columns:
                st.subheader("📋 Resumen de Penalizaciones")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_penalties = results['musician_summary']['Penalizacion_Total'].sum()
                    st.metric("Total Penalizaciones", f"€{total_penalties:,.2f}")
                
                with col2:
                    musicians_with_penalties = len(results['musician_summary'][results['musician_summary']['Penalizacion_Total'] > 0])
                    st.metric("Músicos Penalizados", musicians_with_penalties)
                
                with col3:
                    if musicians_with_penalties > 0:
                        avg_penalty = results['musician_summary'][results['musician_summary']['Penalizacion_Total'] > 0]['Penalizacion_Total'].mean()
                        st.metric("Penalización Promedio", f"€{avg_penalty:,.2f}")
            
            # Show detailed results
            tab1, tab2, tab3, tab4 = st.tabs(["💰 Resumen por Músico", "📊 Comparación Presupuesto", "👥 Músicos por Categoría", "🏦 Retención Banda"])
            
            with tab1:
                st.dataframe(results['musician_summary'], use_container_width=True)
            
            with tab2:
                st.dataframe(results['budget_comparison'], use_container_width=True)
            
            with tab3:
                st.dataframe(results['musicians_by_category'], use_container_width=True)
            
            with tab4:
                st.write("**Detalle de Retención por Acto:**")
                if 'attendees_detail' in results and not results['attendees_detail'].empty:
                    retention_detail = results['attendees_detail'][[
                        'Acto', 'A REPARTIR', 'BANDA_RETENCION_PCT', 
                        'BANDA_RETENCION_AMOUNT', 'A_REPARTIR_NETO'
                    ]].drop_duplicates('Acto').copy()
                    
                    # Format for display
                    retention_detail['A REPARTIR'] = retention_detail['A REPARTIR'].apply(lambda x: f"€{x:,.2f}")
                    retention_detail['BANDA_RETENCION_PCT'] = retention_detail['BANDA_RETENCION_PCT'].apply(lambda x: f"{x}%")
                    retention_detail['BANDA_RETENCION_AMOUNT'] = retention_detail['BANDA_RETENCION_AMOUNT'].apply(lambda x: f"€{x:,.2f}")
                    retention_detail['A_REPARTIR_NETO'] = retention_detail['A_REPARTIR_NETO'].apply(lambda x: f"€{x:,.2f}")
                    
                    retention_detail.columns = ['Acto', 'Presupuesto Original', 'Retención %', 'Retención €', 'Neto para Músicos']
                    st.dataframe(retention_detail, use_container_width=True)
                    
                    # Summary
                    total_retention = results.get('total_band_retention', 0)
                    st.metric("Total Retención de Banda", f"€{total_retention:,.2f}")
                else:
                    st.info("No hay datos de retención para mostrar.")
            
            # Download functionality
            st.subheader("📥 Descargar Resultados")
            
            # Generate Excel directly in download button
            col1, col2 = st.columns(2)
            
            with col1:
                try:
                    with st.spinner("Generando archivo Excel completo..."):
                        excel_buffer = create_excel_export(results, system)
                    
                    st.success("✅ Excel completo generado!")
                    
                    st.download_button(
                        label="💾 Descargar Excel Completo",
                        data=excel_buffer,
                        file_name="cobro_musical_resultados.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Excel con formato profesional y hoja resumen"
                    )
                    
                except Exception as e:
                    st.error(f"Error generando Excel completo: {str(e)}")
            
            with col2:
                try:
                    with st.spinner("Generando Excel básico..."):
                        excel_basic = create_simple_excel_export(results)
                    
                    st.success("✅ Excel básico generado!")
                    
                    st.download_button(
                        label="📄 Descargar Excel Básico",
                        data=excel_basic,
                        file_name="cobro_musical_basico.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Excel simple sin formato avanzado (respaldo)"
                    )
                    
                except Exception as e:
                    st.error(f"Error generando Excel básico: {str(e)}")
                    st.write("Detalle del error:", e)

def create_excel_export(results, system):
    """Create Excel file with all results and proper formatting"""
    try:
        buffer = BytesIO()
        
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Define formatting
            money_format = workbook.add_format({'num_format': '€#,##0.00'})
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # 1. HOJA RESUMEN GENERAL
            try:
                create_summary_sheet(writer, results, system, money_format, header_format)
            except Exception as e:
                st.warning(f"Error creando hoja resumen: {e}")
            
            # 2. Format and write musician summary
            try:
                musician_summary = results['musician_summary'].copy()
                musician_summary['Importe_Individual'] = musician_summary['Importe_Individual'].round(2)
                
                # Round penalty and final amount columns if they exist
                if 'Penalizacion_Total' in musician_summary.columns:
                    musician_summary['Penalizacion_Total'] = musician_summary['Penalizacion_Total'].round(2)
                if 'Importe_Final' in musician_summary.columns:
                    musician_summary['Importe_Final'] = musician_summary['Importe_Final'].round(2)
                
                musician_summary.to_excel(writer, sheet_name='Resumen_Musicos', index=False)
                
                worksheet = writer.sheets['Resumen_Musicos']
                
                # Format money columns
                for col_num, col_name in enumerate(musician_summary.columns):
                    if any(word in col_name for word in ['Importe', 'Penalizacion']):
                        worksheet.set_column(col_num, col_num, 15, money_format)
                    
                # Apply header formatting
                for col_num, value in enumerate(musician_summary.columns.values):
                    worksheet.write(0, col_num, value, header_format)
            except Exception as e:
                st.warning(f"Error creando hoja músicos: {e}")
            
            # 3. Format payment pivot
            try:
                payment_pivot = results['payment_pivot'].round(2)
                payment_pivot.to_excel(writer, sheet_name='Pagos_por_Acto')
                
                worksheet = writer.sheets['Pagos_por_Acto']
                # Format all data columns as money
                for col in range(1, len(payment_pivot.columns) + 1):
                    worksheet.set_column(col, col, 12, money_format)
            except Exception as e:
                st.warning(f"Error creando pivot de pagos: {e}")
            
            # 4. Format budget comparison (now includes band retention)
            try:
                budget_comparison = results['budget_comparison'].copy()
                for col in ['A REPARTIR', 'Distribuido_Real', 'Diferencia', 'Banda_Retencion_Amount', 'Neto_Para_Musicos']:
                    if col in budget_comparison.columns:
                        budget_comparison[col] = budget_comparison[col].round(2)
                
                budget_comparison.to_excel(writer, sheet_name='Comparacion_Presupuesto', index=False)
                
                worksheet = writer.sheets['Comparacion_Presupuesto']
                # Format money columns
                for col_num, col_name in enumerate(budget_comparison.columns):
                    if any(word in col_name.upper() for word in ['REPARTIR', 'DISTRIBUIDO', 'DIFERENCIA', 'RETENCION', 'NETO']):
                        worksheet.set_column(col_num, col_num, 15, money_format)
                    worksheet.write(0, col_num, col_name, header_format)
            except Exception as e:
                st.warning(f"Error creando comparación presupuesto: {e}")
            
            # 5. Musicians by category
            try:
                results['musicians_by_category'].to_excel(writer, sheet_name='Musicos_por_Categoria', index=False)
                
                worksheet = writer.sheets['Musicos_por_Categoria']
                for col_num, value in enumerate(results['musicians_by_category'].columns.values):
                    worksheet.write(0, col_num, value, header_format)
            except Exception as e:
                st.warning(f"Error creando músicos por categoría: {e}")
            
            # 6. Detailed attendance with proper formatting
            try:
                attendees_detail = results['attendees_detail'].copy()
                attendees_detail['Importe_Individual'] = attendees_detail['Importe_Individual'].round(2)
                attendees_detail.to_excel(writer, sheet_name='Detalle_Asistencia', index=False)
                
                worksheet = writer.sheets['Detalle_Asistencia']
                # Find and format money columns
                for col_num, col_name in enumerate(attendees_detail.columns):
                    if 'Importe' in col_name or 'REPARTIR' in col_name:
                        worksheet.set_column(col_num, col_num, 12, money_format)
                    worksheet.write(0, col_num, col_name, header_format)
            except Exception as e:
                st.warning(f"Error creando detalle asistencia: {e}")
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        st.error(f"Error crítico generando Excel: {str(e)}")
        raise e

def create_summary_sheet(writer, results, system, money_format, header_format):
    """Create comprehensive summary sheet"""
    try:
        # Create summary data
        # 1. Budget vs Distributed by Event
        budget_summary = results['budget_comparison'][['ACTES', 'A REPARTIR', 'Distribuido_Real', 'Diferencia']].copy()
        budget_summary = budget_summary.round(2)
        
        # 3. Key Statistics
        total_budget = float(system.presupuesto_df['A REPARTIR'].sum())
        total_distributed = float(results['musician_summary']['Importe_Individual'].sum())
        total_musicians_paid = len(results['musician_summary'])
        avg_payment = float(results['musician_summary']['Importe_Individual'].mean())
        
        # 4. Musicians by Category Summary
        try:
            category_summary = results['musician_summary']['Categoria'].value_counts().reset_index()
            category_summary.columns = ['Categoria', 'Cantidad_Musicos']
            category_earnings = results['musician_summary'].groupby('Categoria')['Importe_Individual'].sum().reset_index()
            category_summary = category_summary.merge(category_earnings, on='Categoria')
            category_summary['Importe_Individual'] = category_summary['Importe_Individual'].round(2)
        except Exception as e:
            st.warning(f"Error procesando categorías: {e}")
            category_summary = pd.DataFrame(columns=['Categoria', 'Cantidad_Musicos', 'Importe_Individual'])
        
        # Write summary sheet
        worksheet = writer.book.add_worksheet('RESUMEN_GENERAL')
        writer.sheets['RESUMEN_GENERAL'] = worksheet
        
        row = 0
        
        # Title
        title_format = writer.book.add_format({
            'bold': True, 
            'font_size': 16, 
            'align': 'center',
            'fg_color': '#1f4e79',
            'font_color': 'white'
        })
        worksheet.merge_range(row, 0, row, 5, 'RESUMEN GENERAL - SISTEMA DE COBRO MUSICAL', title_format)
        row += 3
        
        # Key Metrics
        worksheet.write(row, 0, 'MÉTRICAS PRINCIPALES', header_format)
        row += 1
        worksheet.write(row, 0, 'Total Presupuesto:')
        worksheet.write(row, 1, total_budget, money_format)
        row += 1
        worksheet.write(row, 0, 'Total Distribuido:')
        worksheet.write(row, 1, total_distributed, money_format)
        row += 1
        worksheet.write(row, 0, 'Diferencia:')
        worksheet.write(row, 1, total_budget - total_distributed, money_format)
        row += 1
        worksheet.write(row, 0, 'Músicos Pagados:')
        worksheet.write(row, 1, total_musicians_paid)
        row += 1
        worksheet.write(row, 0, 'Pago Promedio:')
        worksheet.write(row, 1, avg_payment, money_format)
        row += 3
        
        # Budget vs Distributed by Event
        worksheet.write(row, 0, 'PRESUPUESTO VS DISTRIBUIDO POR ACTO', header_format)
        row += 1
        
        # Write budget comparison headers
        headers = ['Acto', 'A Repartir', 'Total Repartido', 'Diferencia']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        row += 1
        
        # Write budget comparison data
        for _, event_row in budget_summary.iterrows():
            try:
                worksheet.write(row, 0, str(event_row['ACTES']))
                worksheet.write(row, 1, float(event_row['A REPARTIR']), money_format)
                worksheet.write(row, 2, float(event_row['Distribuido_Real']), money_format)
                worksheet.write(row, 3, float(event_row['Diferencia']), money_format)
                row += 1
            except Exception as e:
                st.warning(f"Error escribiendo fila presupuesto: {e}")
                continue
        
        row += 2
        
        # Category Summary
        if not category_summary.empty:
            worksheet.write(row, 0, 'RESUMEN POR CATEGORÍA', header_format)
            row += 1
            
            cat_headers = ['Categoría', 'Cantidad Músicos', 'Total Ganado']
            for col, header in enumerate(cat_headers):
                worksheet.write(row, col, header, header_format)
            row += 1
            
            for _, cat_row in category_summary.iterrows():
                try:
                    worksheet.write(row, 0, str(cat_row['Categoria']))
                    worksheet.write(row, 1, int(cat_row['Cantidad_Musicos']))
                    worksheet.write(row, 2, float(cat_row['Importe_Individual']), money_format)
                    row += 1
                except Exception as e:
                    st.warning(f"Error escribiendo fila categoría: {e}")
                    continue
        
        # Set column widths
        worksheet.set_column(0, 0, 40)  # Event names
        worksheet.set_column(1, 4, 15)  # Money columns
        
    except Exception as e:
        st.error(f"Error en create_summary_sheet: {str(e)}")
        raise e

def create_simple_excel_export(results):
    """Create simple Excel file without advanced formatting"""
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Simple export without complex formatting
        results['musician_summary'].to_excel(writer, sheet_name='Resumen_Musicos', index=False)
        results['payment_pivot'].to_excel(writer, sheet_name='Pagos_por_Acto')
        results['budget_comparison'].to_excel(writer, sheet_name='Comparacion_Presupuesto', index=False)
        results['musicians_by_category'].to_excel(writer, sheet_name='Musicos_por_Categoria', index=False)
        results['attendees_detail'].to_excel(writer, sheet_name='Detalle_Asistencia', index=False)
    
    buffer.seek(0)
    return buffer

if __name__ == "__main__":
    main()