# EatClub Order Management System (Transactional Outbox Architecture)

## Architecture Overview
This system is designed for high performance and reliability using the **Transactional Outbox Pattern**. This separates the immediate, fast-path API operations (order placement, cancellation) from the slower, asynchronous, and idempotent business logic (inventory deduction/restoration, status updates).



- **Fast Path (API):** When an order is placed, the `Order` record and an `OutboxEvent` (`order.placed.v1`) are written to the database **atomically** within a single transaction. This ensures the API response meets the **<200ms latency requirement**.
- **Slow Path (Consumer):** A dedicated worker (`consumer` service) polls the `outbox_events` table for unpublished records. Upon finding one, it dispatches the event payload to the relevant consumer handler, ensuring that complex, potentially slow logic (like row-level locking for inventory) does not block the API.

## Core Features Implemented

1.  **Placing an order:** `POST /api/v1/orders` (Fast Path, returns 202 Accepted).
2.  **Fetching order details:** `GET /api/v1/orders/{order_id}`.
3.  **Updating order status:** `PATCH /api/v1/orders/{order_id}/status` (Emits `order.status_changed.v1`).
4.  **Cancelling an order:** `POST /api/v1/orders/{order_id}/cancel` (Emits `order.cancelled.v1` for inventory restoration).
5.  **Inventory Deduction:** Handled asynchronously by the consumer (via `order.placed.v1`). Uses **PostgreSQL's `SELECT FOR UPDATE`** (row locking) for data consistency to prevent race conditions during concurrent deductions.
6.  **Inventory Restoration:** Handled asynchronously by the consumer (via `order.cancelled.v1`).
7.  **Idempotency:** The `processed_events` table prevents consumers from reprocessing the same event twice.
8.  **Input Validation:** Fully implemented using **Pydantic Schemas** on all API endpoints.

## Setup & Run Instructions

1.  **Prerequisites:** Ensure **Docker** and **Docker Compose** are installed on your machine.
2.  **Run the System:**
    ```bash
    # Build the image and start the API, DB, and Consumer services
    docker-compose up --build
    ```
    - The `db` service (PostgreSQL) is started first.
    - The `api` and `consumer` services wait for the DB to be healthy before starting.

3.  **Access:**
    -   API Documentation (Swagger UI): `http://localhost:8000/docs`
    -   Consumer Logs: Monitor the terminal output from the `consumer` service.

## Testing Flow

1.  **Seed Data:** Open `http://localhost:8000/docs` and execute the `POST /api/v1/inventory/seed` endpoint. This creates initial data (Restaurant ID: `729d4791-c9f2-411a-826c-949479b12270`, Chicken Biryani ID: `a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11`).
2.  **Place Order:** Execute `POST /api/v1/orders`. Use the seeded restaurant and item IDs in the request body (which must conform to the `OrderRequest` Pydantic schema).
    -   **Observation (API):** The API returns immediately with status `PLACED` and a 202 status code.
    -   **Observation (Consumer):** The `consumer` service logs will show the event being dispatched (`order.placed.v1`), inventory deduction, and finally, the status being updated to `PREPARING` via the `inventory.deducted.success.v1` event chain.
3.  **Test Cancellation:** Use the `order_id` from step 2 and execute `POST /api/v1/orders/{order_id}/cancel`.
    -   **Observation (API):** The API returns instantly with status `CANCELLED`.
    -   **Observation (Consumer):** The `consumer` service logs will show `order.cancelled.v1` dispatch and the inventory restoration.