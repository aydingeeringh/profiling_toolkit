# Table: {params.tables}

```sql table
  select *,
  '/' || '${params.tables}/' || "column_name" as column_link
  from 'summary_${params.tables}'
```

<DataTable
    data={table}
    link=column_link
/>

## Definitions

<Details title="Definitions of the metrics used for data profiling">

    ### Ordinal Position

    Displays the actual location of a field within the table.

    ### Value Count

    Provides the total number of records in your data.

    ### Null Count
    
    Provides the number of records that have the null value.

    ### Mode
    
    Calculates the mode value of your numeric content. The mode is the most frequently occurring score in a distribution. If you have multimodal distributions, this feature is disabled.
    
    ### Minimum Value
    
    Returns the minimum value in your data.
    
    ### Maximum Value
    
    Returns the maximum value in your data.
    
    ### Minimum Length
    
    Determines the minimum string length in your data.
    
    ### Maximum Length
    
    Determines the maximum string length in your data.
    
    ### Mean
    
    Calculates the mean value of your numeric data content. This is calculated by dividing the sum of all the numbers by the total count of numbers.

    ### Median 
    
    Calculates the median value out of your numeric content. The median is the middle of a distribution: half the scores are above the median and half are below the median.
    
    ### Standard Deviation
    
    Calculates the standard deviation of your numeric content. The standard deviation measures the spread of the data about the mean value. It is useful in comparing sets of data which may have the same mean but a different range.
    
    ### Standard Error 

    Calculates the mean standard error of your numeric data. The standard error is the standard deviation of the sampling distribution of a statistic. Thus, the standard error of the mean is the standard deviation of the sampling distribution of the mean.
  
</Details>