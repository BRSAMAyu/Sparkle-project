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
PYTHON_BIN="${BACKEND_PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
    if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
        PYTHON_BIN="$VIRTUAL_ENV/bin/python"
    elif [ -x "$(pwd)/.venv/bin/python" ]; then
        PYTHON_BIN="$(pwd)/.venv/bin/python"
    else
        PYTHON_BIN="python3"
    fi
fi
exec "$PYTHON_BIN" grpc_server.py
