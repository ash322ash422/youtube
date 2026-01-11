-- Select All Columns. No filter applied here
SELECT * 
FROM Fruits;


-- Select few Columns: FruitName, Color
SELECT FruitName, Color
FROM Fruits;


----------ALIAS--------------------
-- Alias allows you do create your own column names
--  without changing table data


-- without ALIAS
SELECT
    FruitName,
    PricePerUnit
FROM Fruits;


-- with ALIAS
SELECT
    FruitName AS Fruit,
    PricePerUnit AS Price
FROM Fruits;



-- Use LIMIT: To get a understanding of ur table without looking at all records
SELECT * 
FROM Fruits 
LIMIT 5;

