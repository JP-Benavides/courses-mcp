from pathlib import Path
import sys

# Support the package import when this file is launched directly.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.middleware.auth.generate_bearer_token import create_server


def main():
    create_server().run(transport="http", host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()
