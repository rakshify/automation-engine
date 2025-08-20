#!/usr/bin/env python3
"""Simple script to run the Workflow Manager."""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_manager.__main__ import main

if __name__ == "__main__":
    main()
