from datetime import datetime, timedelta, date
from decimal import Decimal
import re

from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import FieldType

import connect

app = Flask(__name__)
app.secret_key = "spb+_@#$"

dbconn = None
connection = None

def getCursor():
    global dbconn
    global connection
    # Establishing a database connection
    connection = mysql.connector.connect(
        user=connect.dbuser,
        password=connect.dbpass,
        host=connect.dbhost,
        database=connect.dbname,
        autocommit=True
    )
    dbconn = connection.cursor()
    return dbconn

@app.route("/")
# Home route Redirects the user to the current jobs page.
def home():
    return redirect("/currentjobs")

#----- Technician Interface-----

@app.route("/currentjobs")
# Route to display unfinished jobs.
# Fetches a list of jobs that are not yet completed, 
# sorted by job date in ascending order, and then by customer's family name and first name.
def currentjobs():
    # Execute SQL query to retrieve unfinished jobs
    query = """
        SELECT j.job_id, 
               CONCAT(COALESCE(c.first_name, ''), ' ', COALESCE(c.family_name, '')) AS full_name,
               j.job_date 
        FROM job j 
        JOIN customer c ON j.customer = c.customer_id 
        WHERE completed = 0 
        ORDER BY j.job_date ASC, c.family_name, c.first_name;
    """ 
    try:
        connection = getCursor()
        connection.execute(query)
        jobList = connection.fetchall()
    except Exception as e:      
        print(e)
    
    return render_template("/technician/currentjoblist.html", job_list=jobList)


@app.route("/currentjobs/jobdetail/<int:job_id>")
# Route to display the details of a specific job 
# Show the services and parts that have already been used in the job
# Once a job is marked complete it cannot be modified and job total cost is calculated
def jobdetail(job_id):
 # SQL queries to fetch job and customer details, services, and parts
    customer_job_query = """
        SELECT j.job_id, CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.family_name,'')) AS full_name,
               c.email, c.phone, j.job_date, j.total_cost, j.completed, j.paid
        FROM job j
        JOIN customer c ON j.customer = c.customer_id
        WHERE j.job_id = %s;
    """
    service_qty_query = """
        SELECT s.service_id, s.service_name, SUM(js.qty) as total_qty, s.cost
        FROM service s
        JOIN job_service js ON s.service_id = js.service_id
        WHERE js.job_id = %s
        GROUP BY s.service_id, s.service_name
        ORDER BY s.service_name;
    """
    part_qty_query = """
        SELECT p.part_id, p.part_name, SUM(jp.qty) as total_qty, p.cost 
        FROM part p
        JOIN job_part jp ON p.part_id = jp.part_id
        WHERE jp.job_id = %s
        GROUP BY p.part_id, p.part_name
        ORDER BY p.part_name;
    """
    services_query = """
        SELECT s.service_id, s.service_name
        FROM service s
        ORDER BY s.service_name ASC;
    """
    parts_query = """
        SELECT p.part_id, p.part_name
        FROM part p
        ORDER BY p.part_name ASC;
    """

    # Execute the queries and fetch data
    try:
        connection = getCursor()
        connection.execute(customer_job_query, (job_id,))
        customer_job_info = connection.fetchall()
  
        connection.execute(service_qty_query, (job_id,))
        service_qty_info = connection.fetchall()
        
        connection.execute(part_qty_query, (job_id,))
        part_qty_info = connection.fetchall()
        
        connection.execute(services_query)
        services_list = connection.fetchall()
        
        connection.execute(parts_query)
        parts_list = connection.fetchall()
    except Exception as e:      
        print(e)
        customer_job_info = []
        service_qty_info = []
        part_qty_info = []
        services_list = []
        parts_list = []
    
    # Calculate total cost for services and parts
    service_total, part_total = calculate_totals(job_id)
    service_total = service_total[0][0] if service_total[0][0] else 0
    part_total = part_total[0][0] if part_total[0][0] else 0

    # Update the total cost of the job
    update_job_total(job_id, service_total + part_total)
    
    # Determine return URL based on request arguments
    return_url = 'schedule' if request.args.get('from') == 'admin' else 'currentjobs'

    # Render the job detail page with all fetched data
    return render_template("/technician/jobdetail.html", customer_job=customer_job_info,
                           services_qty=service_qty_info, parts_qty=part_qty_info,
                           service_list=services_list, part_list=parts_list, datetime=datetime,
                           service_total=service_total, part_total=part_total, back_url=return_url)


@app.route('/currentjobs/jobdetail/add_service_to_job/<int:job_id>', methods=['POST'])
# Adds a service to a specific job.
# This route handles the addition of a service to a job. It checks if the service already exists for the job.
# If it does, the quantity is updated; if not, a new service entry is added to the job.
def add_service_to_job(job_id):   
    # Retrieve service ID and quantity from the form
    service_id = int(request.form['service_id'])
    quantity = int(request.form['addqty'])
    try:
        connection = getCursor()
        # Check if the service already exists for the job
        connection.execute("SELECT * FROM job_service WHERE job_id = %s AND service_id = %s",
                        (job_id, service_id))
        existing_service = connection.fetchall()

        # Update quantity if the service exists, else insert a new record
        if existing_service:
            new_qty = existing_service[0][2] + quantity
            connection.execute("UPDATE job_service SET qty = %s WHERE job_id = %s AND service_id = %s",
                            (new_qty, job_id, service_id))
        else:
            connection.execute("INSERT INTO job_service (job_id, service_id, qty) VALUES (%s, %s, %s)",
                            (job_id, service_id, quantity))

        # Fetch the results to finalize the operation
        connection.fetchall()
    except Exception as e:      
        print(e)

    # Redirect to the job detail page
    return redirect(url_for('jobdetail', job_id=job_id))


@app.route('/currentjobs/jobdetail/add_part_to_job/<int:job_id>', methods=['POST'])
# Adds a part to a specific job.
# This route handles the addition of a part to a job. It checks if the part already exists for the job.
# If it does, the quantity is updated; if not, a new part entry is added to the job.
def add_part_to_job(job_id):
    # Retrieve part ID and quantity from the form data
    part_id = int(request.form['part_id'])
    part_quantity = int(request.form['addqty'])
    try:
    
        connection = getCursor()

        # Check if the part already exists for the job
        connection.execute("SELECT * FROM job_part WHERE job_id = %s AND part_id = %s",
                        (job_id, part_id))
        existing_part = connection.fetchall()

        # Update quantity if the part exists, else insert a new record
        if existing_part:
            new_qty = existing_part[0][2] + part_quantity
            connection.execute("UPDATE job_part SET qty = %s WHERE job_id = %s AND part_id = %s",
                            (new_qty, job_id, part_id))
        else:
            connection.execute("INSERT INTO job_part (job_id, part_id, qty) VALUES (%s, %s, %s)",
                            (job_id, part_id, part_quantity))

        # Fetch the results to finalize the operation
        connection.fetchall()
    except Exception as e:      
        print(e)

    # Reset the local variables (optional, as they are not used afterwards)
    new_qty = 0
    part_quantity = 0

    # Redirect to the job detail page
    return redirect(url_for('jobdetail', job_id=job_id))

@app.route("/currentjobs/jobdetail/complete_job/<int:job_id>")
# Marks a job as completed.
def complete_job(job_id):
    
    # Update the status of the job to 'completed'
    update_job_status(job_id)

    # Redirect to the job detail page with the updated information
    return redirect(url_for("jobdetail", job_id=job_id))

#  Calculates the total cost of services and parts for a specific job.
def calculate_totals(job_id):

    # Queries to calculate total cost of services and parts
    service_total_query = """
        SELECT SUM(s.cost * js.qty)
        FROM job_service js
        JOIN service s ON js.service_id = s.service_id
        WHERE js.job_id = %s;
    """
    part_total_query = """
        SELECT SUM(p.cost * jp.qty)
        FROM job_part jp
        JOIN part p ON jp.part_id = p.part_id
        WHERE jp.job_id = %s;
    """

    try:
        connection = getCursor()
        connection.execute(service_total_query, (job_id,))
        service_total = connection.fetchall()

        connection.execute(part_total_query, (job_id,))
        part_total = connection.fetchall()
    except Exception as e:      
        print(e)

    return service_total, part_total


def update_job_total(job_id, total_cost):
# Updates the total cost of a job in the database.
    update_job_total_query = "UPDATE job SET total_cost = %s WHERE job_id = %s"
    total_cost_value = total_cost[0] if isinstance(total_cost, tuple) else total_cost

    try:
        connection = getCursor()
        connection.execute(update_job_total_query, (total_cost_value, job_id,))
        connection.fetchall()
    except Exception as e:      
        print(e)
    return

#  Updates the status of a job to completed.
def update_job_status(job_id):
    
    update_job_status_query = "UPDATE job SET completed = 1 WHERE job_id = %s"

    try:
        connection = getCursor()
        connection.execute(update_job_status_query, (job_id,))
        connection.fetchall()
    except Exception as e:      
        print(e)
    return

# -----Admin Interface-----

# Redirects to the customer management page in the admin section.
@app.route("/admin")
def admin():
    return redirect("/admin/customers")


@app.route("/admin/customers")
# Customer management route for the admin interface.
# This route fetches and displays a list of all customers.
# The customers are displayed for management purposes such as editing,
# deleting, or adding new customers.
def customers():
    
    # Fetch the list of customers
    customerList = get_customer()
    
    # Render the customer management template with the customer list
    return render_template("/admin/customers.html", customer_list=customerList)

# Fetches a list of all customers from the database.

# This function retrieves customer details including ID, first name, 
# family name, email, and phone number, and orders them by family name and first name.
def get_customer():   
    try:
        connection = getCursor()
        # Execute SQL query to retrieve customer details
        connection.execute("""
            SELECT c.customer_id, 
                COALESCE(c.first_name, '') AS first_name,
                COALESCE(c.family_name, '') AS family_name, 
                COALESCE(c.email, '') AS email, 
                COALESCE(c.phone, '') AS phone 
            FROM customer c
            ORDER BY c.family_name, c.first_name;
        """)
        customer_detail = connection.fetchall()
    except Exception as e:      
        print(e)
    # Return the fetched customer details
    return customer_detail


@app.route("/admin/customers/search", methods=['GET'])
# Handles the customer search functionality in the admin interface.
# Retrieves and displays customers based on the search query. If no customers
# are found matching the query, a message is displayed.
def search_customer():
    query = request.args.get('query', '').strip()
    sanitized_query = sanitize_input(query)
    like_pattern = f"%{sanitized_query}%"

    search_query = """
        SELECT 
            customer_id, 
            COALESCE(first_name, '') AS first_name, 
            COALESCE(family_name, '') AS family_name, 
            COALESCE(email, '') AS email, 
            COALESCE(phone, '') AS phone 
        FROM 
            customer 
        WHERE 
            first_name LIKE %s OR 
            family_name LIKE %s
        ORDER BY 
            family_name, 
            first_name
    """
    try:
        connection = getCursor()
        connection.execute(search_query, (like_pattern, like_pattern))
        customer_list = connection.fetchall()

        no_results_message = "" if customer_list else "No results found for your search query."
    except Exception as e:
        print(f"An error occurred: {e}")
        customer_list = []
        no_results_message = "An error occurred while searching."

    return render_template("/admin/customers.html", customer_list=customer_list, no_results_message=no_results_message)

# Function to sanitize input
def sanitize_input(input_string):
    """
    Sanitizes the input string by ensuring it matches the allowed pattern.

    Only allows alphanumeric characters and spaces. If the input doesn't match,
    returns an empty string.
    """
    pattern = re.compile(r'[A-Za-z0-9 ]+')
    return input_string if pattern.fullmatch(input_string) else ""

@app.route('/admin/customers/add', methods=['POST'])
# Adds a new customer to the database.
def add_customer():
    # Sanitize and validate input
    first_name = request.form['first_name'].strip()
    family_name = request.form['family_name'].strip()
    email = request.form['email'].strip()
    phone = request.form['phone'].strip()

    # Validate family name
    if not family_name or not re.match(r"[A-Za-z]+", family_name):
        flash("Family Name is required and must contain only letters.","error")
        return redirect(url_for('customers'))
    # Validate email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Invalid email address.","error")
        return redirect(url_for('customers'))

    # Validate phone number
    if phone and not re.match(r"[0-9]+", phone):
        flash("Phone number must be 10 digits and contain only numbers.","error")
        return redirect(url_for('customers'))

    try:
        connection = getCursor()
        add_query = """
        INSERT INTO customer (first_name, family_name, email, phone)
        VALUES (%s, %s, %s, %s)
        """
        connection.execute(add_query, (first_name, family_name, email, phone))
        flash("The customer has been added.","success")
    except Exception as e:
        print(f"An error occurred: {e}")
      
    return redirect(url_for('customers'))

@app.route('/admin/customers/delete', methods=['POST'])
# Deletes a customer from the database.
def delete_customer():
    customer_id = request.form.get('customer_id')
    
    try:
        connection = getCursor()
        connection.execute("DELETE FROM customer WHERE customer_id = %s", (customer_id,))
        flash("The user has been deleted.","success")
    except Exception as e:
        print(f"An error occurred while deleting the customer: {e}")
        flash("The user has a job associated with it and cannot be deleted.","error")
    return redirect(url_for('customers'))


@app.route('/admin/customers/update', methods=['POST'])
# Updates an existing customer's information in the database.
def update_customer():
    # Retrieve and sanitize form data
    customer_id = request.form.get('customer_id')
    first_name = request.form.get('first_name').strip()
    family_name = request.form.get('family_name').strip()
    email = request.form.get('email').strip()
    phone = request.form.get('phone').strip()

    # Validate family name
    if not family_name or not re.match(r"[A-Za-z]+", family_name):
        flash("Family Name is required and must contain only letters.","error")
        return redirect(url_for('customers'))

    # Validate email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Invalid email address.","error")
        return redirect(url_for('customers')) 

    # Validate phone number
    if phone and not re.match(r"[0-9]+", phone):
        flash( "Phone number must be 10 digits and contain only numbers.","error")
        return redirect(url_for('customers')) 

    try:
        connection = getCursor()
        update_sql = """
        UPDATE customer
        SET first_name = %s, family_name = %s, email = %s, phone = %s
        WHERE customer_id = %s
        """
        connection.execute(update_sql, (first_name, family_name, email, phone, customer_id))
        flash( "Customer information has been updated","success")
    except Exception as e:
        print(f"An error occurred while updating the customer: {e}")

    return redirect(url_for('customers'))

@app.route("/admin/services")
# Displays the list of services for management.
def services():
    try:
        connection = getCursor()
        connection.execute("""
            SELECT s.service_id, s.service_name, s.cost 
            FROM service s 
            ORDER BY s.service_name;
        """)
        serviceList = connection.fetchall()
    except Exception as e:
        print(f"An error occurred while fetching services: {e}")
        serviceList = []

    return render_template("/admin/services.html", service_list=serviceList)

@app.route("/admin/services/add", methods=['POST'])
# Adds a new service to the database.
def add_service():
    service_name = request.form['service_name'].strip()
    service_name = sanitize_input(service_name)  # Assuming sanitize_input is defined
    cost = request.form['cost']

    # Validate service name
    if not service_name:
        flash( "Service name is required.","error")
        return redirect(url_for('services')) 

    # Validate and convert cost
    try:
        cost = float(cost)
        if cost < 0:
            flash( "Cost cannot be negative.","error")
            return redirect(url_for('services')) 
    except ValueError:
        flash( "Invalid cost value.","error")
        return redirect(url_for('services')) 

    # Insert service into database
    try:
        connection = getCursor()
        add_query = """
            INSERT INTO service (service_name, cost)
            VALUES (%s, %s)
        """
        connection.execute(add_query, (service_name, cost))
        flash("The service has been added.","success")
    except Exception as e:
        print(f"An error occurred while adding a service: {e}")
       
    return redirect(url_for('services'))

    
@app.route('/admin/services/update', methods=['POST'])
#  Updates an existing service in the database.
def update_service():
    service_id = request.form.get('service_id')
    service_name = request.form.get('service_name').strip()
    service_name = sanitize_input(service_name)  # Sanitize the service name
    cost = request.form.get('cost')

    # Validate service name
    if not service_name:
        flash( "Service name is required.","error")
        return redirect(url_for('services')) 

    # Validate and convert cost
    try:
        cost = float(cost)
        if cost < 0:
            flash( "Cost cannot be negative.","error")
            return redirect(url_for('services')) 
    except ValueError:
        flash( "Invalid cost value.","error")
        return redirect(url_for('services')) 

    # Attempt to update the service in the database
    try:
        connection = getCursor()
        sql = """
            UPDATE service
            SET service_name = %s, cost = %s
            WHERE service_id = %s
        """
        connection.execute(sql, (service_name, cost, service_id))
        flash("The service has been updated.","success")
    except Exception as e:
        print(f"An error occurred while updating the service: {e}")
        
    return redirect(url_for('services'))


@app.route('/admin/services/delete', methods=['POST'])
# Delete a service from the database
def delete_service():
    service_id = request.form.get('service_id') 
    try:
        connection = getCursor()
        connection.execute("DELETE FROM service WHERE service_id = %s", (service_id,))
        connection.fetchall()
        flash("The service has been deleted.","success")
    except Exception as e:      
        print(e)
        flash("The service has a job associated with it and cannot be deleted.","error")
    return redirect(url_for('services'))
    

@app.route("/admin/parts")
#  Displays the list of parts for management.
def parts():
    try:
        connection = getCursor()
        connection.execute("""SELECT p.part_id, p.part_name,p.cost 
                            FROM part p
                            ORDER BY p.part_name;""")
        partList = connection.fetchall()
    except Exception as e:      
        print(e)
    return render_template("/admin/parts.html",part_list =partList)  


@app.route("/admin/parts/add", methods=['POST'])
# Add a new part to database
def add_part():
    part_name = request.form['part_name'].strip()
    part_name = sanitize_input(part_name)
    cost = request.form['cost']
    
    # Backend Validations
    if not part_name:
        flash("Part name is required.","error")
        return redirect(url_for('parts')) 
    try:
        cost = float(cost)
        if cost < 0:
            flash("Cost cannot be negative.","error")
            return redirect(url_for('parts')) 
    except ValueError:
        flash("Invalid cost value.","error")
        return redirect(url_for('parts')) 
    
    add_query = """
    INSERT INTO part (part_name, cost)
    VALUES (%s, %s)
    """
    try:
        connection = getCursor()
        connection.execute(add_query, (part_name, cost))
        connection.fetchall()   
        flash("The part has been added.","success")
    except Exception as e:      
        print(e)     
    return redirect(url_for('parts'))
    
@app.route('/admin/parts/update', methods=['POST'])
# Updates an existing part in the database.
def update_part():
    part_id = request.form.get('part_id')
    part_name = request.form.get('part_name').strip()
    part_name = sanitize_input(part_name)
    cost = request.form.get('cost')
    
     # Backend Validations
    if not part_name:
        flash("Part name is required.","error")
        return redirect(url_for('parts')) 
    try:
        cost = float(cost)
        if cost < 0:
            flash("Cost cannot be negative.","error")
            return redirect(url_for('parts')) 
    except ValueError:
        flash("Invalid cost value.","error")
        return redirect(url_for('parts')) 
    
    try:
        connection = getCursor()
        sql = """
        UPDATE part
        SET part_name = %s, cost=%s
        WHERE part_id = %s
        """
        connection.execute(sql, (part_name,cost, part_id))
        connection.fetchall()
        flash("The part has been updated.","success")
    except Exception as e:
        print(e) 
    return redirect(url_for('parts'))

@app.route('/admin/parts/delete', methods=['POST'])
# Delete a part from database
def delete_part():
    part_id = request.form.get('part_id') 
    try:
        connection = getCursor()
        connection.execute("DELETE FROM part WHERE part_id = %s", (part_id,))
        connection.fetchall()
        flash("The part has been deleted.","success")
    except Exception as e:      
        print(e)
        flash("The part has a job associated with it and cannot be deleted.","error")
    return redirect(url_for('parts'))
   
@app.route("/admin/schedule")
#Displays the job schedule in the admin interface.
# Fetches and lists all jobs with their status and associated customer details.
# Also provides a list of customers and the current date for scheduling purposes.
def schedule(): 
    try:
        # Establish database connection
        connection = getCursor()
        # Query to retrieve job details including job status
        connection.execute("""
            SELECT
                j.job_id,
                CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.family_name,'')) AS full_name,
                j.job_date,
                CASE
                    WHEN j.completed = 0 THEN 'In Progress'
                    WHEN j.completed = 1 THEN 'Completed'
                END as job_status
            FROM job j
            JOIN customer c ON j.customer = c.customer_id
            ORDER BY j.completed ASC, j.job_date ASC
        """)

        # Fetch the result of the query
        jobList = connection.fetchall()
    except Exception as e:      
        print(f"An error occurred while fetching job schedule: {e}")
        jobList = []

    # Get a list of all customers
    customerList = get_customer()  # Assuming get_customer is a defined function

    # Get the current date in YYYY-MM-DD format
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Render the schedule template with the job list, customer list, and current date
    return render_template("/admin/schedule.html", job_list=jobList, customer_list=customerList, current_date=current_date)

@app.route("/admin/schedule/booking", methods=['POST'])
# Books a new job for a customer.
# This function handles the booking of a new job by inserting the job details
# into the database. It retrieves the customer ID and job date from the form,
# then inserts a new job record with default values for total cost, completed, 
# and paid status. Redirects to the schedule page after successful booking.
def booking_job(): 
    # Retrieve customer ID and job date from the form
    customer_id = request.form.get('customer_id') 
    date = request.form.get('date') 

    try:
        # Establish database connection
        connection = getCursor()

        # SQL query to insert a new job
        connection.execute("""
            INSERT INTO job (customer, job_date, total_cost, completed, paid)
            VALUES (%s, %s, 0.00, 0, 0)
        """, (customer_id, date))
        connection.fetchall()
        flash("The job has been added.","success")
    except Exception as e:      
        print(f"An error occurred while booking the job: {e}")

    return redirect(url_for('schedule'))

@app.route("/admin/payments")
# Display unpaid bills.
# Order by job date,then customer's family name and first name 
def billpayments():
    customer_list = get_customer()
    try:
        connection = getCursor()
        connection.execute("""
                        SELECT 
                            j.job_id,
                            j.job_date,
                            j.total_cost,
                            c.first_name,
                            c.family_name,
                            c.email,
                            c.phone
                        FROM 
                            job j
                        JOIN 
                            customer c ON j.customer = c.customer_id
                        WHERE 
                            j.completed = 1 AND j.paid = 0
                        ORDER BY 
                            j.job_date, c.family_name, c.first_name;
                        """)
        jobs_data = connection.fetchall()  
    except Exception as e:      
            print(e)
    return render_template("/admin/billpayments.html",jobs_data =jobs_data,customer_list=customer_list) 
 
@app.route("/admin/payments/paybill/<int:job_id>")
# Marks a job as paid in the database.
def pay_bill(job_id):
    update_payment_status="""UPDATE job SET paid = 1 
                        WHERE job_id = %s"""
    try:
        connection = getCursor()
        connection.execute(update_payment_status,(job_id,))
        connection.fetchall()
        flash("The bill has been paid.","success")
    except Exception as e:      
        print(e)    
    return redirect(url_for('billpayments')) 


@app.route("/admin/payments/filter", methods=['GET'])
#  Filters and displays jobs based on the selected customer.
def customer_filter():
    # Retrieve customer_id from query parameters
    customer_id = request.args.get('customer_id', default=None, type=int)
    try:
        connection = getCursor()
         # Check if a specific customer is selected or if the default option is chosen
        if customer_id and customer_id != -1:  # Assuming -1 or another invalid ID for "Choose a Customer"
             # Query to retrieve jobs for a specific customer
            connection.execute("""
                            SELECT 
                                j.job_id,
                                j.job_date,
                                j.total_cost,
                                c.first_name,
                                c.family_name,
                                c.email,
                                c.phone
                            FROM 
                                job j
                            JOIN 
                                customer c ON j.customer = c.customer_id
                            WHERE 
                                j.completed = 1 AND j.paid = 0 AND c.customer_id = %s
                            ORDER BY 
                                j.job_date, c.family_name, c.first_name;
                            """, (customer_id,))
        else:
            # Query to retrieve all unpaid, completed jobs
            connection.execute("""
                            SELECT 
                                j.job_id,
                                j.job_date,
                                j.total_cost,
                                c.first_name,
                                c.family_name,
                                c.email,
                                c.phone
                            FROM 
                                job j
                            JOIN 
                                customer c ON j.customer = c.customer_id
                            WHERE 
                                j.completed = 1 AND j.paid = 0
                            ORDER BY 
                                j.job_date, c.family_name, c.first_name;
                            """)
        jobs_data = connection.fetchall()
    except Exception as e:      
        print(f"An error occurred while filtering jobs: {e}")
        jobs_data = []
        
    # Get a list of all customers
    customer_list = get_customer()  # Assuming get_customer is a defined function
    # Render the bill payments template with filtered job data and customer list
    return render_template("/admin/billpayments.html", jobs_data=jobs_data, customer_list=customer_list)

@app.route("/admin/billhistory")
# Displays the billing history for all customers.
# Retrieves and lists the history of all completed jobs, grouped by customer.
# It also calculates the overdue date for payments, based on a 14-day period.
def billhistory():
    try:
        connection = getCursor()
         # Query to get all completed jobs, ordered by customer name and job date
        connection.execute("""
            SELECT c.customer_id, 
                CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.family_name,'')) AS full_name, 
                c.email, 
                c.phone,
                j.job_id, 
                j.job_date, 
                j.total_cost, 
                j.paid
            FROM job j
            JOIN customer c ON j.customer = c.customer_id
            WHERE j.completed = 1
            ORDER BY c.family_name, c.first_name, j.job_date;
        """)
        jobs_list = connection.fetchall()
    except Exception as e:      
        print(e)
 
    # group jobs by customer
    customer_bill = {}
    for job in jobs_list:
        # Create a unique key for each customer
        customer_key = (job[0], job[1], job[2], job[3])
        print(job)
        # Initialize a list for each customer and append their jobs
        if customer_key not in customer_bill:
            customer_bill[customer_key] = []
        customer_bill[customer_key].append(job)
        pass
    # Calculate the overdue date for payments (14 days before the current date)
    overdue_date = (datetime.now() - timedelta(days=14)).date()

    return render_template("/admin/billhistory.html", customer_bill=customer_bill, overdue_date=overdue_date)

