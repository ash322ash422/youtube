-- Fetch names of fruits that start with a 'B' 
SELECT *
FROM Fruits
WHERE FruitName LIKE 'B%';


-- Fetch names of fruits that end with an 'i':
SELECT *
FROM Fruits
WHERE FruitName LIKE '%i';


-- Fetch names of fruits that has 'an' in it:
SELECT *
FROM Fruits
WHERE FruitName LIKE '%an%';

-- Fetch data where it has 'an' in it and PPU > 1.0
SELECT
    FruitName AS Fruit,
    Color,
    PricePerUnit AS Price
FROM Fruits
WHERE FruitName LIKE '%an%'
  AND PricePerUnit > 1.0;





