"""Resolve FuckingFast download URLs without launching a browser."""

import html
import json
import re
from contextlib import closing
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup


MAX_PAGE_BYTES = 1024 * 1024
MAX_STEPS = 10


class ExtractionError(RuntimeError):
    """The host did not return a usable download URL."""


class BrowserRequiredError(ExtractionError):
    """The page requires JavaScript or an interactive challenge."""


def create_http_session():
    """Use a local HTTP client with browser-compatible TLS, without a browser engine."""
    try:
        from curl_cffi import requests
    except ImportError as exc:
        raise ExtractionError(
            "HTTP extraction needs curl_cffi. Run: python -m pip install -r requirements.txt"
        ) from exc
    return requests.Session(impersonate="chrome")


def is_direct_url(url):
    parsed = urlsplit(url)
    return parsed.scheme in ("http", "https") and parsed.hostname == "dl.fuckingfast.co"


def _page_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in (
        "fuckingfast.co", "www.fuckingfast.co"
    ):
        raise ExtractionError("Unsupported file-page URL returned by host.")
    return urldefrag(url)[0]


def _read_page(response):
    # A host response must never cause us to download the actual multi-GB file.
    if "attachment" in response.headers.get("Content-Disposition", "").lower():
        raise ExtractionError("Host returned a file instead of a download link.")
    chunks = []
    size = 0
    for chunk in response.iter_content(chunk_size=16384):
        size += len(chunk)
        if size > MAX_PAGE_BYTES:
            raise ExtractionError("Host response was too large to be a file page.")
        chunks.append(chunk)
    return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")


def _direct_url(soup, source, page_url):
    for element in soup.select("[href], [data-direct-url]"):
        candidate = urljoin(page_url, element.get("data-direct-url") or element.get("href", ""))
        if is_direct_url(candidate):
            return candidate
    # Covers legacy window.open(), location assignments and JSON-escaped URLs.
    source = source.replace(r"\/", "/")
    match = re.search(r'''(?:https?:)?//dl\.fuckingfast\.co/[^\s"'<>\\]+''', source)
    if match:
        return urljoin(page_url, html.unescape(match.group(0)))
    return None


def _static_attributes(button, attribute):
    values = {}
    # HTMX values and headers are inherited; children override their parents.
    for element in [*reversed(list(button.parents)), button]:
        raw = element.get(attribute, element.get("data-" + attribute))
        if raw is None:
            continue
        try:
            value = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise BrowserRequiredError("Download button requires JavaScript. Select an installed browser and retry.") from exc
        if not isinstance(value, dict):
            raise ExtractionError(f"Invalid {attribute} on download button.")
        values.update(value)
    return values


def extract_direct_url(url, session):
    """Use one shared HTTP session for cookies; stop before any file transfer.

    Handles static links, same-host redirects, and HTMX download POSTs. It does
    not execute JavaScript or solve Cloudflare challenges.
    """
    if is_direct_url(url):
        return url
    current_url = _page_url(url)
    method, data, headers = "GET", None, {}
    seen = set()

    for _ in range(MAX_STEPS):
        request_key = (method, current_url, json.dumps(data, sort_keys=True))
        if request_key in seen:
            raise ExtractionError("Host did not return a direct link. Select an installed browser and retry.")
        seen.add(request_key)
        with closing(session.request(
            method, current_url, data=data, headers=headers,
            timeout=20, allow_redirects=False, stream=True,
        )) as response:
            redirect = response.headers.get("HX-Redirect")
            if not redirect and response.is_redirect:
                redirect = response.headers.get("Location")
            if redirect:
                target = urljoin(current_url, redirect)
                if is_direct_url(target):
                    return target
                next_url = _page_url(target)
                if response.status_code not in (307, 308) or response.headers.get("HX-Redirect"):
                    method, data = "GET", None
                headers = {"Referer": current_url}
                current_url = next_url
                continue

            source = _read_page(response)
            # Normal file pages also load Turnstile and background jsd scripts.
            # Only the interstitial challenge itself prevents HTTP extraction.
            if response.headers.get("cf-mitigated", "").lower() == "challenge" or "_cf_chl_opt" in source:
                raise BrowserRequiredError(
                    "Cloudflare returned an interactive challenge. HTTP extraction cannot complete it."
                )
            response.raise_for_status()

        soup = BeautifulSoup(source, "html.parser")
        direct_url = _direct_url(soup, source, current_url)
        if direct_url:
            return direct_url

        button = soup.select_one("[hx-post], [data-hx-post]")
        if button is None:
            raise ExtractionError("No download link or supported download button found. Select an installed browser and retry.")

        endpoint = button.get("hx-post", button.get("data-hx-post", ""))
        next_url = _page_url(urljoin(current_url, endpoint))
        data = {}
        form = button if button.name == "form" else button.find_parent("form")
        if form is not None:
            data.update({
                field["name"]: field.get("value", "")
                for field in form.select('input[type="hidden"][name]:not([disabled])')
            })
        data.update(_static_attributes(button, "hx-vals"))
        if button.get("name"):
            data[button["name"]] = button.get("value", "")
        parsed = urlsplit(current_url)
        headers = _static_attributes(button, "hx-headers")
        headers.update({
            "HX-Request": "true",
            "HX-Current-URL": current_url,
            "Referer": current_url,
            "Origin": f"{parsed.scheme}://{parsed.netloc}",
        })
        if button.get("id"):
            headers["HX-Trigger"] = button["id"]
        current_url, method = next_url, "POST"

    raise ExtractionError("Too many redirects or download steps from host.")
