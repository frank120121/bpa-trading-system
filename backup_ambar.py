import shutil
import os
from datetime import datetime
from ambar_inventario import DATABASE_PATH

def backup_database():
    # Generate backup filename with timestamp
    backup_filename = os.path.splitext(DATABASE_PATH)[0] + '_' + datetime.now().strftime('%Y%m%d_%H%M%S') + os.path.splitext(DATABASE_PATH)[1]
    
    # Copy the original database file to the backup file
    shutil.copy2(DATABASE_PATH, backup_filename)
    print(f"Database backed up to {backup_filename}")

# Run the backup function
backup_database()