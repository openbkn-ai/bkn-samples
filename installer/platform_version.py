"""Read the same public backend version endpoint used by the OpenBKN SDK."""

import json
import re
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_backend_version(base_url):
    """Unavailable or malformed version information must not enable installation."""
    try:
        url = urlsplit(base_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            return ""
        request = Request(base_url.rstrip("/") + "/api/bkn-backend/v1/health",
                          headers={"Accept": "application/json"})
        with build_opener(NoRedirect()).open(request, timeout=5) as response:
            if response.status != 200:
                return ""
            content = response.read(65537)
        if len(content) > 65536:
            return ""
        payload = json.loads(content)
        if not isinstance(payload, dict):
            return ""
        payload = payload.get("data", payload)
        if not isinstance(payload, dict):
            return ""
        version = payload.get("ServerVersion", payload.get("serverVersion"))
        match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:[-+][0-9A-Za-z.+-]+)?", version) if isinstance(version, str) else None
        return match[1] if match else ""
    except (OSError, URLError, ValueError):
        return ""
