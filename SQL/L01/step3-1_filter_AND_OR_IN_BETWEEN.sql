-- Comparison Operators: Show me all columns of fruits WHERE Quantity > 30
SELECT * 
FROM Fruits 
WHERE Quantity > 30;


-- Comparison Operators: Show me all columns of fruits WHERE Quantity <= 30
SELECT * 
FROM Fruits 
WHERE Quantity <= 30;

--Show me FruitName, Color and Quantity of fruits WHERE Quantity >= 27
SELECT FruitName,
       Color,
       Quantity
FROM Fruits 
WHERE Quantity >= 27;


-- Show me all fruits which are yellow 
SELECT * 
FROM Fruits 
WHERE Color = 'Yellow';

-- Show me all fruits which are NOT yellow 
SELECT * 
FROM Fruits 
WHERE Color != 'Yellow';


-- Show me all fruits which are not imported (0)
SELECT * 
FROM Fruits 
WHERE IsImported = 0;
-----------------------------------------------


-- Logical operators: (AND)
-- Show me all fruits which are yellow AND not imported (0)
SELECT * 
FROM Fruits 
WHERE Color = 'Yellow' AND IsImported = 0;


-- Logical operators: (AND)
-- Show me all fruits which are yellow AND not imported AND Quantity > 30
SELECT * 
FROM Fruits 
WHERE Color = 'Yellow' AND IsImported = 0 AND Quantity > 30;


-- Logical operators: (OR)
-- Show me all fruits which are yellow OR green
SELECT * 
FROM Fruits 
WHERE Color = 'Yellow' OR Color = 'Green';


-- Use IN
SELECT * 
FROM Fruits 
WHERE Color IN ('Yellow', 'Green');



-- Use IN
SELECT * 
FROM Fruits 
WHERE Quantity IN (20,30,40,50,60);


-- Use BETWEEN: find all fruits whose price is between 1.0 AND 2.5
SELECT * 
FROM Fruits 
WHERE PricePerUnit BETWEEN 1.0 AND 2.5;
-------------------------------------
