# Raspberry Pi 5 8GB eBay watcher

Uses Python 3 and its standard library; no packages to install.
Default: checks eBay US every 15 minutes for fixed-price listings at $120 or less
including API-reported shipping, before sales tax. This is an editable budget,
not a claim about current market value.

## Setup

1. Obtain production application keys at https://developer.ebay.com/ .
   Your application must have production Browse API access; eBay may require
   additional account setup or approval. Sandbox keys do not search real listings.
2. Open PowerShell in this folder and set credentials for that terminal only:

```powershell
$env:EBAY_CLIENT_ID = 'YOUR_PRODUCTION_APP_ID'
$env:EBAY_CLIENT_SECRET = 'YOUR_PRODUCTION_CERT_ID'
python .\watch.py --max-total 120 --minutes 15 --zip 90210
```

Replace 90210 with your delivery ZIP. Do not share your secret in chat or commit it.
Use `--once` for one check or `--help` for options. Ctrl+C stops the watcher.

## Alerts and limitations

- Prints listing links and sounds a Windows alert on new matches or price drops.
- Saves alerts in `deals.jsonl`; `seen.json` prevents repeat alerts across restarts.
- Runs only while the computer is awake and the script is running. It is not
  installed as a background service or scheduled task.
- Skips unknown shipping, auctions, parts-only condition, and obvious accessory
  or broken-board titles. Conservative filters may also omit complete bundles.
- Title matching cannot prove RAM size, functionality, or authenticity. Inspect
  photos, variation selection, seller, final shipping and tax before purchasing.
- Includes used and refurbished boards. Scans at most the newest 1000 matching
  fixed-price search results per check. Does not buy or message sellers.
- Network/API errors trigger retries with backoff. Credentials are not logged.

API documentation: https://developer.ebay.com/api-docs/buy/browse/overview.html
