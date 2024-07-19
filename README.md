# MacOS Python autologin

This is a long-running process that listens to network connectivity events on a network device and if it detects a captive portal, kills the captive portal assisstant and logs in by itself.

Log-in process is hard-coded to the one I need for my network (see `do_login()`) and expects USERNAME and PASSWORD variables (strings) in a config.py file (not provided).

**RANT**: iOS has the `NEHotspotHelper` class to allow you to do this whole process the nice way, but alas it is unsupported on macs, so we do a more manual process.

## Installation:

Clone the repo, install the requirements, you should be good to go.

## Use-case:

I have a wifi network where I live, it's getting old to type in the password. Captive Network Assisstant.app is not connected to your keychain so I can't have it remember my credentials. Hence this script.

## Issues:

* Hard-coded to my login process (network SSID etc)
* If you run the script while, say, using your phone as a hotspot through a physical connection, it will watch the wrong network interface. Maybe it's better to hard-code `en0` instead of the janky autodetection code.

# Credits

The project wouldn't be here without:
* [NetworkAutoLogin](https://github.com/tyilo/NetworkAutoLogin) that I hastily ported while removing functionality.
* The PyObjC authors & maintainers for making access to CoreFramework possible from Python
* Thanks to ChatGPT for saving some of the work in porting from ObjC to Python
* Thanks to Google for finding me the magic incantation necessary to get Ctrl-C working again (Python + Signals + CFRunLoop is not a happy combination)
