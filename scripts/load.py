#!/usr/bin/env python3
import pathlib
import duckdb
import argparse

def load_parquet_files_to_duckdb(base_dir: str, duckdb_path: str):
    """
    Load parquet files into DuckDB tables, skipping the profiling folder.
    """
    # Connect to DuckDB
    con = duckdb.connect(duckdb_path)
    
    # Get all parquet files
    base_path = pathlib.Path(base_dir)
    for db_dir in base_path.iterdir():
        if not db_dir.is_dir() or db_dir.name == 'profiling':
            continue
            
        for table_dir in db_dir.iterdir():
            if not table_dir.is_dir():
                continue
                
            parquet_file = table_dir / f"{table_dir.name}.parquet"
            if parquet_file.exists():
                table_name = table_dir.name
                query = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM '{parquet_file}'"
                con.execute(query)
                print(f"Created table {table_name}")
    
    con.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load parquet files into DuckDB')
    parser.add_argument('--base-dir', default='.evidence/template/static/data',
                      help='Base directory containing parquet files')
    parser.add_argument('--duckdb-path', default='sources/profiling/database.duckdb',
                      help='Path to DuckDB database')
    
    args = parser.parse_args()
    load_parquet_files_to_duckdb(args.base_dir, args.duckdb_path)