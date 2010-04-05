import unittest
import getpass
import json
import pprint

import parser, scraper

p = parser.parse

examples = {
    'atm': [
        # Standard ATM description
        ['WITHDRAW#  - ATM 1125 1456 510941 BOSTON PRIVATE BK & TR CAMBRIDGE MA',
            {'channel': 'atm',
             'channel_details': {'auth': '510941',
                                 'auth_date': '2009-11-25',
                                 'auth_time': '14:56'},
             'vendor': {'city': 'CAMBRIDGE',
                        'description': 'BOSTON PRIVATE BK & TR',
                        'phone': '',
                        'state': 'MA',
                        'zip': ''}}],
        # Slash format
        ['WITHDRAW /  ATM 0302 1404 205937 MIT FEDERAL CREDIT UNI CAMBRIDGE MA',
            {'channel': 'atm',
             'channel_details': {'auth': '205937',
                                 'auth_date': '2010-03-02',
                                 'auth_time': '14:04'},
             'vendor': {'city': 'CAMBRIDGE',
                        'description': 'MIT FEDERAL CREDIT UNI',
                        'phone': '',
                        'state': 'MA',
                        'zip': ''}}]],
    'check': [
        ['SH DRAFT# 1121',
            {'channel': 'check',
             'channel_details': {'check_number': '1121'},
             'vendor': {'city': '',
                        'description': 'CHECK 1121',
                        'phone': '',
                        'state': '',
                        'zip': ''}}]],
    'dividend': [
        ['DIVIDEND#',
            {'channel': 'dividend',
             'vendor': {'city': '',
                        'description': 'dividend',
                        'phone': '',
                        'state': '',
                        'zip': ''}}],
     ],
    'deposit': [
        ['DEPOSIT#  - MASS. INST. OF TPAYROLL',
            {'channel': 'deposit',
              'vendor': {'city': '',
                         'description': 'MASS. INST. OF TPAYROLL',
                         'phone': '',
                         'state': '',
                         'zip': ''}}],
        ['DEPOSIT',
            {'channel': 'deposit',
             'vendor': {'city': '',
                        'description': 'deposit',
                        'phone': '',
                        'state': '',
                        'zip': ''}}]
     ],
    'fee': [
        ['FEE / INTERNATIONAL TRANSACTION PROCESSING FEE $0.63',
            {'channel': 'fee',
             'channel_details': {
                 'amount': 0.63,
             },
             'vendor': {'city': '',
                        'description': 'INTERNATIONAL TRANSACTION PROCESSING FEE',
                        'phone': '',
                        'state': '',
                        'zip': ''}}],

        
        ['FEE / CURRENCY CONVERSION FEE $0.13',
            {'channel': 'fee',
             'channel_details': {
                 'amount': 0.13,
             },
             'vendor': {'city': '',
                        'description': 'CURRENCY CONVERSION FEE',
                        'phone': '',
                        'state': '',
                        'zip': ''}}],
     ],
     'pos': [
        # Standard credit card string
        ['PURCHASE#  - 11-25-09 SAVENORS MARKET BOSTON MA auth# 60618',
            {'channel': 'pos',
             'channel_details': {'auth': '60618', 'auth_date': '2009-11-25'},
             'vendor': {'city': 'BOSTON',
                        'description': 'SAVENORS MARKET',
                        'phone': '',
                        'state': 'MA',
                        'zip': ''}}],
        # slash format
        ['PURCHASE /  03-21-10 TIVOLI 258 00002QPS UNIVERSITYCTYMO auth# 70968',
            {'channel': 'pos',
             'channel_details': {'auth': '70968', 'auth_date': '2010-03-21'},
             'vendor': {'city': 'UNIVERSITY CITY',
                        'description': 'TIVOLI 258 00002QPS',
                        'phone': '',
                        'state': 'MO',
                        'zip': ''}}],
        # Standard POS string
        ['WITHDRAW#  - POS 1128 1756 531470 HARVEST COOP CAMBRIDGE MA',
            {'channel': 'pos',
             'channel_details': {'auth': '531470',
                               'auth_date': '2009-11-28',
                               'auth_time': '17:56'},
             'vendor': {'city': 'CAMBRIDGE',
                        'description': 'HARVEST COOP',
                        'phone': '',
                        'state': 'MA',
                        'zip': ''}}],
        # Funny city abbreviation
        ['PURCHASE#  - 11-24-09 CLOVER JAMAICA PLAINMA auth# 79129',
            {'channel': 'pos',
             'channel_details': {'auth': '79129', 'auth_date': '2009-11-24'},
             'vendor': {'city': 'JAMAICA PLAIN',
                        'description': 'CLOVER',
                        'phone': '',
                        'state': 'MA',
                        'zip': ''}}],
        # extra weird numbers in description
        ['WITHDRAW#  - POS 1107 1439 378279 SOU THE HOME DEPOT 332 BOSTON MA',
            {'channel': 'pos',
             'channel_details': {'auth': '378279',
                                 'auth_date': '2009-11-07',
                                 'auth_time': '14:39'},
             'vendor': {'city': 'BOSTON',
                        'description': 'SOU THE HOME DEPOT 332',
                        'phone': '',
                        'state': 'MA',
                        'zip': ''}}],
        # hash character in description
        ['WITHDRAW#  - POS 1107 1352 377931 DADDY.S JUNKY MUSIC #6 BOSTON MA',
            {'channel': 'pos',
             'channel_details': {'auth': '377931',
                                 'auth_date': '2009-11-07',
                                 'auth_time': '13:52'},
             'vendor': {'city': 'BOSTON',
                        'description': 'DADDY.S JUNKY MUSIC #6',
                        'phone': '',
                        'state': 'MA',
                        'zip': ''}}],
        # Phone number instead of city
        ['PURCHASE#  - 10-20-09 PAYPAL *NFSN INC 4029357733 CA auth# 21570',
            {'channel': 'pos',
             'channel_details': {'auth': '21570', 'auth_date': '2009-10-20'},
             'vendor': {'city': '',
                        'description': 'PAYPAL *NFSN INC',
                        'phone': '4029357733',
                        'state': 'CA',
                        'zip': ''}}],
        # Another phone number format
        ['PURCHASE#  - 09-19-09 CARBON FUND.ORG 240-293-2700 MD auth# 31933',
            {'channel': 'pos',
             'channel_details': {'auth': '31933', 'auth_date': '2009-09-19'},
             'vendor': {'city': '',
                        'description': 'CARBON FUND.ORG',
                        'phone': '2402932700',
                        'state': 'MD',
                        'zip': ''}}],
        # ZIP code instead of city
        ['WITHDRAW#  - POS 1204 1658 576635 BROADWAY BICYCLE SCHOO 02139 MA',
            {'channel': 'pos',
             'channel_details': {'auth': '576635',
                                 'auth_date': '2009-12-04',
                                 'auth_time': '16:58'},
             'vendor': {'city': 'CAMBRIDGE',
                        'description': 'BROADWAY BICYCLE SCHOO',
                        'phone': '',
                        'state': 'MA',
                        'zip': '02139'}}],
        ],
    'rev fee': [
        ['REV FEE#  - ATM SURCHARGE FEE REIMBURSEMENT $-3.00',
            {'channel': 'rev fee',
             'channel_details': {'amount': -3.00},       
               'vendor': {'city': '',
                          'description': 'ATM SURCHARGE FEE REIMBURSEMENT',
                          'phone': '',
                          'state': '',
                          'zip': ''}}],
    ],
     'withdraw': [
        ['WITHDRAW#  - ebill epayment MIT TUTION091009',
            {'channel': 'withdraw',
              'vendor': {'city': '',
                         'description': 'ebill epayment MIT TUTION091009',
                         'phone': '',
                         'state': '',
                         'zip': ''}}],
     ],
     'unknoown': [
        ['fiddlesticks',
            {'channel': 'unknown',
             'vendor': {'city': '',
                        'description': 'fiddlesticks',
                        'phone': '',
                        'state': '',
                        'zip': ''}}],
     ],
}


class TestParser(unittest.TestCase):
    def test_cc_strings(self):
        for channel, tests in sorted(examples.iteritems()):
            for memo, goal in tests:
                actual = parser.parse(memo)
                self.assertEqual(actual, goal, 
                    "'%s': '%s'\nGOT: %s\nWANTED: %s" % (
                        channel, memo, actual, goal
                    )
                )

class TestScraper(unittest.TestCase):
    def setUp(self):
        # Hardcode values for usernames and passwords here to avoid prompts.
        self.credentials = {
            "wesabe": {
                "username": None,
                "password": None,
            },
            "mint": {
                "username": None,
                "password": None,
            }
        }
        for provider, creds in self.credentials.iteritems():
            if not (creds['username'] and creds['password']):
                print "Please provide login details for %s.  You can" \
                      " hard-code these in the test file to avoid these" \
                      " prompts." % provider

                if not creds['username']:
                    creds['username'] = raw_input("Username: ")
                if not creds['password']:
                    creds['password'] = getpass.getpass("Password: ")

    def test_scraper(self):
        """ 
        It is very difficult to test that transactions were correctly obtained
        in a generic way.  Thus we just run the scraper and display the results
        -- any errors that prevent it from running are caught, and errors in
        functionality can be inspected visually.
        """
        for provider, creds in self.credentials.iteritems():
            print "########################### %s #######################" % provider
            results = scraper.get_transactions(provider, creds['username'], creds['password'])
            chan_counts = {}
            for result in results:
                chan_counts[result['channel']] = chan_counts.get(result['channel'], 0) + 1
                if result['channel'] == 'unknown':
                    print "##! UNKOWN CHANNEL"
                    pprint.pprint(result)
            print "Results by channel: "
            pprint.pprint(chan_counts)
        

if __name__ == '__main__':
    unittest.main()
