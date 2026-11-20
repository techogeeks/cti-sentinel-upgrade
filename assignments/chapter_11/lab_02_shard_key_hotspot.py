"""Lab 11.2 - synthetic hotspot simulation with MongoDB persistence."""
import json
from backend.services.lab_10_12 import shard_key_hotspot
if __name__ == "__main__":
    print(json.dumps(shard_key_hotspot(), indent=2))
