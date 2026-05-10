"""
URL allowlist + outbound text sanitizer for Companion responses.

Defense-in-depth layer that runs ON TOP of the prompts.py rule
"never invent or recall any other phone number or URL." The prompt is
layer 1. This is layer 2.

WHY THIS EXISTS
A prompt-injection attack could theoretically trick the model into
emitting a URL that does not belong in our resource registry — for
example, a URL crafted to exfiltrate context as query parameters, or
a typo/lookalike domain. The prompt rule prevents this in the
overwhelming majority of cases. This function catches the rest.

WHAT IT DOES
Scans outgoing assistant text for URLs. Any URL whose domain (or
subdomain) is not in ALLOWED_DOMAINS gets replaced with the
universal-fallback link. Every replacement is logged so we can
audit later.

WHEN IT RUNS
On the assembled final response, AFTER streaming completes, before
the response is persisted to the database. The user has already
seen the streamed tokens, so per-chunk filtering would protect them
better in real time. That is documented as a future enhancement
below. For the pilot, sanitizing the persisted record is the
realistic defense.

UPDATING THIS FILE
When prompts.py adds or removes a verified resource, update
ALLOWED_DOMAINS to match. Treat both files as a single contract.
"""

import logging
import re

logger = logging.getLogger(__name__)


# Allowlist of verified domains.
# MUST match the resource registry in apps/chat/prompts.py BASE_RULES.
# When you add a resource to prompts.py, add the domain here too.
# Lowercase. No protocol. No trailing slash. No www. (subdomains are
# matched automatically.)
ALLOWED_DOMAINS = frozenset({
    # Universal
    "findahelpline.com",
    "haveibeenpwned.com",

    # Finland — emergency / official
    "112.fi",
    "mieli.fi",
    "tukinet.net",
    "tukinet.fi",

    # Finland — youth / chat / Red Cross
    "sekasin247.fi",
    "sekasin.fi",
    "sekasingaming.fi",
    "punainenristi.fi",
    "redcross.fi",
    "nuortenlinkki.fi",
    "mielenterveystalo.fi",
    "lnk.fi",
    "zekki.fi",
    "ohjaamot.fi",
    "sos-lapsikyla.fi",
    "naisenvakivalta.fi",
    "riku.fi",
    "netari.fi",
    "peaasi.ee",
    "hearing-voices.org",

    # Estonia
    "112.ee",
    "sotsiaalkindlustusamet.ee",
    "palunabi.ee",
    "lasteabi.ee",

    # US
    "988lifeline.org",
    "samhsa.gov",
    "warmline.org",

    # Password managers named in prompts.py sensitive-info teaching
    "bitwarden.com",
    "keepassxc.org",
    "1password.com",

    # Companion's own production domain
    "getcompanionos.com",
})

# When a non-allowlisted URL is found, it is replaced with this.
# findahelpline.com is the universal fallback that always routes a
# user to a verified resource for their country.
SAFE_FALLBACK = "https://findahelpline.com"

# URL detector. Catches http(s)://, optional path, optional query,
# optional fragment. Stops at whitespace.
# Trailing punctuation that is unlikely to be part of a URL
# (period, comma, closing paren, semicolon) is excluded from the
# match so we do not strip the punctuation along with the URL.
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\)\]\}]+",
    flags=re.IGNORECASE,
)

# Matches the host portion of a URL after the scheme.
_HOST_PATTERN = re.compile(
    r"https?://([^/?#\s]+)",
    flags=re.IGNORECASE,
)


def _domain_from_url(url: str) -> str:
    """
    Extract the lowercased domain from a URL. Strips a leading 'www.'.
    Returns an empty string if the URL cannot be parsed.
    """
    match = _HOST_PATTERN.match(url)
    if not match:
        return ""
    domain = match.group(1).lower()
    if domain.startswith("www."):
        domain = domain[4:]
    # Strip port if present (e.g. example.com:8080 -> example.com)
    if ":" in domain:
        domain = domain.split(":", 1)[0]
    return domain


def _is_allowed(url: str) -> bool:
    """
    Return True if the URL's domain (or any of its parents) is in
    ALLOWED_DOMAINS. Subdomains of an allowed domain are allowed.

    Examples:
        https://mieli.fi/foo            -> allowed (mieli.fi)
        https://www.mieli.fi/foo        -> allowed (www stripped)
        https://en.mieli.fi/foo         -> allowed (subdomain of mieli.fi)
        https://mieli.fi.evil.com/foo   -> NOT allowed (different host)
        https://findahelpline.com       -> allowed
        https://attacker.com/?x=1       -> NOT allowed
    """
    domain = _domain_from_url(url)
    if not domain:
        return False
    if domain in ALLOWED_DOMAINS:
        return True
    # Allow any subdomain of an allowed domain.
    for allowed in ALLOWED_DOMAINS:
        if domain.endswith("." + allowed):
            return True
    return False


def sanitize_outgoing_text(text: str) -> str:
    """
    Strip any URLs not in ALLOWED_DOMAINS. Replace each with
    SAFE_FALLBACK. Log every replacement so they can be reviewed.

    Pure function. Deterministic. No side effects other than logging.
    Safe to call on empty / None text (returns input unchanged).
    """
    if not text:
        return text

    def _replace(match: "re.Match[str]") -> str:
        url = match.group(0)
        # Strip trailing punctuation that the regex may have grabbed.
        # We do not want to silently swallow surrounding punctuation
        # if the URL itself is allowed.
        trailing = ""
        while url and url[-1] in ".,;:!?":
            trailing = url[-1] + trailing
            url = url[:-1]
        if _is_allowed(url):
            return url + trailing
        logger.warning(
            "url_validator stripped non-allowlisted URL: %s",
            url,
        )
        return SAFE_FALLBACK + trailing

    return _URL_PATTERN.sub(_replace, text)


# ---------------------------------------------------------------
# FUTURE ENHANCEMENT (not implemented for pilot):
#
# Per-chunk sanitization during streaming. Currently the validator
# runs on the assembled final text after streaming completes, which
# means the user has already seen the streamed tokens on screen.
# The DB record is sanitized; the user's screen briefly showed the
# unsanitized version.
#
# To upgrade: buffer the streamed tokens until a complete URL can be
# parsed (or until whitespace settles the URL boundary), then yield
# the sanitized chunk. Adds latency and code complexity but provides
# real-time defense. Worth doing once pilot data shows whether any
# URLs actually need stripping.
# ---------------------------------------------------------------
