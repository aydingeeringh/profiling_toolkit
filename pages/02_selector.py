import streamlit as st
import ibis
import json
from pathlib import Path
import pandas as pd
import duckdb
from datetime import datetime
from typing import Dict, Any, Optional
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

def load_saved_connections():
    """Load saved connections from a JSON file"""
    config_path = Path("connections.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def create_connection(db_type: str, params: Dict[str, Any]) -> Optional[ibis.BaseBackend]:
    """Create database connection using Ibis"""
    try:
        connection_method = getattr(ibis, db_type.lower())
        
        # For databases that only need a path parameter, pass the path string directly
        if len(params) == 1 and "path" in params:
            return connection_method.connect(params["path"])
            
        return connection_method.connect(**params)
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_schema_info(connection):
    """Get schema and table information using Ibis"""
    try:
        schemas = connection.list_databases()
        schema_tables = {}
        
        for schema in schemas:
            tables = connection.list_tables(database=schema)
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
            table_obj = connection.table(table, database=schema)
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
                'null_count': int(results['null_count'].iloc[0]),
                'unique_count': int(results['unique_count'].iloc[0]),
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

    # Initialize session state for selected tables
    if 'selected_tables' not in st.session_state:
        st.session_state.selected_tables = set()

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
                # Create table data
                table_data = []
                for schema, tables in schema_info.items():
                    for table in tables:
                        table_data.append({
                            "Schema": schema,
                            "Table": table,
                        })

                # Convert to DataFrame and sort
                df = pd.DataFrame(table_data)
        

                # Configure grid options
                gb = GridOptionsBuilder.from_dataframe(df)
                
                # Configure Schema column for grouping and selection
                gb.configure_column("Schema", 
                    rowGroup=True,
                    headerCheckboxSelection=True,
                    headerCheckboxSelectionFilteredOnly=True,
                    checkboxSelection=True,
                    autoSize=True,
                    showRowGroup=True
                )

                # Configure Table column
                gb.configure_column("Table",
                    checkboxSelection=True,
                    headerCheckboxSelection=True,
                    headerCheckboxSelectionFilteredOnly=True,
                    autoSize=True
                )

                # Configure selection
                gb.configure_selection(
                    selection_mode="multiple",
                    use_checkbox=True,
                    groupSelectsChildren=True,
                    groupSelectsFiltered=True
                )

                # Configure grid behavior
                gridOptions = gb.build()
                
                # Add additional grid options for group selection
                gridOptions['groupSelectsChildren'] = True
                gridOptions['groupDefaultExpanded'] = 0
                gridOptions['rowSelection'] = 'multiple'
                gridOptions['suppressRowClickSelection'] = True
                gridOptions['groupSelectsFiltered'] = True

                # Remove the extra Schema column
                gridOptions['columnDefs'] = [{
                    **col,
                    'autoSize': True,
                    'resizable': True,
                    'hide': True if col['field'] == 'Schema' else False
                } for col in gridOptions['columnDefs']]

                # Display the grid
                grid_response = AgGrid(
                    df,
                    gridOptions=gridOptions,
                    height=600,
                    width="100%",
                    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                    update_mode=GridUpdateMode.MODEL_CHANGED,
                    fit_columns_on_grid_load=True,
                    allow_unsafe_jscode=True,
                    enable_enterprise_modules=True
                )

                # Get selected rows as a DataFrame
                selected_rows = grid_response.selected_rows

                # Debug print

                # Check if there are any selected rows
                if selected_rows is not None and len(selected_rows) > 0:
                    st.write("Selected rows:", selected_rows)
                    # Create a button to trigger profiling
                    if st.button("Profile Selected Tables"):
                        with st.spinner("Profiling selected tables..."):
                            for _, row in pd.DataFrame(selected_rows).iterrows():
                                schema = row['Schema']
                                table = row['Table']
                                
                                # Create a progress bar for each table
                                progress_bar = st.progress(0)
                                st.write(f"Profiling {schema}.{table}")
                                
                                # Generate profile for the selected table
                                success, duration = generate_profile(
                                    connection=conn,
                                    schema=schema,
                                    table=table,
                                    progress_bar=progress_bar,
                                    connection_name=selected_connection
                                )
                                
                                if success:
                                    st.success(f"Successfully profiled {schema}.{table} in {duration}")
                                else:
                                    st.error(f"Failed to profile {schema}.{table}")
                else:
                    st.info("Please select tables to profile")


if __name__ == "__main__":
    main()