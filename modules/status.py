import socket
import requests

def get_ip():
    return requests.get('https://ipv4.canhazip.com').text.strip()


def resolve_name(name):
    results = socket.gethostbyname_ex(name)
    ips = []
    for thing in results:
        if thing == []:
            check = "thc"
        elif type(thing) == list:
            check = thing[0]
        elif type(thing) == str:
            check = thing
        else:
            check = "thc"
        if "thc" in check:
            pass
        else:
            ips.append(check)
    return ips[0]


def is_production():

    ip = get_ip()

    print(ip)

    if ip == resolve_name('thc-lab.net') or '34.150.238.46' in ip:

        print("We are in production")

        return True

    else:

        print("We are in Test")

        return False
