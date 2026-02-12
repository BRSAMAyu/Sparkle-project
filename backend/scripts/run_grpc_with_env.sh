#!/bin/bash
# gRPC Server startup script with WeasyPrint library path configuration

# macOS-specific: Add Homebrew library path for WeasyPrint GTK dependencies
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [ -d "/opt/homebrew/lib" ]; then
        export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
        echo "✓ Set DYLD_LIBRARY_PATH for WeasyPrint"
    fi
fi

# Run the gRPC server
cd "$(dirname "$0")/.."
exec python grpc_server.py
