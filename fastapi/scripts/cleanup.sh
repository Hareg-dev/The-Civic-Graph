#!/bin/bash
# Cleanup script for development artifacts

echo "Cleaning up development artifacts..."

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.pyd" -delete

# Remove test databases
rm -f *.db *.sqlite3

# Remove pytest cache
rm -rf .pytest_cache

# Remove coverage reports
rm -rf htmlcov
rm -f .coverage

# Remove build artifacts
rm -rf build dist *.egg-info

echo "✓ Cleanup complete!"
