import json
import re
from sys import exit
from urllib import request
from urllib.error import HTTPError

class GODADDY_DDNS():

    CONFIG_FILE_PATH = './pyddns_config'

    def __init__(self):
        try:
            CONFIG_FILE = open(self.CONFIG_FILE_PATH, 'r')
            self.config = json.loads(CONFIG_FILE.read())
            CONFIG_FILE.close()
            KEY = self.config["user"]["key"]
            SECRET = self.config["user"]["secret"]
            self.HEADERS = {
                "Accept": "application/json",
                'Content-type': 'application/json',
                'Authorization': 'sso-key {}:{}'.format(KEY, SECRET)
            }
            self.DOMAINS = self.config["user"]["domains"].split(",")
        except FileNotFoundError as e:
            print("Config file not found.")
            fd = open(self.CONFIG_FILE_PATH,'w')
            fd.write('''
            {	
                "user": {
                    "key": "",
                    "secret": "",
                    "domains": ""
                },

                "ipv4": {
                    "enable": 0,
                    "checkurl": "https://myip4.ipip.net",
                    "pattern": "([0-9]{1,3}.){3}[0-9]{1,3}",
                    "type": "A",
                    "cache": {
                        "name.domain": "ip"
                    },
                    "names": "",
                    "TTL": 600
                },

                "ipv6": {
                    "enable": 0,
                    "checkurl": "https://myip6.ipip.net",
                    "pattern": "([0-9a-f]{0,4}:|::){1,7}[0-9a-f]{0,4}",
                    "type": "AAAA",
                    "cache": {
                        "name.domain": "ip"
                    },
                    "names": "",
                    "TTL": 600
                }
            }
            ''')
            fd.close()
            print("Config file be created.")
            print("Run after edit config.")
            exit(1)

    def main(self):
        for DOMAIN in self.DOMAINS:
            if self.config["ipv4"]["enable"]:
                self.iptype = "ipv4"
                self.getpbip()
                for NAME in self.config[self.iptype]["names"].split(","):
                    if DOMAIN == "" or NAME == "":
                        continue
                    self.reqget(DOMAIN, NAME)
            if self.config["ipv6"]["enable"]:
                self.iptype = "ipv6"
                self.getpbip()
                for NAME in self.config[self.iptype]["names"].split(","):
                    if DOMAIN == "" or NAME == "":
                        continue
                    self.reqget(DOMAIN, NAME)
    
    def getpbip (self):
        CHECK_URL = self.config[self.iptype]["checkurl"]
        # Get Host Public IP
        PUBLIC_IP = request.urlopen(CHECK_URL).read().decode('utf-8')
        regex = self.config[self.iptype]["pattern"]
        res = re.search(regex, PUBLIC_IP)
        if res:
            self.PUBLIC_IP = res.group()
            print("Get Public IP: {}".format(self.PUBLIC_IP))
        else:
            print("Fail! Public IP: {}".format(self.PUBLIC_IP))
            exit(1)

    def reqget(self,DOMAIN,NAME):
        AD = "%s.%s"%(NAME, DOMAIN)
        GOD_ADDY_API_URL = "https://api.godaddy.com/v1/domains/{}/records/{}/{}".format(DOMAIN, self.config[self.iptype]["type"], NAME)
        # Check if the IP needs to be updated
        if AD not in self.config[self.iptype]["cache"]:
            self.config[self.iptype]["cache"][AD] = ""
        CACHED_IP = self.config[self.iptype]["cache"][AD]
        if CACHED_IP != self.PUBLIC_IP:
            req = request.Request(GOD_ADDY_API_URL, headers=self.HEADERS)
            try:
                with request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    NAME_BIND_IP = data[0]["data"] if data else None
            except HTTPError as e:
                if e.code in (422, 404):
                    NAME_BIND_IP = None
                if e.code == 401:
                    print("Authentication info not sent or invalid")
                    exit(1)
                else:
                    print(e)
                    exit(1)
            if NAME_BIND_IP == self.PUBLIC_IP:
                print("unchanged! Current 'Public IP' matches 'GoDaddy' records. No update required!")
            else:
                print("changed! Updating '{}.{}', {} to {}".format(NAME, DOMAIN, NAME_BIND_IP, self.PUBLIC_IP))
                data = json.dumps([{"data": self.PUBLIC_IP, "name": NAME, "ttl": self.config[self.iptype]["TTL"], "type": self.config[self.iptype]["type"]}]).encode('utf-8')
                req = request.Request(GOD_ADDY_API_URL, data=data, headers=self.HEADERS, method='PUT')
                with request.urlopen(req) as response:
                    print("Success!" if not response.read().decode('utf-8') else "Success!")
                    self.config[self.iptype]["cache"][AD] = self.PUBLIC_IP
                    CONFIG_FILE = open(self.CONFIG_FILE_PATH, mode="w", encoding="utf-8").write(json.dumps(self.config, sort_keys=True, indent=4, separators=(',', ': ')))
        else:
            print("Current 'Public IP' matches 'Cached IP' recorded. No update required!")
            CONFIG_FILE = open(self.CONFIG_FILE_PATH, mode="w", encoding="utf-8").write(json.dumps(self.config, sort_keys=True, indent=4, separators=(',', ': ')))


ddns = GODADDY_DDNS()
ddns.main()