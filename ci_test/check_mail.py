#!/usr/bin/env python3
###
#This example demonstrates how to login to The Kingdom of Loathing and grab the contents of your inbox.
###

import asyncio
from libkol import Session
from libkol.request import kmail_get
import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.join(os.getenv("HOME"), 'libkolconfig'))


async def main():
    async with Session() as kol:
        print("Logging In")
        await kol.login(config['DEFAULT']['username'], config['DEFAULT']['password'])

        print("Getting kmail")
        kmails = await kol.kmail.get()
        print(kmails)
        print("Parsing kmail")
        for kmail in kmails:
            print("Received kmail from %s (#%s)" % (kmail["userName"], kmail["userId"]))
            print("Text: %s" % kmail["text"])
            print("Meat: %s" % kmail["meat"])
            for item in kmail["items"]:
                print("Item: %s (%s)" % (item["name"], item["quantity"]))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
