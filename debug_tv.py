import requests


def debug_tradingview(url):
    print(f"Testing URL: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, allow_redirects=True)
        print(f"Final URL after redirects: {resp.url}")
        print(f"Status Code: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")

        if "text/html" in resp.headers.get("Content-Type", ""):
            print("Response is HTML. Searching for image tags...")
            # Look for common image pattern in TV snapshots
            import re

            img_match = re.search(
                r'https://s3.tradingview.com/snapshots/[^"]+\.png', resp.text
            )
            if img_match:
                print(f"Found image URL in HTML: {img_match.group(0)}")
            else:
                print("Could not find image URL in HTML.")
                print(f"HTML Snippet: {resp.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_tradingview("https://www.tradingview.com/x/Ivpq79wn")
