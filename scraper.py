from profile import Profile
from neoadapter import NeoAdapter 

import os
import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class Scraper:

    fetch_text = False
    depth = 0
    delay = 5
    verbose = True
    neo = None

    __logged_in = False 
    __current_level = 0
    __fetched_profiles = {}

    def __init__(self, headless):
        options = webdriver.firefox.options.Options()
        profile = webdriver.FirefoxProfile()
        profile.set_preference("intl.accept_languages", "en-US")
        profile.update_preferences()
        if headless:
            options.add_argument("--headless")
        self.__browser = webdriver.Firefox(options=options, firefox_profile=profile)

    def __del__(self):
        self.__browser.quit()
		
    def load_profiles(self):
        if self.neo:
            self.__fetched_profiles = self.neo.fetch_profiles()
            if self.verbose:
                print("Profiles loaded")
        elif self.verbose:
            print("No adapter given for loading profiles")

    def login(self, username, password):
        # Open login page
        self.__browser.get("https://www.instagram.com")
        time.sleep(5)
        self.__browser.implicitly_wait(1)
        if "Forgot password?" not in self.__browser.page_source:
            if self.verbose:
                print("Could not log in")
            self.__logged_in = False
            return False
    
        # Submit credentials
        self.__browser.find_element_by_xpath("//input[@name='username']").send_keys(username)
        self.__browser.find_element_by_xpath("//input[@name='password']").send_keys(password)
        self.__browser.find_element_by_xpath("//button[@type='submit']").click()
        time.sleep(5)
        self.__browser.implicitly_wait(1)
        # Error workaround
        if "try again soon" in self.__browser.page_source:
            self.__browser.find_element_by_xpath("//button[@type='submit']").click()
            time.sleep(3)
        # Login failed    
        if "Forgot password?" in self.__browser.page_source: 
            if self.verbose:
                print("Could not log in")
            self.__logged_in = False
            return False
        if self.verbose:
            print("Successfully logged in")
        self.__logged_in = True
        return True

    def fetch_profile(self, target_name):
        if target_name in self.__fetched_profiles:
            return self.__fetched_profiles[target_name]
        # Open profile
        self.__browser.get("https://www.instagram.com/" + target_name + "/")
        self.__browser.implicitly_wait(1)
        # Check for softban
        if "Please wait a few minutes" in self.__browser.page_source:
            if self.verbose:
                print("Softban detected")
            return None
        # Get profile info
        is_private = "This Account is Private" in self.__browser.page_source
        pic = self.__browser.find_element_by_xpath("//img[@data-testid='user-avatar']").get_attribute("src")
        description = self.__browser.find_elements_by_xpath("//header/section/div")[1].text.replace("'", "").replace("\\", "")
        profile = Profile(target_name, self.__current_level, is_private, pic, description)
        if self.fetch_text:
            self.fetch_profile_text(profile)
        profile.extract_references()
        self.__fetched_profiles[profile.name] = profile
        if self.neo:
            self.neo.save(profile)
        time.sleep(self.delay)
        return profile

	# Fetch description of all posts
    def fetch_profile_text(self, profile):
        self.__browser.get("https://www.instagram.com/" + profile.name + "/")
        profile_text = ""
        if profile.is_private or "No Posts yet" in self.__browser.page_source:
            return
        # Open first post
        first_post = self.__browser.find_element_by_xpath("//article/div/div/div[1]/div[1]")
        action = ActionChains(self.__browser)
        action.move_to_element_with_offset(first_post, 5, 5)
        action.click()
        action.perform()
        self.__browser.implicitly_wait(1)
        time.sleep(3)
        if len(self.__browser.find_elements_by_xpath("//svg[@aria-label='close']")) < 1:
            action.perform()
        self.__browser.implicitly_wait(1)
        time.sleep(3)
        # Get text of every post
        while True:
            profile_text += " " + self.__browser.find_element_by_xpath("//li[@role='menuitem']/div/div/div[2]/span").text
            try:
                self.__browser.find_element_by_xpath("//div[@role='dialog']//a[contains(@class, 'coreSpriteRightPaginationArrow')]").click()
                time.sleep(1)
            except Exception:
                break
        profile.text += profile_text.replace("'", "").replace("\\", "")


	# Fetch set of names the profile is following
    def fetch_followed_profiles_list(self, profile):
        # Open profile
        self.__browser.get("https://www.instagram.com/" + profile.name + "/")
        time.sleep(3)
        self.__browser.implicitly_wait(1)
        if "Please wait a few minutes" in self.__browser.page_source:
            if self.verbose:
                print("Softban detected")
        # Get num followed profiles
        num_followed = int(self.__browser.find_element_by_xpath("//header/section/ul/li[3]/a/span").text.replace(",", ""))
        # Open dialog containing followed profiles
        self.__browser.find_element_by_xpath("//header/section/ul/li[3]/a").click()
        time.sleep(5)
        list_scroll = self.__browser.find_element_by_xpath("//div[@role='dialog']/div/div[2]")
        follows_list_element = list_scroll.find_element_by_xpath("//ul/div")
        # Scroll to load all followed profiles
        follows_list_element.click()
        followed_names = set()
        num_found = 0
        noop_iters = 0
		# Load names as long as new ones are loaded into list.
		# Stop when no profiles are loaded during 'noop_iters' times of scrolling down.
        while len(followed_names) < num_followed or noop_iters >= 15:
            followed_names.update(map(lambda profile: profile.text, follows_list_element.find_elements_by_xpath("//li//span/a")))
            if len(followed_names) > num_found:
                noop_iters = 0
                num_found = len(followed_names)
            else:
                noop_iters += 1
            list_scroll.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.3)
        return followed_names 

	# Fetch profile objects of accounts the profile is following and save them in the profile
    def fetch_followed_profiles(self, profile):
        if profile.is_private:
            return
        followed_profiles = self.fetch_followed_profiles_list(profile)
        for profile_name in followed_profiles:
            followed_profile = self.fetch_profile(profile_name)
            profile.follows.add(followed_profile)
            if self.neo:
                self.neo.follows(profile, followed_profile) 

	# Fetch a profile following hierarchy with a determined depth
    def fetch_profile_tree(self, profile):
        self.__current_level = profile.level + 1
        if profile.level < self.depth and len(profile.follows) < 1:
            if self.verbose:
                print("[Level " + str(self.__current_level) + "] Fetching followed profiles of: " + profile.name)
            self.fetch_followed_profiles(profile)
            for next_profile in profile.follows:
                self.fetch_profile_tree(next_profile)

