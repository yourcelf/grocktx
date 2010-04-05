GrockTX
=======

GrockTX is a library for parsing and scraping bank transaction data.  Its
primary function is to obtain and parse the memo strings that appear on bank
and credit card statements such as::

    11-14-09 HAMILTON TRUE VALUE HD DORCHESTER MA auth# 86673

GrockTX provides two main libraries: ``grocktx.parser`` and
``grocktx.scraper``.

* ``grocktx.parser`` parses transaction memo strings.  It picks the
  transaction apart to identify the channel (e.g. point-of-sale, check,
  transfer, etc.), the city, state, phone number and zip (if available), and
  the descriptive portion (e.g. "HAMILTON TRUE VALUE HD").

* ``grocktx.scraper`` scrapes major bank account aggregators (currently
  mint.com and wesabe.com) in order to get personal transaction data, and
  parses it with ``grocktx.parser``.  

..  The libraries are especially useful when combined with the GrockTX tagging
    server at https://grocktx.media.mit.edu, which provides user-supplied metadata
    about the transactions to understand better what they represent.  Documentation
    of the API for this can be found at https://grocktx.media.mit.edu/api

``grocktx.scraper`` depends on pycurl and BeautifulSoup.  ``grocktx.parser``
has no external dependencies beyond python 2.5.

Installation
============

Install using ``python setup.py install``.  You may use with ``pip`` with the
following requirements entry::

    -e git://github.com/yourcelf/grocktx.git#egg=grocktx

grocktx.parser
~~~~~~~~~~~~~~

``grocktx.parser`` defines one public method::

    parse(memo, approx_date=None)

``memo`` is a memo string, such as appears on bank and credit card statements.
``approx_date`` is an optional parameter to use to interpret dates on memo
strings that lack year indicators, such as this one::

    WITHDRAW#  - POS 1128 1756 531470 HARVEST COOP CAMBRIDGE MA

If ``approx_date`` is not provided, the year which makes the date closest to
now will be used.  

Example::

    .. code-block:: python

    >>> from grocktx.parser import parse
    >>> parse("11-14-09 HAMILTON TRUE VALUE HD DORCHESTER MA auth# 86673")
    {
        'channel': 'pos',
        'channel_details': {
            'auth': "86673"
        },
        'vendor': {
            'description': "HAMILTON TRUE VALUE HD",
            'city': "DORCHESTER",
            'state': "MA",
            'zip': "",
            'phone': ""
            }
     }

For more examples of the supported transaction formats and their return
results, see ``grocktx/tests.py``.
    
grocktx.scraper
~~~~~~~~~~~~~~~

``grocktx.scraper`` defines one public method::

    ``get_transactions(provider, username, password)``

``provider`` should be one of ``'mint'`` or ``'wesabe'``, and ``username`` and
``password`` should be the username and password for the chosen provider.

Example::

    .. code-block:: python

    >>> from grocktx.scraper import get_transactions
    >>> get_transactions("wesabe", "myusername", "mypassword")

This method returns a JSON-serializable array of dicts containing the
transaction data.  Each transaction is returned in the following form::

    [
        {
            'unique_id': alphanumeric string that is unique for this 
                         transaction.  May not be identical across providers,
                         but will be identical within a provider.
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
                'description': parsed remainder of memo string, or none (as 
                               in a check)
                'city': city if available, or none
                'state': state if available, or none
                'zip': zip if available, or none
                'phone': phone if available, or none
            },
            'raw': {
                // raw fields from provider (e.g. wesabe, mint), values vary by
                // provider.  Currently:

                // mint.com:
                date: YYYY-MM-DD string
                description: string
                original_description: string
                amount: float
                transaction_type: string
                category: string
                account_name: string
                labels: string
                notes: string

                // wesabe.com
                guid: string
                account_id: integer
                date: YYYY-MM-DD string
                original_date: YYYY-MM-DD string
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
        },
    ...
    ]
