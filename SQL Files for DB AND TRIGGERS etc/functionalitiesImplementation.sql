-- Select the database to use
USE adventureworks;

-- ====================================================================
-- ANALYTICAL QUERY (JOIN, AGGREGATE)
-- Calculates the total stock and total inventory value for every product.
-- ====================================================================
SELECT
    p.ProductID,
    p.Name,
    p.ListPrice,
    p.StandardCost,
    -- Use COALESCE to turn NULL (for items with no stock) into 0
    COALESCE(SUM(pi.Quantity), 0) AS TotalStock,
    
    -- Calculate the total value of the stock
    (p.StandardCost * COALESCE(SUM(pi.Quantity), 0)) AS TotalInventoryValue
FROM
    production_product AS p
LEFT JOIN
    -- Use LEFT JOIN to include products that have 0 inventory
    production_productinventory AS pi ON p.ProductID = pi.ProductID
GROUP BY
    p.ProductID,
    p.Name,
    p.ListPrice,
    p.StandardCost
ORDER BY
    TotalInventoryValue DESC;


-- ====================================================================
-- ANALYTICAL QUERY (JOIN, AGGREGATE)
-- Finds the total number of orders and total purchase value for all vendors.
-- ====================================================================
SELECT
    v.Name AS VendorName,
    COUNT(poh.PurchaseOrderID) AS TotalOrders,
    SUM(poh.TotalDue) AS TotalPurchaseValue
FROM
    purchasing_vendor AS v
JOIN
    -- Join to the orders table to get their financial data
    purchasing_purchaseorderheader AS poh ON v.BusinessEntityID = poh.VendorID
GROUP BY
    v.BusinessEntityID, v.Name
ORDER BY
    TotalPurchaseValue DESC;


-- ====================================================================
-- ANALYTICAL QUERY (AGGREGATE)
-- Calculates the average shipping lead time (in days) for all completed orders.
-- ====================================================================
SELECT
    AVG(DATEDIFF(ShipDate, OrderDate)) AS AverageShippingLeadTime_Days
FROM
    sales_salesorderheader
WHERE
    -- Ensure we only calculate for orders that have been shipped
    ShipDate IS NOT NULL
    -- Per the data, Status = 5 means the order is 'Shipped' (Completed)
    AND Status = 5;


-- ====================================================================
-- ANALYTICAL QUERY (NESTED SUBQUERY)
-- Finds all products that have never been sold.
-- ====================================================================
SELECT
    ProductID,
    Name,
    ListPrice,
    StandardCost
FROM
    production_product
WHERE
    ProductID NOT IN (
        -- This is the nested subquery
        -- It creates a temporary list of every product ID that HAS been sold
        SELECT DISTINCT ProductID FROM sales_salesorderdetail
    );


-- ====================================================================
-- ANALYTICAL QUERY (CTE & WINDOW FUNCTION)
-- Ranks the top 10 customers based on their total lifetime spending.
-- ====================================================================
-- Step 1: Define the CTE (Common Table Expression)
WITH CustomerSpending AS (
    -- This is a temporary, named result set
    -- It joins 3 tables to get the total spending for every customer
    SELECT
        c.CustomerID,
        p.FirstName,
        p.LastName,
        SUM(soh.TotalDue) AS TotalSpending
    FROM
        sales_customer AS c
    JOIN
        -- Get the customer's name
        person_person AS p ON c.PersonID = p.BusinessEntityID
    JOIN
        -- Get their orders to sum the total value
        sales_salesorderheader AS soh ON c.CustomerID = soh.CustomerID
    GROUP BY
        c.CustomerID, p.FirstName, p.LastName
)
-- Step 2: Query from the CTE and use a Window Function
SELECT
    -- This is the window function
    -- It ranks each customer based on their spending
    RANK() OVER (ORDER BY TotalSpending DESC) AS CustomerRank,
    FirstName,
    LastName,
    TotalSpending
FROM
    CustomerSpending -- We select from our temporary CTE
ORDER BY
    CustomerRank ASC -- Order by the new rank
LIMIT 10;


-- ====================================================================
-- VIEW
-- Creates a reusable virtual table showing all products and their specific locations.
-- ====================================================================
CREATE VIEW vw_ProductLocations AS
SELECT
    p.ProductID,
    p.Name AS ProductName,
    l.Name AS LocationName,
    pi.Shelf,
    pi.Bin,
    pi.Quantity
FROM
    production_productinventory AS pi
JOIN
    -- Join to get the product's name
    production_product AS p ON pi.ProductID = p.ProductID
JOIN
    -- Join to get the location's name
    production_location AS l ON pi.LocationID = l.LocationID
ORDER BY
    ProductName, LocationName;
    
-- Example usage:
-- SELECT * FROM vw_ProductLocations
-- WHERE ProductName = 'LL Fork';


-- ====================================================================
-- FUNCTION
-- Creates a function to get the current total stock for any product ID.
-- ====================================================================
-- Tell MySQL to use '$$' as the end-of-command delimiter
DELIMITER $$

CREATE FUNCTION fn_GetProductStock(
    p_ProductID INT
)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    -- Declare a variable to hold the stock
    DECLARE totalStock INT;

    -- Run the query and store the result in the variable
    SELECT
        COALESCE(SUM(Quantity), 0)
    INTO
        totalStock
    FROM
        production_productinventory
    WHERE
        ProductID = p_ProductID;

    -- Return the final value
    RETURN totalStock;

END$$

-- Change the delimiter back to the default semicolon
DELIMITER ;

-- Example usage:
-- SELECT fn_GetProductStock(776) AS StockCount;


-- ====================================================================
-- FUNCTION
-- Creates a function to get the average delivery time (in days) for a specific product.
-- ====================================================================
DELIMITER $$

CREATE FUNCTION fn_GetAvgProductDeliveryTime(
    p_ProductID INT
)
RETURNS DECIMAL(10, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE avgLeadTime DECIMAL(10, 2);

    SELECT
        AVG(DATEDIFF(soh.ShipDate, soh.OrderDate))
    INTO
        avgLeadTime
    FROM
        sales_salesorderheader AS soh
    JOIN
        sales_salesorderdetail AS sod ON soh.SalesOrderID = sod.SalesOrderID
    WHERE
        sod.ProductID = p_ProductID
        -- Only look at completed, shipped orders
        AND soh.ShipDate IS NOT NULL
        AND soh.Status = 5;

    RETURN COALESCE(avgLeadTime, 0);

END$$

DELIMITER ;

-- Example usage:
-- SELECT fn_GetAvgProductDeliveryTime(776) AS AvgDeliveryDays;


-- ====================================================================
-- FUNCTION
-- Creates a function to get the average lead time (in days) from a specific vendor.
-- ====================================================================
DELIMITER $$

CREATE FUNCTION fn_GetAvgVendorLeadTime(
    p_VendorID INT
)
RETURNS DECIMAL(10, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE avgLeadTime DECIMAL(10, 2);

    SELECT
        AVG(DATEDIFF(ShipDate, OrderDate))
    INTO
        avgLeadTime
    FROM
        purchasing_purchaseorderheader
    WHERE
        VendorID = p_VendorID
        -- Only look at completed orders (Status 4 = Completed)
        AND ShipDate IS NOT NULL
        AND Status = 4;

    RETURN COALESCE(avgLeadTime, 0);

END$$

DELIMITER ;

-- Example usage:
-- Let's check the average lead time for vendor 1494
-- SELECT fn_GetAvgVendorLeadTime(1494) AS AvgVendorWaitTime;


-- ====================================================================
-- STORED PROCEDURE
-- Creates a reusable procedure to search for products by name.
-- ====================================================================
-- Tell MySQL to use '$$' as the end-of-command delimiter
DELIMITER $$

CREATE PROCEDURE sp_SearchProducts(
    IN p_SearchTerm VARCHAR(100)
)
BEGIN
    -- This query will be executed when you "CALL" the procedure
    SELECT
        ProductID,
        Name,
        ListPrice,
        StandardCost
    FROM
        production_product
    WHERE
        -- Use CONCAT to add wildcards (%) to the search term
        Name LIKE CONCAT('%', p_SearchTerm, '%');

END$$

-- Change the delimiter back to the default semicolon
DELIMITER ;

-- Example usages:
-- CALL sp_SearchProducts('Mountain Pedal');
-- CALL sp_SearchProducts('Fork');


-- ====================================================================
-- DDL (Data Definition Language)
-- Creates a new table to store the audit log for price changes.
-- ====================================================================
CREATE TABLE product_price_audit (
    AuditID INT AUTO_INCREMENT PRIMARY KEY,
    ProductID INT,
    OldListPrice DECIMAL(19, 4),
    NewListPrice DECIMAL(19, 4),
    ChangedByUser VARCHAR(100),
    ChangedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ====================================================================
-- TRIGGER
-- Creates a trigger that automatically logs price changes into the audit table.
-- ====================================================================
-- Tell MySQL to use '$$' as the end-of-command delimiter
DELIMITER $$

CREATE TRIGGER trg_ProductPriceAudit
-- This trigger will fire AFTER an UPDATE command on production_product
AFTER UPDATE ON production_product
-- This 'FOR EACH ROW' is required syntax
FOR EACH ROW
BEGIN
    -- We only want to log a change if the price actually changed
    IF OLD.ListPrice <> NEW.ListPrice THEN
        -- Insert a new record into our audit table
        INSERT INTO product_price_audit
        (
            ProductID,
            OldListPrice,
            NewListPrice,
            ChangedByUser
        )
        VALUES
        (
            OLD.ProductID,       -- The ID of the product that was updated
            OLD.ListPrice,       -- The price BEFORE the change
            NEW.ListPrice,       -- The price AFTER the change
            USER()               -- A built-in function to get the current user
        );
    END IF;
END$$

-- Change the delimiter back to the default semicolon
DELIMITER ;


-- ====================================================================
-- TRIGGER TEST
-- This updates a price to test if the trigger works, then selects from the log.
-- ====================================================================
-- UPDATE production_product
-- SET ListPrice = 2500.00
-- WHERE ProductID = 776;

-- SELECT * FROM product_price_audit;
