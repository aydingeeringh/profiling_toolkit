#!/usr/bin/env python3
import duckdb

def create_pattern_tables(duckdb_path: str):
    """
    Create pattern tables for all tables in the main schema and
    drop pattern tables for tables that no longer exist in main.
    """
    # Connect to DuckDB
    con = duckdb.connect(duckdb_path)
    
    # Create patterns schema if it doesn't exist
    con.execute("CREATE SCHEMA IF NOT EXISTS patterns")
    
    # Get all tables from main schema
    main_tables = set(row[0] for row in con.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'main'
    """).fetchall())
    
    # Get all pattern tables
    pattern_tables = set(row[0] for row in con.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'patterns'
    """).fetchall())
    
    # Drop pattern tables for non-existent main tables
    for pattern_table in pattern_tables:
        if pattern_table.startswith('pattern_'):
            original_table = pattern_table[8:]  # Remove 'pattern_' prefix
            if original_table not in main_tables:
                try:
                    con.execute(f"DROP TABLE patterns.{pattern_table}")
                    print(f"Dropped obsolete pattern table for {original_table}")
                except Exception as e:
                    print(f"Error dropping pattern table {pattern_table}: {str(e)}")
    
    # Create or replace pattern tables for existing main tables
    for table_name in main_tables:
        pattern_query = f"""
        CREATE OR REPLACE TABLE patterns.pattern_{table_name} AS 
        SELECT REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(COLUMNS(*)::text,
                    '[a-z]', 'a', 'g'),
                '[A-Z]', 'A', 'g'),
            '[0-9]', 'N', 'g') 
        FROM {table_name}
        """
        
        try:
            con.execute(pattern_query)
            print(f"Created pattern table for {table_name}")
        except Exception as e:
            print(f"Error creating pattern table for {table_name}: {str(e)}")
    
    # Print summary
    final_pattern_tables = con.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'patterns'
    """).fetchone()
    
    print(f"\nFinal count: {final_pattern_tables[0]} pattern tables")
    
    con.close()

if __name__ == "__main__":
    duckdb_path = 'sources/needful_things/needful_things.duckdb'
    create_pattern_tables(duckdb_path)