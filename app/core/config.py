import os

# Database Configuration
# Uses default credentials for local Docker Compose setup
DB_URL = os.getenv("DATABASE_URL", "postgres://user:password@db:5432/eatclub_db")

# Application Metadata
PROJECT_NAME = "EatClub Order Management System"
VERSION = "1.0.0"

# Outbox Poller Configuration (Simulates the Consumer/Worker)
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", 1)) # Poller checks for new events every N seconds
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", 5)) # Max retries for an event
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 50)) # How many events to fetch per poll