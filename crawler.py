# Title: crawler.py
# Author: Sheng Wang
# Time: 09/12/2021
# Description: a multi-threaded crawler that crawl a number of pages per second while also prioritizing novel and
# important pages
import logging
import queue
import math
import threading
import re
from concurrent.futures import ThreadPoolExecutor
from time import sleep
import requests
import urllib.robotparser
import urllib.parse
from urllib.parse import urlparse

from finder import Finder
from bs4 import BeautifulSoup

# Global Variable
MAX_PAGE_PER_SITE = 10
FILE_TYPE_BLACKLIST = ['pdf', 'gif', 'tif', 'tiff', 'png', 'eps', 'jpg', 'jpge', 'wav', 'mp3', 'raw', 'asp', 'xml',
                       'doc', 'docx', 'jsp']

#logger
log = logging.getLogger('Main.crawler')

class Crawler(object):

    # Class variables

    def __init__(self, modeSimple, maxlinks, seeds):
        self.maxlinks = maxlinks                     # Max amount of page allowed to crawl
        self.currentDepth = 0
        self.currentScore = 0
        self.num_links_crawled = 0
        self.num_links_found = 0
        self.modeSimple = modeSimple
        self.iscrawling = False

        self.crawled = set()                      # Page(url) that already get crawled, prevent visiting the same page twice
        self.found = dict()                        # (Page(url), times) that already seen for update importance
        self.forbidSite = set()                   # Site(url) that no longer allowed to be crawled
        self.num_site_crawled = dict()            # (site(url), num_crawled) keep track to limit the number of the site get crawled
        self.uncrawled = queue.Queue()                      # url
        self.uncrawledPriority = queue.PriorityQueue()      # (score, url)
        self.pool = ThreadPoolExecutor(max_workers=20)      # For multi-threading

        # Add the initial seed page to the uncrawled list
        if len(seeds) != 0:
            for url in seeds:
                if self.modeSimple:
                    self.currentScore = 0
                    self.uncrawled.put(url)
                else:
                    score = self.calculateScore(url, 1)
                    self.currentScore = score
                    self.uncrawledPriority.put((score*(-1), url))
                    self.found[url] = 1
        else:
            print("No seeds")


    def crawl(self):
        print("Starting crawling ...")
        self.iscrawling = True
        # check if reach maximum depth or uncrawled gets empty
        while self.num_links_crawled <= self.maxlinks and (not self.uncrawled.empty() or not self.uncrawledPriority.empty()):
            if self.modeSimple:
                score = 0
                currentUrl = self.uncrawled.get()
            else:
                currentItem = self.uncrawledPriority.get()
                currentUrl = currentItem[1]
                score = currentItem[0]
                self.currentScore = score


            #Check if current url is already visited
            if currentUrl in self.crawled:
                continue

            #Check if the site of the url has been crawled to many time
            baseUrl = self.getBaseUrl(currentUrl)
            #print("The base url is", baseUrl)
            if not self.checkUrlSite(baseUrl):
                continue

            try:
                self.crawled.add(currentUrl)
                self.currentDepth += 1
                self.num_links_crawled += 1
                # parse for new links
                job = self.pool.submit(self.parse, currentUrl)
                job.add_done_callback(self.crawl_callback)
            except Exception as e:
                print("ERROR during crawling: can't process this url", str(e))
            sleep(0.1)

        print("Stop crawling ...")
        #print("The number of links found is ", self.num_links_found)
        #print(self.uncrawled.qsize())
        self.iscrawling = False
        return None


    def crawl_callback(self, res):
        result = res.result
        if result:
            print("Have crawled", self.num_links_crawled, ' urls')
        else:
            print("Url is not passed for robot exclusion")


    def parse(self, pageUrl):
        # Robot exclusion check
        if not self.check_robot_exclusion(pageUrl):
            if self.currentScore != 0:
                score = self.currentScore * (-1)
                log.info('url %s did not pass robot exclusion. Score: %.4f \n' % (
                pageUrl, score))
            else:
                log.info('url %s did not pass robot exclusion. \n' % (
                    pageUrl))
            return False
        # Fetch url source
        baseUrl = self.getBaseUrl(pageUrl)
        finder = Finder(pageUrl)
        success = finder.fetch()
        statusCode = finder.get_status_code()
        if not success:
            if self.currentScore != 0:
                score = self.currentScore * (-1)
                log.info('url %s failed to fetch with code %d. Score: %.4f \n' % (
                    pageUrl, statusCode, score))
            else:
                log.info('url %s failed to fetch with code %d. \n' % (
                    pageUrl, statusCode))
            return False
        pageSource = finder.get_source()
        pageSize = finder.get_source_size()


        #Download url source and log information
        if self.currentScore != 0:
            score = self.currentScore * (-1)
            log.info('Crawled url %s. Status Code: %d Size: %d bytes. Score: %.4f \n' % (pageUrl, statusCode, pageSize, score))
        else:
            log.info('Crawled url %s. Status Code: %d Size: %d bytes. \n' % (pageUrl, statusCode, pageSize))

        #Parse source for new links
        soup = BeautifulSoup(pageSource, 'html.parser')
        find_all_links = soup.find_all("a", href=True)
        #print('There is total ', len(find_all_links), " links")

        for link in find_all_links:
            url = link['href']

            urlend = url.rsplit('/', 1)[-1]
            throw = ['index.htm', 'index/html', 'index.jsp', 'main.html']
            if urlend.lower() in throw:
                continue

            # Ignore the content after hashtage
            index = url.find('#')
            if index != -1:
                url = url[:index]
                if len(url) == 0:
                    continue
            # Ignore Javascript
            index = url.find('javascript')
            if index != -1:
                continue

            # Fix url ambiguity
            info = urlparse(url)
            if not info.scheme and not info.netloc and not info.path:
                continue
            # Check File type
            if info.path:
                suffix = info.path.split(".")[-1]
                if suffix.lower() in FILE_TYPE_BLACKLIST:
                    continue

            if not info.scheme or not info.netloc:
                url = urllib.parse.urljoin(baseUrl, url)
            # For url start with //
            if not re.match('(?:http|ftp|https)://', url):
                'http://{}'.format(url)
            #print("Url after parse is", url)

            # Check if the url is already crawled
            if self.ifCrawled(url):
                continue
            # Check if the url is already in the priority queue, if true increase importance, update score
            if self.ifFound(url):
                continue

            if self.modeSimple:
                self.num_links_found += 1
                self.uncrawled.put(url)
            else:
                self.num_links_found += 1
                self.found[url] = 1
                score = self.calculateScore(url, 1)
                self.uncrawledPriority.put((score * (-1), url))

        #print("Find total links", len(find_all_links), " And find total links ", self.num_links_found)
        return True


    def getBaseUrl(self, url):
        baseUrl = urlparse(url).scheme + '://' + urlparse(url).netloc
        return baseUrl

    def check_robot_exclusion(self, link):
        baseUrl = self.getBaseUrl(link)
        url = baseUrl + "/robots.txt"
        if not self.if_url_exist(url):
            return True
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(url)
        rp.read()
        if rp.can_fetch("*", link):
            return True
        else:
            return False

    def if_url_exist(self, url):
        try:
            r = requests.head(url, allow_redirects=True)
            if r.status_code < 400:
                return True
            else:
                return False
        except requests.exceptions.RequestException as e:
            #print("In if_url_exist: ", str(e))
            return False


    # check if the domain of the url is still allowed to crawl, return True/False
    def checkUrlSite(self, baseUrl):
        if not (baseUrl in self.forbidSite):
            if baseUrl in self.num_site_crawled:
                num_Visited = self.num_site_crawled[baseUrl]
                # Check if limit is reached
                if num_Visited < MAX_PAGE_PER_SITE:
                    self.num_site_crawled[baseUrl] += 1
                    return True
                else:
                    self.forbidSite.add(baseUrl)
                    self.num_site_crawled[baseUrl] = MAX_PAGE_PER_SITE
            else:
                self.num_site_crawled[baseUrl] = 1
                return True
        return False


    # check if the url is already crawled
    def ifCrawled(self, url):
        if url in self.crawled:
            return True
        return False

    # check if the url is already found (in prority queue)
    def ifFound(self, url):
        if url in self.found:
            # update importance and score
            self.found[url] += 1
            timeAppeared = self.found[url]
            newScore = self.calculateScore(url, timeAppeared)
            self.uncrawledPriority.put((newScore*(-1), url))
            return True
        return False


    # Calculate webpage score
    def calculateScore(self, link, timeAppeared):
        baseUrl = self.getBaseUrl(link)

        # importance relate to time the link has appeared/ use sigmoid function
        importance = 1/(1+ math.exp(-1*timeAppeared))
        #importance = timeAppeared

        # novelty = 1/(1+k) where k is the num of time the site has been crawled
        if baseUrl in self.num_site_crawled:
            novelty_inverse = self.num_site_crawled[baseUrl]
            novelty = 1/(1+novelty_inverse)
        else:
            novelty = 1

        # score
        score = 0.33 * importance + 0.66 * novelty
        #print("The score of ", link, " is ", score)
        return score



































