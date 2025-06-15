#!/usr/bin/env python3
"""
Simple Desktop Application for Sistema de Cobro Musical
Using pure tkinter for maximum compatibility
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import os
from io import BytesIO

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

class SimplePaymentApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema de Cobro Musical - Simple")
        self.root.geometry("1000x700")
        
        # Initialize payment system
        self.payment_system = MusicianPaymentSystem()
        
        # Store the current file path
        self.current_file = None
        
        # Create main interface
        self.create_interface()
        
    def create_interface(self):
        """Create the main application interface"""
        # Main title
        title_frame = tk.Frame(self.root, bg='#2e5984', height=60)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🎵 Sistema de Cobro Musical",
            font=("Arial", 20, "bold"),
            bg='#2e5984',
            fg='white'
        )
        title_label.pack(expand=True)
        
        # File operations frame
        file_frame = tk.Frame(self.root, bg='#f0f0f0', height=50)
        file_frame.pack(fill='x', padx=10, pady=5)
        file_frame.pack_propagate(False)
        
        self.file_label = tk.Label(
            file_frame,
            text="No hay archivo cargado",
            font=("Arial", 10),
            bg='#f0f0f0'
        )
        self.file_label.pack(side='left', padx=10, pady=15)
        
        load_btn = tk.Button(
            file_frame,
            text="📁 Cargar Archivo Excel",
            command=self.load_file,
            font=("Arial", 10),
            bg='#4CAF50',
            fg='white',
            cursor='hand2'
        )
        load_btn.pack(side='right', padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_processing_tab()
        
        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="Listo",
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Arial", 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_dashboard_tab(self):
        """Create dashboard tab"""
        dashboard_frame = tk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Dashboard")
        
        # Metrics frame
        metrics_frame = tk.LabelFrame(dashboard_frame, text="Métricas Principales", font=("Arial", 12, "bold"))
        metrics_frame.pack(fill='x', padx=10, pady=10)
        
        metrics_inner = tk.Frame(metrics_frame)
        metrics_inner.pack(fill='x', padx=10, pady=10)
        
        self.budget_label = tk.Label(
            metrics_inner,
            text="Total a Repartir: €0.00",
            font=("Arial", 11),
            bg='#e3f2fd',
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        self.budget_label.pack(side='left', padx=10, fill='x', expand=True)
        
        self.distributed_label = tk.Label(
            metrics_inner,
            text="Total Distribuido: €0.00",
            font=("Arial", 11),
            bg='#e8f5e8',
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        self.distributed_label.pack(side='left', padx=10, fill='x', expand=True)
        
        self.difference_label = tk.Label(
            metrics_inner,
            text="Diferencia: €0.00",
            font=("Arial", 11),
            bg='#fff3e0',
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        self.difference_label.pack(side='left', padx=10, fill='x', expand=True)
        
        # Data summary frame
        summary_frame = tk.LabelFrame(dashboard_frame, text="Resumen de Datos", font=("Arial", 12, "bold"))
        summary_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.summary_text = tk.Text(summary_frame, height=15, font=("Courier", 10))
        summary_scroll = tk.Scrollbar(summary_frame, orient='vertical', command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        
        self.summary_text.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        summary_scroll.pack(side='right', fill='y', pady=10, padx=(0, 10))
        
    def create_processing_tab(self):
        """Create processing tab"""
        processing_frame = tk.Frame(self.notebook)
        self.notebook.add(processing_frame, text="Procesar y Exportar")
        
        # Instructions
        instruction_frame = tk.Frame(processing_frame)
        instruction_frame.pack(fill='x', padx=10, pady=10)
        
        instruction_label = tk.Label(
            instruction_frame,
            text="Procesa todos los cálculos y genera el archivo Excel con los resultados",
            font=("Arial", 12),
            wraplength=600
        )
        instruction_label.pack()
        
        # Process button
        process_btn = tk.Button(
            processing_frame,
            text="🔄 Procesar Datos",
            command=self.process_payments,
            font=("Arial", 14, "bold"),
            bg='#2196F3',
            fg='white',
            cursor='hand2',
            padx=20,
            pady=10
        )
        process_btn.pack(pady=20)
        
        # Results frame
        self.results_frame = tk.LabelFrame(processing_frame, text="Resultados", font=("Arial", 12, "bold"))
        self.results_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.results_text = tk.Text(self.results_frame, height=10, font=("Courier", 10))
        results_scroll = tk.Scrollbar(self.results_frame, orient='vertical', command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scroll.set)
        
        self.results_text.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        results_scroll.pack(side='right', fill='y', pady=10, padx=(0, 10))
        
    def load_file(self):
        """Load Excel file"""
        try:
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo Excel",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            )
            
            if file_path:
                self.status_bar.config(text="Cargando archivo...")
                self.root.update()
                
                if self.payment_system.load_from_file_path(file_path):
                    self.current_file = file_path
                    filename = os.path.basename(file_path)
                    self.file_label.config(text=f"Archivo cargado: {filename}")
                    self.update_dashboard()
                    self.status_bar.config(text="Archivo cargado correctamente")
                    messagebox.showinfo("Éxito", "Archivo cargado correctamente!")
                else:
                    self.status_bar.config(text="Error cargando archivo")
                    messagebox.showerror("Error", "Error al cargar el archivo")
                    
        except Exception as e:
            self.status_bar.config(text="Error en diálogo de archivos")
            messagebox.showerror("Error", f"Error: {str(e)}")
    
    def update_dashboard(self):
        """Update dashboard with loaded data"""
        if self.payment_system.asistencia_df is None:
            return
            
        try:
            # Update metrics
            total_budget, total_distributed, difference = self.payment_system.calculate_budget_difference()
            
            self.budget_label.config(text=f"Total a Repartir: €{total_budget:,.2f}")
            self.distributed_label.config(text=f"Total Distribuido: €{total_distributed:,.2f}")
            self.difference_label.config(text=f"Diferencia: €{difference:,.2f}")
            
            # Update summary
            self.summary_text.delete(1.0, tk.END)
            
            summary_info = f"""
RESUMEN DE DATOS CARGADOS
{'='*50}

📊 INFORMACIÓN GENERAL:
   • Total músicos: {len(self.payment_system.asistencia_df)}
   • Total eventos: {len(self.payment_system.get_events_list())}
   • Total presupuesto: €{self.payment_system.presupuesto_df['A REPARTIR'].sum():,.2f}

👥 MÚSICOS POR CATEGORÍA:
"""
            
            category_counts = self.payment_system.asistencia_df['Categoria'].value_counts()
            for category, count in category_counts.items():
                summary_info += f"   • Categoría {category}: {count} músicos\n"
            
            summary_info += f"\n💰 TOP 10 EVENTOS POR PRESUPUESTO:\n"
            top_events = self.payment_system.presupuesto_df.nlargest(10, 'A REPARTIR')
            for _, event in top_events.iterrows():
                summary_info += f"   • {event['ACTES']}: €{event['A REPARTIR']:,.2f}\n"
            
            self.summary_text.insert(1.0, summary_info)
            
        except Exception as e:
            print(f"Error updating dashboard: {e}")
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.insert(1.0, f"Error actualizando dashboard: {str(e)}")
    
    def process_payments(self):
        """Process payment calculations"""
        if self.payment_system.asistencia_df is None:
            messagebox.showwarning("Advertencia", "No hay datos cargados")
            return
        
        try:
            self.status_bar.config(text="Procesando datos...")
            self.root.update()
            
            # Process payments
            results = self.payment_system.process_payments()
            
            if results:
                # Clear results
                self.results_text.delete(1.0, tk.END)
                
                # Show summary
                total_musicians = len(results['musician_summary'])
                total_distributed = results['musician_summary']['Importe_Individual'].sum()
                avg_payment = results['musician_summary']['Importe_Individual'].mean()
                
                results_info = f"""
RESULTADOS DEL PROCESAMIENTO
{'='*50}

📈 MÉTRICAS PRINCIPALES:
   • Músicos con ganancias: {total_musicians}
   • Total distribuido: €{total_distributed:,.2f}
   • Pago promedio: €{avg_payment:,.2f}

💰 TOP 10 MÚSICOS CON MAYORES GANANCIAS:
"""
                
                top_musicians = results['musician_summary'].nlargest(10, 'Importe_Individual')
                for _, musician in top_musicians.iterrows():
                    results_info += f"   • {musician['Musico']}: €{musician['Importe_Individual']:,.2f}\n"
                
                results_info += f"\n📊 RESUMEN POR CATEGORÍA:\n"
                category_summary = results['musician_summary'].groupby('Categoria').agg({
                    'Importe_Individual': ['count', 'sum', 'mean']
                }).round(2)
                
                for category in category_summary.index:
                    count = category_summary.loc[category, ('Importe_Individual', 'count')]
                    total = category_summary.loc[category, ('Importe_Individual', 'sum')]
                    avg = category_summary.loc[category, ('Importe_Individual', 'mean')]
                    results_info += f"   • Categoría {category}: {count} músicos, Total: €{total:,.2f}, Promedio: €{avg:,.2f}\n"
                
                self.results_text.insert(1.0, results_info)
                
                # Add export button
                export_btn = tk.Button(
                    self.results_frame,
                    text="💾 Exportar a Excel",
                    command=lambda: self.export_to_excel(results),
                    font=("Arial", 12, "bold"),
                    bg='#4CAF50',
                    fg='white',
                    cursor='hand2'
                )
                export_btn.pack(pady=10)
                
                self.status_bar.config(text="Datos procesados correctamente")
                messagebox.showinfo("Éxito", "Datos procesados correctamente!")
                
            else:
                self.status_bar.config(text="Error procesando datos")
                messagebox.showerror("Error", "Error al procesar los datos")
                
        except Exception as e:
            self.status_bar.config(text="Error durante procesamiento")
            messagebox.showerror("Error", f"Error durante procesamiento: {str(e)}")
    
    def export_to_excel(self, results):
        """Export results to Excel"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Guardar resultados",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            
            if file_path:
                self.status_bar.config(text="Exportando a Excel...")
                self.root.update()
                
                with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                    # Write all sheets
                    results['musician_summary'].to_excel(writer, sheet_name='Resumen_Musicos', index=False)
                    results['payment_pivot'].to_excel(writer, sheet_name='Pagos_por_Acto')
                    results['budget_comparison'].to_excel(writer, sheet_name='Comparacion_Presupuesto', index=False)
                    results['musicians_by_category'].to_excel(writer, sheet_name='Musicos_por_Categoria', index=False)
                    results['attendees_detail'].to_excel(writer, sheet_name='Detalle_Asistencia', index=False)
                
                filename = os.path.basename(file_path)
                self.status_bar.config(text=f"Exportado: {filename}")
                messagebox.showinfo("Éxito", f"Archivo exportado correctamente:\n{filename}")
                
        except Exception as e:
            self.status_bar.config(text="Error exportando")
            messagebox.showerror("Error", f"Error al exportar: {str(e)}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    app = SimplePaymentApp()
    app.run()

if __name__ == "__main__":
    main()