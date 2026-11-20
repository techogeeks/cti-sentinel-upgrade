"""Lab 12.1 - read-only role inspection. Configure RBAC manually in sandbox."""
import json
from backend.services.lab_10_12 import security_readiness
if __name__ == "__main__":
    print(json.dumps(security_readiness(1), indent=2))
