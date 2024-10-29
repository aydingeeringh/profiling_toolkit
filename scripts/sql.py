import os
from pathlib import Path
import duckdb

def generate_sql_files():
    # Connect to DuckDB database
    db_path = 'sources/profiling/database.duckdb'
    conn = duckdb.connect(db_path)
    
    try:
        # Get all tables and their schemas from DuckDB
        tables_query = """
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE'
        """
        tables = conn.execute(tables_query).fetchall()
        
        # Group tables by schema
        schema_tables = {}
        for schema, table in tables:
            if schema not in schema_tables:
                schema_tables[schema] = []
            schema_tables[schema].append(table)
        
        # Base directory for SQL files
        base_dir = Path('sources/profiling')
        
        # Process each schema and its tables
        for schema, table_names in schema_tables.items():
            # Create schema directory if it doesn't exist
            schema_dir = base_dir / schema
            schema_dir.mkdir(parents=True, exist_ok=True)
            
            # Get existing SQL files
            existing_files = {f.stem: f for f in schema_dir.glob('*.sql')}
            
            # Remove files for tables that no longer exist
            for file_name in list(existing_files.keys()):
                if file_name not in table_names:
                    existing_files[file_name].unlink()
                    print(f"Removed obsolete file: {schema}/{file_name}.sql")
            
            # Generate SQL files for each table
            for table_name in table_names:
                sql_file = schema_dir / f'{table_name}.sql'
                
                # Skip if file already exists
                if sql_file.exists():
                    print(f"Skipping existing file: {schema}/{table_name}.sql")
                    continue
                
                # Generate and write SQL query to file
                sql_query = f"select * from {schema}.{table_name}"
                
                with open(sql_file, 'w') as f:
                    f.write(sql_query)
                print(f"Generated new file: {schema}/{table_name}.sql")
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    generate_sql_files()
