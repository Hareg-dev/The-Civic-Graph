"""
Test ngrok deployment
Automatically detects ngrok URL and runs tests
"""

import requests
import json
import time
import sys
from typing import Optional

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

def get_ngrok_url() -> Optional[str]:
    """Get ngrok public URL from API"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get('tunnels', [])
            if tunnels:
                # Get HTTPS URL if available, otherwise HTTP
                for tunnel in tunnels:
                    if tunnel.get('proto') == 'https':
                        return tunnel.get('public_url')
                # Fallback to first tunnel
                return tunnels[0].get('public_url')
    except Exception as e:
        print_error(f"Could not connect to ngrok API: {e}")
    return None

def test_deployment(base_url: str) -> bool:
    """Test the deployment"""
    print_header("Testing ngrok Deployment")
    print(f"Testing URL: {base_url}")
    
    results = {}
    
    # Test 1: Health check
    print_info("Test 1: Health Check")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print_success(f"Health check passed: {response.json()}")
            results['health'] = True
        else:
            print_error(f"Health check failed: {response.status_code}")
            results['health'] = False
    except Exception as e:
        print_error(f"Health check error: {e}")
        results['health'] = False
    
    # Test 2: API Documentation
    print_info("Test 2: API Documentation")
    try:
        response = requests.get(f"{base_url}/docs", timeout=10)
        if response.status_code == 200:
            print_success("API documentation accessible")
            results['docs'] = True
        else:
            print_error(f"API documentation failed: {response.status_code}")
            results['docs'] = False
    except Exception as e:
        print_error(f"API documentation error: {e}")
        results['docs'] = False
    
    # Test 3: Monitoring endpoint
    print_info("Test 3: Monitoring Endpoint")
    try:
        response = requests.get(f"{base_url}/api/monitoring/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print_success(f"Monitoring endpoint accessible: {health_data.get('status', 'unknown')}")
            results['monitoring'] = True
        else:
            print_error(f"Monitoring endpoint failed: {response.status_code}")
            results['monitoring'] = False
    except Exception as e:
        print_error(f"Monitoring endpoint error: {e}")
        results['monitoring'] = False
    
    # Test 4: External accessibility
    print_info("Test 4: External Accessibility")
    try:
        # Test from external perspective
        response = requests.get(f"{base_url}/health", timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (External Test)'
        })
        if response.status_code == 200:
            print_success("Platform is accessible from external networks")
            results['external'] = True
        else:
            print_error("Platform may not be accessible externally")
            results['external'] = False
    except Exception as e:
        print_error(f"External accessibility error: {e}")
        results['external'] = False
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{test_name}: {status}")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}✓ All tests passed! Your platform is live!{Colors.END}")
        return True
    else:
        print(f"\n{Colors.YELLOW}⚠ Some tests failed, but platform may still be accessible{Colors.END}")
        return False

def main():
    """Main entry point"""
    print_header("FreeWill Video Platform - ngrok Deployment Test")
    
    # Try to get ngrok URL automatically
    print_info("Detecting ngrok tunnel...")
    ngrok_url = get_ngrok_url()
    
    if ngrok_url:
        print_success(f"Found ngrok URL: {ngrok_url}")
    else:
        print_error("Could not detect ngrok URL automatically")
        print_info("Make sure ngrok is running!")
        print_info("You can also manually enter the URL...")
        
        # Ask user for URL
        try:
            ngrok_url = input("\nEnter your ngrok URL (or press Enter to exit): ").strip()
            if not ngrok_url:
                print_info("Exiting...")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\n\nExiting...")
            sys.exit(0)
    
    # Ensure URL has protocol
    if not ngrok_url.startswith('http'):
        ngrok_url = f"https://{ngrok_url}"
    
    # Wait a moment for services
    print_info("Waiting for services to be ready...")
    time.sleep(2)
    
    # Run tests
    success = test_deployment(ngrok_url)
    
    # Show access information
    print_header("Access Your Platform")
    print(f"🌐 Public URL: {ngrok_url}")
    print(f"📚 API Docs: {ngrok_url}/docs")
    print(f"❤️  Health: {ngrok_url}/health")
    print(f"📊 Metrics: {ngrok_url}/api/monitoring/metrics")
    print("")
    print(f"{Colors.YELLOW}⚠️  Remember:{Colors.END}")
    print("  - Keep ngrok running to maintain the tunnel")
    print("  - Free ngrok tier has connection limits")
    print("  - URL changes each time you restart ngrok")
    print("  - For permanent deployment, use a real domain")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
