# Title: finder.py
# Author: Sheng Wang
# Time: 09/12/2021
# Description: retrieve page source


import requests



class Finder(object):

    def __init__(self, sourceUrl):
        self.sourceUrl = sourceUrl
        self.pageSource = None
        self.sourceSize = 0
        self.statusCode = 0


    def get_source(self):
        return self.pageSource

    def get_source_size(self):
        return self.sourceSize

    def get_status_code(self):
        return self.statusCode

    def check_fetch_status(self, response):
        self.statusCode = response.status_code
        if response.status_code == 200:
            if 'html' in response.headers['Content-Type']:
                return True
            else:
                print("No html")
        else:
            print("Request to " + self.sourceUrl + " faild with code" + response.status_code)
        return False

    def fetch(self):
        try:
            response = requests.get(self.sourceUrl, timeout=(3,30))
            size = len(response.content)
            self.sourceSize = size
            if self.check_fetch_status(response):
                # Set source
                self.pageSource = response.text
                return True
            else:
                print("not html")
        except Exception as e:
            return False
        return False





