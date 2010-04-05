"""
This module defines one public method:
    parse(memo, approx_date=None)
The returned value is a dict containing the parsed details of the memo string,
in the following format: 
    {
        'channel': string, one of "POS", "ATM", "check", "fee", ....,
        'channel_details': {
            'check_no': string, if present
            'auth': string, if present
            'auth_date': "YYYY-MM-DD", if present
            'auth_time': "HH:MM", if present
        }
        'vendor': {
            'description': string,
            'city': string, if present
            'state': string, if present
            'zip': string, if present
            'phone': string, if present
        }
    }
"""
import os
import re
import csv
import datetime

# Utilities
CHAN_SEP = "(#\s+-\s+|\s+/\s+)"
TYPE_STUB = "^((?P<type>\w+)%s)?" % CHAN_SEP
DOLLAR_AMOUNT = "(?P<amount>-?\$[-\d\.]+)"

# Main transaction types
atm_re = re.compile(TYPE_STUB + \
    "ATM (?P<date>\d{4} \d{4}) (?P<auth>\d{6}) (?P<description>.+)$")
credit_card_re = re.compile(TYPE_STUB + \
    "(?P<date>\d\d-\d\d-\d\d) (?P<description>.+) auth# (?P<auth>\d+)$")
pos_re = re.compile(TYPE_STUB + 
    "POS (?P<date>\d{4} \d{4}) (?P<auth>\d{6}) (?P<description>.+)$")
check_re = re.compile("^SH DRAFT(#(\s+-\s+)?\s*(?P<checkno>\d+)?)?$")
deposit_re = re.compile("^DEPOSIT" + CHAN_SEP + "?\s*(?P<description>.*)$")
dividend_re = re.compile("^(DIVIDEND|Dividend|Savings)(#?$|" + CHAN_SEP + "(?P<description>.*)$)")
transfer_re = re.compile("^(TRANSFER|Transfer)($|\s*(?P<acct_descr>.*)" + \
        CHAN_SEP + "(?P<description>.+)$)")
fee_end = CHAN_SEP + "(?P<description>.*?)\s*" + DOLLAR_AMOUNT + "?$"
fee_re = re.compile("^(?P<type>FEE)" + fee_end)
rev_fee_re = re.compile("^(?P<type>REV FEE)" + fee_end)
other_re = re.compile(TYPE_STUB + "(?P<description>.*)")

# Sub filters for some transactions
phone_end_re = re.compile("^(?P<description>.*) (?P<phone>[-0-9\.]{7,15})$")
zip_end_re = re.compile("^(?P<description>.*) (?P<zip>\d{5})$")
clean_phone_re = re.compile("[^\d]")

def _bash_amount(amount):
    """ Sometimes the tx says "$-2.0-50". """
    amount = amount.replace("$", "")
    if amount[0] == "-":
        return -float(amount.replace("-", ""))
    else:
        return float(amount)

class ZipData(object):
    ZIP_CITY_DATA = os.path.join(os.path.dirname(__file__), "data", "zips.csv")

    def __init__(self):
        self.cities_by_state = {}
        self.cities_by_zip = {}
        with open(self.ZIP_CITY_DATA) as file:
            reader = csv.reader(file)
            for zip, city, state in reader:
                arr = self.cities_by_zip.get(zip, [])
                arr.append(city)
                self.cities_by_zip[zip] = arr

                arr = self.cities_by_state.get(state, [])
                arr.append(city)
                self.cities_by_state[state] = arr
ZIP = ZipData()

def parse_pos_date(date_time_str, target):
    """
    Parse a POS/ATM date string, which lacks a 'year'.  Get the year from the
    date in ``target``, which should be a date near the correct date.  This is
    done to correct for the boundaries near Jan 1.
    """
    date = datetime.datetime.strptime("%s %s" % (
            target.year,
            date_time_str),
        "%Y %m%d %H%M")
    # Handle the case where we guess the wrong year because we're near Jan 1.
    diff = date - target
    if abs(diff) > datetime.timedelta(180):
        if diff < datetime.timedelta(0):
            date = datetime.datedatetime(date.year + 1, date.month, date.day, 
                    date.hour, date.minute)
        else:
            date = datetime.datetime(date.year - 1, date.month, date.day,
                    date.hour, date.minute)
    return date

def parse_vendor(description):
    memo = description.strip()
    if not memo:
        return None

    vendor = {
        'description': "",
        'state': "",
        'city': "",
        'zip': "",
        'phone': "",
    }
    memo_guess, state_guess = memo[:-2].strip(), memo[-2:]
    cities = ZIP.cities_by_state.get(state_guess, None)
    if cities:
        # We have a state match.
        vendor['state'] = state_guess

        # Does the listing end with a phone number?
        match = phone_end_re.match(memo_guess)
        if match:
            vendor['description'] = match.group('description')
            vendor['phone'] = clean_phone_re.sub("",
                    match.group('phone')
            )
            return vendor

        # Does the listing end with a zip code?
        match = zip_end_re.match(memo_guess)
        if match:
            vendor['description'] = match.group('description')
            vendor['zip'] = match.group('zip')
            vendor['city'] = ZIP.cities_by_zip.get(vendor['zip'], [""])[0]
            return vendor

        # Otherwise, try to match city.
        vendor['description'], vendor['city'] = parse_city(cities, memo_guess)
        if vendor['city']:
            return vendor

    # Fall back
    vendor['description'] = memo
    return vendor

def parse_city(cities, memo):
    """ 
    Split off a (potentially abbreviated) city stub from the end of the
    memo string.  Assume: 
    1. The city will come at the end of the memo string.
    2. The city may contain deletions from the "real" city name, but not
       insertions -- hence, the represented city name will not be longer
       than the real city name.
    3. The city abbreviation will be preceded by a space or the beginning
       of the string.
    """
    words = memo.split(' ')
    best_score = 0
    best_city = None
    remainder = None
    for city in cities:
        pot_words = []
        run_length = -1 # initial space
        for word in reversed(words):
            if run_length + len(word) + 1 <= len(city):
                pot_words.insert(0, word)
                run_length += len(word) + 1 # add one for space
            else:
                break
        pot_city = (" ".join(pot_words)).upper()
        pot_city_pos = len(pot_city) - 1
        score = 0
        for i in range(len(city) - 1, -1, -1):
            if pot_city_pos < 0:
                score -= i
                break
            if city[i] == pot_city[pot_city_pos]:
                score += 1
                pot_city_pos -= 1
            else:
                score -=1
        if score > best_score:
            best_score = score
            best_city = city
            remainder = " ".join(words[:-len(pot_words)])

    if best_city and best_score > len(best_city) / 2:
        return remainder, best_city
    else:
        return memo, ""

def parse_memo(memo, approx_date):
    parsed = {'vendor': {
        'description': "",
        'city': "",
        'state': "",
        'zip': "",
        'phone': "",
        }}
    if not memo:
        parsed['channel'] = "unknown"
        return parsed

    # checks
    match = check_re.match(memo)
    if match:
        parsed['channel'] = "check"
        checkno = match.group('checkno') or ""
        parsed['channel_details'] = {
            'check_number': checkno
        }
        parsed['vendor']["description"] = "CHECK %s" % checkno
        return parsed

    # POS and ATM transactions
    for channel, regex in (
            ('pos', pos_re),
            ('atm', atm_re)):
        match = regex.match(memo)
        if match:
            parsed['channel'] = channel
            try:
                date = parse_pos_date(match.group('date'), approx_date)
                parsed['channel_details'] = {
                    'auth_date': date.strftime("%Y-%m-%d"),
                    'auth_time': date.strftime("%H:%M"),
                    'auth': str(match.group('auth'))
                }
                parsed['vendor'] = parse_vendor(match.group('description'))
                return parsed
            except ValueError:
                pass

    # credit card transactions
    match = credit_card_re.match(memo)
    if match:
        parsed['channel'] = "pos"
        try:
            parsed['channel_details'] = {
                'auth_date': datetime.datetime.strptime(
                    match.group('date'), "%m-%d-%y").strftime("%Y-%m-%d"),
                'auth': str(match.group('auth')),
            }
            parsed['vendor'] = parse_vendor(match.group('description'))
            return parsed
        except ValueError:
            pass

    # transfers
    match = transfer_re.match(memo)
    if match:
        parsed['channel'] = "transfer"
        if match.group('acct_descr'):
            parsed['channel_details'] = {
                'account_description': match.group('acct_descr')
            }
        parsed['vendor']['description'] = memo
        return parsed

    # deposits
    match = deposit_re.match(memo)
    if match:
        parsed['channel'] = "deposit"
        parsed['vendor']['description'] = match.group('description') or \
                "deposit"
        return parsed

    # dividends
    match = dividend_re.match(memo)
    if match:
        parsed['channel'] = "dividend"
        parsed['vendor']['description'] = match.group('description') or \
                "dividend"
        return parsed

    # fees and rev fees
    for regex in (rev_fee_re, fee_re):
        match = regex.match(memo)
        if match:
            parsed['channel'] = match.group("type").lower()
            if match.group("amount"):
                parsed['channel_details'] = {
                    'amount': _bash_amount(match.group("amount"))
                }
            parsed['vendor']['description'] = match.group("description")
            return parsed
            

    # everything else
    match = other_re.match(memo)
    if match and match.group('type'):
        type = match.group('type').lower()
        if type in ["fee"]:
            parsed['channel'] = type
            parsed['vendor']['description'] = \
                re.sub("\$[-\d\.]+", "", match.group('description')).strip(),
            return parsed

        elif type in ["withdraw", "transfer"]:
            parsed['channel'] = type
            if match.group('description'):
                parsed['vendor']['description'] = match.group('description')
            return parsed

    # fallback
    parsed['channel'] = "unknown"
    parsed['vendor']['description'] = memo
    return parsed

def parse(memo, date=None):
    """ Parse a memo string. """
    if not date:
        date = datetime.datetime.now()
    return parse_memo(memo.strip(), date)
