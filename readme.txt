Project Name: simple multi-threaded crawler
Author: Sheng Wang

1.Environment: python 3.9

2.Usage: 
In terminal, go into the project directory.
Run python main.py -m "simple" (for simple crawl)
Run python main.py -m "Priority" (for prority crawl)

type in the query you want in the prompt and hit enter.


3.Description:
The program will take in a user query and run a google search for 10 intial seed pages.
Then the seeds will be passed into crawler and the crawler will start crawling until certain condition is meet.
The crawled results will be write to a log file. For each log entry, it will record the crawled url, its fetch status, the size of the page if it get fetched successfully, and the priority score if the mode is priority.



