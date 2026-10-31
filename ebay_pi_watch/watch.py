"""Watch eBay's official Browse API for inexpensive Raspberry Pi 5 8GB boards.
Python standard library only. See README.md for credentials and usage.
"""
import argparse
import base64
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def request_json(url, headers, data=None):
    with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
        return json.load(response)


class Ebay:
    def __init__(self):
        self.token = None
        self.expires = 0

    def search(self, maximum, postal_code):
        if time.monotonic() >= self.expires:
            credentials = f"{os.environ['EBAY_CLIENT_ID']}:{os.environ['EBAY_CLIENT_SECRET']}"
            result = request_json(
                'https://api.ebay.com/identity/v1/oauth2/token',
                {'Authorization': 'Basic ' + base64.b64encode(credentials.encode()).decode(),
                 'Content-Type': 'application/x-www-form-urlencoded'},
                urlencode({'grant_type': 'client_credentials',
                           'scope': 'https://api.ebay.com/oauth/api_scope'}).encode())
            self.token = result['access_token']
            self.expires = time.monotonic() + max(1, int(result['expires_in']) - 60)
        headers = {'Authorization': 'Bearer ' + self.token,
                   'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'}
        if postal_code:
            headers['X-EBAY-C-ENDUSERCTX'] = 'contextualLocation=' + urlencode(
                {'country': 'US', 'zip': postal_code}).replace('&', ',')
        items = []
        # Bounded pagination; no unbounded crawling.
        for offset in range(0, 1000, 200):
            params = {'q': 'raspberry pi 5 8gb', 'limit': 200, 'offset': offset,
                      'sort': 'newlyListed',
                      'filter': f'buyingOptions:{{FIXED_PRICE}},price:[..{maximum}],priceCurrency:USD,deliveryCountry:US'}
            try:
                result = request_json('https://api.ebay.com/buy/browse/v1/item_summary/search?' + urlencode(params), headers)
            except HTTPError as error:
                if error.code == 401:
                    self.expires = 0
                raise
            items.extend(result.get('itemSummaries', []))
            if not result.get('next'):
                break
        else:
            print('Warning: search capped at 1000 results; some listings may be omitted.')
        return items


def candidate(item, maximum):
    title = item.get('title', '')
    if not re.search(r'raspberry\s*pi\s*5\b', title, re.I):
        return None
    if not re.search(r'\b8\s*g(?:b|ig(?:abyte)?s?)\b', title, re.I):
        return None
    # Conservative title filtering. Human review is still required, especially variations.
    if re.search(r'\b(for|case|cooler|heatsink|fan|broken|faulty|repair|defective|untested|wanted|empty)\b', title, re.I):
        return None
    if item.get('conditionId') == '7000':
        return None
    if 'FIXED_PRICE' not in item.get('buyingOptions', []):
        return None
    try:
        price = item['price']
        if price['currency'] != 'USD':
            return None
        shipping = [Decimal(option['shippingCost']['value'])
                    for option in item.get('shippingOptions', [])
                    if option.get('shippingCost', {}).get('currency') == 'USD']
        if not shipping:
            return None  # Unknown shipping is not assumed to be free.
        total = Decimal(price['value']) + min(shipping)
        if total < 0 or total > maximum:
            return None
        return total
    except (KeyError, InvalidOperation, TypeError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-total', type=Decimal, default=Decimal('120'), help='USD including listed shipping, before tax (default: 120)')
    parser.add_argument('--minutes', type=float, default=15, help='Check interval; minimum 5 minutes')
    parser.add_argument('--zip', dest='postal_code', default='', help='US delivery ZIP for shipping estimates')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if not args.max_total.is_finite() or args.max_total <= 0 or args.minutes < 5:
        parser.error('Use a positive finite price and an interval of at least 5 minutes.')
    if args.postal_code and not re.fullmatch(r'\d{5}', args.postal_code):
        parser.error('--zip must be a five-digit US ZIP code.')
    if not all(os.environ.get(key) for key in ('EBAY_CLIENT_ID', 'EBAY_CLIENT_SECRET')):
        parser.exit(2, 'Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET to your eBay production API credentials. See README.md.\n')
    state_path = ROOT / 'seen.json'
    seen = json.loads(state_path.read_text()) if state_path.exists() else {}
    client = Ebay()
    failures = 0
    print(f'Watching Pi 5 8GB listings at <= ${args.max_total} shipped, before tax. Ctrl+C stops.\n', flush=True)
    while True:
        try:
            items = client.search(args.max_total, args.postal_code)
            count = 0
            for item in items:
                total = candidate(item, args.max_total)
                if total is None:
                    continue
                item_id = item['itemId']
                previous = seen.get(item_id)
                if previous is not None and total >= Decimal(previous):
                    continue
                alert = {'time': datetime.now().astimezone().isoformat(),
                         'title': item['title'], 'total_before_tax': str(total),
                         'condition': item.get('condition', 'Unknown'),
                         'url': item.get('itemWebUrl', '')}
                with (ROOT / 'deals.jsonl').open('a', encoding='utf-8') as log:
                    log.write(json.dumps(alert) + '\n')
                print(f"\nDEAL: ${total} shipped before tax | {alert['title']}\n{alert['condition']}\n{alert['url']}\n", flush=True)
                print('\a', end='', flush=True)
                if os.name == 'nt':
                    import winsound
                    winsound.MessageBeep()
                seen[item_id] = str(total)
                count += 1
            temp = state_path.with_suffix('.tmp')
            temp.write_text(json.dumps(seen, indent=2), encoding='utf-8')
            temp.replace(state_path)
            failures = 0
            print(f'{datetime.now():%H:%M:%S}: checked {len(items)} listings; {count} new deals/price drops.', flush=True)
        except HTTPError as error:
            failures += 1
            print(f'eBay HTTP {error.code}. For 401/403, verify production credentials and Browse API access. For 429, backing off.', flush=True)
            if args.once:
                return 1
        except (URLError, TimeoutError, OSError, ValueError) as error:
            failures += 1
            print(f'Check failed ({type(error).__name__}); will retry.', flush=True)
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(min(args.minutes * 60 * (2 ** min(failures, 4)), 14400))


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nWatcher stopped.')
