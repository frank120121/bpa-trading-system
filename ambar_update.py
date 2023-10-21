import sqlite3
import pandas as pd
import math

DATABASE_PATH = 'C:/Users/p7016/Documents/bpa/ambar_inventario.db'
SHOP_CSV_PATH = 'C:/Users/p7016/Documents/bpa/shopify_import.csv'

# Read from SQLite to DataFrame
def custom_round(price):
    rounded_price = math.ceil(price / 50.0) * 50.0 - 0.01
    return rounded_price

conn = sqlite3.connect(DATABASE_PATH)
df = pd.read_sql_query("SELECT * from Products", conn)
conn.close()


# Pricing Strategy
def calculate_price(cost):
    if cost * 4 > 750:
        price = cost * 3
    else:
        price = cost * 3
        
    return custom_round(price)

def compare_at(cost):
    return calculate_price(cost) * 1.15

# Transformations
df['Handle'] = df['SKU']
df['Title'] = df['Title']
df['Body (HTML)'] = df['Title']
df['Vendor'] = 'AMBAR'
df['Product Category'] = 'Lingerie'
df['Type'] = 'Lenceria'
df['Tags'] = 'Lenceria, ropa interior, ropa intima, sexy'
df['Published'] = 'FALSE'
df['Option1 Name'] = 'Color'
df['Option1 Value'] = df['Color']
df['Option2 Name'] = 'Size'
df['Option2 Value'] = df['Size']
df['Option3 Name'] = ''
df['Option3 Value'] = ''
df['Variant SKU'] = df['SKU']
df['Variant Grams'] = 200
df['Variant Inventory Tracker'] = 'shopify'
df['Variant Inventory Qty'] = df['Quantity']
df['Variant Inventory Policy'] = 'deny'
df['Variant Fulfillment Service'] = 'manual'
df['Variant Price'] = df['Cost_per_item'].apply(calculate_price)
df['Variant Compare At Price'] = df['Cost_per_item'].apply(compare_at)
df['Variant Requires Shipping'] = 'True'
df['Variant Taxable'] = 'False'
df['Variant Barcode'] = '' 
df['Image Src'] = '' 
df['Image Position'] = ''
df['Image Alt Text'] = df['Title']
df['Gift Card'] = 'False'
df['SEO Title'] = df['Title']
df['SEO Description'] = df['Title']
df['Variant Weight Unit'] ='g'
df['Status'] = 'Active'

# Select required columns
columns = ['Handle', 'Title', 'Body (HTML)', 'Vendor', 'Product Category', 'Type', 'Tags', 'Published', 'Option1 Name', 'Option1 Value', 
           'Option2 Name', 'Option2 Value', 'Option3 Name', 'Option3 Value', 'Variant SKU', 'Variant Grams', 'Variant Inventory Tracker', 'Variant Inventory Qty', 'Variant Inventory Policy', 
           'Variant Fulfillment Service', 'Variant Price', 'Variant Compare At Price', 'Variant Requires Shipping', 'Variant Taxable', 'Variant Barcode', 'Image Src', 
           'Image Position', 'Image Alt Text', 'Gift Card', 'SEO Title', 'SEO Description', 
           'Variant Weight Unit', 'Status']
shopify_df = df[columns]

# Write to CSV
shopify_df.to_csv(SHOP_CSV_PATH, index=False)
