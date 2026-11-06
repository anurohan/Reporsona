"""Provider status endpoint (§27).

Exposes which optional integrations are configured — never the secret values.
The frontend Settings page renders this as a status board.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.schemas import ProviderStatusOut
from app.services.providers import provider_status_dicts

router = APIRouter(tags=["providers"])


@router.get("/providers", response_model=List[ProviderStatusOut])
def get_providers() -> List[ProviderStatusOut]:
    return [ProviderStatusOut(**p) for p in provider_status_dicts()]
