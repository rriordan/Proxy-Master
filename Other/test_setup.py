#!/usr/bin/env python3
"""
Test script to verify the proxy pipeline setup.
Run this to check if all dependencies and scripts are working correctly.
"""

import sys
import importlib
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    required_modules = [
        'requests',
        'aiohttp', 
        'tqdm',
        'asyncio',
        'csv',
        'os',
        'time',
        'collections'
    ]
    
    print("Testing module imports...")
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            failed_imports.append(module)
    
    return len(failed_imports) == 0

def test_scripts():
    """Test if all required scripts exist."""
    required_scripts = [
        'getproxy.py',
        'proxy_benchmark.py',
        'run_proxy_pipeline.py'
    ]
    
    print("\nTesting script files...")
    missing_scripts = []
    
    for script in required_scripts:
        if Path(script).exists():
            print(f"  ✅ {script}")
        else:
            print(f"  ❌ {script} (not found)")
            missing_scripts.append(script)
    
    return len(missing_scripts) == 0

def test_workflow():
    """Test if GitHub Actions workflow exists."""
    workflow_path = Path('.github/workflows/proxy_pipeline.yml')
    
    print("\nTesting GitHub Actions workflow...")
    if workflow_path.exists():
        print(f"  ✅ {workflow_path}")
        return True
    else:
        print(f"  ❌ {workflow_path} (not found)")
        return False

def test_requirements():
    """Test if requirements.txt exists."""
    req_path = Path('requirements.txt')
    
    print("\nTesting requirements file...")
    if req_path.exists():
        print(f"  ✅ {req_path}")
        return True
    else:
        print(f"  ❌ {req_path} (not found)")
        return False

def main():
    """Run all tests."""
    print("🧪 Proxy Pipeline Setup Test")
    print("=" * 40)
    
    all_passed = True
    
    # Run tests
    if not test_imports():
        all_passed = False
    
    if not test_scripts():
        all_passed = False
    
    if not test_workflow():
        all_passed = False
    
    if not test_requirements():
        all_passed = False
    
    # Summary
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed! Setup is ready.")
        print("\nYou can now run:")
        print("  python run_proxy_pipeline.py  # Full pipeline")
        print("  python getproxy.py           # Just scraping")
        print("  python proxy_benchmark.py    # Just benchmarking")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Ensure all script files are in the current directory")
        print("  3. Check file permissions and paths")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
