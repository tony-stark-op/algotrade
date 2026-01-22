# Redirect to new production config
import sys
from pathlib import Path

# Add src to path if needed, though usually in path
# Just import the new config
from src.production.config import config, Config
