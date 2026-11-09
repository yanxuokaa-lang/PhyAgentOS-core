JevleKa – Smart Canteen Ordering System

JevleKa is a smart web-based canteen ordering system created to solve common problems faced by college and institutional canteens. It helps reduce long waiting lines, avoid manual mistakes, and improve order handling by using a simple digital platform. The system allows users to place orders in advance and collect them efficiently, saving time for both customers and canteen staff. The project has been developed with an academic mindset while keeping future scalability and real-world adoption in focus.

FULL WORKFLOW - The user orders food from their phone by selecting items from the menu and completing payment. As soon as the payment is successful, a QR code is generated and the order is sent to the backend system. The canteen staff is immediately notified and starts preparing the order. When the user reaches the canteen, they scan the QR code at the counter, which generates a receipt token for verification and record keeping. After validation, the user collects the prepared food without waiting.

Ideation and Research 

During rush hours like lunch breaks, college canteens face long queues and overcrowding, causing students to waste time waiting to place orders. Orders are taken verbally, which becomes difficult for staff to manage when many students order at the same time.
This leads to confusion, delayed food preparation, and mistakes such as wrong items, missed orders, or payment issues. Without proper order tracking, students are unsure when their food will be ready, making the pickup process unpredictable. Staff efficiency also drops due to manual handling of multiple orders.

Students prefer a fast and predictable takeaway system, but existing food delivery platforms are too complex and costly for a single-canteen setup. These challenges highlight the need for a simple and efficient digital ordering solution for college canteens.

Requirement Analysis and Scope Definition

The system is a practical solution for essential canteen operations. It supports user authentication for students and staff, menu browsing, cart-based ordering, and digital order placement. A dummy payment flow ( for now - to avoid gateway fees) and then QR generation. Orders are processed directly without manual intervention.

A staff dashboard allows real-time order viewing and status management. The system is optimized for fast response during peak hours and supports easy local deployment with minimal infrastructure. Delivery and logistics are intentionally excluded. The scope is limited to a single-canteen setup to keep the system lightweight and efficient.

Business Overview

JevleKa is envisioned as an end-to-end autonomous canteen ordering platform. In its extended business vision, students can place food orders using a web or mobile interface, make instant UPI payments, generate QR-based coupons, and print those coupons using dedicated kiosk hardware. From the canteen’s perspective, the system helps reduce queues, lower manpower requirements, speed up order processing, enable digital revenue tracking, and increase order throughput during peak hours.

The platform combines SaaS-based software with optional kiosk hardware leasing, making it suitable for colleges and other institutional food outlets.

Target Market

The primary target market for JevleKa includes colleges and universities. Secondary markets include corporate cafeterias, while hostels and coaching institutes are considered part of future expansion. These markets are characterized by high daily footfall, heavy congestion during peak hours, price sensitivity combined with high volume, and long-term vendor relationships.

Revenue Model

JevleKa follows a hybrid monetization strategy to accommodate canteens of different sizes and operational maturity. Once sufficient demand and adoption are achieved, a commission-based revenue model can be applied where a small percentage of monthly revenue generated through the app is charged. A commission range of three to five percent is considered fair for educational institutions operating on high volume and low margins.

An optional hardware leasing add-on can be offered, which includes ESP32-based devices, printer maintenance, and hardware replacement risk coverage. This add-on can be charged as an additional commission. For example, if a canteen generates six lakh rupees in monthly app-based revenue, a four percent commission would yield twenty-four thousand rupees, with operating costs of approximately six thousand rupees, resulting in a gross margin of around seventy-five percent. This model is highly scalable as order volume increases.

Technical Implementation

JevleKa is implemented as a full-stack web application using HTML, CSS, JavaScript, Node.js, Express.js, and SQLite. It follows a simple client–server architecture where the frontend communicates with backend APIs for data storage and retrieval. The architecture is intentionally kept minimal to ensure ease of understanding, deployment, and maintenance.

Project Architecture

The system is divided into three layers: the frontend layer responsible for user interaction, the backend layer responsible for business logic and API handling, and the database layer responsible for data persistence.

Frontend Implementation

The frontend is developed using HTML, CSS, and Vanilla JavaScript. Multiple HTML pages are used to separate different user interfaces, including login, dashboard, menu display, cart management, user profile, and staff order management. Styling and layout are handled using a centralized CSS file, while JavaScript manages DOM manipulation, user interactions, and API calls to the backend using the fetch API. Static assets such as images and audio files are served directly.

Backend Implementation

The backend is built using Node.js with the Express.js framework. The main server file initializes the Express application, defines RESTful APIs, handles HTTP requests and responses, and serves static frontend files. Environment variables are managed using a .env file, with a reference template provided through .env_example. Project dependencies and scripts are managed using package.json, while package-lock.json ensures dependency version consistency.

Database Implementation

SQLite is used as the database for fast and lightweight local storage. The database stores user details, menu items, and order or cart-related information. A dedicated database handler file manages database connections, table creation, and all CRUD operations including create, read, update, and delete queries.

Environment and Security

Sensitive information such as configuration details and database paths are stored securely using environment variables. The .gitignore file ensures that sensitive files such as node_modules, environment files, and database files are not pushed to version control. Basic backend-level input validation is implemented to prevent invalid or malformed data entries.

Application Flow

The application flow begins with the user interacting with the frontend interface. JavaScript sends requests to backend APIs, which process the logic and interact with the SQLite database. The backend then sends responses back to the frontend, and the user interface updates dynamically based on the received data.

Technologies Used

The frontend is built using HTML, CSS, and JavaScript. The backend uses Node.js and Express.js. SQLite is used as the initial database, with PostgreSQL planned for future migration. Development tools include npm and Visual Studio Code.

Important Links

Demo Video:
https://drive.google.com/file/d/1BEhlpCKFKhJsB2SsywH4xlPTaE5XAUip/view?usp=sharing

System Architecture Diagram:
https://drive.google.com/file/d/1DsZiaPyWiNg4Bq4POFdE46WHZRPeXntS/view?usp=sharing

Future Business Models:
https://docs.google.com/document/d/1Xz-lZ2OOXqtgLwLRjJbaZXuKK5-EOd1frT6Vqw6aryA

Hardware Prototype:
https://drive.google.com/file/d/16PM4-nG2GsNLSt3POB-_FZ4qT2uQ2dHS/view?usp=sharing

System Design Architecture:
https://docs.google.com/document/d/126vzwjnPWDXbb-yem3fOjbf3r0WcxZ2d8AOY6e4DtM0

Future Scope

Future enhancements include UPI payment integration, QR-based coupon generation and validation, dedicated kiosk deployment, migration to PostgreSQL, multi-canteen support, and advanced analytics for administrators.
