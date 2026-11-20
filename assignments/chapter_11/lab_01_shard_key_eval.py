"""Lab 11.1 - illustrative shard-key evaluation, no MongoDB required."""
import json
from backend.services.lab_10_12 import shard_key_evaluation
if __name__ == "__main__":
    print(json.dumps(shard_key_evaluation(), indent=2))
