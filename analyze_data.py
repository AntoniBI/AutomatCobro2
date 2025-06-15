import pandas as pd
import numpy as np

def analyze_excel_structure():
    """Analyze the structure of the Excel file"""
    file_path = '/Users/antonimolla/Desktop/Claude_Cobro/Data/Actes.xlsx'
    
    # Load Excel file
    excel_file = pd.ExcelFile(file_path)
    
    print("=== EXCEL FILE ANALYSIS ===")
    print(f"File: {file_path}")
    print(f"Number of sheets: {len(excel_file.sheet_names)}")
    print("\nAvailable sheets:")
    
    for i, sheet_name in enumerate(excel_file.sheet_names):
        print(f"{i+1}. {sheet_name}")
        
        # Load each sheet
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"   - Shape: {df.shape}")
        print(f"   - Columns: {list(df.columns)}")
        
        # Show first few rows
        print(f"   - First 3 rows:")
        print(df.head(3).to_string(index=False))
        print(f"   - Data types:")
        print(df.dtypes.to_string())
        print("-" * 80)

if __name__ == "__main__":
    analyze_excel_structure()