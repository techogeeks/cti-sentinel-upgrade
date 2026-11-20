"""Inspect local MongoDB and optionally compare it with Atlas."""
import os
from platform import python_version
import pymongo


def exercise(client, collection):
    result = {
        "python": python_version(),
        "pymongo": pymongo.version,
        "local_version": client.server_info()["version"],
        "passed": True,
    }
    atlas_uri = os.getenv("MONGO_URI_ATLAS")
    if not atlas_uri:
        result.update(passed=None, note="Local check passed. Set MONGO_URI_ATLAS to compare with Atlas.")
        return result

    try:
        with pymongo.MongoClient(atlas_uri, serverSelectionTimeoutMS=5000, timeoutMS=10000) as atlas:
            result["atlas_version"] = atlas.server_info()["version"]
    except pymongo.errors.PyMongoError:
        result.update(passed=False, note="Atlas check failed. Check credentials and the Atlas network access list.")
        return result

    result["same_version"] = result["local_version"] == result["atlas_version"]
    return result
