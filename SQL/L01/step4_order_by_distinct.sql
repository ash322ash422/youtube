-- Use ORDER BY to get results in ascending/descending order 
SELECT FruitName, PricePerUnit
FROM Fruits
ORDER BY FruitName;


-- Order By by PPU
SELECT FruitName, PricePerUnit
FROM Fruits
ORDER BY PricePerUnit;

-- by descending
SELECT FruitName, PricePerUnit
FROM Fruits
ORDER BY PricePerUnit DESC;


-- Sort by Color, then by Price: Groups same colors together, expensive ones first
SELECT FruitName, Color, PricePerUnit
FROM Fruits
ORDER BY Color, PricePerUnit DESC;


SELECT
    FruitName AS Fruit,
    Quantity * PricePerUnit AS InventoryValue
FROM Fruits
ORDER BY InventoryValue DESC;
---------------------------------------------------------------------------




-- DISTINCT — removing duplicates
-- 1) Without DISTINCT: Shows all colors
SELECT Color 
FROM Fruits;

-- 2) With DISTINCT: Shows only distinct colors, without repetition 
SELECT DISTINCT Color 
FROM Fruits;




-- 1) without DISTINCT on multiple columns
SELECT Color, IsImported
FROM Fruits;

-- 2) with DISTINCT on multiple columns
SELECT DISTINCT Color, IsImported
FROM Fruits;





-- DISTINCT + ORDER BY
SELECT DISTINCT Color
FROM Fruits
ORDER BY Color;


-- DISTINCT + ORDER BY + WHERE:
-- Fetch colors whose Quantity > 20
SELECT DISTINCT Color
FROM Fruits
WHERE Quantity > 20
ORDER BY Color;
