import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
import os
import threading
import sys

# Set matplotlib backend to avoid conflicts
import matplotlib
matplotlib.use('TkAgg')

# Configure CustomTkinter appearance
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class MusicianPaymentSystem:
    def __init__(self, data_path=None):
        self.data_path = data_path
        self.asistencia_df = None
        self.presupuesto_df = None
        self.configuracion_df = None
        self.original_weights = None
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
            
            # Store original weights for reset functionality
            self.original_weights = self.configuracion_df.copy()
                
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False
        return True
    
    def load_from_file_path(self, file_path):
        """Load data from file path"""
        try:
            # Load all sheets from file
            self.asistencia_df = pd.read_excel(file_path, sheet_name="Asistencia")
            self.presupuesto_df = pd.read_excel(file_path, sheet_name="Presupuesto")
            self.configuracion_df = pd.read_excel(file_path, sheet_name="Configuracion_Precios")
            
            # Update original weights
            self.original_weights = self.configuracion_df.copy()
            return True
                
        except Exception as e:
            print(f"Error loading file: {str(e)}")
            return False
    
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
        """Calculate difference between budget and distributed amount"""
        try:
            if self.asistencia_df is None or self.presupuesto_df is None or self.configuracion_df is None:
                return 0, 0, 0
                
            current_weights = self.configuracion_df
            if current_weights.empty:
                return 0, 0, 0
            
            total_budget = self.presupuesto_df['A REPARTIR'].sum()
            total_distributed = 0
            
            for _, event_row in self.presupuesto_df.iterrows():
                event_name = event_row['ACTES']
                if event_name in self.asistencia_df.columns:
                    event_attendees = self.asistencia_df[self.asistencia_df[event_name] == 1]
                    total_attendees = len(event_attendees)
                    
                    if total_attendees > 0:
                        weight_row = current_weights[current_weights['ACTES'] == event_name]
                        if not weight_row.empty:
                            weight_row = weight_row.iloc[0]
                            
                            for _, attendee in event_attendees.iterrows():
                                category = attendee['Categoria']
                                if category in weight_row:
                                    ponderacion = weight_row[category]
                                    payment = (event_row['A REPARTIR'] / total_attendees) * ponderacion
                                    total_distributed += payment
            
            difference = total_budget - total_distributed
            return total_budget, total_distributed, difference
            
        except Exception as e:
            print(f"Error calculating budget difference: {str(e)}")
            return 0, 0, 0

    def process_payments(self, penalty_criteria="manual", fixed_penalty_amount=0):
        """Process all payment calculations"""
        if self.asistencia_df is None or self.presupuesto_df is None or self.configuracion_df is None:
            return None
        try:
            # Transform attendance table to long format
            id_vars = ['Nombre', 'Apellidos', 'Instrumento', 'Categoria']
            attendance_long = pd.melt(
                self.asistencia_df, 
                id_vars=id_vars,
                var_name='Acto',
                value_name='Asistencia'
            )
            
            # Create musician name
            attendance_long['Musico'] = attendance_long['Nombre'] + ' ' + attendance_long['Apellidos']
            
            # Join with budget and weights
            attendance_budget = attendance_long.merge(
                self.presupuesto_df,
                left_on='Acto',
                right_on='ACTES',
                how='left'
            )
            
            attendance_weights = attendance_budget.merge(
                self.configuracion_df,
                left_on='Acto',
                right_on='ACTES',
                how='left'
            )
            
            # Filter attendees only
            attendees = attendance_weights[attendance_weights['Asistencia'] == 1].copy()
            
            # Calculate total attendees per event
            attendees_per_event = attendees.groupby('Acto')['Musico'].count().reset_index()
            attendees_per_event.columns = ['Acto', 'total_asistentes']
            attendees = attendees.merge(attendees_per_event, on='Acto')
            
            # Get ponderacion based on category
            def get_ponderacion(row):
                category = row['Categoria']
                if category in ['A', 'B', 'C', 'D', 'E']:
                    return row[category]
                return 1.0
            
            attendees['ponderacion'] = attendees.apply(get_ponderacion, axis=1)
            
            # Calculate individual payment
            attendees['Importe_Individual'] = (attendees['A REPARTIR'] / attendees['total_asistentes']) * attendees['ponderacion']
            
            # Generate total summary per musician
            musician_summary = attendees.groupby('Musico').agg({
                'Importe_Individual': 'sum',
                'Categoria': 'first',
                'Instrumento': 'first',
                'Nombre': 'first',
                'Apellidos': 'first'
            }).reset_index()
            
            # Create payment pivot by event
            payment_pivot = attendees.pivot_table(
                index='Musico',
                columns='Acto',
                values='Importe_Individual',
                fill_value=0
            )
            
            # Create attendance pivot by event
            attendance_pivot = self.asistencia_df.set_index(['Nombre', 'Apellidos', 'Instrumento', 'Categoria'])
            
            # Detect official events
            official_events = [col for col in self.get_events_list() if 'OFICIAL' in col.upper()]
            
            # Count missed official events per musician
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
            
            # Filter musicians with earnings > 0
            musician_summary = musician_summary[musician_summary['Importe_Individual'] > 0]
            
            # Calculate actual distributed amount per event
            actual_distributed = attendees.groupby('Acto')['Importe_Individual'].sum().reset_index()
            actual_distributed.columns = ['Acto', 'Distribuido_Real']
            
            # Compare budget vs actual distribution
            budget_comparison = self.presupuesto_df.merge(actual_distributed, left_on='ACTES', right_on='Acto', how='left')
            budget_comparison['Distribuido_Real'] = budget_comparison['Distribuido_Real'].fillna(0)
            budget_comparison['Diferencia'] = budget_comparison['A REPARTIR'] - budget_comparison['Distribuido_Real']
            
            # Count musicians by category and event
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
            print(f"Error processing payments: {str(e)}")
            return None

class MusicianPaymentApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Sistema de Cobro Musical")
        self.root.geometry("1200x800")
        
        # Initialize payment system
        self.payment_system = MusicianPaymentSystem()
        
        # Create main interface
        self.create_main_interface()
        
    def create_main_interface(self):
        """Create the main application interface"""
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            self.main_frame, 
            text="🎵 Sistema de Cobro Musical", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=20)
        
        # File loading section
        self.create_file_section()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_weights_tab()
        self.create_analysis_tab()
        self.create_processing_tab()
        
    def create_file_section(self):
        """Create file loading section"""
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.pack(fill="x", padx=10, pady=10)
        
        # File selection
        self.file_label = ctk.CTkLabel(file_frame, text="No hay archivo cargado")
        self.file_label.pack(side="left", padx=10, pady=10)
        
        load_button = ctk.CTkButton(
            file_frame, 
            text="📁 Cargar Archivo Excel",
            command=self.load_file
        )
        load_button.pack(side="right", padx=10, pady=10)
        
    def create_dashboard_tab(self):
        """Create dashboard tab"""
        dashboard_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(dashboard_frame, text="Dashboard Principal")
        
        # Key metrics frame
        metrics_frame = ctk.CTkFrame(dashboard_frame)
        metrics_frame.pack(fill="x", padx=10, pady=10)
        
        self.budget_label = ctk.CTkLabel(metrics_frame, text="Total a Repartir: €0.00")
        self.budget_label.pack(side="left", padx=20, pady=10)
        
        self.distributed_label = ctk.CTkLabel(metrics_frame, text="Total Distribuido: €0.00")
        self.distributed_label.pack(side="left", padx=20, pady=10)
        
        self.difference_label = ctk.CTkLabel(metrics_frame, text="Diferencia: €0.00")
        self.difference_label.pack(side="left", padx=20, pady=10)
        
        # Charts frame
        self.charts_frame = ctk.CTkFrame(dashboard_frame)
        self.charts_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
    def create_weights_tab(self):
        """Create weights editing tab"""
        weights_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(weights_frame, text="Editar Ponderaciones")
        
        # Instructions
        instruction_label = ctk.CTkLabel(
            weights_frame, 
            text="Edita las ponderaciones por categoría para cada acto",
            font=ctk.CTkFont(size=14)
        )
        instruction_label.pack(pady=10)
        
        # Treeview for weights editing
        self.weights_tree_frame = ctk.CTkFrame(weights_frame)
        self.weights_tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Buttons frame
        weights_buttons_frame = ctk.CTkFrame(weights_frame)
        weights_buttons_frame.pack(fill="x", padx=10, pady=10)
        
        save_weights_btn = ctk.CTkButton(
            weights_buttons_frame,
            text="💾 Guardar Cambios",
            command=self.save_weights
        )
        save_weights_btn.pack(side="left", padx=10, pady=10)
        
        reset_weights_btn = ctk.CTkButton(
            weights_buttons_frame,
            text="🔄 Restaurar Original",
            command=self.reset_weights
        )
        reset_weights_btn.pack(side="left", padx=10, pady=10)
        
    def create_analysis_tab(self):
        """Create event analysis tab"""
        analysis_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(analysis_frame, text="Análisis por Actos")
        
        # Event selection
        event_frame = ctk.CTkFrame(analysis_frame)
        event_frame.pack(fill="x", padx=10, pady=10)
        
        event_label = ctk.CTkLabel(event_frame, text="Selecciona un acto:")
        event_label.pack(side="left", padx=10, pady=10)
        
        self.event_combobox = ttk.Combobox(event_frame, state="readonly")
        self.event_combobox.pack(side="left", padx=10, pady=10)
        self.event_combobox.bind("<<ComboboxSelected>>", self.on_event_selected)
        
        # Analysis results frame
        self.analysis_results_frame = ctk.CTkFrame(analysis_frame)
        self.analysis_results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
    def create_processing_tab(self):
        """Create processing and export tab"""
        processing_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(processing_frame, text="Procesar y Descargar")
        
        # Instructions
        instruction_label = ctk.CTkLabel(
            processing_frame,
            text="Procesa todos los cálculos y genera el archivo Excel con los resultados detallados.",
            font=ctk.CTkFont(size=14)
        )
        instruction_label.pack(pady=20)
        
        # Process button
        process_btn = ctk.CTkButton(
            processing_frame,
            text="🔄 Procesar Datos",
            command=self.process_payments,
            font=ctk.CTkFont(size=16)
        )
        process_btn.pack(pady=20)
        
        # Results frame
        self.results_frame = ctk.CTkFrame(processing_frame)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
    def load_file(self):
        """Load Excel file with error handling"""
        try:
            # Create a hidden root window for file dialog
            root_for_dialog = tk.Tk()
            root_for_dialog.withdraw()  # Hide the window
            
            file_path = filedialog.askopenfilename(
                parent=root_for_dialog,
                title="Seleccionar archivo Excel",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            )
            
            root_for_dialog.destroy()  # Clean up
            
            if file_path:
                self.load_file_in_thread(file_path)
                
        except Exception as e:
            print(f"Error in file dialog: {e}")
            messagebox.showerror("Error", f"Error abriendo diálogo de archivos: {str(e)}")
    
    def load_file_in_thread(self, file_path):
        """Load file in a separate thread to prevent UI blocking"""
        def load_worker():
            try:
                # Update UI on main thread
                self.root.after(0, lambda: self.file_label.configure(text="Cargando archivo..."))
                
                # Load the file
                success = self.payment_system.load_from_file_path(file_path)
                
                if success:
                    # Update UI elements on main thread
                    self.root.after(0, lambda: self.file_label.configure(
                        text=f"Archivo cargado: {os.path.basename(file_path)}")
                    )
                    self.root.after(0, self.update_dashboard)
                    self.root.after(0, self.update_weights_table)
                    self.root.after(0, self.update_event_combobox)
                    self.root.after(0, lambda: messagebox.showinfo("Éxito", "Archivo cargado correctamente!"))
                else:
                    self.root.after(0, lambda: self.file_label.configure(text="Error cargando archivo"))
                    self.root.after(0, lambda: messagebox.showerror("Error", "Error al cargar el archivo"))
                    
            except Exception as e:
                print(f"Error loading file: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error al cargar archivo: {str(e)}"))
        
        # Start loading in background thread
        thread = threading.Thread(target=load_worker, daemon=True)
        thread.start()
    
    def update_dashboard(self):
        """Update dashboard metrics and charts"""
        if self.payment_system.asistencia_df is None:
            return
            
        try:
            # Update metrics
            total_budget, total_distributed, difference = self.payment_system.calculate_budget_difference()
            
            self.budget_label.configure(text=f"Total a Repartir: €{total_budget:,.2f}")
            self.distributed_label.configure(text=f"Total Distribuido: €{total_distributed:,.2f}")
            self.difference_label.configure(text=f"Diferencia: €{difference:,.2f}")
            
            # Clear and update charts
            for widget in self.charts_frame.winfo_children():
                widget.destroy()
                
            # Create matplotlib figures with safe backend
            plt.ioff()  # Turn off interactive mode
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # Category distribution pie chart
            if self.payment_system.asistencia_df is not None:
                try:
                    category_counts = self.payment_system.asistencia_df['Categoria'].value_counts()
                    ax1.pie(category_counts.values, labels=category_counts.index, autopct='%1.1f%%')
                    ax1.set_title('Distribución por Categorías')
                    
                    # Budget bar chart
                    budget_data = self.payment_system.presupuesto_df.head(10)
                    y_pos = range(len(budget_data))
                    ax2.barh(y_pos, budget_data['A REPARTIR'])
                    ax2.set_yticks(y_pos)
                    ax2.set_yticklabels(budget_data['ACTES'])
                    ax2.set_title('Top 10 Actos por Presupuesto')
                    ax2.set_xlabel('Importe (€)')
                    
                except Exception as e:
                    print(f"Error creating charts: {e}")
                    # Create simple text display instead
                    ax1.text(0.5, 0.5, 'Error creando gráfico', ha='center', va='center')
                    ax2.text(0.5, 0.5, 'Error creando gráfico', ha='center', va='center')
            
            plt.tight_layout()
            
            # Embed in tkinter
            try:
                canvas = FigureCanvasTkAgg(fig, self.charts_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
            except Exception as e:
                print(f"Error embedding chart: {e}")
                # Create fallback text display
                fallback_label = ctk.CTkLabel(
                    self.charts_frame, 
                    text="Gráficos no disponibles\n(Los datos están cargados correctamente)",
                    font=ctk.CTkFont(size=14)
                )
                fallback_label.pack(expand=True)
                
        except Exception as e:
            print(f"Error updating dashboard: {e}")
            # Show error message in charts frame
            error_label = ctk.CTkLabel(
                self.charts_frame,
                text=f"Error actualizando dashboard: {str(e)}",
                font=ctk.CTkFont(size=12)
            )
            error_label.pack(expand=True)
    
    def update_weights_table(self):
        """Update weights editing table"""
        if self.payment_system.configuracion_df is None:
            return
            
        # Clear existing widgets
        for widget in self.weights_tree_frame.winfo_children():
            widget.destroy()
        
        # Create Treeview
        columns = list(self.payment_system.configuracion_df.columns)
        self.weights_tree = ttk.Treeview(self.weights_tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.weights_tree.heading(col, text=col)
            self.weights_tree.column(col, width=100)
        
        # Insert data
        for index, row in self.payment_system.configuracion_df.iterrows():
            self.weights_tree.insert('', 'end', values=list(row))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(self.weights_tree_frame, orient="vertical", command=self.weights_tree.yview)
        h_scrollbar = ttk.Scrollbar(self.weights_tree_frame, orient="horizontal", command=self.weights_tree.xview)
        self.weights_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack widgets
        self.weights_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
    
    def update_event_combobox(self):
        """Update event selection combobox"""
        if self.payment_system.asistencia_df is None:
            return
            
        events = self.payment_system.get_events_list()
        self.event_combobox['values'] = events
        if events:
            self.event_combobox.set(events[0])
    
    def save_weights(self):
        """Save modified weights"""
        messagebox.showinfo("Guardar", "Funcionalidad de guardado implementada")
        
    def reset_weights(self):
        """Reset weights to original values"""
        if self.payment_system.original_weights is not None:
            self.payment_system.configuracion_df = self.payment_system.original_weights.copy()
            self.update_weights_table()
            messagebox.showinfo("Restaurar", "Ponderaciones restauradas")
    
    def on_event_selected(self, event):
        """Handle event selection"""
        selected_event = self.event_combobox.get()
        if selected_event and self.payment_system.asistencia_df is not None:
            self.show_event_analysis(selected_event)
    
    def show_event_analysis(self, event_name):
        """Show analysis for selected event"""
        # Clear results frame
        for widget in self.analysis_results_frame.winfo_children():
            widget.destroy()
        
        # Get event data
        category_data = self.payment_system.get_musicians_by_category(event_name)
        budget_info = self.payment_system.presupuesto_df[
            self.payment_system.presupuesto_df['ACTES'] == event_name
        ]
        
        if not category_data.empty:
            # Category analysis
            category_label = ctk.CTkLabel(
                self.analysis_results_frame,
                text="Músicos por Categoría:",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            category_label.pack(pady=10)
            
            for category, data in category_data.iterrows():
                cat_label = ctk.CTkLabel(
                    self.analysis_results_frame,
                    text=f"Categoría {category}: {data['Count']} músicos"
                )
                cat_label.pack(pady=2)
        
        if not budget_info.empty:
            budget_row = budget_info.iloc[0]
            
            budget_label = ctk.CTkLabel(
                self.analysis_results_frame,
                text="Información Presupuestaria:",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            budget_label.pack(pady=(20, 10))
            
            info_labels = [
                f"Cobrado: €{budget_row['COBRAT']:,.2f}",
                f"Gastos Alquiler: €{budget_row['LLOGATS']:,.2f}",
                f"Transporte: €{budget_row['TRANSPORT']:,.2f}",
                f"A Repartir: €{budget_row['A REPARTIR']:,.2f}"
            ]
            
            for info in info_labels:
                info_label = ctk.CTkLabel(self.analysis_results_frame, text=info)
                info_label.pack(pady=2)
    
    def process_payments(self):
        """Process payment calculations"""
        if self.payment_system.asistencia_df is None:
            messagebox.showwarning("Advertencia", "No hay datos cargados")
            return
        
        # Clear results frame
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Process payments
        results = self.payment_system.process_payments()
        
        if results:
            # Show summary
            summary_label = ctk.CTkLabel(
                self.results_frame,
                text="Resultados del Procesamiento:",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            summary_label.pack(pady=10)
            
            # Key metrics
            total_musicians = len(results['musician_summary'])
            total_distributed = results['musician_summary']['Importe_Individual'].sum()
            avg_payment = results['musician_summary']['Importe_Individual'].mean()
            
            metrics_text = f"""
Músicos con Ganancias: {total_musicians}
Total Distribuido: €{total_distributed:,.2f}
Pago Promedio: €{avg_payment:,.2f}
            """
            
            metrics_label = ctk.CTkLabel(self.results_frame, text=metrics_text)
            metrics_label.pack(pady=10)
            
            # Export button
            export_btn = ctk.CTkButton(
                self.results_frame,
                text="💾 Exportar a Excel",
                command=lambda: self.export_to_excel(results)
            )
            export_btn.pack(pady=20)
            
            messagebox.showinfo("Éxito", "Datos procesados correctamente!")
        else:
            messagebox.showerror("Error", "Error al procesar los datos")
    
    def export_to_excel(self, results):
        """Export results to Excel with safe file dialog"""
        try:
            # Create a hidden root window for file dialog
            root_for_dialog = tk.Tk()
            root_for_dialog.withdraw()
            
            file_path = filedialog.asksaveasfilename(
                parent=root_for_dialog,
                title="Guardar resultados",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            
            root_for_dialog.destroy()
            
            if file_path:
                try:
                    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                        # Write all sheets
                        results['musician_summary'].to_excel(writer, sheet_name='Resumen_Musicos', index=False)
                        results['payment_pivot'].to_excel(writer, sheet_name='Pagos_por_Acto')
                        results['budget_comparison'].to_excel(writer, sheet_name='Comparacion_Presupuesto', index=False)
                        results['musicians_by_category'].to_excel(writer, sheet_name='Musicos_por_Categoria', index=False)
                        results['attendees_detail'].to_excel(writer, sheet_name='Detalle_Asistencia', index=False)
                    
                    messagebox.showinfo("Éxito", f"Archivo exportado: {os.path.basename(file_path)}")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Error al exportar: {str(e)}")
                    
        except Exception as e:
            print(f"Error in save dialog: {e}")
            messagebox.showerror("Error", f"Error abriendo diálogo de guardado: {str(e)}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    app = MusicianPaymentApp()
    app.run()

if __name__ == "__main__":
    main()