from fastapi import APIRouter

from app.config import settings
from app.services.embeddings import embedding_service
from app.services.vector_store import make_vector_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    # touch the vector factory to report the active backend
    store = make_vector_store(embedding_service.dim)
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.env,
        "demo_mode": settings.demo_mode,
        "llm_provider": settings.llm_provider,
        "embedding_backend": embedding_service.backend,
        "embedding_dim": embedding_service.dim,
        "vector_store": type(store).__name__,
    }
