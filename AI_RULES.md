# AI Development Rules and Tech Stack Guidelines

This document outlines the core technologies and best practices for developing and maintaining the Payroll Monitoring System. Adhering to these guidelines ensures consistency, maintainability, and efficient collaboration.

## 🚀 Tech Stack Overview

The system is built primarily with Python and leverages several key technologies:

*   **Python 3.8+**: The primary programming language for all backend logic, scripting, and automation.
*   **Web Scraping**: Utilizes robust libraries for fetching and parsing web content, including handling dynamic JavaScript-rendered pages.
*   **AI/ML**: Incorporates AI-powered algorithms for advanced change detection and analysis.
*   **Database**: Employs a relational database for persistent storage of monitoring data, configurations, and historical changes.
*   **Web Framework**: A lightweight Python web framework powers the API endpoints and the real-time dashboard.
*   **Configuration Management**: YAML files are used for structured and human-readable system configurations.
*   **Notification Services**: Integrates with various communication platforms for multi-channel alerts.
*   **Task Scheduling**: An automated scheduler manages periodic monitoring tasks.
*   **Containerization**: Docker is used for consistent and isolated deployment environments.
*   **Environment Variables**: Sensitive information and deployment-specific settings are managed via environment variables.

## 📚 Library Usage Guidelines

To maintain a consistent and efficient codebase, please adhere to the following library choices for specific functionalities:

*   **HTTP Requests**: Use `requests` for making HTTP requests to external websites.
*   **HTML Parsing**: For parsing HTML and XML content, `BeautifulSoup4` is the standard.
*   **JavaScript-heavy Scraping**: When dynamic content or JavaScript rendering is required, use `Selenium` with a headless browser (e.g., Chrome/Chromium).
*   **Database ORM**: `SQLAlchemy` should be used for all database interactions, providing an Object Relational Mapper (ORM) for cleaner data handling.
*   **Database Drivers**: Use `sqlite3` for SQLite connections (development/testing) and `psycopg2` for PostgreSQL connections (production).
*   **YAML Configuration**: `PyYAML` is the designated library for loading and parsing `config/*.yaml` files.
*   **Web Framework**: `Flask` is the preferred micro-framework for building the REST API and serving the web dashboard.
*   **Task Scheduling**: `APScheduler` is used for managing and executing scheduled monitoring tasks.
*   **Environment Variables**: Use `python-dotenv` for loading environment variables from `.env` files during development.
*   **Email Notifications**: Utilize Python's built-in `smtplib` for sending email alerts.
*   **Webhook Notifications (Slack/Teams)**: Use the `requests` library to send POST requests to Slack and Microsoft Teams webhooks.
*   **Logging**: Python's standard `logging` module should be used for all application logging.
*   **AI/ML (General)**: For general machine learning tasks, `scikit-learn` is recommended. For more advanced NLP tasks, consider `spaCy` or `NLTK`. If deep learning is required, `TensorFlow` or `PyTorch` can be introduced after discussion.