import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
from fastembed import TextEmbedding
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize Qdrant Client (with local fallback if credentials are not provided)
if settings.QDRANT_URL and settings.QDRANT_API_KEY:
    logger.info(f"Connecting to Qdrant Cloud at {settings.QDRANT_URL}...")
    _client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )
else:
    logger.info("QDRANT_API_KEY or QDRANT_URL is missing/empty. Falling back to local persistent Qdrant (./qdrant_db)...")
    # Store Qdrant DB at the backend folder level
    db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "qdrant_db"))
    os.makedirs(db_path, exist_ok=True)
    _client = QdrantClient(path=db_path)

if not _client.collection_exists(settings.QDRANT_COLLECTION_NAME):
    _client.create_collection(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

# Unconditionally verify/create payload indexes for existing collections
REQUIRED_INDEXES = ["filename", "document_type", "drive_file_name", "title", "source"]
for field in REQUIRED_INDEXES:
    try:
        _client.create_payload_index(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            field_name=field,
            field_schema="keyword"
        )
    except Exception:
        pass

logger.info(f"Verified Qdrant payload indexes: {REQUIRED_INDEXES}")

_embedding_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
