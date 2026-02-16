"""
Shared helpers for the content pipeline tools.

Environment variables are loaded by uv via UV_ENV_FILE — see the justfile
and shell scripts. These are just convenience functions.
"""

import os
import sys


def get_project_dir(project_name):
  """Get the absolute path to a project directory."""
  root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  project_dir = os.path.join(root_dir, "projects", project_name)
  if not os.path.isdir(project_dir):
    raise FileNotFoundError(f"Project not found: {project_dir}")
  return project_dir


def require_env(key):
  """Get a required environment variable or exit."""
  val = os.environ.get(key)
  if not val:
    print(f"Error: {key} not set. Check your .env file.")
    sys.exit(1)
  return val
