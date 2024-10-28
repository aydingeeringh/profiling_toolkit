import duckdb
import os
import time

def get_duckdb_connection(db_path='sources/profiling/database.duckdb'):
    """Create or connect to a DuckDB database"""
    return duckdb.connect(db_path)

def initialize_database(con):
    """Initialize DuckDB with PostgreSQL extension and connection"""
    con.execute("INSTALL postgres")
    con.execute("LOAD postgres")
    
    # Create secret for PostgreSQL connection
    con.execute("""
    CREATE SECRET IF NOT EXISTS postgres_secret (
        TYPE POSTGRES,
        HOST 'localhost',
        PORT 5432,
        DATABASE 'postgres',
        USER 'postgres',
        PASSWORD 'postgres'
    )
    """)
    
    # Attach PostgreSQL database
    con.execute("ATTACH '' AS postgres_db (TYPE POSTGRES, SCHEMA 'public', SECRET postgres_secret)")
    
    # Create schemas in DuckDB
    con.execute("CREATE SCHEMA IF NOT EXISTS source")
    con.execute("CREATE SCHEMA IF NOT EXISTS patterns")
    con.execute("CREATE SCHEMA IF NOT EXISTS summaries")
    
    print("Database initialized with PostgreSQL connection and schemas.")

def load_postgres_tables(con):
    """Load PostgreSQL tables into DuckDB source schema"""
    tables = con.execute("SHOW TABLES FROM postgres_db").fetchall()
    
    for table in tables:
        table_name = table[0]
        try:
            # Create table in source schema
            con.execute(f"""
            CREATE OR REPLACE TABLE source.{table_name} AS 
            SELECT * FROM postgres_db.{table_name}
            """)
            print(f"Loaded table: source.{table_name}")
        except Exception as e:
            print(f"Error loading table {table_name}: {str(e)}")

def create_pattern_view(con, source_table):
    """Create pattern view for a given table"""
    pattern_table_name = f"patterns.pattern_{source_table}"
    
    # Get column information
    columns = con.execute(f"DESCRIBE source.{source_table}").fetchall()
    
    # Build column transformations
    column_transforms = []
    for col in columns:
        col_name = col[0]
        transform = f"""
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(CAST({col_name} AS TEXT), '[a-z]', 'a', 'g'),
                '[A-Z]', 'A', 'g'
            ),
            '[0-9]', 'N', 'g'
        ) AS {col_name}"""
        column_transforms.append(transform)
    
    # Create view query
    view_query = f"""
    CREATE OR REPLACE VIEW {pattern_table_name} AS 
    SELECT {', '.join(column_transforms)}
    FROM source.{source_table}
    """
    
    con.execute(view_query)
    print(f"Created pattern view: {pattern_table_name}")

def create_summary_table(con, source_table):
    """Create and populate summary table for a given table"""
    summary_table_name = f"summaries.summary_{source_table}"
    
    # Create summary table with new columns
    con.execute(f"""
    CREATE TABLE IF NOT EXISTS {summary_table_name} (
        column_name TEXT,
        ordinal_position INTEGER,
        data_type TEXT,
        min_length INTEGER,
        max_length INTEGER,
        mean_length DOUBLE,
        median_length DOUBLE,
        std_dev_length DOUBLE,
        std_error_length DOUBLE,
        pattern_count BIGINT,
        row_count BIGINT,
        distinct_count BIGINT,
        null_count BIGINT,
        null_percentage DOUBLE,
        min_value TEXT,
        max_value TEXT
    )
    """)
    
    # Get column information
    columns = con.execute(f"DESCRIBE source.{source_table}").fetchall()
    
    # Clear existing summary data
    con.execute(f"DELETE FROM {summary_table_name}")
    
    # Calculate and insert summary statistics for each column
    for i, col in enumerate(columns, 1):
        col_name = col[0]
        data_type = col[1]
        
        summary_query = f"""
        INSERT INTO {summary_table_name}
        SELECT 
            '{col_name}' AS column_name,
            {i} AS ordinal_position,
            '{data_type}' AS data_type,
            COUNT(*) AS row_count,
            COUNT(DISTINCT {col_name}) AS distinct_count,
            COUNT(*) - COUNT({col_name}) AS null_count,
            ROUND(100.0 * (COUNT(*) - COUNT({col_name})) / COUNT(*), 2) AS null_percentage,
            MIN(CAST({col_name} AS TEXT)) AS min_value,
            MAX(CAST({col_name} AS TEXT)) AS max_value,
            MIN(LENGTH(CAST({col_name} AS TEXT))) AS min_length,
            MAX(LENGTH(CAST({col_name} AS TEXT))) AS max_length,
            AVG(LENGTH(CAST({col_name} AS TEXT))) AS mean_length,
            MEDIAN(LENGTH(CAST({col_name} AS TEXT))) AS median_length,
            STDDEV_SAMP(LENGTH(CAST({col_name} AS TEXT))) AS std_dev_length,
            STDDEV_SAMP(LENGTH(CAST({col_name} AS TEXT))) / SQRT(COUNT(*)) AS std_error_length,
            COUNT(DISTINCT 
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(CAST({col_name} AS TEXT),
                            '[a-z]', 'a', 'g'),
                        '[A-Z]', 'A', 'g'),
                    '[0-9]', 'N', 'g')
            ) AS pattern_count
        FROM source.{source_table}
        """
        
        con.execute(summary_query)
    
    print(f"Created and populated summary table: {summary_table_name}")


def generate_select_scripts(con, output_dir):
    """Generate SELECT scripts for all tables and views"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate information schema SQL file
    info_schema_file = os.path.join(output_dir, 'information_schema.sql')
    with open(info_schema_file, 'w') as f:
        f.write("SELECT DISTINCT table_name FROM information_schema.columns;")
    print(f"Generated {info_schema_file}")
    
    # Get all tables and views from all schemas
    schemas = ['source', 'patterns', 'summaries']
    for schema in schemas:
        tables = con.execute(f"SHOW TABLES FROM {schema}").fetchall()
        for table in tables:
            table_name = table[0]
            output_file = os.path.join(output_dir, f"{schema}_{table_name}.sql")
            
            if not os.path.exists(output_file):
                with open(output_file, 'w') as f:
                    f.write(f"SELECT * FROM {schema}.{table_name};")
                print(f"Generated {output_file}")
            else:
                print(f"File {output_file} already exists. Skipping.")

def process_tables(con):
    """Process all tables from PostgreSQL database"""
    tables = con.execute("SHOW TABLES FROM source").fetchall()
    
    for table in tables:
        table_name = table[0]
        try:
            create_pattern_view(con, table_name)
            create_summary_table(con, table_name)
        except Exception as e:
            print(f"Error processing table {table_name}: {str(e)}")

def main():
    # Initialize connection and database
    con = get_duckdb_connection()
    initialize_database(con)
    
    # Load PostgreSQL tables into DuckDB
    load_postgres_tables(con)
    
    # Process all tables
    process_tables(con)
    
    # Generate SELECT scripts
    generate_select_scripts(con, 'sources/profiling')
    
    # Close connection
    con.close()

if __name__ == "__main__":
    main()
