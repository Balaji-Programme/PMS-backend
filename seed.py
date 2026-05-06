import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.seeding import seed_all

if __name__ == "__main__":
    reset = "--reset" in sys.argv
    seed_all(reset=reset)
