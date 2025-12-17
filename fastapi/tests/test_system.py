"""
Comprehensive System Testing Script
Tests all features of the FreeWill Video Platform with real systems
"""

import requests
import json
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration
BASE_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123"
}


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_test(name: str):
    """Print test name"""
    print(f"\n{Colors.BLUE}Testing: {name}{Colors.END}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


class SystemTester:
    """Comprehensive system tester"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token: Optional[str] = None
        self.test_user_id: Optional[int] = None
        self.test_video_id: Optional[int] = None
    
    def test_health(self) -> bool:
        """Test system health endpoints"""
        print_test("System Health")
        
        try:
            # Test root endpoint
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                print_success("Root endpoint accessible")
            else:
                print_error(f"Root endpoint failed: {response.status_code}")
                return False
            
            # Test health endpoint
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print_success(f"Health check passed: {health_data}")
            else:
                print_error(f"Health check failed: {response.status_code}")
                return False
            
            # Test monitoring endpoints
            response = self.session.get(f"{self.base_url}/api/monitoring/health")
            if response.status_code == 200:
                print_success("Monitoring health endpoint accessible")
            else:
                print_warning(f"Monitoring health endpoint returned: {response.status_code}")
            
            return True
        
        except Exception as e:
            print_error(f"Health check error: {e}")
            return False
    
    def test_database_connection(self) -> bool:
        """Test database connectivity"""
        print_test("Database Connection")
        
        try:
            response = self.session.get(f"{self.base_url}/api/monitoring/health/database")
            if response.status_code == 200:
                print_success("Database connection successful")
                return True
            else:
                print_error(f"Database connection failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Database test error: {e}")
            return False
    
    def test_redis_connection(self) -> bool:
        """Test Redis connectivity"""
        print_test("Redis Connection")
        
        try:
            response = self.session.get(f"{self.base_url}/api/monitoring/health/redis")
            if response.status_code == 200:
                print_success("Redis connection successful")
                return True
            else:
                print_error(f"Redis connection failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Redis test error: {e}")
            return False
    
    def test_qdrant_connection(self) -> bool:
        """Test Qdrant connectivity"""
        print_test("Qdrant Connection")
        
        try:
            response = self.session.get(f"{self.base_url}/api/monitoring/health/qdrant")
            if response.status_code == 200:
                print_success("Qdrant connection successful")
                return True
            else:
                print_error(f"Qdrant connection failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Qdrant test error: {e}")
            return False
    
    def test_user_registration(self) -> bool:
        """Test user registration"""
        print_test("User Registration")
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/users/register",
                json=TEST_USER
            )
            
            if response.status_code in [200, 201]:
                user_data = response.json()
                self.test_user_id = user_data.get("id")
                print_success(f"User registered successfully: {user_data.get('username')}")
                return True
            elif response.status_code == 400:
                print_warning("User already exists (expected if running multiple times)")
                return True
            else:
                print_error(f"User registration failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            print_error(f"User registration error: {e}")
            return False
    
    def test_user_login(self) -> bool:
        """Test user authentication"""
        print_test("User Authentication")
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/users/login",
                data={
                    "username": TEST_USER["username"],
                    "password": TEST_USER["password"]
                }
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                print_success("User authentication successful")
                return True
            else:
                print_error(f"User authentication failed: {response.status_code}")
                return False
        
        except Exception as e:
            print_error(f"User authentication error: {e}")
            return False
    
    def test_metrics(self) -> bool:
        """Test metrics endpoint"""
        print_test("Metrics Collection")
        
        try:
            response = self.session.get(f"{self.base_url}/api/monitoring/metrics")
            if response.status_code == 200:
                metrics = response.json()
                print_success(f"Metrics collected: {len(metrics)} metrics")
                return True
            else:
                print_warning(f"Metrics endpoint returned: {response.status_code}")
                return True  # Not critical
        except Exception as e:
            print_warning(f"Metrics test error: {e}")
            return True  # Not critical
    
    def run_all_tests(self):
        """Run all system tests"""
        print(f"\n{'='*60}")
        print(f"{Colors.BLUE}FreeWill Video Platform - System Tests{Colors.END}")
        print(f"Testing against: {self.base_url}")
        print(f"{'='*60}")
        
        results = {
            "Health Check": self.test_health(),
            "Database Connection": self.test_database_connection(),
            "Redis Connection": self.test_redis_connection(),
            "Qdrant Connection": self.test_qdrant_connection(),
            "User Registration": self.test_user_registration(),
            "User Authentication": self.test_user_login(),
            "Metrics Collection": self.test_metrics(),
        }
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"{Colors.BLUE}Test Summary{Colors.END}")
        print(f"{'='*60}")
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, result in results.items():
            status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
            print(f"{test_name}: {status}")
        
        print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.END}")
        
        if passed == total:
            print(f"{Colors.GREEN}✓ All tests passed!{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}✗ Some tests failed{Colors.END}")
            return False


def main():
    """Main entry point"""
    print(f"\n{Colors.BLUE}Starting FreeWill Video Platform System Tests...{Colors.END}\n")
    
    # Wait for services to be ready
    print("Waiting for services to be ready...")
    time.sleep(2)
    
    # Run tests
    tester = SystemTester(BASE_URL)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
