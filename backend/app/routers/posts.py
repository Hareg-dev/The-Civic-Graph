"""
Posts Router
Handles video post upload and management endpoints
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import redis

from app.db import get_db
from app.redis_client import get_sync_redis
from app.schemas import (
    VideoMetadata,
    VideoPostResponse,
    UploadSessionCreate,
    UploadSessionResponse,
    ValidationResult
)
from app.services.upload_manager import UploadManager
from app.models import VideoPost

router = APIRouter(prefix="/api/posts", tags=["posts"])


def get_upload_manager(
    db: Session = Depends(get_db)
) -> UploadManager:
    """Dependency to get upload manager instance"""
    redis_client = get_sync_redis()
    return UploadManager(redis_client, db)


@router.post("/upload/initiate", response_model=UploadSessionResponse)
async def initiate_upload(
    filename: str = Form(...),
    file_size: int = Form(...),
    total_chunks: int = Form(1),
    user_id: int = Form(...),  # TODO: Get from auth token
    upload_manager: UploadManager = Depends(get_upload_manager)
):
    """
    Initiate a new video upload session
    Requirements: 1.1, 1.2, 1.4
    """
    session = await upload_manager.initiate_upload(
        user_id=user_id,
        filename=filename,
        file_size=file_size,
        total_chunks=total_chunks
    )
    
    return UploadSessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        filename=session.filename,
        file_size=session.file_size,
        total_chunks=session.total_chunks,
        uploaded_chunks=list(session.uploaded_chunks),
        status=session.status,
        created_at=session.created_at,
        expires_at=session.expires_at
    )


@router.post("/upload/chunk")
async def upload_chunk(
    session_id: str = Form(...),
    chunk_number: int = Form(...),
    file: UploadFile = File(...),
    upload_manager: UploadManager = Depends(get_upload_manager)
):
    """
    Upload a chunk of video data
    Requirements: 1.5
    """
    chunk_data = await file.read()
    
    result = await upload_manager.upload_chunk(
        session_id=session_id,
        chunk_number=chunk_number,
        chunk_data=chunk_data
    )
    
    return result


@router.post("/upload/finalize", response_model=VideoPostResponse)
async def finalize_upload(
    session_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: str = Form("[]"),  # JSON string of tags
    checksum: Optional[str] = Form(None),
    upload_manager: UploadManager = Depends(get_upload_manager)
):
    """
    Finalize upload and create Video Post
    Requirements: 1.6, 1.7, 1.8
    """
    import json
    
    # Parse tags
    try:
        tags_list = json.loads(tags)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid tags format")
    
    metadata = VideoMetadata(
        title=title,
        description=description,
        tags=tags_list
    )
    
    video_post = await upload_manager.finalize_upload(
        session_id=session_id,
        metadata=metadata,
        expected_checksum=checksum
    )
    
    return VideoPostResponse.from_orm(video_post)


@router.post("/upload", response_model=VideoPostResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: str = Form("[]"),
    user_id: int = Form(...),  # TODO: Get from auth token
    upload_manager: UploadManager = Depends(get_upload_manager)
):
    """
    Simple single-file upload endpoint
    Requirements: 1.1, 1.2, 1.3, 1.7, 1.8
    """
    import json
    import tempfile
    
    # Parse tags
    try:
        tags_list = json.loads(tags)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid tags format")
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Initiate session
    session = await upload_manager.initiate_upload(
        user_id=user_id,
        filename=file.filename,
        file_size=file_size,
        total_chunks=1
    )
    
    # Upload chunk
    await upload_manager.upload_chunk(
        session_id=session.session_id,
        chunk_number=0,
        chunk_data=content
    )
    
    # Finalize
    metadata = VideoMetadata(
        title=title,
        description=description,
        tags=tags_list
    )
    
    video_post = await upload_manager.finalize_upload(
        session_id=session.session_id,
        metadata=metadata
    )
    
    return VideoPostResponse.from_orm(video_post)


@router.get("/{video_id}", response_model=VideoPostResponse)
def get_video_post(
    video_id: int,
    db: Session = Depends(get_db)
):
    """Get video post by ID"""
    video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
    
    if not video_post:
        raise HTTPException(status_code=404, detail="Video post not found")
    
    return VideoPostResponse.from_orm(video_post)


@router.get("/", response_model=list[VideoPostResponse])
def list_video_posts(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List video posts with optional filters"""
    query = db.query(VideoPost)
    
    if user_id:
        query = query.filter(VideoPost.user_id == user_id)
    
    if status:
        query = query.filter(VideoPost.status == status)
    
    query = query.order_by(VideoPost.created_at.desc())
    video_posts = query.offset(skip).limit(limit).all()
    
    return [VideoPostResponse.from_orm(vp) for vp in video_posts]


@router.delete("/{video_id}")
def delete_video_post(
    video_id: int,
    db: Session = Depends(get_db)
):
    """Delete video post"""
    video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
    
    if not video_post:
        raise HTTPException(status_code=404, detail="Video post not found")
    
    # TODO: Delete associated files
    # TODO: Check user permissions
    
    db.delete(video_post)
    db.commit()
    
    return {"message": "Video post deleted successfully"}


@router.post("/{video_id}/process")
async def process_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger video processing
    In production, this would be handled automatically by background workers
    """
    from app.workers.media import create_media_worker, VideoProcessingTask
    
    video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
    
    if not video_post:
        raise HTTPException(status_code=404, detail="Video post not found")
    
    if not video_post.original_file_path:
        raise HTTPException(status_code=400, detail="No video file to process")
    
    # Create media worker and process
    worker = create_media_worker(db)
    task = VideoProcessingTask(video_id, video_post.original_file_path)
    result = await worker.process_video_task(task)
    
    if result.success:
        return {
            "message": "Video processed successfully",
            "video_id": video_id,
            "resolutions": list(result.resolutions.keys()),
            "thumbnails": list(result.thumbnails.keys()),
            "duration": result.duration
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Video processing failed: {result.error}"
        )
