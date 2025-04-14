#!/usr/bin/env python
import os
import sys

# Add the project directory to the path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Import and run the GUI
from gui.interface import main

if __name__ == "__main__":
    main() 