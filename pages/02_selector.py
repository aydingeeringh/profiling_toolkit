import streamlit as st
import ibis
import json
from pathlib import Path
import pandas as pd
import duckdb
from datetime import datetime

def load_saved_connections():
    """Load saved connections from a JSON file"""
    config_path = Path("connections.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def create_connection(db_type, params):
    """Create database connection using Ibis"""
    try:
        # Convert database type to lowercase for ibis connection string
        db_type_lower = db_type.lower()
        
        # Handle special cases for database names
        db_mapping = {
            "postgres": "postgres",
            "bigquery": "bigquery",
            "clickhouse": "clickhouse",
            "duckdb": "duckdb",
            "mysql": "mysql",
            "sqlite": "sqlite",
            "snowflake": "snowflake"
        }
        
        # Get the correct database name for ibis
        db_name = db_mapping.get(db_type_lower, db_type_lower)
        
        # Create the connection dynamically
        connect_func = getattr(ibis, db_name).connect
        
        # Connect using the parameters
        return connect_func(**params)
    
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_schema_info(connection):
    """Get schema and table information using Ibis"""
    try:
        schemas = connection.list_schemas()
        schema_tables = {}
        
        for schema in schemas:
            tables = connection.list_tables(schema=schema)
            if tables:  # Only add schemas that have tables
                schema_tables[schema] = tables
                
        # If no schemas found, try getting tables from default schema
        if not schema_tables:
            tables = connection.list_tables()
            if tables:
                schema_tables["default"] = tables
                
        return schema_tables
    except Exception as e:
        st.error(f"Error fetching schema information: {str(e)}")
        return {}

def get_table_schema(connection, table, schema=None):
    """Get table schema information"""
    try:
        # Get table reference
        if schema and schema != "default":
            table_obj = connection.table(table, schema=schema)
        else:
            table_obj = connection.table(table)
        
        # Get column information
        columns = table_obj.columns
        types = [str(table_obj[col].type()) for col in columns]
        
        return pd.DataFrame({
            'Column': columns,
            'Type': types
        })
    except AttributeError:
        # Handle the specific 'str' object has no attribute 'name' error
        st.info(f"Unable to fetch schema for {table}")
        return 
    except Exception as e:
        st.error(f"Error getting table schema: {str(e)}")
        return pd.DataFrame(columns=['Column', 'Type'])
    
def generate_profile(connection, schema, table, progress_bar, connection_name):
    """Generate profile for a table using Ibis compiled SQL"""
    try:
        table_start_time = datetime.now()
        
        # Get table reference
        if schema and schema != "default":
            table_obj = connection.table(table, schema=schema)
        else:
            table_obj = connection.table(table)
        
        # Create directory structure
        base_dir = Path("data_profiles")
        conn_dir = base_dir / connection_name
        schema_dir = conn_dir / schema
        table_dir = schema_dir / table
        table_dir.mkdir(parents=True, exist_ok=True)
        
        # Define paths
        data_path = table_dir / "data.parquet"
        summary_path = table_dir / "summary.parquet"
        pattern_path = table_dir / "patterns.parquet"
        
        # Get column names
        columns = table_obj.columns
        total_columns = len(columns)
        
        # Export raw data to parquet
        progress_bar.progress(0.2, f"Exporting {table} to parquet...")
        table_obj.to_parquet(str(data_path))
        
        # Create a new table reference from the parquet file
        parquet_table = ibis.read_parquet(str(data_path))
        
        # Get total rows first
        total_rows = parquet_table.count().execute()
        
        progress_bar.progress(0.4, "Analyzing columns...")
        # Process each column
        summary_data = []
        
        # Create pattern expressions for string columns
        pattern_expressions = {}
        for col in columns:
            column_type = str(parquet_table[col].type())
            if 'string' in column_type.lower():
                pattern_expressions[col] = (
                    parquet_table[col]
                    .cast('string')
                    .re_replace(r'[0-9]', 'N')
                    .re_replace(r'[^a-zA-Z0-9]', '')
                    .re_replace(r'[a-zA-Z]', 'a')
                ).name(col)  # Add explicit column naming
        
        # Generate patterns table if there are string columns
        if pattern_expressions:
            progress_bar.progress(0.5, "Generating patterns...")
            patterns_expr = parquet_table.mutate(**pattern_expressions)
            patterns_df = patterns_expr.select(list(pattern_expressions.keys())).execute()
            patterns_df.to_parquet(str(pattern_path))


        # Process column metrics
        for i, col in enumerate(columns):
            progress = 0.6 + (0.3 * (i / total_columns))
            progress_bar.progress(progress, f"Analyzing column: {col}")
            
            metrics = [
                parquet_table[col].isnull().sum().name('null_count'),
                parquet_table[col].nunique().name('unique_count')
            ]
            results = parquet_table.aggregate(metrics).execute()
            
            summary_data.append({
                'column_name': col,
                'row_count': int(total_rows),
                'null_count': int(results['null_count']),
                'unique_count': int(results['unique_count']),
                'schema_name': schema,
                'table_name': table,
                'profile_date': datetime.now(),
                'connection_name': connection_name,
                'has_patterns': 'string' in str(parquet_table[col].type()).lower()
            })
        
        progress_bar.progress(0.9, "Saving results...")
        # Save summary
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_parquet(str(summary_path))
        
        # Update catalog
        catalog_db = duckdb.connect('profiles.db')
        
        # Create catalog table if it doesn't exist
        catalog_db.execute("""
            CREATE TABLE IF NOT EXISTS profile_catalog (
                connection_name VARCHAR,
                schema_name VARCHAR,
                table_name VARCHAR,
                data_path VARCHAR,
                summary_path VARCHAR,
                pattern_path VARCHAR,
                last_profiled TIMESTAMP,
                PRIMARY KEY (connection_name, schema_name, table_name)
            )
        """)
        
        # Delete existing entry if it exists
        catalog_db.execute("""
            DELETE FROM profile_catalog 
            WHERE connection_name = ? 
            AND schema_name = ? 
            AND table_name = ?
        """, [connection_name, schema, table])
        
        # Insert new entry
        catalog_db.execute("""
            INSERT INTO profile_catalog 
            (connection_name, schema_name, table_name, data_path, summary_path, pattern_path, last_profiled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            connection_name, 
            schema, 
            table, 
            str(data_path),
            str(summary_path),
            str(pattern_path) if pattern_expressions else None,
            datetime.now()
        ])
        
        # Complete the progress
        table_end_time = datetime.now()
        duration = table_end_time - table_start_time
        progress_bar.progress(1.0, f"Complete! Time taken: {duration}")
        
        return True, duration
    
    except Exception as e:
        st.error(f"Error profiling {schema}.{table}: {str(e)}")
        return None, None

def main():
    st.title("Database Explorer")

    # Initialize session state for selected tables if it doesn't exist
    if 'selected_tables' not in st.session_state:
        st.session_state.selected_tables = set()  # Store as {(schema, table), ...}

    # Load saved connections
    saved_connections = load_saved_connections()

    if not saved_connections:
        st.warning("No saved connections found. Please create a connection first.")
        return

    # Connection selector
    connection_names = list(saved_connections.keys())
    selected_connection = st.selectbox(
        "Select a connection:",
        connection_names,
        index=None,
        placeholder="Choose a connection..."
    )

    if selected_connection:
        connection_info = saved_connections[selected_connection]
        db_type = connection_info["type"]
        params = connection_info["params"]

        # Create connection
        with st.spinner("Connecting to database..."):
            conn = create_connection(db_type, params)

        if conn:
            st.success(f"Connected to {db_type}")

            # Get schema information
            schema_info = get_schema_info(conn)

            if schema_info:
                # Create schema dropdown with "All Schemas" option
                schema_options = ["All Schemas"] + list(schema_info.keys())
                selected_schema = st.selectbox(
                    "Select Schema",
                    options=schema_options,
                    index=0
                )

                # Create a list of all tables with their schemas
                table_data = []
                for schema, tables in schema_info.items():
                    # Only include tables from selected schema or all schemas
                    if selected_schema == "All Schemas" or schema == selected_schema:
                        for table in tables:
                            table_data.append({
                                "Schema": schema,
                                "Table": table,
                                "Selected": (schema, table) in st.session_state.selected_tables
                            })

                # Add previously selected tables that might be filtered out
                for schema, table in st.session_state.selected_tables:
                    if not any(d["Schema"] == schema and d["Table"] == table for d in table_data):
                        table_data.append({
                            "Schema": schema,
                            "Table": table,
                            "Selected": True
                        })

                # Convert to DataFrame and sort
                df = pd.DataFrame(table_data)
                if not df.empty:
                    df = df.sort_values(["Schema", "Table"])

                    # Display editable table with checkboxes
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "Schema": "Schema",
                            "Table": "Table",
                            "Selected": st.column_config.CheckboxColumn(
                                "Select",
                                help="Select table for profiling",
                                default=False
                            )
                        },
                        hide_index=True,
                        disabled=["Schema", "Table"]
                    )

                    # Update selected tables automatically based on checkbox state
                    st.session_state.selected_tables = {
                        (row["Schema"], row["Table"]) 
                        for _, row in edited_df[edited_df["Selected"]].iterrows()
                    }

                    # Display selected tables
                    if st.session_state.selected_tables:
                        st.subheader("Selected Tables")
                        selected_df = pd.DataFrame([
                            {"Schema": schema, "Table": table}
                            for schema, table in st.session_state.selected_tables
                        ]).sort_values(["Schema", "Table"])
                        
                        st.dataframe(selected_df, hide_index=True)

                        # Add button to start profiling
                        if st.button("Profile Selected Tables"):
                            datetime.now()
                            
                            # Create containers for progress and timing
                            progress_container = st.container()
                            st.container()
                            
                            # Store timings for summary
                            table_timings = []
                            
                            # Profile each table with its own progress bar
                            for schema, table in st.session_state.selected_tables:
                                with progress_container:
                                    st.write(f"Profiling {schema}.{table}")
                                    progress_bar = st.progress(0)
                                    success, duration = generate_profile(
                                        conn, 
                                        schema, 
                                        table, 
                                        progress_bar,
                                        selected_connection
                                    )
                                    if success:
                                        table_timings.append({
                                            'schema': schema,
                                            'table': table,
                                            'duration': duration
                                        })


                else:
                    st.info("No tables match the criteria")

            else:
                st.warning("No schemas or tables found in the database.")

if __name__ == "__main__":
    main()
