import json
import re

class Profile:

	def __init__(self, name, level, is_private, profile_picture, description):
		self.name = name
		self.level = level
		self.is_private = is_private
		self.profile_picture = profile_picture
		self.description = description
		self.follows = set()
		self.text = name + " " + description + " "
		self.profile_links = {}
		self.used_hashtags = {}
		
	def extract_references(self):
		# Extract and count hashtags
		for hashtag in re.findall("(\#[a-zA-Z0-9]+)", self.text):
			if hashtag in self.used_hashtags:
				self.used_hashtags[hashtag] += 1
			else:
				self.used_hashtags[hashtag] = 1
		# Extract and count profile links
		for ref in re.findall("(@[a-zA-Z0-9\._]+)", self.text):
			if ref in self.profile_links:
				self.profile_links[ref] += 1
			else:
				self.profile_links[ref] = 1

	def toJSON(self):
		return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
		
	def toNeoAttrs(self):
		return "{" + "name: '{}', description: '{}', is_private: '{}', level:'{}', text: '{}'".format(self.name, self.description, self.is_private, self.level, self.text) + "}"
