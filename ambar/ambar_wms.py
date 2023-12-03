from ambar_inventario import DATABASE_PATH
import sqlite3

def remove_columns_except_hook():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Step 2: Create a temporary table without Board, Row, and Column columns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Products_temp3 (
        ID INTEGER PRIMARY KEY,
        Title TEXT,
        Color TEXT,
        Size TEXT,
        Quantity INTEGER,
        SKU TEXT,
        Cost_per_item REAL,
        Date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        Hook TEXT DEFAULT ''
    )
    """)
    
    # Copy data from the original table to the temporary table
    cursor.execute("""
    INSERT INTO Products_temp3 (ID, Title, Color, Size, Quantity, SKU, Cost_per_item, Date, Hook)
    SELECT ID, Title, Color, Size, Quantity, SKU, Cost_per_item, Date, Hook FROM Products
    """)
    
    # Step 3: Delete the original table
    cursor.execute("DROP TABLE Products")
    
    # Step 4: Rename the temporary table to the original table's name
    cursor.execute("ALTER TABLE Products_temp3 RENAME TO Products")
    
    conn.commit()
    conn.close()

# Run the function to make changes
remove_columns_except_hook()

