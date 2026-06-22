import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.db.qdrant import _client as client, Filter, FieldCondition, MatchValue

def clean_metadata():
    print(f"Using Qdrant client...")

    
    collection_name = settings.QDRANT_COLLECTION_NAME

    print("Retrieving all points to check for missing metadata...")
    offset = None
    all_points = []
    
    while True:
        points, offset = client.scroll(
            collection_name=collection_name,
            limit=1000,
            with_payload=True,
            offset=offset
        )
        all_points.extend(points)
        if offset is None:
            break

    print(f"Retrieved {len(all_points)} total points.")

    updated_source_count = 0
    updated_type_count = 0

    for p in all_points:
        payload = p.payload or {}
        updates = {}
        
        if "source" not in payload or payload["source"] == "UNKNOWN_SOURCE":
            updates["source"] = "supabase_storage"
            updated_source_count += 1
            
        if "document_type" not in payload or payload["document_type"] == "UNKNOWN_TYPE":
            updates["document_type"] = "general"
            updated_type_count += 1
            
        if updates:
            client.set_payload(
                collection_name=collection_name,
                payload=updates,
                points=[p.id]
            )

    print(f"Updated {updated_source_count} points missing 'source'.")
    print(f"Updated {updated_type_count} points missing 'document_type'.")

    print("Metadata cleanup complete.")

if __name__ == "__main__":
    clean_metadata()
