"""Lab 10.2 - inventory concurrency demonstration with synthetic stock."""
import json
from backend.services.lab_10_12 import inventory_reservation
if __name__ == "__main__":
    print(json.dumps(inventory_reservation(), indent=2))
