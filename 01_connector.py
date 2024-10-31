import streamlit as st
import ibis
import json
from pathlib import Path
import pandas as pd
from typing import Optional, List

def load_saved_connections():
    """Load saved connections from a JSON file"""
    config_path = Path("connections.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def save_connection(name, db_type, params):
    """Save connection details to a JSON file"""
    connections = load_saved_connections()
    connections[name] = {
        "type": db_type,
        "params": params
    }
    with open("connections.json", "w") as f:
        json.dump(connections, f, indent=4)

def get_connection_params(db_type):
    """Return connection parameters based on database type"""
    params = {
        "BigQuery": {
            "project_id": "",
            "dataset": ""
        },
        "ClickHouse": {
            "host": "localhost",
            "port": "8123",
            "database": "",
            "user": "",
            "password": ""
        },
        "DuckDB": {
            "path": "path/to/database.db"
        },
        "MySQL": {
            "host": "localhost",
            "port": "3306",
            "database": "",
            "user": "",
            "password": ""
        },
        "Postgres": {
            "host": "localhost",
            "port": "5432",
            "database": "",
            "user": "",
            "password": ""
        },
        "MSSQL": {  # Add MSSQL parameters
            "host": "localhost",
            "port": "1433",
            "database": "",
            "user": "",
            "password": "",
            "driver": "ODBC Driver 17 for SQL Server"  # Default SQL Server driver
        },
        "SQLite": {
            "database": "path/to/database.db"
        },
        "Snowflake": {
            "account": "",
            "user": "",
            "password": "",
            "database": "",
            "warehouse": "",
            "schema": "PUBLIC"
        }
    }
    return params.get(db_type, {})

def create_connection(db_type, params):
    """Create database connection using Ibis"""
    try:
        if db_type == "BigQuery":
            return ibis.bigquery.connect(
                project_id=params["project_id"],
                dataset=params["dataset"]
            )
        elif db_type == "ClickHouse":
            return ibis.clickhouse.connect(
                host=params["host"],
                port=int(params["port"]),
                database=params["database"],
                user=params["user"],
                password=params["password"]
            )
        elif db_type == "DuckDB":
            return ibis.duckdb.connect(params["path"])
        elif db_type == "MySQL":
            return ibis.mysql.connect(
                host=params["host"],
                port=int(params["port"]),
                database=params["database"],
                user=params["user"],
                password=params["password"]
            )
        elif db_type == "Postgres":
            return ibis.postgres.connect(
                host=params["host"],
                port=int(params["port"]),
                database=params["database"],
                user=params["user"],
                password=params["password"]
            )
        elif db_type == "MSSQL":  # Add MSSQL connection
            connection_string = (
                f"DRIVER={{{params['driver']}}};"
                f"SERVER={params['host']},{params['port']};"
                f"DATABASE={params['database']};"
                f"UID={params['user']};"
                f"PWD={params['password']}"
            )
            return ibis.mssql.connect(connection_string)
        elif db_type == "SQLite":
            return ibis.sqlite.connect(params["database"])
        elif db_type == "Snowflake":
            return ibis.snowflake.connect(
                account=params["account"],
                user=params["user"],
                password=params["password"],
                database=params["database"],
                warehouse=params["warehouse"],
                schema=params["schema"]
            )
        else:
            st.error(f"Database type {db_type} not supported yet")
            return None
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def main():
    st.title("Database Connection Manager")

    # Database selection
    db_options = [
        "BigQuery",
        "ClickHouse",
        "DuckDB",
        "MySQL",
        "MSSQL",
        "Postgres",
        "SQLite",
        "Snowflake"
    ]

    selected_db = st.selectbox(
        "Select a database system:",
        db_options,
        index=None,
        placeholder="Choose a database..."
    )

    if selected_db:
        # Connection name input
        connection_name = st.text_input("Connection name", f"{selected_db}_connection")

        # Get connection parameters for selected database
        params = get_connection_params(selected_db)
        connection_params = {}

        # Create input fields for connection parameters
        st.subheader("Connection Parameters")
        for param, default_value in params.items():
            if param == "password":
                connection_params[param] = st.text_input(
                    param, 
                    default_value,
                    type="password"
                )
            elif param == "port":
                connection_params[param] = st.text_input(
                    param, 
                    default_value
                )
            else:
                connection_params[param] = st.text_input(
                    param, 
                    default_value
                )

        col1, col2 = st.columns(2)

        # Test connection button
        with col1:
            if st.button("Test Connection"):
                conn = create_connection(selected_db, connection_params)
                if conn:
                    st.success("Connection successful!")

        # Save connection button
        with col2:
            if st.button("Save Connection"):
                save_connection(connection_name, selected_db, connection_params)
                st.success(f"Connection '{connection_name}' saved successfully!")

        # Show saved connections
        st.subheader("Saved Connections")
        saved_connections = load_saved_connections()
        if saved_connections:
            for name, details in saved_connections.items():
                st.write(f"**{name}** ({details['type']})")

if __name__ == "__main__":
    main()
