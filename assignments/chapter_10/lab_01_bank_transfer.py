"""Lab 10.1 - reproducible bank transfer demo with synthetic accounts."""
import json
from backend.services.lab_10_12 import bank_transfer
if __name__ == "__main__":
    print(json.dumps(bank_transfer(), indent=2))
