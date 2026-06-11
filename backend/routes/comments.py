from __future__ import annotations

import logging

from fastapi import HTTPException, APIRouter
from pydantic import BaseModel

from backend.services.comments_service import get_comments, add_comment, resolve_comment

logger = logging.getLogger(__name__)
router = APIRouter()


class CommentCreate(BaseModel):
    act: str
    section: str
    author: str = "Anonymous"
    text: str


class CommentResolve(BaseModel):
    comment_id: int


@router.get("/api/comments/{act}/{section}")
def list_comments(act: str, section: str, limit: int = 100, offset: int = 0):
    try:
        comments = get_comments(act, section, limit, offset)
        return {"act": act, "section": section, "count": len(comments), "comments": comments}
    except Exception:
        logger.exception("Error fetching comments")
        raise HTTPException(status_code=500, detail="Failed to fetch comments")


@router.post("/api/comments")
def create_comment(payload: CommentCreate):
    try:
        return add_comment(payload.act, payload.section, payload.author, payload.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Error creating comment")
        raise HTTPException(status_code=500, detail="Failed to create comment")


@router.post("/api/comments/resolve")
def mark_resolved(payload: CommentResolve):
    try:
        resolve_comment(payload.comment_id)
        return {"ok": True}
    except Exception:
        logger.exception("Error resolving comment")
        raise HTTPException(status_code=500, detail="Failed to resolve comment")
