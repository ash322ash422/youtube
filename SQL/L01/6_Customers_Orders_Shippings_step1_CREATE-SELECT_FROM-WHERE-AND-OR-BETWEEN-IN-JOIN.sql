-- Drop tables safely (order matters because of foreign keys)
DROP TABLE IF EXISTS Shippings;
DROP TABLE IF EXISTS Orders;
DROP TABLE IF EXISTS Customers;


CREATE TABLE Customers (
    customer_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100)
);

CREATE TABLE Orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    amount DECIMAL(10,2),
    order_date DATE,
    item VARCHAR(100),
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);


CREATE TABLE Shippings (
    ship_id INT PRIMARY KEY,
    order_id INT,
    status VARCHAR(50),
    FOREIGN KEY (order_id) REFERENCES Orders(order_id)
);


-- Lets insert some records into above 3 tables
INSERT INTO Customers (customer_id, name, city) VALUES
(1, 'Wagner', 'New York'),
(2, 'Shankar', 'Los Angeles'),
(3, 'Mozart', 'Chicago'),
(4, 'Beethoven', 'New York'),
(5, 'Vogel', 'Houston'),
(6, 'Fischer', 'Chicago');

-- Orders
INSERT INTO Orders (order_id, customer_id, amount, item, order_date) VALUES
(1, 1, 250.00,'Phone', '2024-01-10'),
(2, 1, 125.00,'Computer','2024-02-15'),
(3, 2, 300.00,'Computer','2024-03-20'),
(4, 3, 75.00,'Phone','2024-04-05'),
(5, 3, 150.00,'Computer','2024-04-10'),
(6, 6, 200.00,'Phone','2024-05-01'),
(7, 5, 350.00,'Computer','2024-05-15'),
(8, 2, 100.00,'Phone','2024-06-01');


-- Shippings
INSERT INTO Shippings (ship_id, order_id, status) VALUES
(1, 1,'Shipped'),
(2, 4, 'Delivered'),
(3, 2, 'Shipped'),
(4, 3, 'Delivered'),
(5, 8, 'Delivered'),
(6, 6, 'Shipped'),
(7, 5, 'Delivered'),
(8, 7, 'Shipped');




-- Select all records from Customers
SELECT * 
FROM Customers;

-- select only name and city for all customers
SELECT name, city 
FROM Customers;


-- SELECT all records from Customers who live in New York
SELECT * 
FROM Customers 
WHERE city = 'New York';

-- SELECT all records from Customers who live in Los Angeles and name is Shankar
SELECT * 
FROM Customers 
WHERE city = 'Los Angeles' AND name = 'Shankar';


-- SELECT all records from Customers who live in Chicago OR Houston
SELECT * 
FROM Customers 
WHERE city = 'Chicago' OR city = 'Houston';


-- IN: SELECT all records from customers who live in New York or Chicago
SELECT * 
FROM Customers 
WHERE city IN ('New York', 'Chicago');

-- NOT IN: SELECT all records from customers who DO NOT live in New York or Chicago
SELECT * 
FROM Customers 
WHERE city NOT IN ('New York', 'Chicago');


--BETWEEN: SELECT all records from orders who ordered b/w '2024-03-01' AND '2024-04-29' 
SELECT *
FROM Orders
WHERE order_date BETWEEN '2024-03-01' AND '2024-04-29';

--BETWEEN: SELECT all records from orders whose ordered amount is b/w 100 and 300
SELECT * 
FROM Orders 
WHERE amount BETWEEN 100 AND 300;


------------------------------------
--JOIN (Customers with their Orders): By default, JOIN uses INNER
-- Show me customers_name, order amount, order date for all customers who have orders
-- step1: First create appropriate JOIN on table Customers and Orders
SELECT *
FROM Orders 
     JOIN Customers ON Customers.customer_id = Orders.customer_id;

-- step2: Then add the column names you want to extract
SELECT Customers.name,
       Orders.amount,
       Orders.order_date
FROM Orders
     JOIN Customers ON Customers.customer_id = Orders.customer_id;


-- LEFT JOIN 
-- Show customers_name, order amount, order date for all customers even if they have no orders
SELECT Customers.name,
       Orders.amount,
       Orders.order_date
FROM Customers 
     LEFT JOIN Orders ON Customers.customer_id = Orders.customer_id;
---------------------


-- List all orders with customer names,amount, order_date 
-- ordered by amount descending:
SELECT Customers.name,
       Orders.amount,
       Orders.order_date
FROM Customers 
    JOIN Orders ON Customers.customer_id = Orders.customer_id
ORDER BY Orders.amount DESC;





----------------
-- Show each shipped item with customer name, order amount, order item and shipping status 
-- STEP1: First create appropriate JOIN on table
SELECT *
FROM Shippings 
   JOIN Orders  ON Shippings.order_id = Orders.order_id
   JOIN Customers ON Orders.customer_id = Customers.customer_id;

-- STEP2 : Create alias for above join to make it little easy to read
SELECT *
FROM Shippings s
  JOIN Orders o ON s.order_id = o.order_id
  JOIN Customers c ON o.customer_id = c.customer_id;

-- STEP3: Extract relevant columns
SELECT 
    c.name AS customer_name,
    o.item,
    o.amount,
    s.status
FROM Shippings s
   JOIN Orders o ON s.order_id = o.order_id
   JOIN Customers c ON o.customer_id = c.customer_id;
-------------------

-- Show only Delivered orders with full details
SELECT 
    c.name AS customer_name,
    c.city,
    o.item,
    o.amount,
    o.order_date,
    s.status
FROM Shippings s
   JOIN Orders o ON s.order_id = o.order_id
   JOIN Customers c ON o.customer_id = c.customer_id
WHERE s.status = 'Delivered';


-- Find all orders shipped to customers in Chicago
SELECT 
    c.name,
    c.city,
    o.order_id,
    o.item,
    s.status
FROM Customers c
    JOIN Orders o ON c.customer_id = o.customer_id
    JOIN Shippings s ON o.order_id = s.order_id
WHERE c.city = 'Chicago';

-- Which customers have orders that have not been delivered yet? 
SELECT DISTINCT
    c.name,
    o.order_id,
    s.status
FROM Customers c
    JOIN Orders o ON c.customer_id = o.customer_id
    JOIN Shippings s ON o.order_id = s.order_id
WHERE s.status != 'Delivered';



-- JOIN + DISTINCT
-- List distinct cities of customers who have placed at least one order:
SELECT DISTINCT Customers.city
FROM Customers 
   JOIN Orders ON Customers.customer_id = Orders.customer_id;


-- Find customers who placed orders only in specific cities:'New York', 'Chicago'
SELECT Customers.name, Orders.amount
FROM Customers 
   JOIN Orders ON Customers.customer_id = Orders.customer_id
WHERE Customers.city IN ('New York', 'Chicago');



-- LEFT JOIN + WHERE IS NULL
-- Show all customers who have never placed an order:
SELECT Customers.name
FROM Customers LEFT JOIN Orders ON Customers.customer_id = Orders.customer_id
WHERE Orders.order_id IS NULL;



-- Get orders from customers in 'New York' who spent more than $200:
SELECT Customers.name,
       Orders.amount
FROM Customers 
   JOIN Orders ON Customers.customer_id = Orders.customer_id
WHERE Customers.city = 'New York' AND Orders.amount > 200;



