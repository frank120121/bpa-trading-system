import sqlite3
import pandas as pd

# Path to your SQLite database
DATABASE_PATH = 'C:/Users/p7016/Documents/bpa/ambar_inventario.db'

# Connect to the SQLite database
conn = sqlite3.connect(DATABASE_PATH)

# Read data from the 'Products' table into a pandas DataFrame
query = "SELECT * FROM Products"
df = pd.read_sql_query(query, conn)

# Close the connection to the database
conn.close()

# Path where you want to save the Excel file
excel_path = 'C:/Users/p7016/Documents/bpa/products.xlsx'

# Write the DataFrame to an Excel file
df.to_excel(excel_path, index=False)

print(f"Data exported to Excel file at {excel_path}")
