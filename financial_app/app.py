import random
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, flash, url_for, send_file, session, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from io import BytesIO
from flask_mail import Mail, Message

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

app = Flask(__name__, template_folder='components/')
app.secret_key = 'sdafafgahshsjksklakakskak'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'finance_tracker'

mysql = MySQL(app)

bcrypt = Bcrypt(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if user exists
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", [username])
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Check if password matches
            if bcrypt.check_password_hash(user[4], password):  # Assuming the password is stored in the 5th column
                # Store user info in session
                session['user_id'] = user[0]  # Assuming the first column is user ID
                session['username'] = user[1]  # Assuming the second column is the username
                flash("Login successful!", "success")
                return redirect(url_for('index'))  # Redirect to the dashboard page or wherever
            else:
                flash("Invalid password!", "danger")
        else:
            flash("User not found!", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    flash("You have logged out successfully!", "success")
    return redirect(url_for('login'))  # Redirect to the login page





@app.route('/', methods=['GET'])
@login_required
def index():
    cur = mysql.connection.cursor()

    # Execute the query to get account balances (for Total Budget)
    cur.execute("SELECT balance FROM accounts")
    account_balances = cur.fetchall()
    total_budget = sum(balance[0] for balance in account_balances)  # Sum all account balances

    # Execute the query to get transaction data for Total Income and Total Expense
    cur.execute("""
        SELECT 
            t.id AS transaction_id,
            u.full_name AS user_name,
            a.account_name AS account_name,
            t.receiver AS transaction_receiver,
            t.type AS transaction_type,
            t.amount AS transaction_amount,
            t.description AS transaction_description,
            t.date AS transaction_date,
            sc.name AS sub_category_name,
            c.name AS category_name
        FROM 
            transactions t
        JOIN 
            users u ON t.user_id = u.id
        JOIN 
            accounts a ON t.account_id = a.id
        JOIN 
            sub_categories sc ON t.sub_cat_id = sc.id
        JOIN 
            categories c ON sc.cat_id = c.id
    """)
    transactions = cur.fetchall()

    # Calculate Total Income and Total Expense
    total_income = sum(transaction[5] for transaction in transactions if transaction[4].lower() == 'income')
    total_expense = sum(transaction[5] for transaction in transactions if transaction[4].lower() == 'expense')

    # Format the amounts as currency
    formatted_transactions = []
    for transaction in transactions:
        transaction_id, user_name, account_name, receiver, trans_type, amount, description, date, sub_category, category = transaction
        formatted_amount = "{:,.2f}".format(amount)  # Format amount as currency
        formatted_transactions.append((transaction_id, user_name, account_name, receiver, trans_type, formatted_amount,
                                       description, date, sub_category, category))

    cur.close()

    # Return the data to the template
    return render_template('index.html', transactions=formatted_transactions, total_income=total_income,
                           total_expense=total_expense, total_budget=total_budget)


# ----------------------------- users section -------------------------------------
@app.route('/users')
@login_required
def view_users():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    return render_template('users/users.html', users=users)


# 2. Add a new user
@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['email']

        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (full_name, username, email, password) VALUES (%s, %s, %s, %s)",
                       (fullname, username, email, password))
        mysql.connection.commit()
        cursor.close()
        flash("User added successfully!", "success")
        return redirect(url_for('view_users'))
    flash("User not added!", "success")
    return render_template('users/add_user.html')


# 3. Edit a user
@app.route('/edit-user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
    user = cursor.fetchone()
    cursor.close()

    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['email']

        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE users SET full_name = %s, username = %s, email = %s, password = %s WHERE id = %s",
                       (fullname, username, email, password, id))
        mysql.connection.commit()
        cursor.close()
        flash("User updated successfully!", "success")
        return redirect(url_for('view_users'))
    flash("User not updated successfully!", "error")
    return render_template('users/edit_user.html', user=user)


# 4. Delete a user
@app.route('/delete-user/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_user(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("User deleted successfully!", "success")
    return redirect(url_for('view_users'))


# --------------------------- end users section -----------------------------------


# ------------------------- categories and sub_categories --------------------------

@app.route('/categories')
@login_required
def categories():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    cursor.close()
    return render_template('categories/categories.html', categories=categories)


# 2. Add Category
@app.route('/category/add', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO categories (name, description) VALUES (%s, %s)", (name, description))
        mysql.connection.commit()
        cursor.close()
        flash("Category added successfully!", "success")
        return redirect(url_for('categories'))
    return render_template('categories/add_category.html')


# 3. Edit Category
@app.route('/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM categories WHERE id = %s", (id,))
    category = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        cursor.execute("UPDATE categories SET name = %s, description = %s WHERE id = %s", (name, description, id))
        mysql.connection.commit()
        cursor.close()
        flash("Category updated successfully!", "success")
        return redirect(url_for('categories'))

    return render_template('categories/edit_category.html', category=category)


# 4. Delete Category
@app.route('/category/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_category(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM categories WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Category deleted successfully!", "success")
    return redirect(url_for('categories'))


# Subcategories CRUD

# 1. Display Subcategories
@app.route('/sub_categories')
@login_required
def sub_categories():
    cursor = mysql.connection.cursor()

    # Join categories and sub_categories to fetch all relevant fields
    query = """
        SELECT
            sc.id,
            c.name AS category_name, 
            sc.name AS subcategory_name, 
            sc.description AS subcategory_description, 
            sc.date_created AS subcategory_date_created
        FROM sub_categories AS sc
        JOIN categories AS c ON sc.cat_id = c.id
    """
    cursor.execute(query)
    sub_categories = cursor.fetchall()
    cursor.close()

    return render_template('sub_categories/sub_categories.html', sub_categories=sub_categories)


# 2. Add Subcategory
@app.route('/subcategory/add/', methods=['GET', 'POST'])
@login_required
def add_subcategory():
    if request.method == 'POST':
        cat_id = request.form['cat_id']
        name = request.form['name']
        description = request.form['description']
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO sub_categories (cat_id, name, description) VALUES (%s, %s, %s)",
                       (cat_id, name, description))
        mysql.connection.commit()
        cursor.close()
        flash("Subcategory added successfully!", "success")
        return redirect(url_for('sub_categories'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name FROM categories")
    cat_name = cursor.fetchall()
    cursor.close()
    return render_template('sub_categories/add_subcategory.html', cat_name=cat_name)


# 3. Edit Subcategory
@app.route('/subcategory/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_subcategory(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM sub_categories WHERE id = %s", (id,))
    subcategory = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        cursor.execute("UPDATE sub_categories SET name = %s, description = %s WHERE id = %s",
                       (name, description, id))
        mysql.connection.commit()
        cursor.close()
        flash("Subcategory updated successfully!", "success")
        return redirect(url_for('sub_categories'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name FROM categories")
    cat_name = cursor.fetchall()
    cursor.close()
    return render_template('sub_categories/edit_subcategory.html', subcategory=subcategory, cat_name=cat_name)


# 4. Delete Subcategory
@app.route('/subcategory/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_subcategory(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM sub_categories WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Subcategory deleted successfully!", "success")
    return redirect(url_for('sub_categories'))


# ------------------------- end categories and sub_categories --------------------------


# ---------------------------------- transaction ---------------------------------------


@app.route('/transactions', methods=['GET'])
@login_required
def transactions():
    cur = mysql.connection.cursor()

    # Execute the query
    cur.execute("""
        SELECT 
            t.id AS transaction_id,
            u.full_name AS user_name,
            a.account_name AS account_name,
            t.receiver AS transaction_receiver,
            t.type AS transaction_type,
            t.amount AS transaction_amount,
            t.description AS transaction_description,
            t.date AS transaction_date,
            sc.name AS sub_category_name,
            c.name AS category_name
        FROM 
            transactions t
        JOIN 
            users u ON t.user_id = u.id
        JOIN 
            accounts a ON t.account_id = a.id
        JOIN 
            sub_categories sc ON t.sub_cat_id = sc.id
        JOIN 
            categories c ON sc.cat_id = c.id
    """)
    transactions = cur.fetchall()
    cur.close()

    # Format the amounts as currency
    formatted_transactions = []
    for transaction in transactions:
        transaction_id, user_name, account_name, receiver, trans_type, amount, description, date, sub_category, category = transaction
        formatted_amount = "{:,.2f}".format(amount)  # Format amount as currency
        formatted_transactions.append((
            transaction_id, user_name, account_name, receiver, trans_type, formatted_amount,
            description, date, sub_category, category
        ))

    return render_template('transactions/transactions.html', transactions=formatted_transactions)



def send_email_notification(to_email, subject, message):
    import smtplib
    from email.mime.text import MIMEText

    try:
        # Email server configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "info.kwolalabs@gmail.com"
        sender_password = f"{random.Random(9999999)}"  # Use the generated App Password

        # Create the email message
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email

        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Start TLS encryption
            server.login(sender_email, sender_password)  # Login to the email server
            server.send_message(msg)  # Send the email

        print(f"Notification email sent to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transactions():
    if request.method == 'POST':
        user_id = request.form['user_id']
        receiver = request.form["receiver"]
        account_id = request.form['account_id']
        trans_type = request.form['trans_type']
        amount = float(request.form['amount'])
        description = request.form['description']
        date = request.form['date']
        sub_cat_id = request.form['sub_cat_id']

        cur = mysql.connection.cursor()
        cur.execute("SELECT balance, status FROM accounts WHERE id = %s", (account_id,))
        account = cur.fetchone()

        if not account:
            flash('Account not found!', 'danger')
            return redirect('/transactions')

        account_balance, account_status = account

        if account_status != 1:
            flash('The selected account is no longer active!', 'danger')
            return redirect('/transactions')

        if trans_type.lower() == 'expense':
            if amount > account_balance:
                # Fetch email addresses of users with type = 1
                cur.execute("SELECT email FROM users WHERE type = 1")
                emails = cur.fetchall()

                # Send email notifications
                for email in emails:
                    to_email = email[0]
                    subject = "Low Account Balance Alert"
                    message = (
                        f"Dear User,\n\n"
                        f"A transaction could not be processed due to insufficient balance in account ID: {account_id}.\n"
                        f"Transaction Amount: {amount:,.2f}\n"
                        f"Current Balance: {account_balance:,.2f}\n\n"
                        f"Please take the necessary action."
                    )
                    send_email_notification(to_email, subject, message)

                flash('Insufficient balance in the selected account! Notifications sent.', 'danger')
                return redirect('/transactions')

            # Deduct the amount from the account balance
            new_balance = account_balance - amount
        elif trans_type.lower() == 'income':
            new_balance = account_balance + amount
        else:
            flash('Invalid transaction type!', 'danger')
            return redirect('/transactions')

        cur.execute("""
            INSERT INTO transactions (user_id, receiver, account_id, type, amount, description, date, sub_cat_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, receiver, account_id, trans_type, amount, description, date, sub_cat_id))

        cur.execute("UPDATE accounts SET balance = %s WHERE id = %s", (new_balance, account_id))
        mysql.connection.commit()
        cur.close()

        flash('Transaction added successfully!', 'success')
        return redirect('/transactions')

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, account_name FROM accounts WHERE status = %s", (1,))
    accounts = cur.fetchall()
    cur.execute("SELECT id, name FROM categories")
    cat = cur.fetchall()
    cur.close()

    return render_template('transactions/add_transactions.html', accounts=accounts, cat=cat)


@app.route('/delete_transaction/<int:transaction_id>', methods=['GET'])
@login_required
def delete_transaction(transaction_id):
    cur = mysql.connection.cursor()

    # Get transaction details
    cur.execute("SELECT account_id, amount FROM transactions WHERE id = %s", (transaction_id,))
    transaction = cur.fetchone()

    if not transaction:
        flash('Transaction not found!', 'danger')
        return redirect('/transactions')

    account_id, amount = transaction

    # Update the account balance
    cur.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (amount, account_id))

    # Delete the transaction
    cur.execute("DELETE FROM transactions WHERE id = %s", (transaction_id,))
    mysql.connection.commit()
    cur.close()

    flash('Transaction deleted and account balance updated!', 'success')
    return redirect('/transactions')


@app.route('/get_subcategories/<int:category_id>', methods=['GET'])
@login_required
def get_subcategories(category_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM sub_categories WHERE cat_id = %s", (category_id,))
    subcategories = cur.fetchall()
    cur.close()

    # Convert the data into a JSON format
    subcategories_list = [{'id': sub[0], 'name': sub[1]} for sub in subcategories]
    return jsonify({'subcategories': subcategories_list})


# ---------------------------------- end transaction ---------------------------------------

# -------------------------------------- accounts -------------------------------------------


@app.route('/budget')
@login_required
def accounts():
    cursor = mysql.connection.cursor()

    # Update statuses based on current date and `end_date`
    current_date = datetime.now()
    cursor.execute("""
        UPDATE accounts
        SET status = 0
        WHERE end_date < %s
    """, (current_date,))
    mysql.connection.commit()

    # Fetch all accounts
    cursor.execute("SELECT * FROM accounts")
    accounts = cursor.fetchall()

    # Format the balance as currency
    formatted_accounts = []
    for account in accounts:
        account_id, account_name, balance, start_date, end_date, status = account
        formatted_balance = "{:,.2f}".format(balance)  # Format the balance as currency
        formatted_accounts.append((account_id, account_name, formatted_balance, start_date, end_date, status))

    cursor.close()

    return render_template('budgets/accounts.html', accounts=formatted_accounts)


@app.route('/create_budget', methods=['GET', 'POST'])
@login_required
def create_account():
    if request.method == 'POST':
        account_name = request.form['acc_name']
        balance = request.form['balance']
        start_date = request.form['start_date']
        end_date = request.form['end_date']


        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO accounts (account_name, balance, start_date, end_date) 
            VALUES (%s, %s, %s, %s)
        """, (account_name, balance, start_date, end_date))
        mysql.connection.commit()
        cursor.close()
        flash('Account Created Successfully!', 'success')
        return redirect(url_for('accounts'))
    return render_template('budgets/add_account.html')


@app.route('/edit_budget/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_account(id):
    cursor = mysql.connection.cursor()
    if request.method == 'POST':
        account_name = request.form['acc_name']
        balance = request.form['balance']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']

        cursor.execute("""
            UPDATE accounts 
            SET account_name = %s, balance = %s, start_date = %s, end_date = %s, status = %s 
            WHERE id = %s
        """, (account_name, balance, start_date, end_date, status, id))
        mysql.connection.commit()
        cursor.close()
        flash('Account Updated Successfully!', 'success')
        return redirect(url_for('accounts'))

    cursor.execute("SELECT * FROM accounts WHERE id = %s", (id,))
    account = cursor.fetchone()
    cursor.close()
    return render_template('budgets/edit_account.html', account=account)


@app.route('/delete_budget/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_account(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM accounts WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash('Account Deleted Successfully!', 'danger')
    return redirect(url_for('accounts'))


# -------------------------------------- accounts -------------------------------------------


@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    cur = mysql.connection.cursor()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date and end_date:
        query = """
            SELECT 
                t.id AS transaction_id,
                u.full_name AS user_name,
                a.account_name AS account_name,
                t.receiver AS transaction_receiver,
                t.type AS transaction_type,
                t.amount AS transaction_amount,
                t.description AS transaction_description,
                t.date AS transaction_date,
                sc.name AS sub_category_name,
                c.name AS category_name
            FROM 
                transactions t
            JOIN 
                users u ON t.user_id = u.id
            JOIN 
                accounts a ON t.account_id = a.id
            JOIN 
                sub_categories sc ON t.sub_cat_id = sc.id
            JOIN 
                categories c ON sc.cat_id = c.id
            WHERE 
                t.date BETWEEN %s AND %s
        """
        cur.execute(query, (start_date, end_date))
    else:
        query = """
            SELECT 
                t.id AS transaction_id,
                u.full_name AS user_name,
                a.account_name AS account_name,
                t.receiver AS transaction_receiver,
                t.type AS transaction_type,
                t.amount AS transaction_amount,
                t.description AS transaction_description,
                t.date AS transaction_date,
                sc.name AS sub_category_name,
                c.name AS category_name
            FROM 
                transactions t
            JOIN 
                users u ON t.user_id = u.id
            JOIN 
                accounts a ON t.account_id = a.id
            JOIN 
                sub_categories sc ON t.sub_cat_id = sc.id
            JOIN 
                categories c ON sc.cat_id = c.id
        """
        cur.execute(query)

    transactions = cur.fetchall()
    cur.close()

    # Format the amounts as currency
    formatted_transactions = []
    for transaction in transactions:
        transaction_id, user_name, account_name, receiver, trans_type, amount, description, date, sub_category, category = transaction
        formatted_amount = "{:,.2f}".format(amount)  # Format amount as currency
        formatted_transactions.append((
            transaction_id, user_name, account_name, receiver, trans_type, formatted_amount,
            description, date, sub_category, category
        ))

    return render_template('transactions/report.html', transactions=formatted_transactions, start_date=start_date,
                           end_date=end_date)


@app.route('/download_pdf', methods=['GET'])
@login_required
def download_pdf():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    cur = mysql.connection.cursor()
    query = """
        SELECT 
            t.id AS transaction_id,
            u.full_name AS user_name,
            a.account_name AS account_name,
            t.receiver AS transaction_receiver,
            t.type AS transaction_type,
            t.amount AS transaction_amount,
            t.description AS transaction_description,
            t.date AS transaction_date,
            sc.name AS sub_category_name,
            c.name AS category_name
        FROM 
            transactions t
            JOIN users u ON t.user_id = u.id
            JOIN accounts a ON t.account_id = a.id
            JOIN sub_categories sc ON t.sub_cat_id = sc.id
            JOIN categories c ON sc.cat_id = c.id
    """
    if start_date and end_date:
        query += " WHERE t.date BETWEEN %s AND %s"
        cur.execute(query, (start_date, end_date))
    else:
        cur.execute(query)

    transactions = cur.fetchall()
    cur.close()

    # Headers for the table
    headers = ["#", "Name", "Account", "Receiver", "Type", "Amount", "Description", "Date", "Category", "Subcategory"]
    font_name = "Helvetica"
    font_size = 10

    # Calculate column widths
    col_widths = [stringWidth("#", font_name, font_size) + 10]  # Initial width for the auto-increment column
    for header in headers[1:]:  # Skip "#" (already initialized)
        col_widths.append(stringWidth(header, font_name, font_size) + 20)

    for idx, t in enumerate(transactions, start=1):  # Add index for auto-increment
        col_widths[0] = max(col_widths[0], stringWidth(str(idx), font_name, font_size) + 10)
        col_widths[1] = max(col_widths[1], stringWidth(t[1], font_name, font_size) + 10)
        col_widths[2] = max(col_widths[2], stringWidth(t[2], font_name, font_size) + 10)
        col_widths[3] = max(col_widths[3], stringWidth(t[3], font_name, font_size) + 10)
        col_widths[4] = max(col_widths[4], stringWidth(t[4], font_name, font_size) + 10)
        col_widths[5] = max(col_widths[5], stringWidth(f"{t[5]:,.2f}", font_name, font_size) + 10)
        col_widths[6] = max(col_widths[6], stringWidth(t[6], font_name, font_size) + 10)
        col_widths[7] = max(col_widths[7], stringWidth(t[7].strftime("%Y-%m-%d"), font_name, font_size) + 10)
        col_widths[8] = max(col_widths[8], stringWidth(t[9], font_name, font_size) + 10)
        col_widths[9] = max(col_widths[9], stringWidth(t[8], font_name, font_size) + 10)

    # Prepare table data
    data = [headers]
    for idx, t in enumerate(transactions, start=1):  # Add index for auto-increment
        row = [
            str(idx),  # Auto-increment ID
            t[1],  # Name
            t[2],  # Account
            t[3],  # Receiver
            t[4],  # Type
            f"{t[5]:,.2f}",  # Amount
            t[6],  # Description
            t[7].strftime("%Y-%m-%d") if isinstance(t[7], datetime) else str(t[7]),  # Date
            t[9],  # Category
            t[8],  # Subcategory
        ]
        data.append(row)

    # Generate PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
    pdf.setTitle("Transaction Report")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(300, 550, "Transaction Report")
    pdf.setFont("Helvetica", 12)

    if start_date and end_date:
        pdf.drawString(30, 500, f"Date Range: {start_date} to {end_date}")
    else:
        pdf.drawString(30, 500, "Date Range: All Records")

    # Create Table
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))

    # Position and render table
    table.wrapOn(pdf, 800, 300)
    table.drawOn(pdf, 30, 200)

    pdf.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Transaction_Report_{start_date}_TO_{end_date}.pdf",
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)
