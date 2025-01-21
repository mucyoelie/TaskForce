Wallet Web Application
This project is a wallet web application developed as a solution for managing personal finances. The application allows users to track transactions,
generate reports, set budgets, and visualize financial summaries.



Features

1.Transaction Tracking
Record all income and expenses from multiple accounts



2.Report Generation
Generate detailed reports for a specific time period to track financial trends.



3.Budget Management
Set budgets and receive notifications when spending exceeds the set limits.



4.Categorization
Add categories and subcategories for expenses and link them to transactions.



5.Visualization
View summaries of transactions with graphs and charts for better understanding.



Technologies Used
Backend: Flask
Frontend: HTML, Tailwind CSS
Database: MySQL


Deployment
The application is hosted on pythonanywhere. You can access it here.


Access Credentials
Username: Admin
Password: (123)





Windows

1. Clone the repository:

	git clone https://github.com/mucyoelie/TaskForce.git  
	cd TaskForce

2. Create and activate a virtual environment:

	python -m venv venv  
	venv\Scripts\activate

3. Install the required dependencies:

	pip install -r requirements.txt

4. Open MySQL and create a database:

	CREATE DATABASE finance_tracker;

5. Import database in :

	/db/finance_tracker.sql

6. Run the project :

	flask run  


Open your browser and navigate to http://127.0.0.1:5000.
