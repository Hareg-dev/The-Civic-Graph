"""
Users Router
Handles user profile, identity, and migration endpoints
Requirements: 8.1-8.8
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services.identity import create_identity_service
from app.schemas import DIDCreate, DIDResponse, MigrationInitiate, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/users",
    tags=["users"]
)


# Placeholder for getting current user
def get_current_user(db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    # For now, return a test user
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user


@router.post("/me/did", status_code=status.HTTP_201_CREATED, response_model=DIDResponse)
async def create_user_did(
    did_data: DIDCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DIDResponse:
    """
    Create a DID for the current user
    Requirements: 8.1, 8.2
    
    Generates a did:key identifier with Ed25519 key pair.
    Private key is encrypted with user's password.
    
    Args:
        did_data: Password for key encryption
        
    Returns:
        DID document
    """
    try:
        identity_service = create_identity_service(db)
        
        did_document = await identity_service.create_did(
            user=current_user,
            password=did_data.password
        )
        
        return DIDResponse(
            did=did_document.did,
            public_key=did_document.public_key,
            current_instance_url=did_document.current_instance_url,
            created_at=did_document.created_at
        )
        
    except Exception as e:
        logger.error(f"Error creating DID: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create DID"
        )


@router.get("/me/did", response_model=DIDResponse)
async def get_user_did(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DIDResponse:
    """
    Get the current user's DID
    
    Returns:
        DID document
    """
    try:
        from app.models import DIDDocument
        
        did_document = db.query(DIDDocument).filter(
            DIDDocument.user_id == current_user.id
        ).first()
        
        if not did_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DID not found"
            )
        
        return DIDResponse(
            did=did_document.did,
            public_key=did_document.public_key,
            current_instance_url=did_document.current_instance_url,
            created_at=did_document.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DID: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get DID"
        )


@router.get("/{username}/actor")
async def get_actor_object(
    username: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get ActivityPub Actor object for a user
    Requirements: 8.3
    
    Returns Actor object with DID as the id field.
    
    Args:
        username: Username to get actor for
        
    Returns:
        ActivityPub Actor object
    """
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get DID document
        from app.models import DIDDocument
        did_document = db.query(DIDDocument).filter(
            DIDDocument.user_id == user.id
        ).first()
        
        if not did_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User does not have a DID"
            )
        
        # Create identity service
        identity_service = create_identity_service(db)
        
        # Get actor object
        actor = identity_service.get_actor_object(user, did_document)
        
        return actor
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting actor object: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get actor object"
        )


@router.post("/me/migrate", status_code=status.HTTP_202_ACCEPTED)
async def initiate_migration(
    migration_data: MigrationInitiate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Initiate profile migration to a new instance
    Requirements: 8.4, 8.5
    
    Creates a Move activity and delivers it to all followers.
    
    Args:
        migration_data: New instance URL and password
        
    Returns:
        Migration status and Move activity
    """
    try:
        identity_service = create_identity_service(db)
        
        result = await identity_service.initiate_migration(
            user=current_user,
            new_instance_url=migration_data.new_instance_url,
            password=migration_data.password
        )
        
        return {
            "status": "migration_initiated",
            "message": "Move activity sent to followers",
            "new_instance_url": result["new_instance_url"]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error initiating migration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate migration"
        )


@router.get("/me/export")
async def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Export all user data in ActivityPub format
    Requirements: 8.8
    
    Returns all Video Posts and metadata in ActivityPub format.
    
    Returns:
        User data export in ActivityPub format
    """
    try:
        identity_service = create_identity_service(db)
        
        export_data = await identity_service.export_user_data(current_user)
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename=user_{current_user.username}_export.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting user data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user's profile
    
    Returns:
        User profile
    """
    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        bio=current_user.bio,
        id=current_user.id,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )
