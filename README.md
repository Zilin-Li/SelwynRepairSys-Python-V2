#### Name: Zilin Li

#### ID: 1159924

# Selwyn Panel Beaters: Web App Report

## Web Application Structure

The web application is structured around Flask routes, each corresponding to a specific functionality within the application. The routes are defined in app.py and render templates located in the template’s directory, which is further organized into admin and technician subdirectories for role-specific views. Data exchange between the routes and templates is handled through HTTP requests, with data being passed to templates for rendering and received from forms as user input.

## Routes and Functions


### Technician Interface

The Technician Interface is responsible for managing job details, including viewing current jobs, job details, adding services and parts to jobs, and marking jobs as complete. Below is the structure of routes, associated functions, templates, and data interactions:

- **Route**: `/`
  - **Function**: `home()`
  - **Action**: Redirects to the `/currentjobs` route for the Technician Interface.
  - **Redirects To**: `/currentjobs`

- **Current Jobs**

	- **Route**: `/currentjobs`
	  - **Function**: `currentjobs()`
	  - **Template**: `technician/currentjoblist.html`
	  - **Description**: Fetches and displays a list of unfinished jobs, sorted by job date, and customer name.
	  - **Data Flow**: Retrieves a list of jobs from the database and passes this data to the template.
	  
- **Job Details**
 
	- **Route**: `/currentjobs/jobdetail/<int:job_id>`
	  - **Function**: `jobdetail(job_id)`
	  - **Template**: `technician/jobdetail.html`
	  - **Description**: Displays detailed information for a specific job, including services and parts used.
	  - **Data Flow**: Fetches job details, services, and parts from the database and calculates total costs. Passes this information to the template.
	  - **Sub-functions**:
	    - **Add Service to Job**:
	      - **Route**: `/currentjobs/jobdetail/add_service_to_job/<int:job_id>`
	      - **Function**: `add_service_to_job(job_id)`
	      - **Method**: POST
	      - **Description**: Adds a service to a job, updating the quantity if it exists or creating a new entry.
	      - **Data Flow**: Receives service ID and quantity from the form, updates the database, and redirects back to the job detail page.
	    - **Add Part to Job**:
	      - **Route**: `/currentjobs/jobdetail/add_part_to_job/<int:job_id>`
	      - **Function**: `add_part_to_job(job_id)`
	      - **Method**: POST
	      - **Description**: Adds a part to a job, updating the quantity if it exists or creating a new entry.
	      - **Data Flow**: Receives part ID and quantity from the form, updates the database, and redirects back to the job detail page.
	    - **Complete Job**:
	      - **Route**: `/currentjobs/jobdetail/complete_job/<int:job_id>`
	      - **Function**: `complete_job(job_id)`
	      - **Description**: Marks a job as completed and prevents further modifications.
	      - **Data Flow**: Updates the job status in the database to 'completed' and redirects back to the job detail page.
      
### Admin Interface

The Admin Interface facilitates the management of customers, services, parts, schedule, unpaid bills and bill history. Below is the structure of routes, associated functions, templates, and data interactions:

- **Route**: `/admin`
  - **Function**: `admin()`
  - **Action**: Redirects to the customer management route.
  - **Redirects To**: `/admin/customers`

- **Customer Management**
  - **Route**: `/admin/customers`
    - **Function**: `customers()`
    - **Template**: `admin/customers.html`
    - **Description**: Fetches and displays a list of all customers for management purposes.
    - **Data Flow**: Calls `get_customer()` function to retrieve all customer records from the database and passes them to the template for display.

  - **Route**: `/admin/customers/search`
    - **Function**: `search_customer()`
    - **Method**: GET
    - **Template**: `admin/customers.html`
    - **Description**: Searches for customers based on the provided query and displays results.
    - **Data Flow**: Receives search query, sanitizes it with `sanitize_input()`, executes search, and returns results to the same customer management template with an optional no-results message.

  - **Route**: `/admin/customers/add`
    - **Function**: `add_customer()`
    - **Method**: POST
    - **Action**: Adds a new customer to the database.
    - **Data Flow**: Receives new customer data from the form, validates input, adds a new record to the database, and redirects back to the customer management page with a success or error message.

  - **Route**: `/admin/customers/delete`
    - **Function**: `delete_customer()`
    - **Method**: POST
    - **Action**: Deletes a customer from the database.
    - **Data Flow**: Receives customer ID from the form, deletes the customer record from the database, and redirects back to the customer management page with a success or error message.

  - **Route**: `/admin/customers/update`
    - **Function**: `update_customer()`
    - **Method**: POST
    - **Action**: Updates an existing customer's information in the database.
    - **Data Flow**: Receives updated customer data from the form, validates input, updates the customer record in the database, and redirects back to the customer management page with a success or error message.

- **Services Management**

	- **Route**: `/admin/services`
	  - **Function**: `services()`
	  - **Template**: `admin/services.html`
	  - **Description**: Displays a list of services available for management.
	  - **Data Flow**: Retrieves services from the database and passes them to the template.

	- **Route**: `/admin/services/add`
	  - **Function**: `add_service()`
	  - **Method**: POST
	  - **Action**: Adds a new service to the database.
	  - **Data Flow**: Validates and sanitizes input from the form, inserts new service into the database, and redirects to the services list with a message.

	- **Route**: `/admin/services/update`
	  - **Function**: `update_service()`
	  - **Method**: POST
	  - **Action**: Updates an existing service's details in the database.
	  - **Data Flow**: Validates and sanitizes input, updates service details in the database, and redirects to the services list with a message.

	- **Route**: `/admin/services/delete`
	  - **Function**: `delete_service()`
	  - **Method**: POST
	  - **Action**: Deletes a service from the database.
	  - **Data Flow**: Removes the service from the database and redirects to the services list with a message, handling errors if the service is associated with existing jobs.

- **Parts Management**

	- **Route**: `/admin/parts`
	  - **Function**: `parts()`
	  - **Template**: `admin/parts.html`
	  - **Description**: Displays a list of parts available for management.
	  - **Data Flow**: Retrieves parts from the database and passes them to the template.

	- **Route**: `/admin/parts/add`
	  - **Function**: `add_part()`
	  - **Method**: POST
	  - **Action**: Adds a new part to the database.
	  - **Data Flow**: Validates and sanitizes input from the form, inserts new part into the database, and redirects to the parts list with a message.

	- **Route**: `/admin/parts/update`
	  - **Function**: `update_part()`
	  - **Method**: POST
	  - **Action**: Updates an existing part's details in the database.
	  - **Data Flow**: Validates and sanitizes input, updates part details in the database, and redirects to the parts list with a message.

	- **Route**: `/admin/parts/delete`
	  - **Function**: `delete_part()`
	  - **Method**: POST
	  - **Action**: Deletes a part from the database.
	  - **Data Flow**: Removes the part from the database and redirects to the parts list with a message, handling errors if the part is associated with existing jobs.

- **Job Scheduling** 
	- **Route**: `/admin/schedule`
	  - **Function**: `schedule()`
	  - **Template**: `admin/schedule.html`
	  - **Description**: Displays the job schedule, listing all jobs with their status and associated customer details.
	  - **Data Flow**: Retrieves a list of all jobs and customers from the database, along with the current date, and passes this data to the template.

	- **Route**: `/admin/schedule/booking`
	  - **Function**: `booking_job()`
	  - **Method**: POST
	  - **Action**: Books a new job for a customer.
	  - **Data Flow**: Collects customer ID and job date from the form, inserts a new job record into the database, and redirects to the schedule page with a success message.
	  
- **Bill Payments** 
	- **Route**: `/admin/payments`
	  - **Function**: `billpayments()`
	  - **Template**: `admin/billpayments.html`
	  - **Description**: Lists all unpaid bills ordered by job date and customer name.
	  - **Data Flow**: Retrieves unpaid job details from the database and passes them along with the customer list to the template.

	- **Route**: `/admin/payments/paybill/<int:job_id>`
	  - **Function**: `pay_bill(job_id)`
	  - **Action**: Marks a job as paid in the database.
	  - **Data Flow**: Updates the payment status of a job and redirects to the bill payments page with a success message.

	- **Route**: `/admin/payments/filter`
	  - **Function**: `customer_filter()`
	  - **Method**: GET
	  - **Template**: `admin/billpayments.html`
	  - **Description**: Filters and displays jobs based on the selected customer for payment management.
	  - **Data Flow**: Retrieves jobs for a specified customer or all unpaid jobs and passes the filtered data to the bill payments template.

- **Billing History**

	- **Route**: `/admin/billhistory`
	  - **Function**: `billhistory()`
	  - **Template**: `admin/billhistory.html`
	  - **Description**: Shows the billing history for all customers, including completed jobs, total costs, and payment status.
	  - **Data Flow**: Fetches completed job details grouped by customer and calculates overdue dates for payments, then passes this information to the template.


## Design Decisions Overview:

This section outlines the pivotal design choices made during the development of the application to ensure its functionality, usability, and security.

### Architecture

- **MVC Pattern**: Adopted the Model-View-Controller (MVC) pattern with Flask to separate concerns, enhancing maintainability and scalability.

### Routing and Data Handling

- **GET and POST**: Utilized GET requests for data retrieval and POST for actions that modify server state, adhering to HTTP standards for safety and idempotence.
- **Data Validation**: Implemented both client-side and server-side validation for robust data integrity and security.

### Templates and UI

- **Separate Templates**: Opted for separate templates for different functionalities to keep the UI manageable and modular.
- **Conditional Rendering**: Employed IF statements within templates for minor variations, reducing the need for multiple templates for similar views.

### Navigation

- **Intuitive Navigation**: Designed a clear and consistent navigation structure, with a top navigation bar for easy access to main sections.



## Database Questions:

1.  ****What SQL statement creates the job table and defines its fields/columns? (Copy and paste the relevant lines of SQL.)****

```

CREATE TABLE IF NOT EXISTS job

(

job_id INT auto_increment PRIMARY KEY NOT NULL,

job_date date NOT NULL,

customer int NOT NULL,

total_cost decimal(6,2) default null,

completed tinyint default 0,

paid tinyint default 0,

FOREIGN KEY (customer) REFERENCES customer(customer_id)

ON UPDATE CASCADE

);

```

2.  ****Which line of SQL code sets up the relationship between the customer and job tables?****

```

FOREIGN KEY (customer) REFERENCES customer(customer_id)

ON UPDATE CASCADE

```

3.  ****Which lines of SQL code insert details into the parts table?****

```

INSERT INTO part (`part_name`, `cost`) VALUES ('Windscreen', '560.65');

INSERT INTO part (`part_name`, `cost`) VALUES ('Headlight', '35.65');

INSERT INTO part (`part_name`, `cost`) VALUES ('Wiper blade', '12.43');

INSERT INTO part (`part_name`, `cost`) VALUES ('Left fender', '260.76');

INSERT INTO part (`part_name`, `cost`) VALUES ('Right fender', '260.76');

INSERT INTO part (`part_name`, `cost`) VALUES ('Tail light', '120.54');

INSERT INTO part (`part_name`, `cost`) VALUES ('Hub Cap', '22.89');

```

4.  ****Suppose that as part of an audit trail, the time and date a service or part was added to a job needed to be recorded, what fields/columns would you need to add to which tables? Provide the table name, new column name and the data type. (Do not implement this change in your app.)****

To record the time and date a service or part was added to a job for audit purposes, we can modify the database schema by adding a date time column to the related table. .For instance:

#### For Services Added to a Job:

-   **Table Name**: `job_service`
-   **New Column Name**: `added_datetime`
-   **Data Type**: `DATETIME` or `TIMESTAMP`


#### For Parts Added to a Job:

-   **Table Name**: `job_part`
-   **New Column Name**: `added_datetime`
-   **Data Type**: `DATETIME` or `TIMESTAMP`

5.  ****Suppose logins were implemented. Why is it important for technicians and the office administrator to access different routes? As part of your answer, give two specific examples of problems that could occur if all of the web app facilities were available to everyone.****

- **Data security risks :** If a technician has the same access rights as an office administrator, there is a risk that critical data may be inadvertently modified or deleted. For example, a technician might accidentally delete a customer's record when he only intended to update work details. This can lead to data loss, impacting customer trust and service reliability.

- **Operational confusion and errors :** If no access level is defined, it means that any user can schedule jobs or issue invoices, which can lead to operational confusion. Imagine a scenario where a technician unfamiliar with pricing strategies or scheduling constraints schedules a complex job without proper delivery times, or invokes an incorrect fee. This not only disrupts workflow, but also carries the risk of customer dissatisfaction and financial discrepancies that require additional time and resources to correct.

	By describing access rights, we ensure that each user interacts with the system within the scope of their expertise and responsibilities, protects applications from accidental misuse, and maintains the integrity of operational processes.
