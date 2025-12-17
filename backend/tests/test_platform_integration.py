"""
Comprehensive Integration Tests for FreeWill Video Platform
Tests all features with real systems (no mocks/simulations)
"""
import asyncio
import os
import sys
import time
import httpx
import json
from pathlib import Path
from typing import Dict, Any, List

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"
TEST_VIDEO_PATH = "test_video.mp4"

class PlatformTester:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.auth_token = None
        self.user_id = None
        self.test_results = []
 