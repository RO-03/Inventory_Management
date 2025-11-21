import os
import mysql.connector
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, g
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
# A secret key is required for 'flashing' messages
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a_very_secret_default_key')

# --- Database Connection ---

def get_db_connection():
# ... existing code ...
    if 'db_conn' not in g:
        try:
            g.db_conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'adventureworks')
            )
        except mysql.connector.Error as err:
            print(f"Error connecting to database: {err}")
            g.db_conn = None
    return g.db_conn

@app.teardown_appcontext
def close_db_connection(exception):
# ... existing code ...
    db_conn = g.pop('db_conn', None)
    if db_conn is not None:
        db_conn.close()

# --- Helper Function for Procedure Errors ---
def handle_sql_error(err, success_message, redirect_url):
# ... existing code ...
    if err.errno == 1644: # This is the '45000' SQLSTATE we signaled
        flash(f"Error: {err.msg}", 'error')
    else:
        flash(f"An unexpected database error occurred: {err}", 'error')
    return redirect(redirect_url)

# --- Main Routes ---

@app.route('/')
def index():
# ... existing code ...
    return render_template('index.html')

@app.route('/vendors', methods=['GET', 'POST'])
def vendors_page():
# ... (this route is unchanged from the last version) ...
    conn = get_db_connection()

    # --- POST Form Handling ---
    if request.method == 'POST':
        form_name = request.form.get('form_name')

        # --- Form 1: Get Avg Vendor Lead Time (Feature 9) ---
        if form_name == 'vendor_lead_time_form':
            vendor_id_str = request.form.get('vendor_id') 
            if not vendor_id_str:
                flash("Please enter a Vendor ID.", 'error')
                return redirect(url_for('vendors_page'))
            try:
                vendor_id = int(vendor_id_str)
            except ValueError:
                flash(f"Invalid Vendor ID: '{vendor_id_str}' is not a number.", 'error')
                return redirect(url_for('vendors_page'))
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS count FROM purchasing_vendor WHERE BusinessEntityID = %s", (vendor_id,))
                if cursor.fetchone()['count'] == 0:
                    flash(f"Error: Vendor ID {vendor_id} does not exist.", 'error')
                else:
                    cursor.execute("SELECT fn_GetAvgVendorLeadTime(%s) AS lead_time", (vendor_id,))
                    result = cursor.fetchone()
                    flash(f"Average lead time for Vendor {vendor_id}: {result['lead_time']} days", 'success')
                cursor.close()
            except mysql.connector.Error as err:
                return handle_sql_error(err, "", url_for('vendors_page'))
            return redirect(url_for('vendors_page'))

        # --- Form 2: Buy From Vendor (NEW) ---
        # *** THIS BLOCK WAS REMOVED IN PREVIOUS STEP ***
        
    # --- GET Data Loading ---
    vendor_report_data = []
    purchase_history_data = [] 
    try:
        cursor = conn.cursor(dictionary=True)
        # Feature 2: Vendor Performance Report
        query_feature_2 = """
        SELECT v.Name AS VendorName, v.BusinessEntityID,
            COUNT(poh.PurchaseOrderID) AS TotalOrders,
            SUM(poh.TotalDue) AS TotalPurchaseValue
        FROM purchasing_vendor AS v
        LEFT JOIN purchasing_purchaseorderheader AS poh ON v.BusinessEntityID = poh.VendorID
        GROUP BY v.BusinessEntityID, v.Name
        ORDER BY TotalPurchaseValue DESC;
        """
        cursor.execute(query_feature_2)
        vendor_report_data = cursor.fetchall()

        # Get Product Purchase History
        query_purchase_history = """
        SELECT
            v.BusinessEntityID AS VendorID,
            v.Name AS VendorName,
            p.ProductID,
            p.Name AS ProductName,
            pod.UnitPrice AS LastPricePaid
        FROM
            purchasing_purchaseorderdetail pod
        JOIN
            production_product p ON pod.ProductID = p.ProductID
        JOIN
            purchasing_purchaseorderheader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
        JOIN
            purchasing_vendor v ON poh.VendorID = v.BusinessEntityID
        GROUP BY
            v.BusinessEntityID, p.ProductID, v.Name, p.Name, pod.UnitPrice
        ORDER BY
            VendorName, ProductName
        LIMIT 100; 
        """
        cursor.execute(query_purchase_history)
        purchase_history_data = cursor.fetchall()

        cursor.close()
    except mysql.connector.Error as err:
        flash(f"Error loading page data: {err}", 'error')

    return render_template(
        'vendors.html',
        vendor_data=vendor_report_data,
        purchase_history_data=purchase_history_data 
    )


@app.route('/warehouse', methods=['GET', 'POST'])
def warehouse_page():
    # ... (POST handling code is unchanged) ...
    conn = get_db_connection()

    # --- POST Form Handling ---
    if request.method == 'POST':
        form_name = request.form.get('form_name')
        
        # --- Form 1: Update Price (Feature 12) ---
        if form_name == 'update_price_form':
            product_id_str = request.form.get('product_id')
            new_price_str = request.form.get('new_price')
            
            if not product_id_str or not new_price_str:
                flash("Please enter both Product ID and New Price.", 'error')
                return redirect(url_for('warehouse_page'))

            try:
                product_id = int(product_id_str)
                new_price = float(new_price_str)
            except ValueError:
                flash("Invalid input: Product ID must be an integer and Price must be a number.", 'error')
                return redirect(url_for('warehouse_page'))
            
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE production_product SET ListPrice = %s WHERE ProductID = %s", 
                    (new_price, product_id)
                )
                conn.commit()
                
                if cursor.rowcount == 0:
                    flash(f"Warning: Product ID {product_id} was not found. No price was updated.", 'warning')
                else:
                    flash(f"Successfully updated price for Product {product_id}. Check audit log below!", 'success')
                cursor.close()
            except mysql.connector.Error as err:
                return handle_sql_error(err, "", url_for('warehouse_page'))

        # --- Form 2: Get Product Stock (Feature 7) ---
        elif form_name == 'get_stock_form':
            product_id_str = request.form.get('product_id_stock')

            if not product_id_str:
                flash("Please enter a Product ID.", 'error')
                return redirect(url_for('warehouse_page'))

            try:
                product_id = int(product_id_str)
            except ValueError:
                flash(f"Invalid Product ID: '{product_id_str}' is not a number.", 'error')
                return redirect(url_for('warehouse_page'))
            
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS count FROM production_product WHERE ProductID = %s", (product_id,))
                
                if cursor.fetchone()['count'] == 0:
                    flash(f"Error: Product ID {product_id} does not exist.", 'error')
                else:
                    cursor.execute("SELECT fn_GetProductStock(%s) AS stock", (product_id,))
                    result = cursor.fetchone()
                    flash(f"Current stock for Product {product_id}: {result['stock']} units", 'success')
                cursor.close()
            except mysql.connector.Error as err:
                return handle_sql_error(err, "", url_for('warehouse_page'))
        
        return redirect(url_for('warehouse_page'))

    # --- GET Data Loading ---
    inventory_value_data = []
    unsold_products_data = []
    main_warehouse_stock = []
    locations_data = [] # <-- Keep this for the 4th report
    audit_log_data = []

    try:
        cursor = conn.cursor(dictionary=True)

        # Report 1: Total Inventory Value (Top 20)
        query_report_1 = """
        SELECT p.ProductID, p.Name, p.ListPrice, p.StandardCost,
            COALESCE(SUM(pi.Quantity), 0) AS TotalStock,
            (p.StandardCost * COALESCE(SUM(pi.Quantity), 0)) AS TotalInventoryValue
        FROM production_product AS p
        LEFT JOIN production_productinventory AS pi ON p.ProductID = pi.ProductID
        GROUP BY p.ProductID, p.Name, p.ListPrice, p.StandardCost
        ORDER BY TotalInventoryValue DESC LIMIT 20;
        """
        cursor.execute(query_report_1)
        inventory_value_data = cursor.fetchall()

        # Report 2: ALL Items in Main Warehouse Stock
        # *** FIX: Removed LIMIT ***
        query_report_2 = """
        SELECT p.ProductID, p.Name, pi.Quantity, p.ListPrice
        FROM production_productinventory pi
        JOIN production_product p ON pi.ProductID = p.ProductID
        WHERE pi.LocationID = 1 AND pi.Quantity > 0
        ORDER BY p.Name;
        """
        cursor.execute(query_report_2)
        main_warehouse_stock = cursor.fetchall()

        # Report 3: Products Never Sold
        query_report_3 = """
        SELECT ProductID, Name, ListPrice, StandardCost
        FROM production_product
        WHERE ProductID NOT IN (SELECT DISTINCT ProductID FROM sales_salesorderdetail);
        """
        cursor.execute(query_report_3)
        unsold_products_data = cursor.fetchall()

        # Report 4: Live Inventory Location (View)
        # *** FIX: Removed LIMIT ***
        # Make sure the view vw_ProductLocations exists!
        query_report_4 = "SELECT * FROM vw_ProductLocations ORDER BY ProductName, LocationName;"
        cursor.execute(query_report_4)
        locations_data = cursor.fetchall()

        # Audit Log (for Price Update tool)
        query_audit_log = "SELECT * FROM product_price_audit ORDER BY ChangedAt DESC LIMIT 5;"
        cursor.execute(query_audit_log)
        audit_log_data = cursor.fetchall()

        cursor.close()

    except mysql.connector.Error as err:
        if "1146" in str(err): # Table or View doesn't exist
            if "vw_ProductLocations" in str(err):
                flash("Error: The view 'vw_ProductLocations' does not exist. Please create it using the provided SQL.", 'error')
                locations_data = None # Prevent template error
            elif "product_price_audit" in str(err):
                flash("Error: The table 'product_price_audit' does not exist. Please create it using the provided SQL.", 'error')
                audit_log_data = None # Prevent template error
            else:
                 flash(f"Error loading warehouse data: A table is missing ({err})", 'error')
        else:
            flash(f"Error loading warehouse data: {err}", 'error')

    return render_template(
        'warehouse.html',
        inventory_value_data=inventory_value_data,
        main_warehouse_stock=main_warehouse_stock, # Pass the full list
        unsold_products_data=unsold_products_data,
        locations_data=locations_data, # Pass the full list
        audit_log_data=audit_log_data
    )

@app.route('/search')
def search_page():
# ... (this route is unchanged from the last version) ...
    search_term = request.args.get('search_term', '')
    search_results = []
    
    if search_term:
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # CALL the stored procedure
            cursor.callproc('sp_SearchProducts', [search_term])
            # Stored procedures return results in an iterator
            for result in cursor.stored_results():
                search_results = result.fetchall()
            cursor.close()
        except mysql.connector.Error as err:
            return handle_sql_error(err, "", url_for('search_page'))

    return render_template('search_results.html', 
                           search_term=search_term, 
                           results=search_results)


@app.route('/consumers', methods=['GET', 'POST'])
def consumers_page():
# ... (this route is unchanged from the last version) ...
    conn = get_db_connection()
    
    # --- POST Form Handling ---
    if request.method == 'POST':
        form_name = request.form.get('form_name')

        # --- Form 1: Get Avg Product Delivery Time (Feature 8) ---
        if form_name == 'product_delivery_form':
            product_id_str = request.form.get('product_id_delivery') # Renamed field
            if not product_id_str:
                flash("Please enter a Product ID.", 'error')
                return redirect(url_for('consumers_page'))
            try:
                product_id = int(product_id_str)
            except ValueError:
                flash(f"Invalid Product ID: '{product_id_str}' is not a number.", 'error')
                return redirect(url_for('consumers_page'))
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS count FROM production_product WHERE ProductID = %s", (product_id,))
                if cursor.fetchone()['count'] == 0:
                    flash(f"Error: Product ID {product_id} does not exist.", 'error')
                else:
                    cursor.execute("SELECT fn_GetAvgProductDeliveryTime(%s) AS delivery_time", (product_id,))
                    result = cursor.fetchone()
                    flash(f"Average delivery time for Product {product_id}: {result['delivery_time']} days", 'success')
                cursor.close()
            except mysql.connector.Error as err:
                return handle_sql_error(err, "", url_for('consumers_page'))
            return redirect(url_for('consumers_page'))
        
        # --- Form 2: Place Consumer Order (NEW) ---
        # *** THIS ENTIRE 'elif' BLOCK HAS BEEN REMOVED ***


    # --- GET Data Loading (Features 3 & 5) ---
    top_customers_data = []
    avg_shipping_data = None
    sales_history_data = [] 
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Feature 5: Top 10 Customers (CTE Query)
        query_feature_5 = """
        WITH CustomerSpending AS (
            SELECT c.CustomerID, p.FirstName, p.LastName,
                SUM(soh.TotalDue) AS TotalSpending
            FROM sales_customer AS c
            JOIN person_person AS p ON c.PersonID = p.BusinessEntityID
            JOIN sales_salesorderheader AS soh ON c.CustomerID = soh.CustomerID
            GROUP BY c.CustomerID, p.FirstName, p.LastName
        )
        SELECT
            RANK() OVER (ORDER BY TotalSpending DESC) AS CustomerRank,
            FirstName, LastName, TotalSpending
        FROM CustomerSpending
        ORDER BY CustomerRank ASC LIMIT 10;
        """
        cursor.execute(query_feature_5)
        top_customers_data = cursor.fetchall()

        # Feature 3: Average Shipping Lead Time
        query_feature_3 = """
        SELECT AVG(DATEDIFF(ShipDate, OrderDate)) AS AvgLeadTime
        FROM sales_salesorderheader
        WHERE ShipDate IS NOT NULL AND Status = 5;
        """
        cursor.execute(query_feature_3)
        avg_shipping_data = cursor.fetchone()

        # Get Sales History
        query_sales_history = """
        SELECT
            c.CustomerID,
            p.FirstName,
            p.LastName,
            prod.ProductID,
            prod.Name AS ProductName
        FROM
            sales_salesorderdetail sod
        JOIN
            sales_salesorderheader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN
            sales_customer c ON soh.CustomerID = c.CustomerID
        JOIN
            person_person p ON c.PersonID = p.BusinessEntityID
        JOIN
            production_product prod ON sod.ProductID = prod.ProductID
        GROUP BY
            c.CustomerID, p.FirstName, p.LastName, prod.ProductID, prod.Name
        ORDER BY
            p.LastName, prod.Name 
        LIMIT 100;
        """
        cursor.execute(query_sales_history)
        sales_history_data = cursor.fetchall()
        
        cursor.close()
    except mysql.connector.Error as err:
        flash(f"Error loading consumer data: {err}", 'error')

    return render_template(
        'consumers.html', 
        top_customers_data=top_customers_data,
        avg_shipping_data=avg_shipping_data,
        sales_history_data=sales_history_data 
    )

# --- Run the Application ---
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)