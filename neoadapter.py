from profile import Profile
from neo4j import GraphDatabase
import json

class NeoAdapter:

    __driver = None

    def __init__(self, uri, username, password):
        self.__driver = GraphDatabase.driver(uri, auth=(username, password))

    def __del__(self):
        if self.__driver:
            self.__driver.close()

    def follows(self, profile_from, profile_to):
        with self.__driver.session() as session:
            session.run("MERGE (from:Profile {name: '" + profile_from.name + "'}) MERGE (to:Profile {name: '" + profile_to.name + "'}) MERGE (from)-[:FOLLOWS]->(to) SET from = " + profile_from.toNeoAttrs() + " SET to =" + profile_to.toNeoAttrs())

    def save(self, profile):
        with self.__driver.session() as session:
            for hashtag in profile.used_hashtags:
                session.run("MERGE (tag:Hashtag {name: $tagname}) MERGE (profile:Profile {name: '" + profile.name + "'}) MERGE (profile)-[r:USES]->(tag) SET r.times = $times SET profile = " + profile.toNeoAttrs(), tagname=hashtag, times=profile.used_hashtags[hashtag])
            for reference in profile.profile_links:
                session.run("MERGE (referenced:Profile {name: $refname}) MERGE (profile:Profile {name: '" + profile.name + "'}) MERGE (profile)-[r:REFERENCES]->(referenced) SET r.times = $times SET profile = " + profile.toNeoAttrs(), refname=reference.replace("@", ""), times=profile.profile_links[reference])

    def fetch_profiles(self):
        profiles = {}
        with self.__driver.session() as session:
            result = session.run("MATCH (profile:Profile) WHERE EXISTS(profile.level) RETURN profile");
            for record in result.data():
                try:
                    profile = self.__profile_from_record(record)
                    profiles[profile.name] = profile
                except KeyError:
                    pass
            return profiles

    def __profile_from_record(self, record):
        props = record["profile"]
        level = int(props["level"])
        is_private = json.loads(props["is_private"].lower())
        profile = Profile(props["name"], level, is_private, "", props["description"])
        profile.text = props["text"]
        profile.extract_references()
        return profile

