# Title: main.py
# Author: Sheng Wang
# Time: 09/12/2021
# Description: start of the program execution / handling user inputs and log

import sys
import getopt
import logging
from googlesearch import search
from crawler import Crawler

# Configure logger
def configureLogger(filename):
    logger = logging.getLogger('Main')
    fomatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    try:
        fileHandler = logging.FileHandler(filename)
    except IOError as e:
        print("Error: Log filename -- ", str(e))
        return False
    else:
        fileHandler.setFormatter(fomatter)
        logger.addHandler(fileHandler)
        logger.setLevel(logging.INFO)     #INFO
        return True

def main():
    # Determine crawler mode
    mode = ''
    modeSimple = True
    if len(sys.argv) != 3:
        print('Usage: main.py -m <mode>')
        sys.exit(2)
    try:
        opts, args = getopt.getopt(sys.argv[1:], "m:", ["mode="])
    except getopt.GetoptError as err:
        print('Usage: main.py -m <mode>')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-m", "--mode"):
            mode = arg
    if mode.lower() == 'priority':
        modeSimple = False

    # Get User Query
    query = ''
    while not query:
        query = input("Enter your query: ")

    # Use google search engine to get 10 seeds page for crawling
    seeds = []
    print("Getting seeds ...")
    for i in search(
        query,       # query we want to search
        tld = 'com', # top level domain
        lang = 'en', # language
        num = 1,    # number of results we want
        start= 0,    # first result to get
        stop = 10,   # last result to get
        pause = 2.0 ):
        seeds.append(i)
        #print(i)

    # Set logger, call crawler and pass in the variables
    filename = query.replace(" ", "")
    if modeSimple:
        filename = filename + 'Simple.log'
    else:
        filename = filename + 'Priority.log'
    if configureLogger(filename):
        crawler = Crawler(modeSimple, 10000, seeds)
        crawler.crawl()
    else:
        print('Error in logger configuration')

    return None

# Execution
if __name__ == '__main__':
    main()


