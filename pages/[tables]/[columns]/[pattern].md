# Pattern: {params.pattern}

```sql pattern_data
WITH 
a AS (
    SELECT 
        ROW_NUMBER() OVER () AS index_column,
        "${params.columns}" as "pattern"
    FROM pattern_${params.tables}
),
b AS (
    SELECT 
        ROW_NUMBER() OVER () AS index_column,
        "${params.columns}"
    FROM ${params.tables}
),
matched_counts AS (
    SELECT 
        b."${params.columns}" as "${params.columns}", 
        COUNT(*) as count
    FROM a
    JOIN b ON a.index_column = b.index_column
    WHERE pattern = '${params.pattern}'
    GROUP BY b."${params.columns}"
),
total_count AS (
    SELECT SUM(count) as total
    FROM matched_counts
)
SELECT 
    mc."${params.columns}",
    mc.count,
    (mc.count / tc.total) as percentage_pct
FROM matched_counts mc
CROSS JOIN total_count tc
ORDER BY mc.count DESC
```

## Pattern Analysis

Pattern Frequency Distribution analyzes data by counting and calculating percentages of distinct word or character patterns. It works for both text and numbers, usingt the following syntax:
- `a` for lowercase letters, 
- `A` for uppercase letters and 
- `N` for digits. 

This tool helps identify common structures and anomalies in datasets, useful for data validation and pattern recognition.

<DataTable data={pattern_data} totalRow=true search=true>
    <Column id={params.columns} totalAgg=countDistinct totalFmt='# "unique values"' align=left/>
    <Column id=count title="Count"/>
    <Column id=percentage_pct title="Proportion" fmt='pct2'/>
</DataTable>