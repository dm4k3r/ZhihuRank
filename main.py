import sys
import os
from scrapy.cmdline import execute

sys.path.append(os.pardir.join(os.path.abspath(__name__)))
execute('scrapy,crawl,user'.split(','))