import json
import urllib
import urllib2

SERVER = "http://localhost:8080/"
grocktx_username = "admin"
grocktx_password = "admin"
USER_AGENT = "Example client"

def find_params(params):
    """
    Get all the tags for the vendor identified by the given args.
    """
    url = SERVER + "tags/api"
    data = urllib.urlencode({'params': json.dumps(params)})
    headers = {'User-Agent': USER_AGENT}
    request = urllib2.Request(url + "?" + data, None, headers)
    response = urllib2.urlopen(request)
    return response.read()

def test_find_params():
    params = { 'tags': [{"key": "name", "value": "fedco"}] }
    print find_params(params)

def put_params(params):
    url = SERVER + "tags/api"
    data = urllib.urlencode({'params': json.dumps(params)})
    headers = {'User-Agent': USER_AGENT}
    request = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(request)
    return response.read()


def test_put_params():
    data = {
        'vendor': {
            'description': 'FEDCO SEEDS',
            'phone': '2078737333',
            'state': 'ME',
        },
        'tags': [
            { "key": "name", "value": "Fedco", },
            { "key": "url", "value": "http://www.fedcoseeds.com/" },
        ],
        "username": grocktx_username,
        "password": grocktx_password,
    }
    result = put_params(data)
    print result

def import_transactions():
    """ 
    Interactively attach tags to the vendors present in an aggregator account. 
    """
    import getpass
    import pprint
    from scraper import get_transactions
    aggregator = raw_input("Aggregator (mint/wesabe): ")
    agg_username = raw_input("Username: ")
    agg_password = getpass.getpass("Password: ")

    results = get_transactions(aggregator, agg_username, agg_password)
    for i, result in enumerate(results):
        print "(", i, len(results), ")"
        print result['channel']
        if result['channel'] not in ['atm', 'pos', 'deposit', 'dividend', 'fee', 'rev fee']:
            continue

        pprint.pprint(result['vendor'])
        tagit = raw_input("Tag this? (y/n): ")
        if tagit == "y":
            tagstr = raw_input("Tags (k1=v1|k2=v2|): ")
            tags = dict(tag.split("=") for tag in tagstr.split("|"))
            kwargs = {
                'username': grocktx_username,
                'password': grocktx_password,
                'vendor': result['vendor'],
                'tags': [{"key": k, "value": v} for k,v in tags.iteritems()],
            }
            result = put_params(kwargs)
            print result

if __name__ == "__main__":
    #test_put_params()
    #test_find_params()
    #import_transactions()
