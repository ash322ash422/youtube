-- If table exists, then drop it
DROP TABLE IF EXISTS Fruits;

-- Following creates a table Fruits with 6 columns 

CREATE TABLE Fruits (
    FruitID INTEGER NOT NULL,
    FruitName VARCHAR(100),
    Color VARCHAR(50),
    Quantity INTEGER,
    PricePerUnit DECIMAL(10,2),
    IsImported INTEGER,
    PRIMARY KEY (FruitID)
);


INSERT INTO Fruits (FruitID, FruitName, Color, Quantity, PricePerUnit, IsImported) VALUES
(1, 'Grapes', 'Green', 40, 1.0, 1),
(2, 'Orange', 'Orange', 70, 0.3, 1),
(3, 'Apple', 'Red', 50, 0.5, 0),
(4, 'Blueberry', 'Blue', 20, 2.5, 1),
(5, 'Mango', 'Yellow', 60, 1.2, 0),
(6, 'Strawberry', 'Red', 30, 2.0, 1),
(7, 'Kiwi', 'Brown', 25, 1.8, 1),
(8, 'Pineapple', 'Brown', 15, 3.0, 0),
(9, 'Banana', 'Yellow', 100, 0.2, 0),
(10, 'DragonFruit', 'Brown', 15, 2.0, 0),
(11, 'JackFruit', 'Brown', 15, 3.0, 0),
(12, 'Watermelon', 'Green', 10, 5.0, 0),
(13, 'Lychee', 'Red', 50, 0.5, 0),
(14, 'StarFruit', 'Yellow', 100, 0.2, 0),
(15, 'PassionFruit', 'Green', 70, 0.3, 1);

