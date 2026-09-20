# Vercel serverless entry point - imports the Flask app from parent directory
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app

# Vercel expects a callable named "app"
