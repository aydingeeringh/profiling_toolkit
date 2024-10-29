#!/usr/bin/env python3
import duckdb

def create_summary_tables(duckdb_path: str):
    """
    Create summary tables with column statistics for all tables in the main schema
    and drop summary tables for tables that no longer exist in main.
    """
    # Connect to DuckDB
    con = duckdb.connect(duckdb_path)
    
    # Create summaries schema if it doesn't exist
    con.execute("CREATE SCHEMA IF NOT EXISTS summaries")
    
    # Get all tables from main schema
    main_tables = set(row[0] for row in con.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'main'
    """).fetchall())
    
    # Get all summary tables
    summary_tables = set(row[0] for row in con.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'summaries'
    """).fetchall())
    
    # Drop summary tables for non-existent main tables
    for summary_table in summary_tables:
        if summary_table.startswith('summary_'):
            original_table = summary_table[8:]  # Remove 'summary_' prefix
            if original_table not in main_tables:
                try:
                    con.execute(f"DROP TABLE summaries.{summary_table}")
                    print(f"Dropped obsolete summary table for {original_table}")
                except Exception as e:
                    print(f"Error dropping summary table {summary_table}: {str(e)}")
    
    # Create or replace summary tables for existing main tables
    for table_name in main_tables:
        summary_query = f"""
        CREATE OR REPLACE TABLE summaries.summary_{table_name} AS 
        WITH column_stats AS (
            SELECT
                c.column_name,
                c.ordinal_position,
                c.data_type,
                MIN(LENGTH(column_value::TEXT)) AS min_length,
                MAX(LENGTH(column_value::TEXT)) AS max_length,
                AVG(LENGTH(column_value::TEXT)) AS mean_length,
                MEDIAN(LENGTH(column_value::TEXT)) AS median_length,
                STDDEV_SAMP(LENGTH(column_value::TEXT)) AS std_dev_length,
                STDDEV_SAMP(LENGTH(column_value::TEXT)) / SQRT(COUNT(*)) AS std_error_length,
                COUNT(DISTINCT regexp_replace(regexp_replace(regexp_replace(column_value::TEXT,
                                '[a-z]',
                                'a',
                                'g'),
                            '[A-Z]',
                            'A',
                            'g'),
                        '[0-9]',
                        'N',
                        'g')) AS pattern_count
            FROM
                (SELECT COLUMNS(*)::TEXT FROM {table_name}) UNPIVOT (column_value FOR column_name IN(*)) u
                JOIN information_schema.columns c ON c.column_name = u.column_name
                    AND c.table_name = '{table_name}'
                GROUP BY
                    c.column_name,
                    c.ordinal_position,
                    c.data_type
        )
        SELECT
            *
        FROM
            column_stats
        ORDER BY
            ordinal_position
        """
        
        try:
            con.execute(summary_query)
            print(f"Created summary table for {table_name}")
            
            # Print row count for verification
            row_count = con.execute(f"SELECT COUNT(*) FROM summaries.summary_{table_name}").fetchone()[0]
            print(f"  - Generated {row_count} column summaries")
            
        except Exception as e:
            print(f"Error creating summary table for {table_name}: {str(e)}")
    
    # Print final summary
    final_summary_tables = con.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'summaries'
    """).fetchone()
    
    print(f"\nFinal count: {final_summary_tables[0]} summary tables")
    
    con.close()

if __name__ == "__main__":
    duckdb_path = 'sources/needful_things/needful_things.duckdb'
    create_summary_tables(duckdb_path)