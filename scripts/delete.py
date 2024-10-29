import os
import shutil
import duckdb
from pathlib import Path

def remove_profiling_data(table_name: str):
    """
    Removes profiling data for a specific table, including its folder and database entry.
    Includes safety check to prevent deletion if only one table exists.
    
    Args:
        table_name (str): Name of the table to remove
    """
    # Connect to the database
    db_path = "sources/profiling/database.duckdb"
    conn = duckdb.connect(db_path)
    
    try:
        # Get count of tables in main schema
        table_count = conn.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchone()[0]
        
        if table_count <= 1:
            print(f"Cannot remove table - only {table_count} table exist in the main schema. Add more tables before removing.")
            return
        
        # Path to the profiling folder
        profiling_folder = Path(f".evidence/template/static/data/profiling/{table_name}")
        
        # Remove the folder if it exists
        if profiling_folder.exists():
            shutil.rmtree(profiling_folder)
            print(f"Removed folder: {profiling_folder}")
        
        # Drop the table from the database
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        print(f"Dropped table '{table_name}' from database")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    # Example usage
    table_to_remove = "your_table_name"
    remove_profiling_data(table_to_remove)
