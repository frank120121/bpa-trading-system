import re
import pandas as pd
from ambar_inventario import update_database_from_csv
import os


def process_file(file_path):
    with open(file_path, 'r', encoding="utf-8") as f:
        lines = f.readlines()
    colors, sizes, quantities, skus, prices = [], [], [], [], []
    for index, line in enumerate(lines):
        line = line.strip()
        if not line:
            #print(f"Line {index + 1}: Skipping empty line.")
            continue
        if line.startswith("Productos"):
            print(f"Line {index + 1}: Identified as header. Skipping.")
            continue
        if line == "Todo está enviado":
            print(f"Line {index + 1}: Identified as footer/status. Skipping.")
            continue
        if re.search(r'(\d+)\s+(\w{2}\d+)', line) or 'El artículo no puede ser devuelto' in re.sub(r'[\t ]+', ' ', line):
                
            if 'El artículo no puede ser devuelto' in line:
                parts = re.search(r'El artículo no puede ser devuelto.*?(\d+)\s+([a-z]{2}\w+)', re.sub(r'[\t ]+', ' ', line))
                if parts:
                    quantity, sku = parts.group(1), parts.group(2)
                else:
                    print(f"Error in extracting SKU and quantity at line {index + 1}. Skipping.")
                    continue
            else:
                parts = re.match(r'(\d+)\s+(\w{2}\d+)', line)
                if parts:
                    quantity, sku = parts.group(1), parts.group(2)
                else:
                    print(f"Error in extracting SKU and quantity at line {index + 1}. Skipping.")
                    continue

            quantities.append(quantity)
            skus.append(sku)
            
            # Search backward for color/size
            color_found = False
            size_found = False
            color, size = "", "NA"
            
            for prev_index, prev_line in enumerate(reversed(lines[:index])):
                prev_line = prev_line.strip()
                
                if not prev_line:  # Skip empty lines
                    continue
                
                if re.search(r'\$MXN(\d+\.\d{2})', prev_line):  # This is a price line
                    continue
                elif "/" in prev_line and not color_found:
                    color, size = [part.strip() for part in prev_line.split('/', 1)]
                    if '/' in size:
                        size = size.split('/')[0]
                    print(f"Line {index - prev_index}: Extracted Color: {color}, Size: {size}")
                    break
                elif not color_found:
                    color = prev_line
                    print(f"Line {index - prev_index}: Extracted Color: {color}")
                    break
            
            colors.append(color)
            sizes.append(size)
            
            # Search forward for price
            for next_line in lines[index:]:
                price_search = re.search(r'\$MXN(\d+\.\d{2})', next_line)
                if price_search:
                    prices.append(price_search.group(1))
                    print(f"Line {index + 1 + lines[index:].index(next_line)}: Extracted Price: {price_search.group(1)}")
                    break

    # print(f"\nColors: {len(colors)}")
    # print(f"Sizes: {len(sizes)}")
    # print(f"Quantities: {len(quantities)}")
    # print(f"SKUs: {len(skus)}")
    # print(f"Prices: {len(prices)}")

    if len(colors) == len(sizes) == len(quantities) == len(skus) == len(prices):
        df = pd.DataFrame({
            'Color': colors,
            'Size': sizes,
            'Quantity': quantities,
            'SKU': skus,
            'Price': prices
        })
        # print(df)
        temp_csv_path = 'temp_data.csv'
        df.to_csv(temp_csv_path, index=False)
        update_database_from_csv(temp_csv_path)
    else:
        print("\nData extraction was inconsistent. Please review the input text and the extraction logic.")

# Read order numbers from 'ordenes_shein.txt'
with open(r"C:\Users\p7016\Documents\bpa\ordenes_shein.txt", 'r') as f:
    order_numbers = [line.strip() for line in f if line.strip()]

# For each order number, generate path and process the file
for order_number in order_numbers:
    file_path = fr"C:\Users\p7016\Documents\bpa\{order_number}.txt"
    if os.path.exists(file_path):
        process_file(file_path)
    else:
        print(f"File {file_path} does not exist. Skipping.")
