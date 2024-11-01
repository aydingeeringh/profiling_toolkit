import streamlit as st
import ibis
import json
import pyodbc
from pathlib import Path
from typing import Optional, Dict, Any

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
        # Load available backends from backends.json
        backends = load_backend_configs()
        db_options = sorted(backends.keys())

        # Store selected database in session state
        st.session_state.selected_db = st.selectbox(
            "Select a database system:",
            db_options,
            index=None,
            placeholder="Choose a database..."
        )

        if st.session_state.selected_db:
            # Connection name input
            st.session_state.connection_name = st.text_input(
                "Connection name", 
                value=f"{st.session_state.selected_db}_connection",
                key="connection_name_create"
            )

            # Get connection parameters for selected database
            params = get_connection_params(st.session_state.selected_db)
            st.session_state.connection_params = {}

            # Create input fields for connection parameters
            st.subheader("Connection Parameters")
            
            # Special handling for MSSQL to include driver selection
            if st.session_state.selected_db.lower() == "mssql":
                # Add other MSSQL parameters
                for param, default_value in params.items():
                    if param != 'driver':  # Skip driver as it's handled above
                        st.session_state.connection_params[param] = (
                            st.text_input(
                                param,
                                str(default_value),
                                type="password" if param == "password" else "default",
                                key=f"create_{param}"
                            )
                        )

                # Get available SQL Server drivers
                drivers = [driver for driver in pyodbc.drivers()]
                driver = st.selectbox(
                    "Select SQL Server Driver",
                    drivers,
                    key="driver_select_create"
                )
                st.session_state.connection_params['driver'] = driver
                
            else:
                # Handle other database types normally
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
                    conn = create_connection(st.session_state.selected_db, st.session_state.connection_params)
                    if conn:
                        st.success("Connection successful!")

            # Save connection button
            with col2:
                if st.button("Save Connection", key="save_conn_create"):
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
            # Create a selection box for choosing a connection to manage
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
                        # Store the connection details in session state for editing
                        st.session_state['editing_connection'] = selected_connection
                        st.session_state['editing_details'] = conn_details
                        st.rerun()

                with col2:
                    if st.button("Delete Connection", key="delete_conn_btn"):
                        delete_connection(selected_connection)
                        st.success(f"Connection '{selected_connection}' deleted successfully!")
                        st.rerun()

                # Edit connection form
                if st.session_state.get('editing_connection') == selected_connection:
                    st.subheader("Edit Connection")
                    
                    # Add connection name editing
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
                            # Delete old connection if name changed
                            if new_connection_name != selected_connection:
                                delete_connection(selected_connection)
                            
                            # Save with new name and parameters
                            save_connection(new_connection_name, conn_details['type'], new_params)
                            st.success("Changes saved successfully!")
                            # Clear editing state
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