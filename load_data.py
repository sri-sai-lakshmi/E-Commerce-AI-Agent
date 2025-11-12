# load_data.py
import pandas as pd
from sqlalchemy import create_engine
import os
import glob

# --- CONFIGURATION ---
# !!! **UPDATE THESE VALUES** !!!
DB_USER = "root" 
DB_PASSWORD = "" # Your MySQL password
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "olist_db"

# Path to the folder containing your 9 CSV files
# Make sure your CSV files are in a folder named 'data' in your project directory
# or update this path.
CSV_FOLDER_PATH = "./"
# --- END CONFIGURATION ---

# Create the database connection string
connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    engine = create_engine(connection_string)
    print("Database connection successful.")
except Exception as e:
    print(f"Error connecting to database: {e}")
    print("Please check your DB_USER, DB_PASSWORD, and other settings.")
    exit()

# Find all CSV files in the specified folder
csv_files = glob.glob(os.path.join(CSV_FOLDER_PATH, "*.csv"))

if not csv_files:
    print(f"No CSV files found in '{CSV_FOLDER_PATH}'.")
    print("Please make sure your CSV files are in the correct directory.")
    exit()

print(f"Found {len(csv_files)} CSV files. Starting data load...")

for csv_file in csv_files:
    # Extract a clean table name from the file name
    # e.g., 'olist_customers_dataset.csv' -> 'olist_customers_dataset'
    table_name = os.path.basename(csv_file).replace('.csv', '')

    print(f"\nProcessing {csv_file} -> table '{table_name}'...")

    try:
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(csv_file)

        # Clean column names (remove quotes, etc.)
        df.columns = df.columns.str.strip().str.strip('"')

        print(f"  Read {len(df)} rows. Columns: {list(df.columns)}")

        # Write the DataFrame to the MySQL database
        # 'if_exists='replace'' will overwrite the table if it already exists.
        # Use 'if_exists='append'' if you want to add data, or 'fail' to error.
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)

        print(f"  Successfully loaded data into table '{table_name}'.")

    except Exception as e:
        print(f"  Error processing file {csv_file}: {e}")

print("\n--- Data loading complete! ---")
print(f"All CSV files have been loaded into the '{DB_NAME}' database.")
