from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from decimal import Decimal

import re
from datetime import datetime
import mysql.connector
from mysql.connector import FieldType
import connect

app = Flask(__name__)

dbconn = None
connection = None

def getCursor():
    global dbconn
    global connection
    connection = mysql.connector.connect(user=connect.dbuser, \
    password=connect.dbpass, host=connect.dbhost, \
    database=connect.dbname, autocommit=True)
    dbconn = connection.cursor()
    return dbconn


# Technician Interface
# Main page redirect to /currentjobs
@app.route("/")
def home():
    return redirect("/currentjobs")

# Use to display unfinished jobs
@app.route("/currentjobs")
def currentjobs():
    connection = getCursor()
    connection.execute("SELECT j.job_id, CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.family_name,'')) AS full_name,j.job_date \
                        FROM job j \
                        JOIN customer c ON j.customer = c.customer_id \
                        where completed=0 ;")
    jobList = connection.fetchall()
    
    return render_template("currentjoblist.html", job_list = jobList)    

# Used to show the details of a specific job
@app.route("/currentjobs/jobdetail/<int:job_id>")
def jobdetail(job_id):
    customer_job_query = """
        SELECT 
            j.job_id,
            CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.family_name,'')) AS full_name,
            c.email, 
            c.phone, 
            j.job_date, 
            j.total_cost, 
            j.completed, 
            j.paid
        FROM 
            job j
        JOIN 
            customer c ON j.customer = c.customer_id
        WHERE 
            j.job_id = %s;
        """
    service_qty_query = """
            SELECT 
                s.service_id,
                s.service_name,              
                SUM(js.qty) as total_qty,
                s.cost
            FROM 
                service s
            JOIN 
                job_service js ON s.service_id = js.service_id
            WHERE 
                js.job_id = %s
            GROUP BY s.service_id, s.service_name;
            """    
    part_qty_query = """
            SELECT 
                p.part_id,
                p.part_name, 
                SUM(jp.qty) as total_qty,
                p.cost 
            FROM 
                part p
            JOIN 
                job_part jp ON p.part_id = jp.part_id
            WHERE 
                jp.job_id = %s
            GROUP BY 
                p.part_id, p.part_name;
            """  
    services_query ="""
            SELECT 
                s.service_id,
                s.service_name                           
            FROM 
	            service s
            ORDER BY 
                s.service_name ASC;
            """  
    parts_query ="""
            SELECT 
                p.part_id,
                p.part_name                           
            FROM 
	            part p
            ORDER BY 
                p.part_name ASC;
            """  
    connection = getCursor()
    connection.execute(customer_job_query, (job_id,))
    customer_job_info=connection.fetchall()
    
    connection.execute(service_qty_query, (job_id,))
    service_qty_info = connection.fetchall()
    
    connection.execute(part_qty_query, (job_id,))
    part_qty_info = connection.fetchall()
    
    connection.execute(services_query)
    services_list = connection.fetchall()
    
    connection.execute(parts_query)
    parts_list = connection.fetchall()
    # Additionally, get the service_total and part_total from the query parameters if they exist.
    service_total = request.args.get('service_total', 0)
    part_total = request.args.get('part_total', 0)
   
    
    return render_template("jobdetail.html",customer_job=customer_job_info, \
            services_qty=service_qty_info, parts_qty=part_qty_info, \
            service_list =services_list,  part_list =parts_list, datetime=datetime, \
            service_total=service_total , \
            part_total=part_total
            )

# Used to add service to a specific job
@app.route('/currentjobs/jobdetail/add_service_to_job/<int:job_id>', methods=['POST'])
def add_service_to_job(job_id):   
    service_id = int(request.form['service_id'])
    quantity = int(request.form['addqty'])
    connection = getCursor()
    connection.execute("""SELECT * FROM job_service 
                    WHERE job_id = %s AND service_id = %s""",
                    (job_id, service_id))
    existing_service = connection.fetchall()
    if existing_service:
        new_qty = existing_service[0][2] + quantity
        connection.execute("""UPDATE job_service SET qty = %s 
                              WHERE job_id = %s AND service_id = %s""",
                              (new_qty, job_id, service_id))
        
    else:
        connection.execute("""INSERT INTO job_service (job_id, service_id, qty) 
                              VALUES (%s, %s, %s)""",
                              (job_id, service_id, quantity))     
    connection.fetchall()
    new_qty = 0
    quantity= 0 
    return redirect(url_for('jobdetail', job_id=job_id))

# Used to add part to a specific job
@app.route('/currentjobs/jobdetail/add_part_to_job/<int:job_id>', methods=['POST'])
def add_part_to_job(job_id):
    
    part_id = int(request.form['part_id'])
    part_quantity = int(request.form['addqty'])
    connection = getCursor()
    connection.execute("""SELECT * FROM job_part 
                    WHERE job_id = %s AND part_id = %s""",
                    (job_id, part_id))
    existing_part = connection.fetchall()    
    if existing_part:
        new_qty = existing_part[0][2] + part_quantity
        connection.execute("""UPDATE job_part SET qty = %s 
                              WHERE job_id = %s AND part_id = %s""",
                              (new_qty, job_id, part_id))
        
    else:
        connection.execute("""INSERT INTO job_part (job_id, part_id, qty) 
                              VALUES (%s, %s, %s)""",
                              (job_id, part_id, part_quantity))
    connection.fetchall()
    new_qty = 0
    part_quantity =0
    return redirect(url_for('jobdetail', job_id=job_id))


@app.route("/currentjobs/jobdetail/complete_job/<int:job_id>")

def complete_job(job_id):
    # Step 1: Calculate service and part totals.
    service_total, part_total = calculate_totals(job_id)
    

    # Step 2: Update the job total in the database.
    update_job_total(job_id, service_total+part_total)
    
    # Step 3: Set the job as completed.
    update_job_status(job_id)
    
    # Step 4: Redirect to the job detail page with the updated info.
    return redirect(url_for("jobdetail", job_id=job_id, service_total=service_total,part_total=part_total))

def calculate_totals(job_id):
    service_total_query ="""
            SELECT SUM(s.cost * js.qty)
            FROM job_service js
            JOIN service s ON js.service_id = s.service_id
            WHERE js.job_id = %s ;
            """  
    part_total_query ="""
            SELECT SUM(p.cost * jp.qty)
            FROM job_part jp
             JOIN part p ON jp.part_id = p.part_id
            WHERE jp.job_id = %s;
            """  
    connection = getCursor()
    connection.execute(service_total_query, (job_id,))
    service_total=connection.fetchall()
    service_total=service_total[0]
    
    connection.execute(part_total_query, (job_id,))
    part_total=connection.fetchall()
    part_total =part_total[0]
    
    # Execute queries to get service total and part total...
    return service_total, part_total

def update_job_total(job_id, total_cost):
    update_job_total="""UPDATE job SET total_cost = %s
                        WHERE job_id = %s"""
    total_cost_value = total_cost[0] if isinstance(total_cost, tuple) else total_cost
    
    connection = getCursor()
    connection.execute(update_job_total,(total_cost_value,job_id,))
    connection.fetchall()
    return

def update_job_status(job_id):
    update_job_status="""UPDATE job SET completed = 1 
                        WHERE job_id = %s"""
    connection = getCursor()
    connection.execute(update_job_status,(job_id,))
    connection.fetchall()
    return


# Admin Interface
# Main page redirect to customers page
@app.route("/admin")
def admin():
    return redirect("/admin/customers")  

# Use for customer management
@app.route("/admin/customers")
def customers():
    connection = getCursor()
    connection.execute("SELECT c.customer_id, \
                        CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.family_name,'')) AS full_name, \
                        COALESCE(c.email,'') AS email, \
                        COALESCE(c.phone,'') AS phone \
                        FROM customer c;")
    custmerList = connection.fetchall()
    return render_template("customers.html",customer_list=custmerList)  

# Use for service management
@app.route("/admin/services")
def services():
    connection = getCursor()
    connection.execute("SELECT s.service_id, s.service_name,s.cost \
                        FROM service s;")
    serviceList = connection.fetchall()
  
    return render_template("services.html",service_list =serviceList )  

# Use for part management
@app.route("/admin/parts")
def parts():
    connection = getCursor()
    connection.execute("SELECT p.part_id, p.part_name,p.cost \
                        FROM part p;")
    partList = connection.fetchall()
  
    return render_template("parts.html",part_list =partList)  


@app.route("/admin/booking")
def booking():
  
    return render_template("booking.html")  

@app.route("/admin/payments")
def payments():
  
    return render_template("payments.html")  
