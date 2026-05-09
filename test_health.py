from __future__ import annotations

import json
from urllib.request import urlopen


def main() -> None:
    with urlopen("http://localhost:8000/health", timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    print(payload)


if __name__ == "__main__":
    main()