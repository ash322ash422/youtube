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


--------------VIEWS---------------
-- VIEW1---------------
-- Following creates a view with no output
CREATE VIEW VW_HighValueCustomers AS
    SELECT *
    FROM Customers 
        LEFT JOIN Orders ON Customers.customer_id = Orders.customer_id
    WHERE Orders.amount > 100;

-- Lets look inside the above view
SELECT *
FROM VW_HighValueCustomers;


-- Find HighValueCustomers name and product ordered who are living in  New York
-- (With views , I do not have to recreate JOIN anymore)
SELECT name,
       item
FROM VW_HighValueCustomers
WHERE city='New York';




-- VIEW2----------------
CREATE VIEW VW_LowValueCustomers AS
    SELECT *
    FROM Customers 
      LEFT JOIN Orders ON Customers.customer_id = Orders.customer_id
    WHERE Orders.amount < 100;


SELECT *
FROM VW_LowValueCustomers;

-- Find LowValueCustomers living in Chicago
-- (With views , I do not have to use JOIN anymore)
SELECT *
FROM VW_LowValueCustomers
WHERE city='Chicago';



--VIEWS3------------------------
CREATE VIEW VW_CustomerOrdersShippings AS
    SELECT
        c.customer_id,
        c.name AS customer_name,
        c.city,
        o.order_id,
        o.item,
        o.amount,
        o.order_date,
        s.ship_id,
        s.status AS shipping_status
    FROM Customers c
        JOIN Orders o ON c.customer_id = o.customer_id
        JOIN Shippings s ON o.order_id = s.order_id;

-- Lets look at all the records of the view
SELECT *
FROM VW_CustomerOrdersShippings;

-- Show all Delivered orders with customer and shipping info
SELECT 
    customer_name,
    order_id,
    item,
    amount,
    shipping_status
FROM VW_CustomerOrdersShippings
WHERE shipping_status = 'Delivered';

-- Show all orders shipped to New York
SELECT 
    customer_name,
    city,
    order_id,
    item,
    amount,
    shipping_status
FROM VW_CustomerOrdersShippings
WHERE city = 'New York';

-- List orders from customers in 'New York' who spent more than $200:
SELECT customer_name,
       amount
FROM VW_CustomerOrdersShippings
WHERE city = 'New York' AND amount > 200;

