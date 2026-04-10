"""
Validate notification tests syntax and structure
Run this to check if tests are properly structured before running them
"""
import os
import sys
import ast
import importlib.util

def validate_test_file(filepath):
    """Validate Python test file syntax"""
    print(f"Validating {filepath}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Check syntax
        try:
            ast.parse(code)
            print("[OK] Syntax is valid")
        except SyntaxError as e:
            print(f"[ERROR] Syntax error: {e}")
            return False
        
        # Check for required imports
        required_imports = ['pytest', 'asyncpg', 'AsyncMock']
        missing_imports = []
        for imp in required_imports:
            if imp not in code:
                missing_imports.append(imp)
        
        if missing_imports:
            print(f"[WARN] Missing imports (may be OK if using fixtures): {missing_imports}")
        else:
            print("[OK] Required imports found")
        
        # Count test functions (including async functions)
        tree = ast.parse(code)
        test_functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                test_functions.append(node.name)
        print(f"[OK] Found {len(test_functions)} test functions:")
        for func in test_functions:
            print(f"  - {func}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error validating file: {e}")
        return False

def main():
    """Main validation function"""
    print("=" * 80)
    print("NOTIFICATION TESTS VALIDATION")
    print("=" * 80)
    
    test_file = os.path.join(os.path.dirname(__file__), 'tests', 'test_notifications.py')
    
    if not os.path.exists(test_file):
        print(f"[ERROR] Test file not found: {test_file}")
        return 1
    
    print(f"Test file: {test_file}\n")
    
    success = validate_test_file(test_file)
    
    print("\n" + "=" * 80)
    if success:
        print("VALIDATION PASSED")
        print("\nTo run tests, execute:")
        print("  cd services/bot")
        print("  python -m pytest tests/test_notifications.py -v -s")
        print("\nOr with debug logging:")
        print("  DEBUG=1 python -m pytest tests/test_notifications.py -v -s")
    else:
        print("VALIDATION FAILED")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
