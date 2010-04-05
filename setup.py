from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
import os

root = os.path.dirname(__file__)
os.chdir(root)

master_file = open(os.path.join(root, ".git", "refs", "heads", "master"))
VERSION = '0.1.git-' + master_file.read().strip()
master_file.close()

# Make data go to the right place.
# http://groups.google.com/group/comp.lang.python/browse_thread/thread/35ec7b2fed36eaec/2105ee4d9e8042cb
for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

data_dir = "data"
data = [os.path.join(data_dir, f) for f in os.listdir(data_dir)]

setup(
    name='grocktx',
    version=VERSION,
    description="Libraries for scraping transaction data from aggregators"
                " and parsing the transactions.",
    long_description="""
GrockTX provides two main libraries: ``grocktx.parser`` and ``grocktx.scraper``.

 * ``grocktx.parser`` parses transaction memo strings, such as:

    11-14-09 HAMILTON TRUE VALUE HD DORCHESTER MA auth# 86673

  It picks the transaction apart to identify the channel (e.g. point-of-sale,
  check, transfer, etc.), the city, state, phone number and zip (if available),
  and the descriptive portion (e.g. "HAMILTON TRUE VALUE HD").

 * ``grocktx.scraper`` scrapes major bank account aggregators (currently
   mint.com and wesabe.com) in order to get personal transaction data, and
   parses it with ``grocktx.parser``.  

The libraries are especially useful when combined with the GrockTX tagging
server at https://grocktx.media.mit.edu, which provides user-supplied metadata
about the transactions to understand better what they represent.

``grocktx.scraper`` depends on pycurl and BeautifulSoup.  ``grocktx.parser``
has no external dependencies beyond python 2.5.
    """,
    author="Charlie DeTar",
    author_email="cfd@media.mit.edu",
    url="http://github.com/yourcelf/grocktx",
    license="MIT License",
    platforms=["any"],
    packages=['grocktx'],
    data_files=[(data_dir, data)],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    include_package_data=True,
)
