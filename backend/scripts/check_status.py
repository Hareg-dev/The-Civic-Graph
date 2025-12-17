"""
Quick status check for FreeWill Video Platform
Checks if all services are running and accessible
"""

import requests
import sys
import time

SERVICES = {
    "API": "http://localhost:8000/health",
    "PostgreSQL": "http://localhost:8000/api/monitoring/health/database",
    "Redis": "http://localhost:8000/api/monitoring/health/redis",
    "Qdrant": "http://localhost:8000/api/monitoring/health/qdrant",
}

def check_service(name: str, url: str, timeout: int = 5) -> bool:
    """Check if a service is accessible"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print(f"✓ {name}: Running")
            return True
        else:
            print(f"✗ {name}: Error (HTTP {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ {name}: Not accessible")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ {name}: Timeout")
        return False
    except Exception as e:
        print(f"✗ {name}: Error ({e})")
        return False

def main():
    """Main entry point"""
    print("\nFreeWill Video Platform - Status Check")
    print("=" * 50)
    
    # Wait a moment for services to be ready
    time.sleep(1)
    
    results = {}
    for name, url in SERVICES.items():
        results[name] = check_service(name, url)
    
    print("=" * 50)
    
    all_running = all(results.values())
    if all_running:
        print("\n✓ All services are running!")
        print("\nAccess the platform:")
        print("  - API: http://localhost:8000")
        print("  - Docs: http://localhost:8000/docs")
        return 0
    else:
        print("\n✗ Some services are not running")
        print("\nTroubleshooting:")
        print("  1. Check if Docker is running: docker ps")
        print("  2. Start services: docker-compose up -d")
        print("  3. View logs: docker-compose logs -f")
        return 1

if __name__ == "__main__":
    sys.exit(main())
