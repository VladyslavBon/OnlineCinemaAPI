# Online Cinema API

A digital platform that allows users to select, watch, and purchase access to movies and other video materials via the internet.

---

## Features

- **User Registration**: Users can register, log in, and manage their profiles.
- **Movie Management**: Add, update, and delete books in the library.
- **Orders&Cart System**: Users can order movie to cart and pay for them.
- **Payment Tracking**: Keeps track of payments for movies.

---

## Technologies Used

- **FastAPI** for backend API
- **PostgreSQL** for database
- **Celery** for email notifications
- **Stripe** for payment processing
- **Docker** for containerization

---

# Setup

## Prerequisites
* Python 3.12.8+
* Poetry
* Docker & Docker Compose

## **Local** Setup

Follow these steps to set up the project locally.

### 1. Clone the Repository
Clone the repository to your local machine using Git:

```bash
git clone https://github.com/VladyslavBon/LibraryServiceAPI.git
cd OnlineCinemaAPI
```

### 2. Environment
Create a `.env` file based on the `.env.sample` file. You can do this by copying the `.env.sample` to `.env`:

```bash
cp .env.sample .env
```

### 3. Install Dependencies
Use Poetry to install the necessary dependencies:
```bash
poetry install
```

### 4. Apply Migrations
Run the migrations to set up the database schema:
```bash
alembic upgrade head
```


### 5. Start the Server
Run the FastAPI development server:
```bash
python uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Your server will be available at: http://localhost:8000/

---

## Running with **Docker**

If you'd like to run the project using Docker, follow the steps below.

### 1. Build and Start the Services
Use Docker Compose to build and run the application and database containers:
```bash
docker-compose up --build
```

### 2. Access the API
Once the services are up, the API will be available at: http://localhost:8000/

The PostgreSQL database will be available on port `5432`.

---

## Documentation
API documentation is available via Swagger at:

`http://localhost:8000/docs/`
