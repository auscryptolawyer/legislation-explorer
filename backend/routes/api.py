"""API route assembly."""
from fastapi import APIRouter

from .acts import router as acts_router
from .definitions import router as definitions_router
from .search import router as search_router
from .cases import router as cases_router
from .rulings import router as rulings_router
from .commentary import router as commentary_router
from .comments import router as comments_router

router = APIRouter()
router.include_router(acts_router)
router.include_router(definitions_router)
router.include_router(search_router)
router.include_router(cases_router)
router.include_router(rulings_router)
router.include_router(commentary_router)
router.include_router(comments_router)
