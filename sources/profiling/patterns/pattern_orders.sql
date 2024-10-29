SELECT REGEXP_REPLACE(
         REGEXP_REPLACE(
           REGEXP_REPLACE(CAST(COLUMNS(*) AS TEXT),
             '[a-z]', 'a', 'g'),
           '[A-Z]', 'A', 'g'),
         '[0-9]', 'N', 'g') 
FROM orders