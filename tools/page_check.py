"""
Check that a ticker's research page is serving after a publish.

A publish only writes files. The page is rendered by roboinvestor-app from the brief and
from the filer's own statements, so a page can fail on something no file here shows: a
filing the page cannot render broke /research/tsn (2026-11-21) and nothing reported it
until an unrelated build went red two days later.

Three outcomes:
  200          the page is serving.
  404          not serving yet, and not a failure: the site reads the catalog through a
               cache of up to an hour, so a ticker new to the site appears after that.
  anything else, after retries: the check fails. The artifacts are published and stay
               published; the fault is in the page, not in the publish.

A page that rendered before keeps serving its last good render while a new one fails, so
this catches a page with no good render behind it, not every regression.

Usage:
    uv run python tools/page_check.py TSN [APD ...]
"""

import argparse
import time
import urllib.error
import urllib.request

RESEARCH_URL = "https://roboinvestor.ai/research/{ticker}"
ATTEMPTS = 3
WAIT_SECONDS = 10
TIMEOUT_SECONDS = 90  # a cold page fetches and parses the filing before it answers


def research_page_url(ticker):
  return RESEARCH_URL.format(ticker=ticker.lower())


def page_status(url):
  """The page's HTTP status, or the reason no response came back."""
  req = urllib.request.Request(url, headers={"User-Agent": "content-publish-check"})
  try:
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as res:
      return res.status
  except urllib.error.HTTPError as e:
    return e.code
  except (urllib.error.URLError, TimeoutError) as e:
    return str(getattr(e, "reason", e))


def check_research_page(ticker):
  """True when the page serves, False when it is not on the site yet; exits on a fault."""
  url = research_page_url(ticker)
  status = None
  for attempt in range(ATTEMPTS):
    if attempt:
      time.sleep(WAIT_SECONDS)
    status = page_status(url)
    if status == 200:
      print(f"  page OK: {url}")
      return True
    if status == 404:
      print(
        f"  page not serving yet (404): {url}\n"
        f"  The site picks a new ticker up within the hour; "
        f"check then with `just check-page {ticker}`."
      )
      return False
  raise SystemExit(
    f"{ticker}: published, but the page is failing ({status}): {url}\n"
    "The artifacts are live, so do not publish again. The fault is in how "
    "roboinvestor-app renders this page; report it."
  )


def main():
  ap = argparse.ArgumentParser(description="Check published research pages serve")
  ap.add_argument("tickers", nargs="+", help="Project name(s) / ticker(s)")
  args = ap.parse_args()
  for ticker in args.tickers:
    check_research_page(ticker)


if __name__ == "__main__":
  main()
