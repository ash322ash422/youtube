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





--Find customers with orders count:
SELECT Customers.name,
       COUNT(Orders.order_id) AS OrderCount
FROM Customers 
    JOIN Orders ON Customers.customer_id = Orders.customer_id
GROUP BY Customers.name;


--Find customers with exactly 2 orders:
SELECT Customers.name,
       COUNT(Orders.order_id) AS OrderCount
FROM Customers 
    JOIN Orders ON Customers.customer_id = Orders.customer_id
GROUP BY Customers.name
HAVING OrderCount = 2;



-- Show me how many items have been ordered by all customers and their total amount
SELECT customer_id,
       COUNT(*) AS OrderCount,
       SUM(amount) AS TotalSpent
FROM Orders
GROUP BY customer_id;



-- Show customers, order count along with their total amount
SELECT Customers.customer_id,
       Customers.name,
       COUNT(Orders.order_id) AS OrderCount,
       SUM(Orders.amount) AS TotalSpent
FROM Customers
  JOIN Orders 
    ON Customers.customer_id = Orders.customer_id
GROUP BY Customers.customer_id, Customers.name;



-- Show customers who have made more than 1 order, along with their MAX amount
-- , MIN amount, AVERAGE amount:
SELECT Customers.customer_id,
       Customers.name,
       COUNT(Orders.order_id) AS OrderCount,
       MIN(Orders.amount) AS MINSpent,
       MAX(Orders.amount) AS MAXSpent,
       AVG(Orders.amount) AS AVGSpent

FROM Customers
   JOIN Orders ON Customers.customer_id = Orders.customer_id

GROUP BY Customers.customer_id, Customers.name
HAVING COUNT(Orders.order_id) > 1;




-- List total spending per customer, sorted from highest spender to lowest:
SELECT Customers.name,
       SUM(Orders.amount) AS TotalSpent
FROM Customers 
   JOIN Orders ON Customers.customer_id = Orders.customer_id
GROUP BY Customers.name
ORDER BY TotalSpent DESC;




