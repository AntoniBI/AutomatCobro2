import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go

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
        # Use Miembros.xlsx as default instead of Actes.xlsx
        if data_path is None:
            data_path = "Data/Miembros.xlsx"
        self.data_path = data_path
        self.asistencia_df = None
        self.presupuesto_df = None
        self.configuracion_df = None
        if data_path:
            self.load_data()
    
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
                
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return False
        return True
    
    def load_from_uploaded_file(self, uploaded_file):
        """Load data from uploaded Excel file"""
        try:
            # Load all sheets from uploaded file
            self.asistencia_df = pd.read_excel(uploaded_file, sheet_name="Asistencia")
            self.presupuesto_df = pd.read_excel(uploaded_file, sheet_name="Presupuesto")
            self.configuracion_df = pd.read_excel(uploaded_file, sheet_name="Configuracion_Precios")
            
            # Validate data consistency
            self._validate_data_consistency()
            
            # Update original weights
            st.session_state.original_weights = self.configuracion_df.copy()
            return True
                
        except Exception as e:
            st.error(f"Error loading uploaded file: {str(e)}")
            return False
    
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
                
            # Get current weights from session state or use default
            current_weights = getattr(self, 'configuracion_df', st.session_state.get('original_weights', pd.DataFrame()))
            
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
                        # Get weights for this event
                        weight_row = current_weights[current_weights['ACTES'] == event_name]
                        if not weight_row.empty:
                            weight_row = weight_row.iloc[0]
                            
                            # Calculate payment for each attendee
                            for _, attendee in event_attendees.iterrows():
                                category = attendee['Categoria']
                                if category in weight_row:
                                    ponderacion = weight_row[category]
                                    payment = (event_row['A REPARTIR'] / total_attendees) * ponderacion
                                    total_distributed += payment
            
            difference = total_budget - total_distributed
            return total_budget, total_distributed, difference
            
        except Exception as e:
            st.error(f"Error calculating budget difference: {str(e)}")
            return 0, 0, 0

    def process_payments(self, penalty_criteria="manual", fixed_penalty_amount=0):
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
            
            # 8. Calculate individual payment using correct formula
            # (row["A REPARTIR"] / row["total_asistentes"]) * row["ponderacion"]
            attendees['Importe_Individual'] = (attendees['A REPARTIR'] / attendees['total_asistentes']) * attendees['ponderacion']
            
            # 9. Generate total summary per musician
            musician_summary = attendees.groupby('Musico').agg({
                'Importe_Individual': 'sum',
                'Categoria': 'first',
                'Instrumento': 'first',
                'Nombre': 'first',
                'Apellidos': 'first'
            }).reset_index()
            
            # 10. Create payment pivot by event
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
            
            # 11. Create attendance pivot by event
            attendance_pivot = self.asistencia_df.set_index(['Nombre', 'Apellidos', 'Instrumento', 'Categoria'])
            
            # 12. Detect official events (those with "OFICIAL" in name)
            official_events = [col for col in self.get_events_list() if 'OFICIAL' in col.upper()]
            
            # 13. Count missed official events per musician - FIXED INDEX ISSUE
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
            
            # 14. Apply penalty for missed official events
            if penalty_criteria != "manual":
                musician_summary = self._apply_official_event_penalties(
                    musician_summary, penalty_criteria, fixed_penalty_amount
                )
            
            # 15. Filter musicians with earnings > 0
            musician_summary = musician_summary[musician_summary['Importe_Individual'] > 0]
            
            # 16. Calculate actual distributed amount per event
            actual_distributed = attendees.groupby('Acto')['Importe_Individual'].sum().reset_index()
            actual_distributed.columns = ['Acto', 'Distribuido_Real']
            
            # 17. Compare budget vs actual distribution
            budget_comparison = self.presupuesto_df.merge(actual_distributed, left_on='ACTES', right_on='Acto', how='left')
            budget_comparison['Distribuido_Real'] = budget_comparison['Distribuido_Real'].fillna(0)
            budget_comparison['Diferencia'] = budget_comparison['A REPARTIR'] - budget_comparison['Distribuido_Real']
            
            # 18. Count musicians by category and event
            musicians_by_category = attendees.groupby(['Acto', 'Categoria']).size().reset_index(name='Cantidad_Musicos')
            
            return {
                'musician_summary': musician_summary,
                'payment_pivot': payment_pivot,
                'attendance_pivot': attendance_pivot,
                'budget_comparison': budget_comparison,
                'musicians_by_category': musicians_by_category,
                'attendees_detail': attendees
            }
            
        except Exception as e:
            st.error(f"Error processing payments: {str(e)}")
            return None
    
    def _apply_official_event_penalties(self, musician_summary, penalty_criteria, fixed_penalty_amount):
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
                        # Option 1: Fixed amount per missed official event
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
    uploaded_file = st.sidebar.file_uploader(
        "Selecciona un archivo Excel:",
        type=['xlsx', 'xls'],
        help="El archivo debe contener las hojas: Asistencia, Presupuesto y Configuracion_Precios"
    )
    
    if uploaded_file is not None:
        if st.sidebar.button("🔄 Cargar Archivo", use_container_width=True):
            with st.spinner("Cargando archivo..."):
                if system.load_from_uploaded_file(uploaded_file):
                    # Reset editing state when new file is loaded
                    if 'editing_weights' in st.session_state:
                        del st.session_state.editing_weights
                    st.success("✅ Archivo cargado correctamente!")
                    st.rerun()
                else:
                    st.error("❌ Error al cargar el archivo")
    
    st.sidebar.markdown("---")
    
    # Sidebar navigation
    st.sidebar.subheader("🎵 Navegación")
    page = st.sidebar.selectbox(
        "Selecciona una página:",
        ["Dashboard Principal", "Editar Ponderaciones", "Análisis por Actos", "Procesar y Descargar"]
    )
    
    if page == "Dashboard Principal":
        show_dashboard(system)
    elif page == "Editar Ponderaciones":
        show_weights_editor(system)
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
        st.info("👈 Utiliza el botón 'Cargar Archivo Excel' en la barra lateral para comenzar.")
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
    
    # Create editable dataframe with custom column configuration
    column_config = {
        "ACTES": st.column_config.TextColumn("Acto", disabled=True),
        "A": st.column_config.NumberColumn("A", min_value=0.0, max_value=10.0, step=0.1, format="%.2f"),
        "B": st.column_config.NumberColumn("B", min_value=0.0, max_value=10.0, step=0.1, format="%.2f"),
        "C": st.column_config.NumberColumn("C", min_value=0.0, max_value=10.0, step=0.1, format="%.2f"),
        "D": st.column_config.NumberColumn("D", min_value=0.0, max_value=10.0, step=0.1, format="%.2f"),
        "E": st.column_config.NumberColumn("E", min_value=0.0, max_value=10.0, step=0.1, format="%.2f")
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
    
    # Update session state immediately when data changes
    if not edited_df.equals(st.session_state.editing_weights):
        st.session_state.editing_weights = edited_df.copy()
    
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
        if st.button("👀 Vista Previa"):
            st.write("Vista previa de las ponderaciones:")
            st.dataframe(st.session_state.editing_weights)
    
    # Budget comparison table
    st.divider()
    st.subheader("💰 Comparación Presupuestaria en Tiempo Real")
    
    # Calculate budget comparison with current weights
    try:
        # Calculate distributed amounts using current weights from session state
        budget_comparison_df = system.presupuesto_df.copy()
        budget_comparison_df['Total Repartido'] = 0.0
        
        for idx, row in budget_comparison_df.iterrows():
            event_name = row['ACTES']
            if event_name in system.asistencia_df.columns:
                # Get attendees for this event
                event_attendees = system.asistencia_df[system.asistencia_df[event_name] == 1]
                total_attendees = len(event_attendees)
                
                if total_attendees > 0:
                    # Get weights for this event from session state
                    current_weights = st.session_state.editing_weights
                    weight_row = current_weights[current_weights['ACTES'] == event_name]
                    
                    if not weight_row.empty:
                        weight_row = weight_row.iloc[0]
                        total_event_payment = 0
                        
                        # Calculate payment for each attendee
                        for _, attendee in event_attendees.iterrows():
                            category = attendee['Categoria']
                            if category in ['A', 'B', 'C', 'D', 'E'] and category in weight_row:
                                ponderacion = weight_row[category]
                                payment = (row['A REPARTIR'] / total_attendees) * ponderacion
                                total_event_payment += payment
                        
                        budget_comparison_df.at[idx, 'Total Repartido'] = total_event_payment
        
        # Calculate difference
        budget_comparison_df['A Repartir - Total Repartido'] = budget_comparison_df['A REPARTIR'] - budget_comparison_df['Total Repartido']
        
        # Display the comparison table
        display_df = budget_comparison_df[['ACTES', 'A REPARTIR', 'Total Repartido', 'A Repartir - Total Repartido']].copy()
        display_df['A REPARTIR'] = display_df['A REPARTIR'].round(2)
        display_df['Total Repartido'] = display_df['Total Repartido'].round(2)
        display_df['A Repartir - Total Repartido'] = display_df['A Repartir - Total Repartido'].round(2)
        
        st.dataframe(display_df, use_container_width=True)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_budget = budget_comparison_df['A REPARTIR'].sum()
            st.metric("Total Presupuesto", f"€{total_budget:,.2f}")
        
        with col2:
            total_distributed = budget_comparison_df['Total Repartido'].sum()
            st.metric("Total a Repartir", f"€{total_distributed:,.2f}")
        
        with col3:
            total_difference = budget_comparison_df['A Repartir - Total Repartido'].sum()
            st.metric("Diferencia Total", f"€{total_difference:,.2f}", delta=f"{total_difference:,.2f}")
            
    except Exception as e:
        st.error(f"Error calculando comparación presupuestaria: {str(e)}")
        st.write("Mostrando tabla básica de presupuesto:")
        st.dataframe(system.presupuesto_df)
    
    # Real-time earnings table by category and event
    st.divider()
    st.subheader("💵 Ganancias por Categoría y Acto (Tiempo Real)")
    
    try:
        # Calculate earnings by category for each event - SHOW ALL EVENTS
        earnings_data = []
        current_weights = st.session_state.editing_weights
        
        for _, event_row in system.presupuesto_df.iterrows():
            event_name = event_row['ACTES']
            
            if event_name in system.asistencia_df.columns:
                # Get attendees for this event by category
                event_attendees = system.asistencia_df[system.asistencia_df[event_name] == 1]
                total_attendees = len(event_attendees)
                
                # Get weights for this event
                weight_row = current_weights[current_weights['ACTES'] == event_name]
                
                if not weight_row.empty:
                    weight_row = weight_row.iloc[0]
                    
                    # Calculate earnings for each category - ALWAYS show, even if no attendees
                    event_earnings = {'Acto': event_name}
                    
                    for category in ['A', 'B', 'C', 'D', 'E']:
                        if category in weight_row:
                            if total_attendees > 0:
                                ponderacion = float(weight_row[category])
                                # Calculate individual payment for this category
                                individual_payment = (event_row['A REPARTIR'] / total_attendees) * ponderacion
                                event_earnings[category] = f"€{individual_payment:.2f}"
                            else:
                                # No attendees - show €0.00
                                event_earnings[category] = "€0.00"
                        else:
                            event_earnings[category] = "€0.00"
                    
                    earnings_data.append(event_earnings)
        
        if earnings_data:
            earnings_df = pd.DataFrame(earnings_data)
            
            # Display the simplified earnings table
            st.write("**Ganancias individuales por categoría según acto**")
            st.dataframe(earnings_df, use_container_width=True)
        else:
            st.info("No hay datos de ganancias para mostrar")
            
    except Exception as e:
        st.error(f"Error calculando ganancias por categoría: {str(e)}")
        st.write("Detalle del error:", e)

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
    if penalty_criteria == "fixed":
        fixed_penalty_amount = st.number_input(
            "Cantidad a descontar por acto oficial no asistido (€):",
            min_value=0.0,
            value=50.0,
            step=5.0,
            help="Cantidad fija que se descontará por cada acto oficial al que no haya asistido el músico"
        )
    elif penalty_criteria == "average":
        st.info("💡 Se calculará automáticamente la media de lo que ha ganado cada músico por acto asistido y se descontará esa cantidad por cada acto oficial no asistido.")
    else:
        st.info("💡 No se aplicarán penalizaciones automáticas. Podrás añadirlas manualmente en el Excel descargado.")
    
    st.divider()
    
    if st.button("🔄 Procesar Datos", type="primary"):
        with st.spinner("Procesando datos..."):
            results = system.process_payments(penalty_criteria, fixed_penalty_amount)
        
        if results:
            st.success("✅ Datos procesados correctamente!")
            
            # Show summary
            st.subheader("📋 Resumen de Resultados")
            
            col1, col2, col3 = st.columns(3)
            
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
            tab1, tab2, tab3 = st.tabs(["💰 Resumen por Músico", "📊 Comparación Presupuesto", "👥 Músicos por Categoría"])
            
            with tab1:
                st.dataframe(results['musician_summary'], use_container_width=True)
            
            with tab2:
                st.dataframe(results['budget_comparison'], use_container_width=True)
            
            with tab3:
                st.dataframe(results['musicians_by_category'], use_container_width=True)
            
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
            
            # 4. Format budget comparison
            try:
                budget_comparison = results['budget_comparison'].copy()
                for col in ['A REPARTIR', 'Distribuido_Real', 'Diferencia']:
                    if col in budget_comparison.columns:
                        budget_comparison[col] = budget_comparison[col].round(2)
                
                budget_comparison.to_excel(writer, sheet_name='Comparacion_Presupuesto', index=False)
                
                worksheet = writer.sheets['Comparacion_Presupuesto']
                # Format money columns
                for col_num, col_name in enumerate(budget_comparison.columns):
                    if any(word in col_name.upper() for word in ['REPARTIR', 'DISTRIBUIDO', 'DIFERENCIA']):
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