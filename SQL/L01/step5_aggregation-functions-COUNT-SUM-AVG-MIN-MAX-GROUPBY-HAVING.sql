
-- COUNT: counts the number of records without retrieving all 
-- records across network....saves bandwidth
SELECT COUNT(*) 
FROM Fruits;


-- GROUP BY with Aggregation---------------------

-- Count fruits by color
SELECT Color, 
       COUNT(*) AS ColorCount 
FROM Fruits 
GROUP BY Color;



-- Total quantity of fruits by color
SELECT Color, 
       SUM(Quantity) AS SumQuantity
FROM Fruits
GROUP BY Color;



-- Average price per unit of fruits by color
SELECT Color, 
       AVG(PricePerUnit) AS AveragePrice
FROM Fruits
GROUP BY Color;



-- Minimum and maximum price of fruits by color
SELECT Color, 
       MIN(PricePerUnit) AS MinPrice,
       MAX(PricePerUnit) AS MaxPrice
FROM Fruits
GROUP BY Color;



-- Total price/vale of fruits in inventory by color
SELECT Color, 
       SUM(Quantity * PricePerUnit) AS TotalPrice
FROM Fruits
GROUP BY Color;


-- Now print all of the above stats
SELECT 
    color,
    COUNT(*) as count,
    AVG(quantity) as avg_qty,
    SUM(quantity) as total_qty,
    MIN(quantity) as min_qty,
    MAX(quantity) as max_qty
FROM Fruits 
GROUP BY color
ORDER BY color;
-------------------------------------------



-- HAVING with GROUP BY
-- Find colors HAVING total quantity is more than 70 
SELECT Color, 
       SUM(Quantity) AS TotalQuantity
FROM Fruits
GROUP BY Color
HAVING TotalQuantity > 70;


-- Find colors HAVING count > 3
SELECT Color,
       COUNT(*) AS FruitCount
FROM Fruits 
GROUP BY Color 
HAVING FruitCount > 3;

