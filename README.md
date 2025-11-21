# AdventureWorks Warehouse Management System  
### Integrated Database Application for Inventory, Vendor & Sales Management

**Course:** Database Management System (UE23CS351A)  
**Team Members:** Vishal P, Roshan KC

---

## Project Overview

Adventure Works Cycles, a global manufacturing company, faces inefficiencies in stock control and order fulfillment due to disconnected data systems.  
This project implements an **Integrated Warehouse & Inventory Management System** that streamlines operations by consolidating data into a unified backend built on the AdventureWorks schema.

The system includes:

- Real-time inventory insights  
- Vendor performance analysis  
- Customer value tracking  
- ACID-compliant transactional ordering  
- Automated auditing using triggers  
- A simple web interface for real-time decision-making

---

## Key Features

### 🔹 Real-Time Inventory Dashboard  
Monitor stock levels and total warehouse asset value across all locations.

### 🔹 Vendor Performance Analysis  
Rank suppliers by total purchase value and calculate average lead time.

### 🔹 Customer Insights  
Identify the highest-value customers based on lifetime purchases.

### 🔹 Transactional Ordering  
Place customer sales orders and receive vendor shipments with full ACID compliance and automatic stock updates.

### 🔹 Automated Auditing  
Track every product price change using triggers and audit tables.

---

## Tech Stack

| Component | Technology |
|----------|------------|
| **Database** | MySQL 8.0 |
| **Backend** | Python 3.10+ (Flask) |
| **Frontend** | HTML5, JavaScript (ES6), Tailwind CSS |
| **Connector** | mysql-connector-python |
| **Tools** | MySQL Workbench, VS Code |

---

## How to Run the Project

### **1. Database Setup**

#### Install MySQL  
Ensure MySQL Server 8.0+ is installed and running.

#### Create Database  
Open **MySQL Workbench** and run the script:

- `databaseSetup.sql` → Creates the base AdventureWorks schema  
- `functionalitiesImplementation.sql` → Installs all custom backend logic:

  - Views 
  - Functions
  - Stored Procedures 
  - Triggers 
  - Audit tables 

---

### **2. Application Setup**

#### Clone the Repository
```bash
git clone https://github.com/RO-03/Inventory_Management.git
cd AdventureWorks-Warehouse-App
````

#### Install Python Dependencies

```bash
pip install Flask mysql-connector-python
```

#### Configure Database Connection

```python
db_config = {
    'user': 'root',
    'password': 'YOUR_PASSWORD',
    'host': 'localhost',
    'database': 'adventureworks'
}
```

#### Run the Server

```bash
flask run
```

#### Access the Application

Open your browser:
 **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**


---

## Application Screenshots

*(Included in the project report)*

* Inventory Dashboard: Real-time stock & value tracking
* Vendor Report: Supplier ranking by purchase value
* Order Form: ACID-compliant order placement


