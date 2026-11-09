"""Turn a public web page into a markdown note.

The server fetches whatever URL a user types, so every hop is checked to stay on the public
internet: no private networks, no loopback, no cloud metadata addresses.
"""

import ipaddress
import re
import socket
from html.parser import HTMLParser

import httpx

MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 10
MIN_BODY_CHARS = 50
ALLOWED_PORTS = {None, 80, 443}

USER_AGENT = "Mozilla/5.0 (compatible; RecapNoteImporter/1.0)"


class WebNoteError(Exception):
    """A problem the user can act on; the message is shown to them as is."""


def _make_client() -> httpx.Client:
    return httpx.Client(
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"},
    )


def _require_public(host: str, port: int) -> None:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise WebNoteError("주소를 찾을 수 없어요. URL을 다시 확인해주세요.") from exc
    for info in infos:
        if not ipaddress.ip_address(info[4][0].split("%")[0]).is_global:
            raise WebNoteError("공개된 웹 페이지만 가져올 수 있어요.")


def _validate(url: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url.strip())
    except httpx.InvalidURL as exc:
        raise WebNoteError("올바른 URL이 아니에요.") from exc
    if parsed.scheme not in ("http", "https") or not parsed.host:
        raise WebNoteError("http:// 또는 https:// 로 시작하는 주소를 입력해주세요.")
    if parsed.userinfo or parsed.port not in ALLOWED_PORTS:
        raise WebNoteError("공개된 웹 페이지만 가져올 수 있어요.")
    _require_public(parsed.host, parsed.port or (443 if parsed.scheme == "https" else 80))
    return parsed


def _check_peer(response: httpx.Response) -> None:
    """The address we actually connected to, in case DNS changed between check and connect."""
    stream = response.extensions.get("network_stream")
    address = stream.get_extra_info("server_addr") if stream is not None else None
    if address and not ipaddress.ip_address(address[0].split("%")[0]).is_global:
        raise WebNoteError("공개된 웹 페이지만 가져올 수 있어요.")


def _read_body(response: httpx.Response) -> str:
    chunks, size = [], 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > MAX_BYTES:
            raise WebNoteError("페이지가 너무 커서 가져올 수 없어요.")
        chunks.append(chunk)
    return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")


def fetch_page(url: str) -> tuple[bool, str]:
    """(is_html, body) of the page, following a few redirects, each re-checked."""
    with _make_client() as client:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            target = _validate(current)
            try:
                with client.stream("GET", target) as response:
                    _check_peer(response)
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise WebNoteError("페이지를 가져오지 못했어요.")
                        current = str(target.join(location))
                        continue
                    if response.status_code != 200:
                        raise WebNoteError(f"페이지를 가져오지 못했어요 (HTTP {response.status_code}).")
                    kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if kind not in ("text/html", "application/xhtml+xml", "text/plain"):
                        raise WebNoteError("웹 문서(HTML)나 텍스트 페이지만 가져올 수 있어요.")
                    return kind != "text/plain", _read_body(response)
            except httpx.TimeoutException as exc:
                raise WebNoteError("페이지가 응답하지 않아요. 잠시 후 다시 시도해주세요.") from exc
            except httpx.HTTPError as exc:
                raise WebNoteError("페이지에 연결하지 못했어요.") from exc
    raise WebNoteError("이동(리다이렉트)이 너무 많은 페이지예요.")


_SKIP = {"script", "style", "noscript", "svg", "iframe", "nav", "header", "footer", "aside", "template", "head"}
_BLOCKS = {
    "p", "div", "li", "br", "tr", "pre", "blockquote", "section", "article", "main", "ul", "ol", "table", "dd", "dt",
}
_HEADINGS = {f"h{n}": n for n in range(1, 7)}


class _Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.title = ""
        self._line: list[str] = []
        self._skip = 0
        self._in_title = False
        self._heading = 0
        self._item = False

    def _flush(self):
        text = re.sub(r"\s+", " ", "".join(self._line)).strip()
        self._line.clear()
        if not text:
            return
        if self._heading:
            text = f"{'#' * self._heading} {text}"
        elif self._item:
            text = f"- {text}"
        self.lines.append(text)

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in _SKIP:
            self._skip += 1
        elif not self._skip:
            self._flush()
            if tag in _HEADINGS:
                self._heading = _HEADINGS[tag]
            elif tag == "li":
                self._item = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in _SKIP:
            self._skip = max(0, self._skip - 1)
        elif not self._skip and (tag in _HEADINGS or tag in _BLOCKS):
            self._flush()
            if tag in _HEADINGS:
                self._heading = 0
            elif tag == "li":
                self._item = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self._line.append(data)

    def close(self):
        super().close()
        self._flush()


def page_to_markdown(html: str, fallback_title: str) -> tuple[str, str]:
    """(title, markdown body) with headings kept, so chunking can follow the page's structure."""
    extractor = _Extractor()
    extractor.feed(html)
    extractor.close()

    title = re.sub(r"\s+", " ", extractor.title).strip()
    if not title:
        first = next((line for line in extractor.lines if line.startswith("# ")), "")
        title = first[2:].strip()
    body = "\n".join(extractor.lines)
    if len(body) < MIN_BODY_CHARS:
        raise WebNoteError("본문을 찾지 못했어요. 로그인이 필요하거나 스크립트로 그려지는 페이지일 수 있어요.")
    return (title or fallback_title)[:80], body


def import_url(url: str) -> tuple[str, str]:
    """(title, markdown note text) for a public web page."""
    is_html, page = fetch_page(url)
    host = httpx.URL(url.strip()).host
    if is_html:
        title, body = page_to_markdown(page, fallback_title=host)
    else:
        title, body = host, page.strip()
        if len(body) < MIN_BODY_CHARS:
            raise WebNoteError("본문을 찾지 못했어요.")
    return title, f"# {title}\n\n출처: {url.strip()}\n\n{body}"
