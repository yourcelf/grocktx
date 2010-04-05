"""
This module scrapes transaction data from aggregators such as http://mint.com
and http://wesabe.com, so that you can use this data in your applications.  It
parses the transactions into a common format, but also preserves the original
data.

The module defines one public method:

    get_transactions(provider, username, password)

The method returns a list of dicts which contain parsed details of bank
transactions available from the given provider (e.g. mint or wesabe).

If this module is invoked from the command line, use the form:
    $ scraper.py <provider> <username> <password>
JSON containing the transactions will be returned to STDOUT.

The transaction dicts or JSON returned have the following form:
{
    'unique_id': alphanumeric string that is unique for this transaction.  May
                 not be identical across providers, but will be identical within 
                 a provider.
    'channel': string,
    'channel_details': {
        'check_number': present if channel is a check
        'auth': present if channel is POS or ATM
        'auth_date': YYYY-MM-DD, present if available
        'auth_time': HH:MM, present if available
    },
    'data_source': string, one of "wesabe", "mint", ...,
    'amount': float, debits negative, credits positive
    'date': YYYY-MM-DD,
    'vendor': {
        'description': parsed remainder of memo string, or none (as in a check)
        'city': city if available, or none
        'state': state if available, or none
        'zip': zip if available, or none
        'phone': phone if available, or none
    },
    'raw': {
        // raw fields from provider (e.g. wesabe, mint), values vary by
        // provider.  Currently:
        // mint values:
        date: YYYY-MM-DD
        description: string
        original_description: string
        amount: float
        transaction_type: string
        category: string
        account_name: string
        labels: string
        notes: string

        // wesabe values
        guid: string
        account_id: integer
        date: YYYY-MM-DD
        original_date: YYYY-MM-DD
        amount: float
        display_name: string
        check_number: integer
        raw_name: string
        raw_txntype: string
        memo: string
        transfer_guid: string
        merchant_id: integer
        merchant_name: string
        tags: string

    }
}
"""
import re
import sys
import csv
import json
import base64
import hashlib
import StringIO
import urllib2, urllib
import datetime
from htmlentitydefs import name2codepoint

import pycurl
from BeautifulSoup import BeautifulSoup

import parser

class MintScraper(object):
    base_url = "https://www.mint.com"
    login_url = "https://wwws.mint.com/login.event"
    login_post_url = "https://wwws.mint.com/loginUserSubmit.xevent"
    transactions_url = "https://wwws.mint.com/transaction.event"
    csv_url = "https://wwws.mint.com/transactionDownload.event?"
    user_agent = "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)"

    def __init__(self):
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        self.opener.addheaders = [('User-Agent', self.user_agent)]
        urllib2.install_opener(self.opener)

    def parse(self, csv_stub):
        """
        Parse one row of mint.com's CSV dump format. ``csv_stub`` should be a
        CSV string.
        """
        reader = csv.reader([csv_stub], delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)
        row = reader.next()

        tx = {'raw': {}}
        tx_date = datetime.datetime.strptime(row[0], "%m/%d/%Y")
        # raw values
        tx['raw']['date'] = tx_date.strftime("%Y-%m-%d")
        tx['raw']['description'] = row[1]
        tx['raw']['original_description'] = row[2]
        tx['raw']['amount'] = float(row[3])
        tx['raw']['transaction_type'] = row[4]
        tx['raw']['category'] = row[5]
        tx['raw']['account_name'] = row[6]
        tx['raw']['labels'] = row[7]
        tx['raw']['notes'] = row[8]

        # parsed values
        tx['unique_id'] = hashlib.sha1(csv_stub).hexdigest()
        tx['data_source'] = 'mint'
        tx['date'] = tx['raw']['date']
        if tx['raw']['transaction_type'] == "credit":
            tx['amount'] = tx['raw']['amount'] 
        else:
            tx['amount'] = -tx['raw']['amount']
        tx.update(parser.parse(tx['raw']['original_description'], tx_date))
        return tx

    def _build_request(self, url, referer=None):
        req = urllib2.Request(url)
        if referer:
            req.add_header('Referer', referer)
        return req

    def get_transactions(self, username, password):
        req = self._build_request(self.login_url)
        page = self.opener.open(req).read()
        soup = BeautifulSoup(page)
        form = soup.find(attrs={'id': "form-login"})
        inputs = form.findAll('input')
        data = {}
        for input in inputs:
            if input.has_key('name'):
                data[input['name']] = input['value']
        data['username'] = username
        data['password'] = password

        params = urllib.urlencode(data)
        f = self.opener.open(self.login_post_url, params)
        page = f.read()

        txs = self.opener.open(self.csv_url)
        parsed = []
        for line in txs.readlines()[1:]:
            parsed.append(self.parse(line))
        return parsed

class WesabeScraper(object):
    tx_re = re.compile("<txaction>((?:.(?!</txaction>))*.)</txaction>", re.DOTALL)
    merchant_re = re.compile("<merchant>([^<]*)</merchant>", re.DOTALL)
    tags_re = re.compile("<tags>([^<]*)</tags>", re.DOTALL)
    name_re = re.compile("<name>([^<]*)</name>", re.DOTALL)
    transfer_re = re.compile("<transfer>\s*<guid>\s*([^<]*)\s*</guid>\s*</transfer>")
    entity_re = re.compile(r'&(#?)(x?)(\w+);')

    def _re_xml_parse(self, field_attr_func_list, dictobj, xml_stub):
        """ Simple regex xml parsing.  Because it's easier than DOM. """
        for field, attr, func in field_attr_func_list:
            match = re.search("<%(field)s(?:\s+[^>]*)?>([^<]*)</%(field)s>" % \
                    {'field': field}, 
                xml_stub, re.DOTALL)
            if match:
                if func:
                    dictobj[attr] = func(match.group(1))
                else:
                    dictobj[attr] = match.group(1)

    def _bash_amount(self, amount):
        amount = amount.replace("$", "")
        if amount.find("-") != -1:
            return -float(amount.replace("-", ""))
        else:
            return float(amount)

    def parse(self, xml_stub):
        """ 
        Parse one transaction from Wesabe's XML transaction export format.
        ``xml_stub`` should be a string containing <txaction>...</txaction>.
        """
        tx = {'raw': {}}

        # raw fields
        self._re_xml_parse((
                ('guid', 'guid', None), 
                ('account-id', 'account_id', lambda i: int(i)),
                ('date', 'date', 
                    lambda x: datetime.datetime.strptime(x, "%Y-%m-%d")),
                ('original-date', 'original_date', 
                    lambda x: datetime.datetime.strptime(x, "%Y-%m-%d")),
                ('amount', 'amount', lambda f: float(f)),
                ('display-name', 'display_name', self._decode_htmlentities),
                ('raw-name', 'raw_name', None),
                ('raw-txntype', 'raw_txntype', None),
                ('memo', 'memo', self._decode_htmlentities),
                ('check-number', 'check_number', lambda i: int(i)),
            ), tx['raw'], xml_stub)
        tx_date = tx['raw']['date']
        tx['raw']['date'] = tx['raw']['date'].strftime("%Y-%m-%d")
        tx['raw']['original_date'] = tx['raw']['original_date'].strftime("%Y-%m-%d")

        match = self.merchant_re.search(xml_stub)
        if match:
            self._re_xml_parse((
                    ('id', 'merchant_id', None),
                    ('name', 'merchant_name', None)
                ), tx['raw'], match.group(1))
        match = self.tags_re.search(xml_stub)
        if match:
            tags = self.name_re.findall(match.group(1))
            tx['raw']['tags'] = ",".join(tags)

        # Parsed values
        tx['unique_id'] = tx['raw']['guid']
        tx['data_source'] = "wesabe"
        tx['date'] = tx['raw']['date']
        tx['amount'] = tx['raw']['amount']
        if tx['raw'].has_key('check_number'):
            memo = "SH DRAFT# %s" % tx['raw']['check_number']
        elif tx['raw'].has_key('memo'):
            memo = "%s /  %s" % (tx['raw']['raw_name'], 
                    tx['raw']['memo'])
        else:
            memo = tx['raw'].get('raw_name', tx['raw']['display_name'])
        # set channel, channel_details, and vendor
        tx.update(parser.parse(memo, tx_date))
        return tx

    def get_transactions(self, username, password):
        credentials = base64.encodestring('%s:%s' % (username, password))[:-1]
        c = pycurl.Curl()
        c.setopt(pycurl.URL, "https://www.wesabe.com/transactions.xml")
        c.setopt(pycurl.HTTPHEADER, ["Accept: application/xml",
                                     "User-Agent: GrockTxServer/0.1",
                                     "Authorization: Basic %s" % credentials])
        s = StringIO.StringIO()
        c.setopt(pycurl.WRITEFUNCTION, s.write)
        c.perform()
        response = s.getvalue()
        c.close()

        parsed = []
        tx_xml = self.tx_re.findall(response)
        for xml in tx_xml:
            parsed.append(self.parse(xml))
        return parsed

    @classmethod
    def _decode_htmlentities(cls, string):
        return cls.entity_re.subn(cls._substitute_entity, string)[0]

    @classmethod
    def _substitute_entity(cls, match):
        """ Adapted from http://snippets.dzone.com/posts/show/4569 """
        ent = match.group(3)
        if match.group(1) == '#':
            if match.group(2) == '':
                return unichr(int(ent))
            elif match.group(2) == 'x':
                return unichr(int('0x' + ent, 16))
        else:
            cp = name2codepoint.get(ent)
            if cp:
                return unichr(cp)
            else:
                return match.group()

def get_transactions(provider, username, password):
    if provider == "wesabe":
        return WesabeScraper().get_transactions(username, password)
    elif provider == "mint":
        return MintScraper().get_transactions(username, password)
    else:
        sys.stderr.write("Provider %s not supported" % provider)
        return []

if __name__ == "__main__":
    try:
        provider, username, password = sys.argv[1:4]
        results = get_transactions(provider, username, password)
        print json.dumps(results, indent=4)
    except ValueError:
        sys.stderr.write(
            "Usage: %s <provider> <username> <password>" % __file__)
        sys.exit(1)
