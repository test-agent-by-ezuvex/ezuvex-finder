from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time
import random
import json
import urllib.parse

app = Flask(__name__)
CORS(app)

# ── Rotating User Agents ──
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

COUNTRY_MAP = {
    "US": {"domain": "amazon.com",    "flag": "🇺🇸"},
    "UK": {"domain": "amazon.co.uk",  "flag": "🇬🇧"},
    "CA": {"domain": "amazon.ca",     "flag": "🇨🇦"},
    "DE": {"domain": "amazon.de",     "flag": "🇩🇪"},
    "FR": {"domain": "amazon.fr",     "flag": "🇫🇷"},
    "IT": {"domain": "amazon.it",     "flag": "🇮🇹"},
    "ES": {"domain": "amazon.es",     "flag": "🇪🇸"},
    "JP": {"domain": "amazon.co.jp",  "flag": "🇯🇵"},
    "IN": {"domain": "amazon.in",     "flag": "🇮🇳"},
    "AU": {"domain": "amazon.com.au", "flag": "🇦🇺"},
    "AE": {"domain": "amazon.ae",     "flag": "🇦🇪"},
}


# ──────────────────────────────────────────────
# 1. SCRAPE AMAZON SEARCH → get brand names + ASINs
# ──────────────────────────────────────────────
def scrape_amazon_brands(niche, domain, count=20):
    """Search Amazon and extract real brand names from listings."""
    brands = []
    page = 1
    seen = set()

    while len(brands) < count and page <= 4:
        query = urllib.parse.quote_plus(niche)
        url = f"https://www.{domain}/s?k={query}&page={page}"
        try:
            session = requests.Session()
            session.headers.update(get_headers())
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select('[data-component-type="s-search-result"]')

            for item in items:
                if len(brands) >= count:
                    break

                # Brand name
                brand_el = item.select_one('.a-size-base-plus.a-color-base') or \
                           item.select_one('.s-line-clamp-1 span') or \
                           item.select_one('[data-cy="title-recipe-badge-container"] span')

                # ASIN
                asin = item.get("data-asin", "")

                # Rating
                rating_el = item.select_one('.a-icon-alt')
                rating = None
                if rating_el:
                    m = re.search(r'([\d.]+) out of', rating_el.text)
                    if m:
                        rating = float(m.group(1))

                # Review count
                review_el = item.select_one('[aria-label*="stars"] + span a span') or \
                            item.select_one('.a-size-base.s-underline-text')
                review_count = 0
                if review_el:
                    rc = re.sub(r'[^\d]', '', review_el.text)
                    review_count = int(rc) if rc else 0

                # Price
                price_el = item.select_one('.a-price .a-offscreen')
                price = None
                if price_el:
                    pm = re.search(r'[\d,.]+', price_el.text.replace(',', ''))
                    if pm:
                        try:
                            price = float(pm.group().replace(',', ''))
                        except:
                            price = None

                # Title to infer brand
                title_el = item.select_one('h2 a span') or item.select_one('.a-text-normal')
                title = title_el.text.strip() if title_el else ""

                # Extract brand from title (first 1-2 words usually)
                brand_name = None
                if brand_el:
                    brand_name = brand_el.text.strip()
                elif title:
                    words = title.split()
                    brand_name = words[0] if words else None

                if not brand_name or brand_name in seen or len(brand_name) < 2:
                    continue
                if any(x in brand_name.lower() for x in ['sponsored', 'amazon', 'result', 'overall']):
                    continue

                seen.add(brand_name)
                brands.append({
                    "brand": brand_name,
                    "topASIN": asin or None,
                    "rating": rating,
                    "reviewCount": review_count,
                    "title": title,
                    "price": price,
                    "domain": domain,
                })

            page += 1
            time.sleep(random.uniform(1.5, 3.0))

        except Exception as e:
            print(f"Amazon scrape error page {page}: {e}")
            break

    return brands


# ──────────────────────────────────────────────
# 2. FIND BRAND WEBSITE via Google/DDG
# ──────────────────────────────────────────────
def find_brand_website(brand_name):
    """Search DuckDuckGo for brand's official website."""
    try:
        query = urllib.parse.quote_plus(f"{brand_name} official website")
        url = f"https://html.duckduckgo.com/html/?q={query}"
        resp = requests.get(url, headers=get_headers(), timeout=12)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        results = soup.select('.result__url')
        skip = ['amazon.', 'facebook.', 'instagram.', 'twitter.', 'youtube.',
                'linkedin.', 'wikipedia.', 'reddit.', 'ebay.', 'walmart.',
                'etsy.', 'pinterest.', 'tiktok.', 'yelp.']

        for r in results[:5]:
            href = r.text.strip()
            if not href:
                continue
            if any(s in href.lower() for s in skip):
                continue
            if '.' in href and len(href) > 4:
                if not href.startswith('http'):
                    href = 'https://' + href
                return href

        return None
    except Exception as e:
        print(f"Website search error for {brand_name}: {e}")
        return None


# ──────────────────────────────────────────────
# 3. SCRAPE BRAND WEBSITE for contacts
# ──────────────────────────────────────────────
def scrape_brand_contacts(website_url):
    """Visit brand website and extract email, phone, social links."""
    result = {
        "email": None,
        "phone": None,
        "facebook": None,
        "instagram": None,
        "linkedin": None,
        "contactName": None,
    }

    if not website_url:
        return result

    pages_to_try = [
        website_url,
        website_url.rstrip('/') + '/contact',
        website_url.rstrip('/') + '/contact-us',
        website_url.rstrip('/') + '/about',
        website_url.rstrip('/') + '/about-us',
    ]

    combined_html = ""
    for page_url in pages_to_try[:2]:
        try:
            resp = requests.get(page_url, headers=get_headers(), timeout=12, allow_redirects=True)
            if resp.status_code == 200:
                combined_html += resp.text
            time.sleep(0.5)
        except:
            pass

    if not combined_html:
        return result

    soup = BeautifulSoup(combined_html, "html.parser")
    text = soup.get_text()
    html = combined_html

    # Email
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    skip_email = ['noreply', 'no-reply', 'mailer', 'example', 'test@', 'placeholder',
                  'sentry', 'wixpress', 'shopify', 'wordpress', 'squarespace', '.png', '.jpg']
    for e in emails:
        if not any(s in e.lower() for s in skip_email):
            result["email"] = e.lower()
            break

    # Phone
    phones = re.findall(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phones:
        result["phone"] = phones[0].strip()

    # Facebook
    fb = re.findall(r'https?://(?:www\.)?facebook\.com/[A-Za-z0-9._\-/]+', html)
    if fb:
        result["facebook"] = fb[0].split('?')[0]

    # Instagram
    ig = re.findall(r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9._]+/?', html)
    if ig:
        result["instagram"] = ig[0].split('?')[0]

    # LinkedIn
    li = re.findall(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9._\-]+/?', html)
    if li:
        result["linkedin"] = li[0].split('?')[0]

    return result


# ──────────────────────────────────────────────
# 4. ESTIMATE REVENUE (heuristic)
# ──────────────────────────────────────────────
def estimate_revenue(review_count, price):
    """Rough monthly revenue estimate based on reviews & price."""
    if not review_count or not price:
        return None
    # Rough: ~30 sales/month per 1000 reviews, times price
    monthly_sales = max(30, int(review_count * 0.03))
    return round(monthly_sales * (price or 25))


def priority_from_reviews(rc):
    if rc >= 2000:
        return "Hot"
    elif rc >= 500:
        return "Medium"
    return "Low"


def storefront_url(domain, brand, asin=None):
    enc = urllib.parse.quote_plus(brand)
    return f"https://www.{domain}/s?k={enc}&rh=p_4%3A{enc}"


# ──────────────────────────────────────────────
# MAIN ROUTE
# ──────────────────────────────────────────────
@app.route("/api/search", methods=["POST"])
def search():
    data = request.json or {}
    niche   = data.get("niche", "Home Decor")
    country = data.get("country", "US")
    count   = min(int(data.get("count", 10)), 30)

    country_info = COUNTRY_MAP.get(country, COUNTRY_MAP["US"])
    domain = country_info["domain"]

    results = []

    # Step 1: Get brands from Amazon
    brands = scrape_amazon_brands(niche, domain, count * 2)

    if not brands:
        return jsonify({"error": "Could not reach Amazon. Try again in a moment.", "leads": []}), 200

    # Step 2: For each brand, find website + contacts
    for b in brands:
        if len(results) >= count:
            break

        brand_name = b["brand"]

        # Find website
        website = find_brand_website(brand_name)
        time.sleep(random.uniform(0.5, 1.2))

        # Scrape contacts
        contacts = scrape_brand_contacts(website)

        # Build lead
        rev = estimate_revenue(b.get("reviewCount", 0), b.get("price"))
        ppc = round(rev * 0.15) if rev else None

        lead = {
            "_id": f"{brand_name.lower().replace(' ', '_')}_{random.randint(1000,9999)}",
            "brand": brand_name,
            "initials": ''.join(w[0].upper() for w in brand_name.split()[:2]),
            "niche": niche,
            "country": country,
            "domain": domain,
            "storefrontURL": storefront_url(domain, brand_name, b.get("topASIN")),
            "topASIN": b.get("topASIN") or None,
            "website": website,
            "email": contacts["email"],
            "phone": contacts["phone"],
            "facebook": contacts["facebook"],
            "instagram": contacts["instagram"],
            "linkedin": contacts["linkedin"],
            "contactName": contacts["contactName"],
            "rating": b.get("rating"),
            "reviewCount": b.get("reviewCount", 0),
            "monthlyRevenue": rev,
            "monthlySpend": ppc,
            "priority": priority_from_reviews(b.get("reviewCount", 0)),
            "painPoint": None,
            "recommendedServices": [],
            "dataSource": f"Amazon {domain} search + brand website scrape",
        }

        results.append(lead)

    return jsonify({"leads": results, "total": len(results)})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Amazon Lead Finder API running"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
