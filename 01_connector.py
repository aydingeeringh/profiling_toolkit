import streamlit as st
import ibis
import json
import pyodbc
import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
import os
import csv

def detect_delimiter(file_path: str) -> str:
    """Detect the delimiter in a CSV file"""
    try:
        # Read first few lines of the file
        with open(file_path, 'r') as file:
            sample = file.readline() + file.readline()
        
        # Count potential delimiters
        delimiters = {
            ',': sample.count(','),
            ';': sample.count(';'),
            '\t': sample.count('\t'),
            '|': sample.count('|')
        }
        
        # Return the delimiter with highest count
        return max(delimiters.items(), key=lambda x: x[1])[0]
    except Exception as e:
        st.error(f"Error detecting delimiter: {str(e)}")
        return ','

def preview_csv(file_path: str, delimiter: str, quotechar: str, has_header: bool) -> pd.DataFrame:
    """Preview first 5 rows of CSV file"""
    try:
        df = pd.read_csv(
            file_path,
            delimiter=delimiter,
            quotechar=quotechar,
            header=0 if has_header else None,
            nrows=5
        )
        return df
    except Exception as e:
        st.error(f"Error previewing CSV: {str(e)}")
        return None

def get_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """Get column types from DataFrame"""
    type_mapping = {
        'int64': 'INTEGER',
        'float64': 'DOUBLE',
        'object': 'VARCHAR',
        'bool': 'BOOLEAN',
        'datetime64[ns]': 'TIMESTAMP'
    }
    return {col: type_mapping.get(str(df[col].dtype), 'VARCHAR') for col in df.columns}

def load_backend_configs() -> Dict[str, Dict[str, Any]]:
    """Load backend configurations from backends.json"""
    with open("backends.json", "r") as f:
        return json.load(f)

def load_saved_connections() -> Dict[str, Dict[str, Any]]:
    """Load saved connections from a JSON file"""
    config_path = Path("connections.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def save_connection(name: str, db_type: str, params: Dict[str, Any]) -> None:
    """Save connection details to a JSON file"""
    connections = load_saved_connections()
    connections[name] = {
        "type": db_type,
        "params": params
    }
    with open("connections.json", "w") as f:
        json.dump(connections, f, indent=4)

def delete_connection(name: str) -> None:
    """Delete a saved connection"""
    connections = load_saved_connections()
    if name in connections:
        del connections[name]
        with open("connections.json", "w") as f:
            json.dump(connections, f, indent=4)

def rename_connection(old_name: str, new_name: str) -> None:
    """Rename a saved connection"""
    if old_name == new_name:
        return
    
    connections = load_saved_connections()
    if old_name in connections:
        connections[new_name] = connections.pop(old_name)
        with open("connections.json", "w") as f:
            json.dump(connections, f, indent=4)

def get_connection_params(db_type: str) -> Dict[str, Any]:
    """Return connection parameters based on database type from backends.json"""
    backends = load_backend_configs()
    return backends.get(db_type, {})

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

def main():
    st.title("Database Connection Manager")

    # Initialize session state variables if they don't exist
    if 'selected_db' not in st.session_state:
        st.session_state.selected_db = None
    if 'connection_name' not in st.session_state:
        st.session_state.connection_name = ""
    if 'connection_params' not in st.session_state:
        st.session_state.connection_params = {}

    # Add tabs for managing connections
    tab1, tab2 = st.tabs(["Create Connection", "Manage Connections"])

    with tab1:
        backends = load_backend_configs()
        db_options = sorted(list(backends.keys()) + ["CSV"])

        st.session_state.selected_db = st.selectbox(
            "Select a database system:",
            db_options,
            index=None,
            placeholder="Choose a database..."
        )

        if st.session_state.selected_db:
            st.session_state.connection_name = st.text_input(
                "Connection name", 
                value=f"{st.session_state.selected_db}_connection",
                key="connection_name_create"
            )

            if st.session_state.selected_db == "CSV":
                file_path = st.text_input("CSV File Path", 
                                        help="Provide the full path to your CSV file")
                
                if file_path and os.path.exists(file_path):
                    # CSV Import Options
                    st.subheader("CSV Import Options")
                    
                    # Detect delimiter
                    detected_delimiter = detect_delimiter(file_path)
                    delimiter_options = {
                        'Comma (,)': ',',
                        'Semicolon (;)': ';',
                        'Tab (\\t)': '\t',
                        'Pipe (|)': '|',
                        'Custom': 'custom'
                    }
                    
                    delimiter_choice = st.selectbox(
                        "Delimiter",
                        options=list(delimiter_options.keys()),
                        index=list(delimiter_options.values()).index(detected_delimiter) if detected_delimiter in delimiter_options.values() else 0
                    )
                    
                    if delimiter_choice == 'Custom':
                        delimiter = st.text_input("Enter custom delimiter", value=detected_delimiter)
                    else:
                        delimiter = delimiter_options[delimiter_choice]

                    # Quote character
                    quote_options = {
                        'Double Quote (")': '"',
                        "Single Quote (')": "'",
                        'None': ''
                    }
                    quote_choice = st.selectbox("Quote Character", options=list(quote_options.keys()))
                    quotechar = quote_options[quote_choice]

                    # Header option
                    has_header = st.checkbox("File has header", value=True)

                    # Preview data
                    st.subheader("Preview Data")
                    df_preview = preview_csv(file_path, delimiter, quotechar, has_header)
                    
                    if df_preview is not None:
                        st.dataframe(df_preview)

                        # Improved Column Type UI
                        st.subheader("Column Types")
                        
                        # Auto-detect toggle
                        auto_detect = st.checkbox("Auto-detect column types", value=True)
                        
                        if auto_detect:
                            column_types = get_column_types(df_preview)
                            
                            # Display auto-detected types in a table format
                            type_df = pd.DataFrame({
                                'Column Name': column_types.keys(),
                                'Detected Type': column_types.values()
                            })
                            st.table(type_df)
                            
                        else:
                            # Manual column type selection with improved UI
                            sql_types = ['INTEGER', 'DOUBLE', 'VARCHAR', 'BOOLEAN', 'TIMESTAMP', 'DATE']
                            column_types = {}
                            
                            # Create a container for the column type selection
                            with st.container():
                                # Use tabs to organize column types by category
                                st.markdown("#### Configure Column Types")
                                
                                # Create a DataFrame for the column type selection
                                type_data = []
                                for col in df_preview.columns:
                                    # Get sample values for the column
                                    sample_values = df_preview[col].head(3).tolist()
                                    sample_str = ", ".join(str(x) for x in sample_values)
                                    
                                    # Auto-detect initial type
                                    initial_type = get_column_types(df_preview)[col]
                                    
                                    type_data.append({
                                        "Column": col,
                                        "Sample Values": sample_str,
                                        "Type": initial_type
                                    })
                                
                                # Create selection UI
                                for i, row in enumerate(type_data):
                                    col1, col2, col3 = st.columns([2, 3, 2])
                                    
                                    with col1:
                                        st.text(row["Column"])
                                    
                                    with col2:
                                        st.text(f"Sample: {row['Sample Values'][:50]}...")
                                    
                                    with col3:
                                        column_types[row["Column"]] = st.selectbox(
                                            "Type",
                                            options=sql_types,
                                            index=sql_types.index(row["Type"]) if row["Type"] in sql_types else 0,
                                            key=f"type_{i}",
                                            label_visibility="collapsed"
                                        )
                                
                                # Add quick type selection buttons
                                st.markdown("#### Quick Type Selection")
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    if st.button("All VARCHAR"):
                                        for col in df_preview.columns:
                                            column_types[col] = "VARCHAR"
                                        st.rerun()
                                
                                with col2:
                                    if st.button("All INTEGER"):
                                        for col in df_preview.columns:
                                            column_types[col] = "INTEGER"
                                        st.rerun()
                                
                                with col3:
                                    if st.button("All DOUBLE"):
                                        for col in df_preview.columns:
                                            column_types[col] = "DOUBLE"
                                        st.rerun()
                                
                                with col4:
                                    if st.button("Reset to Auto-detected"):
                                        column_types = get_column_types(df_preview)
                                        st.rerun()

                        # Import to DuckDB with specified options
                        if st.button("Import CSV", type="primary"):
                            try:
                                conn = duckdb.connect("flatfiles.db")
                                
                                # Create table name from file name
                                table_name = Path(file_path).stem.lower().replace(" ", "_")
                                
                                # Show selected configuration
                                st.write("Configuration Summary:")
                                config_df = pd.DataFrame({
                                    'Setting': ['Table Name', 'Delimiter', 'Quote Character', 'Has Header'],
                                    'Value': [table_name, delimiter, quotechar, has_header]
                                })
                                st.dataframe(config_df)
                                
                                # Show column types
                                st.write("Column Types:")
                                types_df = pd.DataFrame({
                                    'Column': column_types.keys(),
                                    'Type': column_types.values()
                                })
                                st.dataframe(types_df)
                                
                                # Construct CREATE TABLE statement with column types
                                columns_def = ", ".join([f'"{col}" {dtype}' for col, dtype in column_types.items()])
                                create_table_sql = f"""
                                CREATE TABLE IF NOT EXISTS {table_name} (
                                    {columns_def}
                                )
                                """
                                conn.execute(create_table_sql)
                                
                                # Import data
                                copy_sql = f"""
                                COPY {table_name} FROM '{file_path}' 
                                (DELIMITER '{delimiter}', 
                                HEADER {str(has_header).lower()},
                                QUOTE '{quotechar if quotechar else ""}')
                                """
                                conn.execute(copy_sql)
                                conn.close()
                                
                                # Store DuckDB parameters
                                st.session_state.connection_params = {"path": "flatfiles.db"}
                                st.success(f"CSV file imported as table: {table_name}")
                                
                            except Exception as e:
                                st.error(f"Error importing CSV: {str(e)}")
                elif file_path:
                    st.error("File not found. Please check the path and try again.")

            # Special handling for MSSQL to include driver selection
            elif st.session_state.selected_db.lower() == "mssql":
                params = get_connection_params(st.session_state.selected_db)
                st.session_state.connection_params = {}
                
                for param, default_value in params.items():
                    if param != 'driver':
                        st.session_state.connection_params[param] = (
                            st.text_input(
                                param,
                                str(default_value),
                                type="password" if param == "password" else "default",
                                key=f"create_{param}"
                            )
                        )

                drivers = [driver for driver in pyodbc.drivers()]
                driver = st.selectbox(
                    "Select SQL Server Driver",
                    drivers,
                    key="driver_select_create"
                )
                st.session_state.connection_params['driver'] = driver
                
            else:
                # Handle other database types normally
                params = get_connection_params(st.session_state.selected_db)
                st.session_state.connection_params = {}
                for param, default_value in params.items():
                    st.session_state.connection_params[param] = (
                        st.text_input(
                            param,
                            str(default_value),
                            type="password" if param == "password" else "default",
                            key=f"create_{param}"
                        )
                    )

            col1, col2 = st.columns(2)

            # Test connection button
            with col1:
                if st.button("Test Connection", key="test_conn_create"):
                    if st.session_state.selected_db == "CSV":
                        conn = create_connection("duckdb", {"path": "flatfiles.db"})
                    else:
                        conn = create_connection(st.session_state.selected_db, st.session_state.connection_params)
                    if conn:
                        st.success("Connection successful!")

            # Save connection button
            with col2:
                if st.button("Save Connection", key="save_conn_create"):
                    if st.session_state.selected_db == "CSV":
                        save_connection(
                            st.session_state.connection_name,
                            "duckdb",
                            {"path": "flatfiles.db"}
                        )
                    else:
                        save_connection(
                            st.session_state.connection_name, 
                            st.session_state.selected_db, 
                            st.session_state.connection_params
                        )
                    st.success(f"Connection '{st.session_state.connection_name}' saved successfully!")

    with tab2:
        st.subheader("Manage Saved Connections")
        saved_connections = load_saved_connections()
        
        if saved_connections:
            selected_connection = st.selectbox(
                "Select a connection to manage",
                list(saved_connections.keys()),
                index=None,
                placeholder="Choose a connection...",
                key="connection_select_manage"
            )

            if selected_connection:
                conn_details = saved_connections[selected_connection]
                
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Edit Connection", key="edit_conn_btn"):
                        st.session_state['editing_connection'] = selected_connection
                        st.session_state['editing_details'] = conn_details
                        st.rerun()

                with col2:
                    if st.button("Delete Connection", key="delete_conn_btn"):
                        delete_connection(selected_connection)
                        st.success(f"Connection '{selected_connection}' deleted successfully!")
                        st.rerun()

                if st.session_state.get('editing_connection') == selected_connection:
                    st.subheader("Edit Connection")
                    
                    new_connection_name = st.text_input(
                        "Connection Name",
                        selected_connection,
                        key="edit_connection_name"
                    )
                    
                    new_params = {}
                    for param, value in conn_details['params'].items():
                        new_params[param] = st.text_input(
                            param,
                            value,
                            type="password" if param == "password" else "default",
                            key=f"edit_{param}"
                        )

                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("Test Connection", key="test_conn_edit"):
                            conn = create_connection(conn_details['type'], new_params)
                            if conn:
                                st.success("Connection successful!")

                    with col2:
                        if st.button("Save Changes", key="save_changes_btn"):
                            if new_connection_name != selected_connection:
                                delete_connection(selected_connection)
                            
                            save_connection(new_connection_name, conn_details['type'], new_params)
                            st.success("Changes saved successfully!")
                            st.session_state.pop('editing_connection', None)
                            st.session_state.pop('editing_details', None)
                            st.rerun()

                    with col3:
                        if st.button("Cancel", key="cancel_edit_btn"):
                            st.session_state.pop('editing_connection', None)
                            st.session_state.pop('editing_details', None)
                            st.rerun()

        else:
            st.info("No saved connections found.")

if __name__ == "__main__":
    main()
