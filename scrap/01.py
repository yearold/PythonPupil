import re
import urlparse
import urllib2
import time
from datetime import datetime
import robotparser
import Queue
"""中文是机器翻译的
"""

def link_crawler(seed_url, link_regex=None, delay=5, max_depth=-1, max_urls=-1, headers=None, user_agent='wswp', proxy=None, num_retries=1):
    """Crawl from the given seed URL following links matched by link_regex
    从给定的种子URL以下链接匹配的link_regex爬行
    """
    # the queue of URL's that still need to be crawled
    # URL的仍然需要爬队列
    crawl_queue = Queue.deque([seed_url])
    # the URL's that have been seen and at what depth
    # URL是已经看到在什么深度
    seen = {seed_url: 0}
    # track how many URL's have been downloaded
    # 跟踪下载了多少URL
    num_urls = 0
    rp = get_robots(seed_url)
    throttle = Throttle(delay)
    headers = headers or {}
    if user_agent:
        headers['User-agent'] = user_agent

    while crawl_queue:
        url = crawl_queue.pop()
        # check url passes robots.txt restrictions
        if rp.can_fetch(user_agent, url):
            throttle.wait(url)
            html = download(url, headers, proxy=proxy, num_retries=num_retries)
            links = []

            depth = seen[url]
            if depth != max_depth:
                # can still crawl further
                # 判断是否可以进一步爬取 
                if link_regex:
                    # filter for links matching our regular expression
                    # 我们的正则表达式匹配的链接过滤
                    links.extend(link for link in get_links(html) if re.match(link_regex, link))

                for link in links:
                    link = normalize(seed_url, link)
                    # check whether already crawled this link
                    # 检查是否已经爬过这个链接
                    if link not in seen:
                        seen[link] = depth + 1
                        # check link is within same domain
                        # 检查链接在同一域内
                        if same_domain(seed_url, link):
                            # success! add this new link to queue
                            # 成功！将这个新链接添加到队列中
                            crawl_queue.append(link)

            # check whether have reached downloaded maximum
            # 检查是否已达到最大下载
            num_urls += 1
            if num_urls == max_urls:
                break
        else:
            print 'Blocked by robots.txt:', url


class Throttle:
    """Throttle downloading by sleeping between requests to same domain
       通过睡眠要求同域之间下载节流（控制下载速度）
    """
    def __init__(self, delay):
        # amount of delay between downloads for each domain
        # 为每个域之间网络延迟量
        self.delay = delay
        # timestamp of when a domain was last accessed
        # 上次访问域时的时间戳
        self.domains = {}
        
    def wait(self, url):
        domain = urlparse.urlparse(url).netloc
        last_accessed = self.domains.get(domain)

        if self.delay > 0 and last_accessed is not None:
            sleep_secs = self.delay - (datetime.now() - last_accessed).seconds
            if sleep_secs > 0:
                time.sleep(sleep_secs)
        self.domains[domain] = datetime.now()


def download(url, headers, proxy, num_retries, data=None):
    print 'Downloading:', url
    request = urllib2.Request(url, data, headers)
    opener = urllib2.build_opener()
    if proxy:
        proxy_params = {urlparse.urlparse(url).scheme: proxy}
        opener.add_handler(urllib2.ProxyHandler(proxy_params))
    try:
        response = opener.open(request)
        html = response.read()
        code = response.code
    except urllib2.URLError as e:
        print 'Download error:', e.reason
        html = ''
        if hasattr(e, 'code'):
            code = e.code
            if num_retries > 0 and 500 <= code < 600:
                # retry 5XX HTTP errors
                return download(url, headers, proxy, num_retries-1, data)
        else:
            code = None
    return html


def normalize(seed_url, link):
    """Normalize this URL by removing hash and adding domain
    规范化这个URL移除哈希和添加域
    """
    link, _ = urlparse.urldefrag(link) # remove hash to avoid duplicates
    return urlparse.urljoin(seed_url, link)


def same_domain(url1, url2):
    """Return True if both URL's belong to same domain
    如果都属于同一个域的URL返回true
    """
    return urlparse.urlparse(url1).netloc == urlparse.urlparse(url2).netloc


def get_robots(url):
    """Initialize robots parser for this domain
    为该域初始化机器人解析器
    """
    rp = robotparser.RobotFileParser()
    rp.set_url(urlparse.urljoin(url, '/robots.txt'))
    rp.read()
    return rp
        

def get_links(html):
    """Return a list of links from html 
    返回HTML链接列表
    """
    # a regular expression to extract all links from the webpage
    # 一个正则表达式提取网页中所有的链接
    webpage_regex = re.compile('<a[^>]+href=["\'](.*?)["\']', re.IGNORECASE)
    # list of all links from the webpage
    # 来自网页的所有链接列表
    return webpage_regex.findall(html)


if __name__ == '__main__':
    link_crawler('http://example.webscraping.com', '/(index|view)', delay=0, num_retries=1, user_agent='BadCrawler')
    link_crawler('http://example.webscraping.com', '/(index|view)', delay=0, num_retries=1, max_depth=1, user_agent='GoodCrawler')
