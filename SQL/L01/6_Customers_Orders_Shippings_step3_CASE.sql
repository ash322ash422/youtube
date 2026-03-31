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



-------------CASE--------------------
-- 1 Categorize Orders as 'High Value' or 'Low Value'

SELECT 
    order_id,
    amount,
    CASE 
        WHEN amount >= 200 THEN 'High Value'
        ELSE 'Low Value'
    END AS order_category

FROM Orders;

-- lets add another value: mid
SELECT 
    order_id,
    amount,
    CASE 
        WHEN amount >= 200 THEN 'High Value'
        WHEN amount >= 100 THEN 'Mid value'  
        ELSE 'Low Value'
    END AS order_category
FROM Orders;


-- 2. Add a 'Shipping Progress' Label
-- Following uses LEFT JOIN so you see all orders — even those without shipping info.
SELECT 
    o.order_id,
    o.item,
    s.status,
    CASE 
        WHEN s.status = 'Delivered' THEN 'Completed'
        WHEN s.status = 'Shipped' THEN 'In Transit'
        ELSE 'Pending'
    END AS shipping_progress

FROM Orders o
  LEFT JOIN Shippings s ON o.order_id = s.order_id;


-- 3️. Use CASE in GROUP BY to Count Customers by City Type
SELECT 
    CASE 
        WHEN city = 'New York' OR city = 'Chicago' THEN 'East'
        ELSE 'Other'
    END AS region,
    COUNT(*) AS customer_count

FROM Customers
GROUP BY region;



-- 4️. CASE + JOIN: : Show Orders with a Custom Message
-- Add a note if an order is over $200.-
SELECT 
    o.order_id,
    c.name AS customer_name,
    o.amount,
    CASE 
        WHEN o.amount > 200 THEN 'Eligible for free gift'
        ELSE 'No free gift'
    END AS promotion_status

FROM Orders o
  JOIN Customers c ON o.customer_id = c.customer_id;



-- 5️. Combine CASE with Aggregate Functions
-- Show total order value for each customer, and add a loyalty tier.
SELECT 
    c.name,
    SUM(o.amount) AS total_spent,
    CASE 
        WHEN SUM(o.amount) >= 500 THEN 'Gold'
        WHEN SUM(o.amount) >= 300 THEN 'Silver'
        ELSE 'Bronze'
    END AS loyalty_tier

FROM Customers c
 JOIN Orders o ON c.customer_id = o.customer_id
GROUP BY c.name;



