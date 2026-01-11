import os
import re

def fix_grpc_imports(base_dir):
    print(f"Fixing gRPC imports in {base_dir}...")
    for root, dirs, files in os.walk(base_dir):
        # 1. Ensure __init__.py exists
        if "__init__.py" not in files:
            with open(os.path.join(root, "__init__.py"), "w") as f:
                pass
            print(f"Created __init__.py in {root}")
        
        # 2. Fix pb2 imports in generated files
        for file in files:
            if file.endswith("_pb2.py") or file.endswith("_pb2_grpc.py"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                
                # Replace 'import xxx_pb2' with 'from . import xxx_pb2'
                new_content = re.sub(r'^import (.*_pb2)', r'from . import \1', content, flags=re.MULTILINE)
                
                if new_content != content:
                    with open(path, "w") as f:
                        f.write(new_content)
                    print(f"Fixed imports in {path}")

if __name__ == "__main__":
    # Target directories
    gen_dir = os.path.abspath(os.path.join(os.getcwd(), "backend", "app", "gen"))
    fix_grpc_imports(gen_dir)
