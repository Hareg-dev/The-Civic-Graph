"""
Federation Router
Handles ActivityPub federation endpoints (inbox, outbox)
Requirements: 6.1-6.9
"""

import logging
import json
import hashlib
import base64
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.federation.inbox import create_inbox_handler
from app.schemas import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/federation",
    tags=["federation"]
)


@router.post("/inbox", status_code=status.HTTP_202_ACCEPTED)
async def inbox_endpoint(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    ActivityPub inbox endpoint for receiving federated activities
    Requirements: 6.1, 6.2, 6.3
    
    Receives activities from remote instances and processes them.
    Verifies HTTP Signatures before processing.
    
    Returns:
        202 Accepted if activity is queued for processing
        401 Unauthorized if signature is invalid
        400 Bad Request if activity is malformed
    """
    try:
        # Get request body
        body = await request.body()
        activity = await request.json()
        
        # Extract headers for signature verification
        signature = request.headers.get("signature", "")
        date = request.headers.get("date", "")
        host = request.headers.get("host", "")
        
        # Compute digest
        digest_hash = hashlib.sha256(body).digest()
        digest = f"SHA-256={base64.b64encode(digest_hash).decode()}"
        
        # Verify digest header if present
        digest_header = request.headers.get("digest", "")
        if digest_header and digest_header != digest:
            logger.error("Digest mismatch")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Digest mismatch"
            )
        
        # Check for required headers
        if not signature:
            logger.error("Missing signature header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature"
            )
        
        if not date:
            logger.error("Missing date header")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing date header"
            )
        
        # Create inbox handler
        inbox_handler = create_inbox_handler(db)
        
        # Process activity
        result = await inbox_handler.handle_activity(
            activity=activity,
            signature=signature,
            request_target="post /api/federation/inbox",
            host=host,
            date=date,
            digest=digest
        )
        
        # Handle result
        result_status = result.get("status", 500)
        result_message = result.get("message", "Unknown error")
        
        if result_status == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result_message
            )
        elif result_status == 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result_message
            )
        elif result_status == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result_message
            )
        elif result_status >= 500:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result_message
            )
        
        # Success
        return {
            "status": "accepted",
            "message": result_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in inbox endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/inbox")
async def inbox_get_endpoint():
    """
    GET endpoint for inbox (for discovery)
    Returns basic information about the inbox
    """
    return {
        "type": "OrderedCollection",
        "id": "/api/federation/inbox",
        "totalItems": 0
    }


@router.post("/outbox", status_code=status.HTTP_201_CREATED)
async def outbox_endpoint(
    activity: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    ActivityPub outbox endpoint for publishing activities
    Requirements: 5.5-5.8
    
    Publishes local activities to federated instances.
    
    Returns:
        201 Created if activity is published
    """
    # This will be implemented when we work on outbox publishing
    # For now, return a placeholder
    return {
        "status": "created",
        "message": "Activity published"
    }


@router.get("/outbox")
async def outbox_get_endpoint():
    """
    GET endpoint for outbox (for discovery)
    Returns basic information about the outbox
    """
    return {
        "type": "OrderedCollection",
        "id": "/api/federation/outbox",
        "totalItems": 0
    }
