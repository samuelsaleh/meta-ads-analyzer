# Meta Ad Library API - Application Template

## How to Apply

1. Go to: https://www.facebook.com/ads/library/api
2. Click **"Get Started"** or **"Request Access"**
3. Use the information below to fill out your application

---

## Application Template

### 1. Organization Information

**Organization Name:**
> [Your company/organization name]

**Organization Type:**
> - [ ] Academic/Research Institution
> - [ ] News Organization  
> - [x] Business/Company
> - [ ] Non-Profit/NGO
> - [ ] Government Agency

**Website:**
> [Your website URL]

**Country:**
> [Your country]

---

### 2. Purpose & Use Case

**Why do you need access to the Ad Library API?**

> We are building an internal competitive intelligence tool to analyze advertising strategies of brands in our industry. The tool will help us:
>
> 1. **Competitive Analysis**: Understand how competitors position their products and messaging in paid social advertising
> 2. **Market Research**: Identify trends in ad creative, messaging strategies, and campaign timing within our industry
> 3. **Strategic Planning**: Inform our own marketing strategy based on market landscape analysis
>
> We will use the Ad Library API to programmatically retrieve public ad data for specific brands, analyze messaging patterns, creative formats, and campaign timing. This replaces manual searches on the Ad Library website, improving efficiency and enabling systematic analysis.

---

### 3. Data Usage

**How will you use the data retrieved from the API?**

> The data will be used exclusively for:
>
> - **Internal business analysis** - generating reports for our marketing team
> - **Competitive benchmarking** - comparing ad strategies across brands
> - **Trend identification** - tracking messaging and creative evolution over time
>
> We will NOT:
> - Resell or redistribute the raw data
> - Use data for political purposes
> - Share individual ad data publicly without Meta's permission
> - Use data to target or identify individuals

---

### 4. Data Storage & Security

**How will you store and protect the data?**

> - Data will be stored on **secure, encrypted servers** (e.g., AWS with encryption at rest)
> - Access will be **limited to authorized employees** only
> - We will implement **role-based access controls**
> - Data will be **retained only as long as necessary** for analysis (max 12 months)
> - We will comply with **GDPR and applicable privacy regulations**
> - Regular **security audits** will be conducted

---

### 5. Technical Implementation

**How will you access the API?**

> - **Programming Language**: Python
> - **Framework**: FastAPI backend
> - **Authentication**: OAuth 2.0 with secure token storage
> - **Rate Limiting**: We will respect API rate limits and implement exponential backoff
> - **Error Handling**: Robust error handling to prevent excessive retry requests

---

### 6. Team Information

**Who will have access to the API?**

> - **Primary Contact**: [Your Name] - [Your Title]
> - **Technical Lead**: [Name] - Developer
> - **Team Size**: [X] people will have access
>
> All team members have been trained on data privacy and responsible use.

---

### 7. Expected Usage

**Estimated API usage:**

> - **Queries per day**: ~100-500 searches
> - **Brands monitored**: 50-100 brands
> - **Geographic focus**: [Your target markets, e.g., US, EU, UK]
> - **Industry focus**: [Your industry, e.g., Fashion, Tech, E-commerce]

---

## Tips for Approval

1. **Be specific** - Vague applications get rejected
2. **Be honest** - Don't claim to be a researcher if you're a business
3. **Show legitimacy** - Have a real website, business registration
4. **Explain the "why"** - Why API vs. manual searches?
5. **Address privacy** - Show you understand data responsibility
6. **Keep it professional** - Proper grammar, clear formatting

---

## After Approval

Once approved, you'll receive:
- **Access Token** - for API authentication
- **App ID** - your unique application identifier
- **Documentation** - detailed API reference

### Sample API Call

```python
import requests

ACCESS_TOKEN = "your_access_token"
AD_LIBRARY_API = "https://graph.facebook.com/v18.0/ads_archive"

params = {
    "access_token": ACCESS_TOKEN,
    "search_terms": "Nike",
    "ad_reached_countries": "US",
    "ad_active_status": "ACTIVE",
    "fields": "id,ad_creative_body,ad_creative_link_title,ad_delivery_start_time,page_name,spend,impressions",
    "limit": 100
}

response = requests.get(AD_LIBRARY_API, params=params)
data = response.json()

for ad in data.get("data", []):
    print(f"Brand: {ad.get('page_name')}")
    print(f"Text: {ad.get('ad_creative_body')}")
    print(f"Started: {ad.get('ad_delivery_start_time')}")
    print("---")
```

---

## Integration with Our Tool

Once you have API access, I can update the extractor to use the API instead of browser scraping:

**Benefits:**
- ✅ 100% reliable (no missed ads)
- ✅ Much faster (~5 seconds vs 2 minutes)
- ✅ All ads retrieved (not limited by scrolling)
- ✅ More data fields available
- ✅ No browser automation needed

Let me know when you get approved and I'll integrate it!
