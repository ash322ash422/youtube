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


-- An intermediate query is basically:
-- 1) A query inside another query.
-- 2) It helps break down complex logic step by step.
-- 3) Makes SQL modular and easier to understand.

-- 1) Get all customers who have placed orders over $100
-- Breakdown:
-- Step1: Inner query (SELECT DISTINCT customer_id ...) gets customer IDs with orders over $200.
SELECT DISTINCT customer_id
FROM Orders
WHERE amount > 100;

-- Step2: Outer query filters Customers to only these IDs.
SELECT *
FROM Customers
WHERE customer_id IN (
  SELECT DISTINCT customer_id
  FROM Orders
  WHERE amount > 100 
);
------------------------------------



-- 2) Subquery with NOT IN — Customers who never ordered 
SELECT *
FROM Customers
WHERE customer_id NOT IN (
  SELECT DISTINCT customer_id
  FROM Orders
);


-------------------------
-- Subquery with comparison — Orders with above average amount
-- Key idea:
-- The inner subquery computes the average amount once.
SELECT AVG(amount)
FROM Orders;

-- The outer query keeps only orders greater than that average.
SELECT *
FROM Orders
WHERE amount > (
  SELECT AVG(amount)
  FROM Orders
);
--------------------------------


----------------------------------
-- Customers who spent more than the average order amount
SELECT DISTINCT c.name
FROM Customers c
   JOIN Orders o ON c.customer_id = o.customer_id
WHERE o.amount > (
    SELECT AVG(amount)
    FROM Orders
);
------------------------------------


-------------------------------------
-- Correlated subquery — Orders that are the customer’s largest order
-- inner subquery computes the max amount
-- outer query returns the rows whose amount is max amount
SELECT *
FROM Orders o
WHERE amount = (
  SELECT MAX(amount)
  FROM Orders
  WHERE customer_id = o.customer_id
);
----------------------------------


-- DIFFICULT: Find the latest order amount for each customer
SELECT 
    Customers.name,
    Orders.amount,
    Orders.order_date
FROM Customers 
   JOIN Orders ON Customers.customer_id = Orders.customer_id

WHERE 
    Orders.order_date = (
        SELECT MAX(order_date)
        FROM Orders
        WHERE customer_id = Customers.customer_id
    );



