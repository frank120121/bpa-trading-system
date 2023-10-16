import sqlite3
import pandas as pd

DATABASE_PATH = 'ambar_inventario.db'

def create_table_if_not_exists():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Products';")
    table_exists = cursor.fetchone()
    if not table_exists:
        cursor.execute("""
        CREATE TABLE Products (
            ID INTEGER PRIMARY KEY,
            Color TEXT,
            Size TEXT,
            Quantity INTEGER,
            SKU TEXT,
            Price REAL
        )
        """)
        print("Table 'Products' created successfully!")
    conn.close()

def update_database_from_csv(csv_path):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    df = pd.read_csv(csv_path)
    for index, row in df.iterrows():
        cursor.execute("SELECT Quantity FROM Products WHERE SKU=? AND Size=?", (row['SKU'], row['Size']))
        result = cursor.fetchone()

        if result:
            new_quantity = result[0] + row['Quantity']
            cursor.execute("UPDATE Products SET Quantity=? WHERE SKU=? AND Size=?", (new_quantity, row['SKU'], row['Size']))
        else:
            cursor.execute("INSERT INTO Products (Color, Size, Quantity, SKU, Price) VALUES (?, ?, ?, ?, ?)",
                           (row['Color'], row['Size'], row['Quantity'], row['SKU'], row['Price']))
    
    conn.commit()
    conn.close()
    print("Database updated successfully!")


def display_database_content():
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query("SELECT * from Products", conn)
    conn.close()
    print(df)

if __name__ == '__main__':
    create_table_if_not_exists()
    display_database_content()

