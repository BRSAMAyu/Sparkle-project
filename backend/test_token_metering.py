import os
import re
import sys

def fix_grpc_imports(base_dir):
    print(f"Fixing gRPC imports in {base_dir}...")
    for root, dirs, files in os.walk(base_dir):
        if "__init__.py" not in files:
            with open(os.path.join(root, "__init__.py"), "w") as f:
                pass
            print(f"Created __init__.py in {root}")
        
        for file in files:
            if file.endswith("_pb2.py") or file.endswith("_pb2_grpc.py"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                
                new_content = re.sub(r'^import (.*_pb2)', r'from . import \1', content, flags=re.MULTILINE)
                
                if new_content != content:
                    with open(path, "w") as f:
                        f.write(new_content)
                    print(f"Fixed imports in {path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    gen_dir = os.path.join(current_dir, "app", "gen")
    if os.path.exists(gen_dir):
        fix_grpc_imports(gen_dir)
    else:
        print(f"Directory not found: {gen_dir}")
