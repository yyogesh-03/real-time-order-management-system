EatClub Order Management System: Architecture Documentation1. System Architecture OverviewThe EatClub Order Management System (OMS) is built using a Microservice approach centered around the Transactional Outbox Pattern to achieve high throughput, low latency, and guaranteed data consistency.The system is split into two primary paths: the Fast Path (synchronous API) and the Slow Path (asynchronous consumers).Key Components:FastAPI Service (api):Handles all RESTful API requests (Placing Order, Status Update, etc.).Primary goal: Sub-200ms response time.Persistence: Writes all business data (Order, OrderItem) and the corresponding Event into the same PostgreSQL transaction.The Transactional Outbox: The outbox_events table acts as the source of truth for all events.PostgreSQL Database (db):Stores all relational data (Orders, Inventory, Menu) and the Outbox events.Chosen for its transactional guarantees and robust row-level locking capabilities (SELECT FOR UPDATE), which are critical for safe inventory management.Outbox Poller / Consumer Service (consumer):The "worker" service that polls the outbox_events table for unpublished events.Simulates a message broker (like Kafka) by routing events internally to the correct handler functions.Slow Path Logic: Executes complex, slow, and idempotent business logic (e.g., Inventory Deduction, Status Progression).2. Data Flow and Sequence Diagrams2.1. Order Placement Flow (Fast Path & Inventory Deduction)This flow is designed to ensure the immediate API response is fast, while the critical inventory check and status progression happen reliably in the background.Client Request: A user sends POST /api/v1/orders.Atomic Transaction (DB): The API service opens a single transaction:Creates the Order record (Status: PLACED).Creates the OrderItem records.Creates an OutboxEvent with event_type: order.placed.v1.COMMIT: The transaction succeeds or fails atomically. API returns 202 ACCEPTED immediately.Poller Polls: The consumer poller finds the order.placed.v1 event.Inventory Handler: The consumer executes the inventory deduction logic.It uses SELECT FOR UPDATE on the Inventory records to acquire a row-level lock.If successful, it deducts the stock, emits an inventory.deducted.success.v1 event, and marks the original event as published.If insufficient stock, it emits an order.cancellation.required.v1 event.Status Handler: Another internal consumer handler processes the success event (inventory.deducted.success.v1).It updates the Order status from PLACED to PREPARING.2.2. Order Cancellation Flow (Inventory Restoration)This flow restores stock if the user or the system cancels an order.Client/System Request: A user sends POST /api/v1/orders/{id}/cancel.Atomic Transaction (DB): The API service opens a single transaction:Updates the Order status to CANCELLED.Creates an OutboxEvent with event_type: order.cancelled.v1 containing the items to restore.COMMIT: API returns 200 OK.Poller Polls: The consumer poller finds the order.cancelled.v1 event.Inventory Restoration Handler: The consumer executes the inventory restoration logic.It uses SELECT FOR UPDATE on the Inventory records.Increments the stock count for all items in the payload.Marks the original event as published.3. API Contracts (Request/Response Formats)3.1. Place OrderMethodPathDescriptionPOST/api/v1/ordersPlace a new orderResponse202 AcceptedOrder accepted, processing is asynchronousRequest Body (OrderRequest){
  "restaurant_id": "729d4791-c9f2-411a-826c-949479b12270",
  "items": [
    {
      "menu_item_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "quantity": 2
    },
    {
      "menu_item_id": "b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a12",
      "quantity": 1
    }
  ]
}
Response Body (OrderPlacementResponse){
  "order_id": "8c45d3e0-6a3f-4e0a-a1b7-0f8b4d6d0c9f",
  "status": "PLACED",
  "total_amount": 1200.00,
  "message": "Order accepted. Processing inventory in background (Fast Path completed)."
}
3.2. Fetch Order DetailsMethodPathDescriptionGET/api/v1/orders/{order_id}Retrieve details for an orderResponse200 OKDetailed order informationResponse Body (OrderDetailResponse){
  "id": "8c45d3e0-6a3f-4e0a-a1b7-0f8b4d6d0c9f",
  "status": "PREPARING",
  "total_amount": 1200.00,
  "created_at": "2025-11-27 06:30:00.123456+00:00",
  "items": [
    {
      "name": "Chicken Biryani",
      "quantity": 2,
      "price": "450.00"
    },
    {
      "name": "Veg Thali",
      "quantity": 1,
      "price": "300.00"
    }
  ]
}
3.3. Update Order StatusMethodPathDescriptionPATCH/api/v1/orders/{order_id}/statusManually update order statusResponse200 OKConfirmation of status changeRequest Body (OrderStatusUpdate){
  "status": "OUT_FOR_DELIVERY"
}
4. Scaling ConsiderationsLatency and Throughput TargetsMetricTargetLatency< 200ms (for API endpoints)Throughput> 500 req/sScaling StrategyStateless API Tier (Horizontal Scaling):The api service is completely stateless and can be scaled horizontally (add more instances) using a load balancer (e.g., AWS ALB). This is the primary mechanism to handle high concurrent users and meet the throughput target.Database Sharding/Read Replicas:Reads: As order volume grows, read traffic can be distributed across PostgreSQL Read Replicas. Endpoints like GET /api/v1/orders/{id} should be routed to replicas where possible.Writes: The core data (Orders, Outbox, Inventory) will be heavily write-dependent. Once a single PostgreSQL instance becomes a bottleneck, sharding (e.g., based on restaurant_id or geographical location) will be necessary.Consumer Scalability (Competing Consumers):The consumer service uses the database itself as the message broker. Scaling this requires caution:The poller query (SELECT ... LIMIT N) must be fast.The use of Idempotency (processed_events table) ensures that even if multiple consumers process the same event record, the business logic (inventory deduction) is executed only once.The consumer processes events in batches, which is efficient but adds a slight delay to the slow path.Inventory Concurrency:The use of SELECT FOR UPDATE in the Inventory consumer handler is key to data integrity but is a source of contention (lock waits). For extreme scale, this would be replaced with a non-blocking approach like optimistic locking or specialized distributed inventory systems (e.g., using Redis for temporary reservations), but for this architecture, the strong transactional guarantee provided by PostgreSQL is the most robust and reliable option.