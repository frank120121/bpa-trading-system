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
        CREATE TABLE IF NOT EXISTS Products (
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
        print("Table 'Products' created successfully!")
    conn.close()

def search_products_by_sku(sku_ending):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Find products that end with the given SKU digits
    cursor.execute("SELECT SKU, Hook, Color, Size FROM Products WHERE SKU LIKE ?", (f"%{sku_ending}",))
    products = cursor.fetchall()
    
    conn.close()

    return products

def update_hook_by_sku(sku_ending, new_hook):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("UPDATE Products SET Hook = ? WHERE SKU LIKE ?", (new_hook, f"%{sku_ending}",))

    conn.commit()
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


def save_product_to_db(product_data):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Extract product data
    sku = product_data.get('sku')
    cost_per_item = product_data.get('cost_per_item')

    if product_data.get('has_variants'):
        # Handle products with variants
        for variant in product_data['variants']:
            color = variant['color']
            size = variant['size']
            quantity = variant['quantity']

            # Check if this variant already exists
            cursor.execute("SELECT Quantity FROM Products WHERE SKU=? AND Color=? AND Size=?", (sku, color, size))
            result = cursor.fetchone()

            if result:
                # Update product variant if it already exists
                current_quantity = result[0]
                new_quantity = current_quantity + quantity
                cursor.execute("UPDATE Products SET Quantity=?, Cost_per_item=? WHERE SKU=? AND Color=? AND Size=?", 
                               (new_quantity, cost_per_item, sku, color, size))
            else:
                # Insert new product variant if it doesn't exist
                cursor.execute("INSERT INTO Products (Title, Color, Size, Quantity, SKU, Cost_per_item, Board, Row, Column, Hook) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (sku, color, size, quantity, sku, cost_per_item, None, None, None, None))
    else:
        # Handle single product without variants
        color = product_data['color_size']['color']
        size = product_data['color_size']['size']
        quantity = product_data['quantity']

        # Check if the product already exists
        cursor.execute("SELECT Quantity FROM Products WHERE SKU=? AND Color=? AND Size=?", (sku, color, size))
        result = cursor.fetchone()

        if result:
            # Update product if it already exists
            current_quantity = result[0]
            new_quantity = current_quantity + quantity
            cursor.execute("UPDATE Products SET Quantity=?, Cost_per_item=? WHERE SKU=? AND Color=? AND Size=?", 
                           (new_quantity, cost_per_item, sku, color, size))
        else:
            # Insert new product if it doesn't exist
            cursor.execute("INSERT INTO Products (Title, Color, Size, Quantity, SKU, Cost_per_item, Board, Row, Column, Hook) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (sku, color, size, quantity, sku, cost_per_item, None, None, None, None))

    conn.commit()
    conn.close()



def display_database_content():
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query("SELECT * from Products", conn)
    conn.close()
    print(df)

if __name__ == '__main__':
    create_table_if_not_exists()
    display_database_content()

