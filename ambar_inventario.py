import sqlite3
import pandas as pd
pd.set_option('display.max_rows', None)

DATABASE_PATH = 'C:/Users/p7016/Documents/bpa/ambar_inventario.db'

def create_table_if_not_exists():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Products';")
    table_exists = cursor.fetchone()
    if not table_exists:
        cursor.execute("""
        CREATE TABLE Products (
            ID INTEGER PRIMARY KEY,
            Title TEXT,
            Color TEXT,
            Size TEXT,
            Quantity INTEGER,
            SKU TEXT,
            Cost_per_item REAL,
            Date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("Table 'Products' created successfully!")
    conn.close()

def update_database_from_csv(csv_path):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    df = pd.read_csv(csv_path)
    
    for index, row in df.iterrows():
        # Ensure Quantity is an integer
        quantity = int(row['Quantity'])
        
        cursor.execute("SELECT Quantity FROM Products WHERE SKU=? AND Size=? AND Title=?", 
                       (row['SKU'], row['Size'], row['Title']))
        result = cursor.fetchone()

        if result:
            new_quantity = result[0] + quantity
            cursor.execute("UPDATE Products SET Quantity=? WHERE SKU=? AND Size=? AND Title=?", 
                           (new_quantity, row['SKU'], row['Size'], row['Title']))
        else:
            cursor.execute("INSERT INTO Products (Title, Color, Size, Quantity, SKU, Cost_per_item) VALUES (?, ?, ?, ?, ?, ?)",
                           (row['Title'], row['Color'], row['Size'], quantity, row['SKU'], row['Cost_per_item']))
    
    conn.commit()
    conn.close()
    print(f"Database updated successfully! {csv_path}")




def display_database_content():
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query("SELECT * from Products", conn)
    conn.close()
    print(df)

if __name__ == '__main__':
    create_table_if_not_exists()
    display_database_content()

