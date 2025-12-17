#!/usr/bin/env python3
"""Write outbox.py file"""

OUTBOX_CONTENT = '''"""
Outbox Handler for Federation Publishing
Manages delivery of activities to remote instances
Requirements: 5.5-5.8
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.config import settings
from app.models import Activity, DeliveryRecord, Follower, User
from app.federation.activitypub import ActivityPubService

logger = logging.getLogger(__name__)


class OutboxHandler:
    """
    Handles outbound federation activities
    Manages delivery to follower inboxes with retry logic
    """
    
    def __init__(self, db: Session, activitypub_service: ActivityPubService):
        self.db = db
        self.activitypub = activitypub_service
        self.max_attempts = settings.DELIVERY_RETRY_ATTEMPTS
        self.retry_delays = settings.DELIVERY_RETRY_DELAYS_MIN
        self.timeout = settings.FEDERATION_TIMEOUT_SEC
    
    def get_follower_inboxes(self, user_id: int) -> List[str]:
        """
        Retrieve inbox endpoints for all followers
        Requirements: 5.5
        """
        try:
            followers = self.db.query(Follower).filter(
                Follower.user_id == user_id
            ).all()
            
            inboxes = [f.follower_inbox for f in followers if f.follower_inbox]
            
            logger.info(f"Retrieved {len(inboxes)} follower inboxes for user {user_id}")
            return inboxes
            
        except Exception as e:
            logger.error(f"Error retrieving follower inboxes: {e}")
            return []
    
    def create_delivery_tasks(self, activity: Activity, inbox_urls: List[str]) -> List[DeliveryRecord]:
        """
        Create delivery records for each inbox
        Requirements: 5.5, 5.6
        """
        try:
            delivery_records = []
            
            for inbox_url in inbox_urls:
                record = DeliveryRecord(
                    activity_id=activity.id,
                    inbox_url=inbox_url,
                    status="pending",
                    attempts=0,
                    next_retry_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                
                self.db.add(record)
                delivery_records.append(record)
            
            self.db.commit()
            
            logger.info(f"Created {len(delivery_records)} delivery tasks for activity {activity.id}")
            return delivery_records
            
        except Exception as e:
            logger.error(f"Error creating delivery tasks: {e}")
            self.db.rollback()
            return []
    
    async def deliver_activity(self, activity: Activity, inbox_url: str, signature_header: str) -> tuple:
        """
        Deliver activity to remote inbox with HTTP signature
        Requirements: 5.6, 5.7
        """
        try:
            headers = {
                "Content-Type": "application/activity+json",
                "Signature": signature_header,
                "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(inbox_url, json=activity.content, headers=headers)
                
                if 200 <= response.status_code < 300:
                    logger.info(f"Successfully delivered activity {activity.id} to {inbox_url}")
                    return True, None
                elif 400 <= response.status_code < 500:
                    error_msg = f"Client error {response.status_code}: {response.text[:200]}"
                    logger.error(f"Permanent delivery failure to {inbox_url}: {error_msg}")
                    return False, error_msg
                else:
                    error_msg = f"Server error {response.status_code}: {response.text[:200]}"
                    logger.warning(f"Temporary delivery failure to {inbox_url}: {error_msg}")
                    return False, error_msg
                    
        except httpx.TimeoutException as e:
            error_msg = f"Timeout: {str(e)}"
            logger.warning(f"Delivery timeout to {inbox_url}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Delivery error to {inbox_url}: {error_msg}")
            return False, error_msg
    
    async def process_delivery_record(self, delivery_record: DeliveryRecord) -> bool:
        """
        Process a single delivery record with retry logic
        Requirements: 5.7, 5.8
        """
        try:
            activity = self.db.query(Activity).filter(Activity.id == delivery_record.activity_id).first()
            
            if not activity:
                logger.error(f"Activity {delivery_record.activity_id} not found")
                delivery_record.status = "failed"
                delivery_record.error_message = "Activity not found"
                self.db.commit()
                return False
            
            user = self.db.query(User).filter(User.username == activity.actor.split("/")[-1]).first()
            
            if not user or not user.did_document:
                logger.error(f"User or DID not found for activity {activity.id}")
                delivery_record.status = "failed"
                delivery_record.error_message = "User or DID not found"
                self.db.commit()
                return False
            
            key_id = f"{settings.INSTANCE_URL}/users/{user.username}#main-key"
            signature_header = self.activitypub.sign_activity(
                activity.content,
                user.did_document.encrypted_private_key,
                key_id
            )
            
            success, error_msg = await self.deliver_activity(activity, delivery_record.inbox_url, signature_header)
            
            delivery_record.attempts += 1
            delivery_record.last_attempt_at = datetime.utcnow()
            
            if success:
                delivery_record.status = "delivered"
                delivery_record.next_retry_at = None
                logger.info(f"Delivery {delivery_record.id} succeeded")
            else:
                delivery_record.error_message = error_msg
                
                if delivery_record.attempts >= self.max_attempts:
                    delivery_record.status = "failed"
                    delivery_record.next_retry_at = None
                    logger.error(f"Delivery {delivery_record.id} failed after {self.max_attempts} attempts")
                else:
                    delay_minutes = self.retry_delays[delivery_record.attempts - 1]
                    delivery_record.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
                    logger.info(f"Delivery {delivery_record.id} will retry in {delay_minutes} minutes")
            
            self.db.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error processing delivery record {delivery_record.id}: {e}")
            self.db.rollback()
            return False
    
    async def process_pending_deliveries(self, batch_size: int = 100) -> int:
        """
        Process pending delivery records
        Background worker function
        Requirements: 5.8
        """
        try:
            pending = self.db.query(DeliveryRecord).filter(
                and_(
                    DeliveryRecord.status == "pending",
                    DeliveryRecord.next_retry_at <= datetime.utcnow()
                )
            ).limit(batch_size).all()
            
            if not pending:
                logger.debug("No pending deliveries to process")
                return 0
            
            logger.info(f"Processing {len(pending)} pending deliveries")
            
            processed = 0
            for record in pending:
                try:
                    await self.process_delivery_record(record)
                    processed += 1
                except Exception as e:
                    logger.error(f"Error processing delivery {record.id}: {e}")
                    continue
            
            logger.info(f"Processed {processed}/{len(pending)} deliveries")
            return processed
            
        except Exception as e:
            logger.error(f"Error in process_pending_deliveries: {e}")
            return 0
    
    async def publish_activity(self, activity: Activity, user_id: int) -> bool:
        """
        Publish activity to all followers
        Complete outbox flow
        Requirements: 5.5, 5.6, 5.7
        """
        try:
            inboxes = self.get_follower_inboxes(user_id)
            
            if not inboxes:
                logger.info(f"No followers to deliver activity {activity.id}")
                return True
            
            delivery_records = self.create_delivery_tasks(activity, inboxes)
            
            if not delivery_records:
                logger.error(f"Failed to create delivery tasks for activity {activity.id}")
                return False
            
            logger.info(f"Published activity {activity.id} to {len(delivery_records)} inboxes")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing activity: {e}")
            return False
    
    def get_delivery_stats(self, activity_id: int) -> Dict[str, int]:
        """Get delivery statistics for an activity"""
        try:
            records = self.db.query(DeliveryRecord).filter(
                DeliveryRecord.activity_id == activity_id
            ).all()
            
            stats = {
                "total": len(records),
                "delivered": sum(1 for r in records if r.status == "delivered"),
                "pending": sum(1 for r in records if r.status == "pending"),
                "failed": sum(1 for r in records if r.status == "failed")
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting delivery stats: {e}")
            return {"total": 0, "delivered": 0, "pending": 0, "failed": 0}


def create_outbox_handler(db: Session, activitypub_service: ActivityPubService) -> OutboxHandler:
    """Factory function to create outbox handler"""
    return OutboxHandler(db, activitypub_service)
'''

if __name__ == '__main__':
    with open('app/federation/outbox.py', 'w', encoding='utf-8') as f:
        f.write(OUTBOX_CONTENT)
    print("✓ outbox.py written successfully")
    
    # Verify
    with open('app/federation/outbox.py', 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"✓ Verified: {len(content)} characters")
