#!/bin/bash
# Run from cron at 1am. Use full paths so cron has correct env.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec /usr/bin/env python3 "$SCRIPT_DIR/verify_files.py" --config "$SCRIPT_DIR/config.json" --verify-file "$SCRIPT_DIR/VerifyFile"
