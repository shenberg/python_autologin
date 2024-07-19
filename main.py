import objc
from SystemConfiguration import *
import requests
import os
import subprocess
import re
import time
import PyObjCTools.AppHelper
import config
from Cocoa import *

AIRPORT_CONNECTED = 1
AIRPORT_KEY_PATTERN = "State:/Network/Interface/{}/AirPort"
IP_KEY = "State:/Network/Global/IPv4"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".networkautologin.js")
EXAMPLE_CONFIG_PATH = "resources/config.js"
CASPERJS_BIN_PATH = "resources/casperjs/bin/casperjs"
PHANTOMJS_BIN_PATH = "resources/phantomjs"
PATH_ENV = os.environ.get("PATH")

EXIT_LOGGED_IN = 1
EXIT_ALREADY_LOGGED_IN = 2
EXIT_TIMEOUT = 3
EXIT_NO_MATCH = 4
EXIT_NOT_CONNECTED = 5

EXIT_FAILURE = -1
EXIT_SUCCESS = 0

old_BSSID = None
airportKey = None

def get_airport_status(dynStore):
    return SCDynamicStoreCopyValue(dynStore, airportKey)

def check_update(dynStore):
    global old_BSSID

    airport_status = get_airport_status(dynStore)
    if airport_status is None:
        return

    SSID = airport_status.get('SSID_STR')
    BSSID = airport_status.get('BSSID')
    power_status = airport_status.get('Power Status', 0)

    if power_status == AIRPORT_CONNECTED:
        if BSSID and BSSID != old_BSSID:
            result = EXIT_TIMEOUT
            for _ in range(20):
                power_status = get_airport_status(dynStore).get('Power Status', 0)
                if power_status != AIRPORT_CONNECTED:
                    break

                print("Running script...")

                subprocess.run(["killall", "Captive Network Assistant"], stderr=subprocess.DEVNULL)
                time.sleep(0.25)

                result = do_login()

                if result != EXIT_FAILURE:
                    break

                time.sleep(1)

            if result == EXIT_LOGGED_IN:
                print("Successfully logged in.")
            elif result == EXIT_ALREADY_LOGGED_IN:
                print("Already logged in.")
            elif result == EXIT_NO_MATCH:
                print("No credentials found for current SSID/BSSID.")
            elif result == EXIT_TIMEOUT:
                print("Timed out while trying to login.")
            elif result == EXIT_NOT_CONNECTED:
                print("Could not connect to the network.")
            elif result == EXIT_FAILURE:
                print("Failed to connect, see exception printed above")

        old_BSSID = BSSID
    else:
        old_BSSID = None

def callback(dynStore, changedKeys, info):
    print(f"callback: {changedKeys}")
    changed_keys_list = changedKeys 
    for key in changed_keys_list:
        if key == airportKey or key == IP_KEY:
            check_update(dynStore)
            break

def setup_interface_watch():
    # we don't actually use the context, we just need to provide a python object
    context = {}

    dynStore = SCDynamicStoreCreate(None, "NetworkAutoLogin", callback, context)
    if not dynStore:
        raise RuntimeError("SCDynamicStoreCreate() failed: {}".format(SCErrorString(SCError())))

    keys = [airportKey, IP_KEY]
    if not SCDynamicStoreSetNotificationKeys(dynStore, keys, None):
        raise RuntimeError("SCDynamicStoreSetNotificationKeys() failed: {}".format(SCErrorString(SCError())))

    rlSrc = SCDynamicStoreCreateRunLoopSource(None, dynStore, 0)
    CFRunLoopAddSource(CFRunLoopGetCurrent(), rlSrc, kCFRunLoopDefaultMode)

    return dynStore

def get_interface_name():
    try:
        result = subprocess.run(['/sbin/route', 'get', '10.10.10.10'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode()
        match = re.search(r'^\s*interface:\s*(.*)$', output, re.MULTILINE)
        if match:
            return match.group(1)
        return "en0"
    except Exception as e:
        print(f"Error getting interface name: {e}")
        return "en0"


APPLE_HOTSPOT_URL = 'http://captive.apple.com/hotspot-detect.html'

FORM_DICT = {
    '4Tredir' : APPLE_HOTSPOT_URL,
    'magic' : 'REPLACE_THIS',
    'username' : config.USERNAME,
    'password' : config.PASSWORD,
}

def do_login():
    try:
        response_text = requests.get(APPLE_HOTSPOT_URL).text
        if response_text.strip() == '<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>':
            print('Connected to the internet!')
            return EXIT_ALREADY_LOGGED_IN
        
        location_match = re.search('window.location="([^"]*)"', response_text)
        if location_match is None:
            raise RuntimeError("didn't find URL in response:\n" + response_text)
        
        location = location_match.group(1)
        print(f'Got redirect to url: {location}')

        request_form_response = requests.get(location).text

        magic_match = re.search('"magic" value="([0-9a-f]{16})"', request_form_response)
        if magic_match is None:
            raise RuntimeError("Failed to find magic number in response: \n" + request_form_response)
        
        magic = magic_match.group(1)
        print(f'found magic: {magic}')

        form_dict = FORM_DICT.copy()
        form_dict['magic'] = magic

        post_url = location.rsplit('/',1)[0] + '/'
        print('posting to post url: ' + post_url)
        post_response = requests.post(post_url, data=form_dict)
        post_response.raise_for_status()

        print('response ok:\n' + post_response.text)
        return EXIT_LOGGED_IN
    except Exception as e:
        print(f"Exception logging in: {e}")
        return EXIT_FAILURE

def main():
    global airportKey

    interface_name = get_interface_name()
    print(f"Interface selected for NetworkAutoLogin: {interface_name}")

    airportKey = AIRPORT_KEY_PATTERN.format(interface_name)

    dynStore = setup_interface_watch()

    check_update(dynStore)
    print('Starting loop')

    # install signal handler using mach port, otherwise no signal handling while CFRunLoop blocks
    PyObjCTools.AppHelper.installMachInterrupt()

    # start listening to events
    CFRunLoopRun()

if __name__ == "__main__":
    main()
