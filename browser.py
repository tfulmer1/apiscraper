from browsermobproxy import Server
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import os
import json
from urllib.parse import urlparse
import time
from selenium.common.exceptions import TimeoutException


class Browser:

    def __init__(self, chromedriver_path, browsermob_path, har_file_path, cookies=None):
        self.har_file_path = har_file_path
        self.server = Server(browsermob_path)
        self.server.start()
        self.proxy = self.server.create_proxy()

        os.environ["webdriver.chrome.driver"] = chromedriver_path
        url = urlparse(self.proxy.proxy).path
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--proxy-server={0}".format(url))
        
        self.driver = webdriver.Chrome(chromedriver_path, chrome_options=chrome_options)
        if cookies:
            print("Loading cookies from "+str(cookies))
            with open(cookies, 'r') as cookie_file:
                cookie_json = json.loads(cookie_file.read())
            for cookie in cookie_json:
                self.driver.add_cookie(cookie)

    def get(self, url, timeout=20):
        self.proxy.new_har(url, {"captureContent": True})
        try:
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/5);")
            time.sleep(2)  # wait for the page to load
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/4);")
            time.sleep(2)  # wait for the page to load
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(2)  # wait for the page to load
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)  # wait for the page to load
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4)  # wait for the page to load
        except TimeoutException:
            print("Timeout")
            self.driver.find_element_by_tag_name("body").send_keys(Keys.CONTROL+Keys.ESCAPE)

        try:
            source = self.driver.page_source
            result = json.dumps(self.proxy.har, ensure_ascii=False)
            with open(self.har_file_path + "/" + str(int(time.time() * 1000.0)) + ".har", "w") as har_file:
                har_file.write(result)
            return source
        except TimeoutException:
            print("Retrying, with a timeout of "+str(timeout+5))
            return self.get(url, timeout=timeout+5)

    def close(self):
        try:
            self.server.stop()
        except Exception:
            print("Warning: Error stopping server")
            pass

        try:
            self.driver.quit()
        except Exception:
            print("Warning: Error stopping driver")
            pass
