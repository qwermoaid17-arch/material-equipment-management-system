# 🏗️ Material & Equipment Management System

A comprehensive web-based management system built with **Django** and **Django REST Framework**, designed to track material and equipment movements across construction sites, manage site-specific inventories, execute transfer request workflows, and generate official print-ready PDF reports.

---

## 🌟 Key Features

* **Multi-Site Inventory Management:** Track available and excess material stock for each construction site independently.
* **Material Transfer Workflow:** End-to-end transfer lifecycle (Create Request -> Review -> Approve/Reject -> Confirm Receipt).
* **Real-time Notifications System:** Automated notifications informing users of transfer status updates in real time.
* **Role-Based Access Control (RBAC):**
  * **Super Admin:** Full system access, site management, global reporting, and system settings.
  * **Site Admin:** Restricted access to manage assigned site inventory and handle related transfers.
* **Official Print & PDF Reports:** Custom CSS `@media print` layout featuring company header, audit context, and official signature blocks (Prepared / Reviewed / Approved).
* **Audit Logging:** Full event tracking for inventory changes and material movements.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.10+ / Django 5.x / Django REST Framework
* **Frontend:** HTML5 / Tailwind CSS / Vanilla JavaScript
* **Database:** SQLite (Development) / PostgreSQL (Production)
* **Production Deployment:** Gunicorn / WhiteNoise / dj-database-url

---

## 🚀 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/qwermoaid17-arch/material-equipment-management-system.git](https://github.com/qwermoaid17-arch/material-equipment-management-system.git)
   cd ss