# 🔍 Amazon Lead Finder — By Ezuvex

Real Amazon seller lead collection tool. No API key needed. Scrapes live Amazon listings and brand websites.

---

## 📁 Project Structure

```
amazon-lead-finder/
├── api/
│   └── index.py        ← Python Flask backend (scraping engine)
├── public/
│   └── index.html      ← Frontend UI
├── requirements.txt    ← Python dependencies
├── vercel.json         ← Vercel deployment config
└── README.md
```

---

## 🚀 Deploy to Vercel (Free)

### Step 1 — GitHub এ upload করুন
1. GitHub.com এ যান → New Repository → `amazon-lead-finder`
2. এই সব ফাইল upload করুন (structure maintain করুন)

### Step 2 — Vercel এ deploy করুন
1. [vercel.com](https://vercel.com) এ যান
2. "Add New Project" → GitHub repo select করুন
3. Framework: **Other**
4. Deploy করুন — ব্যস!

### Step 3 — Use করুন
- Vercel দেওয়া URL এ যান
- Category, Country, Lead count select করুন
- "Find Amazon Sellers" click করুন

---

## 💻 Local এ run করতে চাইলে

```bash
# Install dependencies
pip install -r requirements.txt

# Run backend
python api/index.py

# Open public/index.html in browser
```

---

## ⚙️ How it works

1. **Amazon Search** — আপনার niche + country দিয়ে Amazon search করে real brands খুঁজে
2. **Brand Website** — DuckDuckGo দিয়ে প্রতিটা brand এর official website খুঁজে
3. **Contact Scrape** — Website এর contact/about page থেকে email, phone, social links extract করে
4. **Real Data Only** — যদি কোনো info না পাওয়া যায়, null দেখায় — কখনো fake data দেয় না

---

## ✅ Features

- 🔴 No API key needed
- 🌍 11টি Amazon marketplace support (US, UK, CA, DE, FR, IT, ES, JP, IN, AU, AE)
- 📧 Real email extraction from brand websites
- 📱 Facebook, Instagram, LinkedIn links
- 💾 Save leads locally
- 📊 Export to CSV / Google Sheets
- 🔄 Estimated monthly revenue & PPC spend
