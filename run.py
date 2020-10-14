#!/usr/bin/env python3
from profile import Profile
from neoadapter import NeoAdapter 
from scraper import Scraper


insta_user = ""
insta_pw = ""
target_name = ""

neo_uri = "bolt://localhost:7687"
neo_user = ""
neo_pw = ""

scraper = Scraper(headless=False)
scraper.neo = NeoAdapter(neo_uri, neo_user, neo_pw)
scraper.verbose = True
# Way more information but way less performance
scraper.fetch_text = True
scraper.depth = 1
scraper.delay = 60


if scraper.login(insta_user, insta_pw):
    scraper.load_profiles()
    target_profile = scraper.fetch_profile(target_name)
    scraper.fetch_profile_tree(target_profile)
