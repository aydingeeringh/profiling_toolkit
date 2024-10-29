---
title: Profiling
---

```sql tables
  select
      table_name,
      count(*) as columns,
      '/' || "table_name" as table_link
  from information_schema
  where table_schema = 'main'
  group by table_name
```

Welcome to InfoBluePrint's Data Profiling Report. This report provides a comprehensive analysis of tables of the selected data source(s). The report includes a table's structure, content, and quality. It is designed to help you understand the characteristics of the data, identify potential issues, and support data quality improvement efforts.

**Click on a table name to drill down!**
<DataTable
    data={tables}
    link=table_link
/>

<LastRefreshed/>
