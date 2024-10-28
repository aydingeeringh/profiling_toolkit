# Column: {params.columns}

```sql summary
select *
from 'summary_${params.tables}'
where column_name = '${params.columns}'
```

```sql kpis
UNPIVOT ${summary}
ON COLUMNS(* EXCLUDE (column_name))
INTO
    NAME metrics
    VALUE values
```

```sql length
select 
    "${params.columns}", LEN("${params.columns}") as char_length
from '${params.tables}'
where "${params.columns}" is not null
order by char_length desc
```

```sql frequency
WITH freq_counts AS (
    SELECT 
        "${params.columns}",
        COUNT(*) AS count
    FROM '${params.tables}'
    GROUP BY "${params.columns}"
)
SELECT
    "${params.columns}",
    len("${params.columns}") as char_len,
    count,
    (count::FLOAT / (SELECT COUNT(*) FROM 'pattern_${params.tables}')) AS percentage_pct
FROM freq_counts
ORDER BY count DESC, "${params.columns}"
```

```sql patterns
WITH pattern_counts AS (
    SELECT 
        "${params.columns}" AS pattern,
        COUNT(*) AS count
    FROM 'pattern_${params.tables}'
    GROUP BY "${params.columns}"
)
SELECT 
    pattern,
    len(pattern) as char_len,
    count,
    (count::FLOAT / (SELECT COUNT(*) FROM 'pattern_${params.tables}')) AS percentage_pct,
    '/${params.tables}/' || '${params.columns}/' || "pattern" as pattern_link
FROM pattern_counts
ORDER BY count DESC, pattern;
```

## Metrics

{#each kpis as kpi}

{#if kpi.values == "N/A"}
{:else }
<BigValue data={kpi} value=values title={kpi.metrics}/>
{/if}

{/each}


## Field Analysis

{#each summary as type}
{#if type.data_type == "VARCHAR"}
<DataTable data={frequency} totalRow=true search=true>
    <Column id={params.columns} totalAgg=countDistinct totalFmt='# "unique values"'/>
    <Column id=char_len title="Character length" totalAgg=max totalFmt='"Max:" #'/>
    <Column id=count title="Count"/>
    <Column id=percentage_pct title="Proportion" fmt='pct2'/>
</DataTable>

<Histogram
    data={length} 
    x=char_length
    title="Character Length Histogram"
/>

{:else if type.data_type == "TIMESTAMP"}

```sql date_tbl
SELECT 
    year("${params.columns}")::text as "Year", 
    month("${params.columns}")::text as "Month", 
    day("${params.columns}")::text as "Day", 
    strftime("${params.columns}", '%Y-%m-%d')::text as "${params.columns}"
FROM '${params.tables}'
```

<DimensionGrid 
    data={date_tbl} 
    metric='count(*)' 
    name=multi_dimensions 
    limit=13
/>

<AreaChart 
    data={frequency} 
    x={params.columns}
    y=count 
    title="Value Count"
/>


{:else if type.data_type == "INTEGER" || type.data_type == "FLOAT"}
<AreaChart 
    data={frequency}
    x={params.columns}
    y=count
    title="Value Count"
/>

{:else}
{/if}

{/each}



## Pattern Analysis

Pattern Frequency Distribution analyzes data by counting and calculating percentages of distinct word or character patterns. It works for both text and numbers, usingt the following syntax:
- `a` for lowercase letters, 
- `A` for uppercase letters and 
- `N` for digits. 

This tool helps identify common structures and anomalies in datasets, useful for data validation and pattern recognition.

<DataTable data={patterns} link=pattern_link totalRow=true search=true>
    <Column id=pattern totalAgg=countDistinct totalFmt='# "unique patterns"' title="Pattern" wrap=true weightCol=0.5/>
    <Column id=char_len title="Character length" totalAgg=max totalFmt='"Max:" #'/>
    <Column id=count title="Count"/>
    <Column id=percentage_pct title="Proportion" fmt='pct2'/>
</DataTable>