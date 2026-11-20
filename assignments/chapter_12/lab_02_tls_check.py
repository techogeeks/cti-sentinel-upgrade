"""Lab 12.2 - TLS ping check. Configure a TLS instance manually first."""
import json
from backend.services.lab_10_12 import security_readiness
if __name__ == "__main__":
    print(json.dumps(security_readiness(2), indent=2))
