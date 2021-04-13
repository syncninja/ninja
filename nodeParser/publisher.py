import getpass
import requests
import random
import string
import json
from os.path import expanduser

CONFIG_FILE = expanduser("~/.ninja/config.json")
BASE = "https://api.sync.ninja"
PUBLISH_URL = f"{BASE}/api/publish_auth"


def get_token():
    config = json.load(open(CONFIG_FILE, "r"))
    return config['token']['token']['access_token']


def random_name():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))


def ask_data():
    print()
    print("Publishing script: ")
    name = input(" script name (my-awesome-script): ")
    if len(name.strip()) == 0:
        return random_name()
    return name.replace(" ", "-")


def publish_script(token, name, script):
    data = {
        "name": name,
        "history": script
    }
    headers = {"Authorization": "Bearer " + token}
    r = requests.post(PUBLISH_URL, json=data, headers=headers)
    return r.json()['url']


def publish(script):
    try:
        token = get_token()
    except:
        print()
        print("You must login in order to record")
        return

    name = ask_data()
    url = publish_script(token, name, script)
    print()
    print("Share your session using the following url:")
    print("   " + url)
    print()
