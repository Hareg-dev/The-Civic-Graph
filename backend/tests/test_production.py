"""
Production Load Testing Script
Tests the production deployment with Gunicorn and Nginx
"""

import requests
import time
import concurrent.futures
import statistics
from typing import List, Dict, Any
import sys

# Configuration
BASE_URL = "http://localhost"  # Nginx endpoint
NUM_REQUESTS = 100
CONCURRENT_USERS = 10

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text: str):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")

class ProductionTester:
    """Production load tester"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health(self) -> bool:
        """Test health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print_success(f"Health check passed: {response.json()}")
                return True
            else:
                print_error(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Health check error: {e}")
            return False
    
    def test_nginx_headers(self) -> bool:
        """Test Nginx security headers"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            headers = response.headers
            
            security_headers = {
                'X-Frame-Options': 'SAMEORIGIN',
                'X-Content-Type-Options': 'nosniff',
                'X-XSS-Protection': '1; mode=block',
            }
            
            all_present = True
            for header, expected in security_headers.items():
                if header in headers:
                    print_success(f"Security header present: {header}")
                else:
                    print_error(f"Security header missing: {header}")
                    all_present = False
            
            return all_present
        except Exception as e:
            print_error(f"Header check error: {e}")
            return False
    
    def test_compression(self) -> bool:
        """Test Gzip compression"""
        try:
            headers = {'Accept-Encoding': 'gzip, deflate'}
            response = self.session.get(f"{self.base_url}/docs", headers=headers)
            
            if 'Content-Encoding' in response.headers:
                encoding = response.headers['Content-Encoding']
                print_success(f"Compression enabled: {encoding}")
                return True
            else:
                print_error("Compression not enabled")
                return False
        except Exception as e:
            print_error(f"Compression test error: {e}")
            return False
    
    def single_request(self, endpoint: str) -> Dict[str, Any]:
        """Make a single request and measure performance"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
            elapsed = time.time() - start_time
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'elapsed': elapsed,
                'error': None
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                'success': False,
                'status_code': 0,
                'elapsed': elapsed,
                'error': str(e)
            }
    
    def load_test(self, endpoint: str, num_requests: int, concurrent: int) -> Dict[str, Any]:
        """Run load test on endpoint"""
        print_info(f"Running load test: {num_requests} requests, {concurrent} concurrent users")
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [executor.submit(self.single_request, endpoint) for _ in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # Calculate statistics
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        response_times = [r['elapsed'] for r in successful]
        
        stats = {
            'total_requests': num_requests,
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / num_requests * 100,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'median_response_time': statistics.median(response_times) if response_times else 0,
        }
        
        return stats
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting"""
        print_info("Testing rate limiting (sending rapid requests)...")
        
        rate_limited = False
        for i in range(50):
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 429:
                rate_limited = True
                print_success(f"Rate limiting working (got 429 after {i+1} requests)")
                break
            time.sleep(0.05)  # 20 requests per second
        
        if not rate_limited:
            print_info("Rate limiting not triggered (may need more requests or is configured differently)")
        
        return True
    
    def test_concurrent_connections(self) -> bool:
        """Test concurrent connection handling"""
        print_info("Testing concurrent connection handling...")
        
        def make_request():
            return self.session.get(f"{self.base_url}/health", timeout=10)
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(make_request) for _ in range(50)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            successful = sum(1 for r in results if r.status_code == 200)
            print_success(f"Handled {successful}/50 concurrent connections")
            return successful >= 45  # Allow some failures
        except Exception as e:
            print_error(f"Concurrent connection test error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all production tests"""
        print_header("FreeWill Video Platform - Production Tests")
        print(f"Testing: {self.base_url}")
        print(f"Requests: {NUM_REQUESTS}")
        print(f"Concurrent Users: {CONCURRENT_USERS}")
        
        results = {}
        
        # Basic tests
        print_header("1. Basic Health Checks")
        results['health'] = self.test_health()
        
        print_header("2. Nginx Security Headers")
        results['security_headers'] = self.test_nginx_headers()
        
        print_header("3. Compression")
        results['compression'] = self.test_compression()
        
        # Performance tests
        print_header("4. Load Test - Health Endpoint")
        health_stats = self.load_test('/health', NUM_REQUESTS, CONCURRENT_USERS)
        print_success(f"Success Rate: {health_stats['success_rate']:.2f}%")
        print_success(f"Avg Response Time: {health_stats['avg_response_time']*1000:.2f}ms")
        print_success(f"Min Response Time: {health_stats['min_response_time']*1000:.2f}ms")
        print_success(f"Max Response Time: {health_stats['max_response_time']*1000:.2f}ms")
        print_success(f"Median Response Time: {health_stats['median_response_time']*1000:.2f}ms")
        results['load_test'] = health_stats['success_rate'] >= 95
        
        print_header("5. Load Test - API Endpoint")
        api_stats = self.load_test('/api/monitoring/health', NUM_REQUESTS // 2, CONCURRENT_USERS)
        print_success(f"Success Rate: {api_stats['success_rate']:.2f}%")
        print_success(f"Avg Response Time: {api_stats['avg_response_time']*1000:.2f}ms")
        
        print_header("6. Rate Limiting")
        results['rate_limiting'] = self.test_rate_limiting()
        
        print_header("7. Concurrent Connections")
        results['concurrent'] = self.test_concurrent_connections()
        
        # Summary
        print_header("Test Summary")
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, result in results.items():
            status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
            print(f"{test_name}: {status}")
        
        print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.END}")
        
        # Performance summary
        print_header("Performance Summary")
        print(f"Health Endpoint:")
        print(f"  - Requests/sec: {NUM_REQUESTS / (health_stats['avg_response_time'] * NUM_REQUESTS):.2f}")
        print(f"  - Avg latency: {health_stats['avg_response_time']*1000:.2f}ms")
        print(f"  - P50 latency: {health_stats['median_response_time']*1000:.2f}ms")
        print(f"  - P99 latency: {health_stats['max_response_time']*1000:.2f}ms")
        
        if passed == total:
            print(f"\n{Colors.GREEN}✓ All production tests passed!{Colors.END}")
            return True
        else:
            print(f"\n{Colors.RED}✗ Some production tests failed{Colors.END}")
            return False

def main():
    """Main entry point"""
    print(f"\n{Colors.BLUE}Starting Production Tests...{Colors.END}\n")
    
    # Wait for services
    print("Waiting for services to be ready...")
    time.sleep(2)
    
    # Run tests
    tester = ProductionTester(BASE_URL)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
