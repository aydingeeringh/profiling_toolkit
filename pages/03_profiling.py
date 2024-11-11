import streamlit as st
import pandas as pd
import ibis

def get_profiled_tables():
    """Get list of profiled tables from catalog"""
    try:
        # Create Ibis connection to catalog
        catalog_con = ibis.duckdb.connect('profiles.db')
        
        # First check if the table exists
        table_exists = catalog_con.list_tables()
        if 'profile_catalog' not in table_exists:
            # Return empty DataFrame if table doesn't exist
            return pd.DataFrame()
            
        catalog_table = catalog_con.table('profile_catalog')
        
        # Get base catalog information
        tables = catalog_table.execute()
        
        # Process each table to get metrics using Ibis
        table_metrics = []
        invalid_records = []
        
        for _, row in tables.iterrows():
            try:
                # Create Ibis connection to summary parquet
                summary_con = ibis.duckdb.connect()
                summary_table = summary_con.read_parquet(row['summary_path'])
                
                # Get metrics using Ibis expressions and ensure scalar values
                metrics_expr = summary_table.aggregate([
                    summary_table.count().name('column_count'),
                    summary_table.row_count.max().name('row_count')
                ])
                
                metrics = metrics_expr.execute()
                
                table_metrics.append({
                    'connection_name': row['connection_name'],
                    'schema_name': row['schema_name'],
                    'table_name': row['table_name'],
                    'profile_date': row['last_profiled'],
                    'column_count': int(metrics['column_count'].iloc[0]),
                    'row_count': int(metrics['row_count'].iloc[0])
                })
            except Exception as e:
                st.warning(f"Could not fetch metrics for {row['schema_name']}.{row['table_name']}: {str(e)}")
                invalid_records.append({
                    'connection_name': row['connection_name'],
                    'schema_name': row['schema_name'],
                    'table_name': row['table_name']
                })
                continue
        
        # Remove invalid records from the catalog
        if invalid_records:
            try:
                # Create direct DuckDB connection
                import duckdb
                duckdb_conn = duckdb.connect('profiles.db')
                
                for record in invalid_records:
                    delete_sql = """
                    DELETE FROM profile_catalog 
                    WHERE connection_name = ? 
                    AND schema_name = ? 
                    AND table_name = ?
                    """
                    duckdb_conn.execute(delete_sql, 
                                      [record['connection_name'],
                                       record['schema_name'],
                                       record['table_name']])
                
                duckdb_conn.commit()
                duckdb_conn.close()
                st.info(f"Removed {len(invalid_records)} invalid records from the catalog")
            except Exception as e:
                st.error(f"Error removing invalid records from catalog: {str(e)}")
                
        return pd.DataFrame(table_metrics)
    except Exception as e:
        st.error(f"Error fetching profiled tables: {str(e)}")
        return pd.DataFrame()

def get_table_profile(connection_name, schema, table):
    """Get detailed profile for a specific table"""
    try:
        # Get summary path from catalog using Ibis
        catalog_con = ibis.duckdb.connect('profiles.db')
        catalog_table = catalog_con.table('profile_catalog')
        
        # Filter for specific table
        summary_path = (
            catalog_table.filter(
                (catalog_table.connection_name == connection_name) &
                (catalog_table.schema_name == schema) &
                (catalog_table.table_name == table)
            )
            .summary_path
            .execute()
            .iloc[0]
        )
        
        # Read summary parquet using Ibis
        summary_con = ibis.duckdb.connect()
        summary_table = summary_con.read_parquet(summary_path)
        
        # Calculate percentages using Ibis expressions
        profile = summary_table.mutate([
            (summary_table.null_count.cast('float') * 100.0 / 
             summary_table.row_count.cast('float')).name('null_percentage'),
            (summary_table.unique_count.cast('float') * 100.0 / 
             summary_table.row_count.cast('float')).name('unique_percentage')
        ]).execute()
        
        return profile.sort_values('column_name')
    except Exception as e:
        st.error(f"Error fetching profile: {str(e)}")
        return pd.DataFrame()

def get_column_metrics(connection_name, schema, table, column):
    """Get detailed metrics for a specific column using Ibis"""
    try:
        # Get data path from catalog
        catalog_con = ibis.duckdb.connect('profiles.db')
        catalog_table = catalog_con.table('profile_catalog')
        
        data_path = (
            catalog_table.filter(
                (catalog_table.connection_name == connection_name) &
                (catalog_table.schema_name == schema) &
                (catalog_table.table_name == table)
            )
            .data_path
            .execute()
            .iloc[0]
        )
        
        # Read data using Ibis
        data_con = ibis.duckdb.connect()
        table_data = data_con.read_parquet(data_path)
        column_data = table_data[column]
        
        # Get column type
        column_type = str(column_data.type())
        
        # Create metrics based on data type
        if 'string' in column_type.lower():
            metrics = (
                table_data.aggregate([
                    column_data.min().name('min_value'),
                    column_data.max().name('max_value'),
                    column_data.count().name('count'),
                    column_data.isnull().sum().name('null_count'),
                    column_data.nunique().name('unique_count')
                ])
            ).execute()
            
            # Add length metrics
            length_metrics = (
                table_data.mutate(str_len=column_data.length())
                .aggregate([
                    ibis._.str_len.min().name('min_length'),
                    ibis._.str_len.max().name('max_length'),
                    ibis._.str_len.mean().name('avg_length')
                ])
            ).execute()
            
            # Combine metrics
            return pd.concat([metrics, length_metrics], axis=1)
            
        elif 'int' in column_type.lower() or 'float' in column_type.lower() or 'decimal' in column_type.lower():
            return (
                table_data.aggregate([
                    column_data.min().name('min_value'),
                    column_data.max().name('max_value'),
                    column_data.mean().name('mean'),
                    column_data.std().name('std_dev'),
                    column_data.approx_median().name('median'),
                    column_data.count().name('count'),
                    column_data.isnull().sum().name('null_count'),
                    column_data.nunique().name('unique_count')
                ])
            ).execute()
            
        elif 'date' in column_type.lower() or 'timestamp' in column_type.lower():
            return (
                table_data.aggregate([
                    column_data.min().name('min_value'),
                    column_data.max().name('max_value'),
                    column_data.count().name('count'),
                    column_data.isnull().sum().name('null_count'),
                    column_data.nunique().name('unique_count')
                ])
            ).execute()
            
        else:
            # For other types, just get basic metrics
            return (
                table_data.aggregate([
                    column_data.count().name('count'),
                    column_data.isnull().sum().name('null_count'),
                    column_data.nunique().name('unique_count')
                ])
            ).execute()
        
    except Exception as e:
        st.error(f"Error getting column metrics: {str(e)}")
        return None

def get_column_histogram(connection_name, schema, table, column):
    """Generate histogram data using Ibis"""
    try:
        # Get data path from catalog
        catalog_con = ibis.duckdb.connect('profiles.db')
        catalog_table = catalog_con.table('profile_catalog')
        
        data_path = (
            catalog_table.filter(
                (catalog_table.connection_name == connection_name) &
                (catalog_table.schema_name == schema) &
                (catalog_table.table_name == table)
            )
            .data_path
            .execute()
            .iloc[0]
        )
        
        # Read data using Ibis
        data_con = ibis.duckdb.connect()
        table_data = data_con.read_parquet(data_path)
        column_data = table_data[column]
        
        # Get column type
        column_type = str(column_data.type()).lower()
        
        # Handle different column types
        if 'string' in column_type:
            # Create histogram of string lengths
            histogram = (
                table_data
                .filter(column_data.notnull())
                .mutate(str_length=column_data.length())
                .group_by('str_length')
                .aggregate(count=lambda t: t.count())
                .order_by('str_length')
            ).execute()
            
            return histogram
            
        elif any(t in column_type for t in ['int', 'float', 'decimal']):
            # Get min and max values
            stats = (
                table_data.aggregate([
                    column_data.min().name('min_val'),
                    column_data.max().name('max_val'),
                    column_data.count().name('total_count')
                ])
            ).execute()
            
            min_val = stats['min_val'].iloc[0]
            max_val = stats['max_val'].iloc[0]
            
            if min_val is not None and max_val is not None:
                # Create 10 equal-width bins
                bin_width = (max_val - min_val) / 10
                
                # Create bins using case/when
                bins = []
                for i in range(10):
                    bin_start = min_val + (i * bin_width)
                    bin_end = min_val + ((i + 1) * bin_width)
                    
                    condition = (
                        (column_data >= bin_start) &
                        (column_data < bin_end if i < 9 else column_data <= bin_end)
                    )
                    bins.append(condition)
                
                # Create histogram using case/when
                histogram = (
                    table_data
                    .filter(column_data.notnull())
                    .group_by(
                        bin_num=ibis.case()
                        .when(bins[0], 0)
                        .when(bins[1], 1)
                        .when(bins[2], 2)
                        .when(bins[3], 3)
                        .when(bins[4], 4)
                        .when(bins[5], 5)
                        .when(bins[6], 6)
                        .when(bins[7], 7)
                        .when(bins[8], 8)
                        .when(bins[9], 9)
                        .end()
                    )
                    .aggregate(count=lambda t: t.count())
                    .mutate(
                        bin_start=min_val + (ibis.literal(bin_width) * ibis._.bin_num),
                        bin_end=min_val + (ibis.literal(bin_width) * (ibis._.bin_num + 1))
                    )
                    .order_by('bin_num')
                ).execute()
                
                return histogram
            
        elif any(t in column_type for t in ['date', 'timestamp']):
            # For date/timestamp, group by the date part
            histogram = (
                table_data
                .filter(column_data.notnull())
                .group_by(column_data.date().name('date_bucket'))
                .aggregate(count=lambda t: t.count())
                .order_by('date_bucket')
            ).execute()
            
            return histogram
            
        else:
            st.info(f"Histogram not available for column type: {column_type}")
            return None
            
    except Exception as e:
        st.error(f"Error generating histogram: {str(e)}")
        return None



def get_value_patterns(connection_name, schema, table, column):
    """Analyze patterns using Ibis"""
    try:
        # Get pattern path from catalog
        catalog_con = ibis.duckdb.connect('profiles.db')
        catalog_table = catalog_con.table('profile_catalog')
        
        pattern_path = (
            catalog_table.filter(
                (catalog_table.connection_name == connection_name) &
                (catalog_table.schema_name == schema) &
                (catalog_table.table_name == table)
            )
            .pattern_path
            .execute()
            .iloc[0]
        )
        
        if pattern_path is None:
            return None
        
        # Read pattern data using Ibis
        pattern_con = ibis.duckdb.connect()
        pattern_data = pattern_con.read_parquet(pattern_path)
        
        # Get patterns for specific column
        if column in pattern_data.columns:
            pattern_counts = (
                pattern_data
                .group_by(column)
                .aggregate(count=lambda t: t.count())
                .order_by(ibis.desc('count'))
                .limit(100)
            ).execute()
            
            # Calculate percentages
            total_count = pattern_counts['count'].sum()
            pattern_counts['percentage'] = (pattern_counts['count'] * 100.0 / total_count).round(2)
            
            return pattern_counts
        return None
        
    except Exception as e:
        st.error(f"Error analyzing patterns: {str(e)}")
        return None

def get_value_frequencies(connection_name, schema, table, column):
    """Get value frequencies using Ibis"""
    try:
        # Get data path from catalog
        catalog_con = ibis.duckdb.connect('profiles.db')
        catalog_table = catalog_con.table('profile_catalog')
        
        data_path = (
            catalog_table.filter(
                (catalog_table.connection_name == connection_name) &
                (catalog_table.schema_name == schema) &
                (catalog_table.table_name == table)
            )
            .data_path
            .execute()
            .iloc[0]
        )
        
        # Read data using Ibis
        data_con = ibis.duckdb.connect()
        table_data = data_con.read_parquet(data_path)
        
        # Create base frequency count
        freq_base = (
            table_data
            .group_by(value=table_data[column])
            .aggregate(count=lambda t: t.count())
            .order_by(ibis.desc('count'))
            .limit(100)
        )
        
        # Execute base frequencies
        frequencies = freq_base.execute()
        
        # Calculate percentages
        total = frequencies['count'].sum()
        frequencies['percentage'] = (frequencies['count'] * 100.0 / total).round(2)
        
        return frequencies
    except Exception as e:
        st.error(f"Error getting value frequencies: {str(e)}")
        return None

@st.cache_data
def get_pattern_matches(connection_name, schema, table, column, pattern):
    """Get values that match a specific pattern"""
    try:
        # Get data path from catalog
        catalog_con = ibis.duckdb.connect('profiles.db')
        catalog_table = catalog_con.table('profile_catalog')
        
        data_path = (
            catalog_table.filter(
                (catalog_table.connection_name == connection_name) &
                (catalog_table.schema_name == schema) &
                (catalog_table.table_name == table)
            )
            .data_path
            .execute()
            .iloc[0]
        )
        
        # Read data using Ibis
        data_con = ibis.duckdb.connect()
        table_data = data_con.read_parquet(data_path)
        
        # Create pattern expression
        pattern_expr = (
            table_data[column]
            .cast('string')
            # Replace lowercase letters with lowercase a
            .re_replace(r'[a-z]', 'a')
            # Replace uppercase letters with uppercase A
            .re_replace(r'[A-Z]', 'A')
            # Replace numbers with N
            .re_replace(r'[0-9]', 'N')
        )
        
        # Filter for matching values
        matches = (
            table_data
            .filter(pattern_expr == pattern)
            .select(table_data[column])
            .group_by(table_data[column])
            .aggregate(count=lambda t: t.count())
            .order_by(ibis.desc('count'))
        ).execute()
        
        return matches
        
    except Exception as e:
        st.error(f"Error getting pattern matches: {str(e)}")
        return None


def main():
    st.title("Table Profile Viewer")

    st.logo("https://infoblueprint.co.za/wp-content/uploads/2021/06/infoblueprint-logo-600px.png")

    # Get list of profiled tables
    profiled_tables = get_profiled_tables()

    if not profiled_tables.empty:
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Table Overview", "Detailed Profile", "Column Profile"])
        
        with tab1:
            st.subheader("Profiled Tables Summary")
            # Display overview of all profiled tables
            st.dataframe(
                profiled_tables,
                column_config={
                    "connection_name": "Connection",
                    "schema_name": "Schema",
                    "table_name": "Table",
                    "profile_date": st.column_config.DatetimeColumn(
                        "Last Profiled",
                        format="DD/MM/YY HH:mm:ss"
                    ),
                    "column_count": st.column_config.NumberColumn("Columns"),
                    "row_count": st.column_config.NumberColumn(
                        "Rows",
                        format="%d"
                    )
                },
                hide_index=True
            )
        
        with tab2:
            # First select connection
            connections = profiled_tables['connection_name'].unique()
            selected_connection = st.selectbox(
                "Select Connection",
                options=connections
            )
            
            if selected_connection:
                # Filter tables for selected connection
                conn_tables = profiled_tables[profiled_tables['connection_name'] == selected_connection]
                
                # Create selection options with schema.table format
                table_options = [
                    f"{row['schema_name']}.{row['table_name']}"
                    for _, row in conn_tables.iterrows()
                ]
                
                # Table selector
                selected_table = st.selectbox(
                    "Select a table to view detailed profile",
                    options=table_options
                )

                if selected_table:
                    schema, table = selected_table.split('.')
                    
                    # Find profiling date for selected table
                    table_info = conn_tables[
                        (conn_tables['schema_name'] == schema) & 
                        (conn_tables['table_name'] == table)
                    ].iloc[0]
                    
                    st.caption(f"Last profiled: {table_info['profile_date'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Get and display profile
                    profile = get_table_profile(selected_connection, schema, table)
                    
                    if not profile.empty:
                        # Display basic table info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Rows", f"{profile['row_count'].iloc[0]:,}")
                        with col2:
                            st.metric("Total Columns", len(profile))
                        with col3:
                            st.metric("Last Profiled", profile['profile_date'].iloc[0].strftime('%Y-%m-%d %H:%M:%S'))

                        # Display column statistics
                        st.subheader("Column Statistics")
                        st.dataframe(
                            profile.drop('profile_date', axis=1),
                            column_config={
                                "column_name": "Column",
                                "row_count": st.column_config.NumberColumn(
                                    "Row Count",
                                    format="%d"
                                ),
                                "null_count": st.column_config.NumberColumn(
                                    "Null Count",
                                    format="%d"
                                ),
                                "null_percentage": st.column_config.NumberColumn(
                                    "Null %",
                                    format="%.2f%%"
                                ),
                                "unique_count": st.column_config.NumberColumn(
                                    "Unique Count",
                                    format="%d"
                                ),
                                "unique_percentage": st.column_config.NumberColumn(
                                    "Unique %",
                                    format="%.2f%%"
                                )
                            },
                            hide_index=True
                        )
        
        with tab3:
            if 'selected_table' in locals() and selected_table:
                schema, table = selected_table.split('.')
                
                # Get profile data to get column names
                profile = get_table_profile(selected_connection, schema, table)
                
                if not profile.empty:
                    # Column selector
                    selected_column = st.selectbox(
                        "Select a column to analyze",
                        options=profile['column_name'].tolist()
                    )
                    
                    if selected_column:
                        # Create subtabs for different analyses
                        metric_tab, hist_tab, freq_tab, pattern_tab = st.tabs([
                            "Metrics", "Histogram", "Value Frequencies", "Patterns"
                        ])
                        
                        with metric_tab:
                            metrics = get_column_metrics(
                                selected_connection, schema, table, selected_column
                            )
                            if metrics is not None:
                                st.dataframe(metrics)
                        
                        with hist_tab:
                            histogram = get_column_histogram(
                                selected_connection, schema, table, selected_column
                            )
                            if histogram is not None:
                                # For string columns (length histogram)
                                if 'str_length' in histogram.columns:
                                    st.write("Distribution of String Lengths")
                                    chart_data = pd.DataFrame({
                                        'Length': histogram['str_length'],
                                        'Count': histogram['count']
                                    })
                                    st.bar_chart(data=chart_data.set_index('Length'))
                                    
                                    # Show raw data in expander
                                    with st.expander("Show histogram data"):
                                        st.dataframe(histogram)
                                    
                                # For numeric columns
                                elif 'bin_start' in histogram.columns:
                                    # Create labels for x-axis
                                    histogram['label'] = histogram.apply(
                                        lambda row: f"{row['bin_start']:.2f} - {row['bin_end']:.2f}",
                                        axis=1
                                    )
                                    
                                    # Create the chart
                                    chart_data = pd.DataFrame({
                                        'bin': histogram['label'],
                                        'count': histogram['count']
                                    })
                                    
                                    # Display using st.bar_chart
                                    st.bar_chart(data=chart_data.set_index('bin'))
                                    
                                    # Show raw data in expander
                                    with st.expander("Show histogram data"):
                                        st.dataframe(histogram)
                                
                                # For date/timestamp columns
                                elif 'date_bucket' in histogram.columns:
                                    # Display using st.line_chart
                                    chart_data = pd.DataFrame({
                                        'date': histogram['date_bucket'],
                                        'count': histogram['count']
                                    })
                                    st.line_chart(data=chart_data.set_index('date'))
                                    
                                    # Show raw data in expander
                                    with st.expander("Show histogram data"):
                                        st.dataframe(histogram)


                        
                        with freq_tab:
                            frequencies = get_value_frequencies(
                                selected_connection, schema, table, selected_column
                            )
                            if frequencies is not None:
                                st.dataframe(frequencies)
                        
                        with pattern_tab:
                            patterns = get_value_patterns(
                                selected_connection, schema, table, selected_column
                            )
                            if patterns is not None:
                                # Initialize the patterns DataFrame with a checkbox column
                                if 'show_values' not in patterns.columns:
                                    patterns['show_values'] = False
                                
                                # Create a unique key for the editor
                                pattern_key = f"pattern_select_{selected_connection}_{schema}_{table}_{selected_column}"
                                
                                # Display patterns with editable checkbox
                                edited_patterns = st.data_editor(
                                    patterns,
                                    column_config={
                                        "show_values": st.column_config.CheckboxColumn(
                                            "Show Values",
                                            help="Select to see matching values",
                                            default=False,
                                        ),
                                        selected_column: "Pattern",
                                        "count": st.column_config.NumberColumn(
                                            "Count",
                                            format="%d"
                                        ),
                                        "percentage": st.column_config.NumberColumn(
                                            "Percentage",
                                            format="%.2f%%"
                                        )
                                    },
                                    disabled=[selected_column, "count", "percentage"],
                                    hide_index=True,
                                    key=pattern_key
                                )
                                
                                # Handle selection
                                selected_patterns = edited_patterns[edited_patterns['show_values']]
                                if not selected_patterns.empty:
                                    # If more than one is selected
                                    if len(selected_patterns) > 1:
                                        st.warning("Please select only one pattern at a time.")
                                    else:
                                        # Show matching values for the selected pattern
                                        selected_pattern = selected_patterns[selected_column].iloc[0]
                                        matches = get_pattern_matches(
                                            selected_connection, 
                                            schema, 
                                            table, 
                                            selected_column,
                                            selected_pattern
                                        )
                                        
                                        if matches is not None and not matches.empty:
                                            st.subheader(f"Values matching pattern: {selected_pattern}")
                                            st.dataframe(
                                                matches,
                                                column_config={
                                                    selected_column: "Value",
                                                    "count": st.column_config.NumberColumn(
                                                        "Count",
                                                        format="%d"
                                                    )
                                                },
                                                hide_index=True,
                                                use_container_width=True
                                            )
                                        else:
                                            st.info("No matching values found")

    else:
        st.info("No profiled tables found. Profile some tables first.")

if __name__ == "__main__":
    main()
