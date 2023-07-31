#!/bin/python3

import json
import requests
import os
import telebot
import threading
import time
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [zillmon]: %(message)s')

BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

telebot.apihelper.READ_TIMEOUT = 5

def send_msg(text, id):
    try:
        bot.send_message(id, text)
    except Exception as e:
        logging.info(e)
        send_msg(text, id)

def reply(message, text):
    try:
        bot.reply_to(message, text)
    except Exception as e:
        logging.info(e)
        reply(message, text)

class zillmon:
    def read_config(self):
        try:
            with open(os.path.expanduser("~") + os.path.sep + ".config/zillmon/zill.json", "r") as f:
                self.config = json.load(f)
        except Exception as e:
            self.config = {"vald_url": "http://162.19.59.17:8080/v1/",
                           "remote_url": "https://fullnode.mainnet.aptoslabs.com/v1/",
                           "chat_id": -932868843
                          }
            logging.warning("User Config is missing: %s", str(e))
            logging.info("Loading default config...")

    def rpc_call(self, url, type_of, counter=0):
        try:
            r = requests.get(url + type_of)
            return json.loads(r.text)
        except Exception as e:
            logging.error(f"There was an issue with the rpc call, check if {url} is up")
            logging.error(str(e))
            if counter < 4:
                time.sleep((counter + 1)*2)
                return self.rpc_call(url, type_of, counter + 1)
            else:
                logging.error("Retried 5 times... Error Occured in RPC call")
                self.error_url = url
                return {"result": "RPC Failure"}

    def get_blockchain_info(self):
        self.blockchain_info_vald = self.rpc_call(self.config["vald_url"], "")
        self.blockchain_info_remote = self.rpc_call(self.config["remote_url"], "")
        if "result" not in self.blockchain_info_vald and "result" not in self.blockchain_info_remote:
            return True
        else:
            return False

    def alert_BlockNum(self):
        if int(self.blockchain_info_vald["block_height"]) < int(self.blockchain_info_remote["block_height"]) - 400:
            send_msg(self.config["chat_id"], f'''Block Height of Aptos Validator is Lagging\n
                              Validator Height: {self.blockchain_info_vald["block_height"]}
                              Remote Node Height: {self.blockchain_info_remote["block_height"]}
                              ''')
            logging.error(f'''Block Height of Aptos Validator is Lagging''')
            logging.error(f''' Validator Height: {self.blockchain_info_vald["block_height"]} Remote Node Height: {self.blockchain_info_remote["block_height"]}''')
        logging.info(f''' Validator Height: {self.blockchain_info_vald["block_height"]} Remote Node Height: {self.blockchain_info_remote["block_height"]}''')

    def alert_EpochDiff(self):
        if int(self.blockchain_info_vald["epoch"]) < int(self.blockchain_info_remote["epoch"]):
            send_msg(self.config["chat_id"], f'''Difference in epoch! Aptos Validator is Lagging\n
                              Validator Epoch: {self.blockchain_info_vald["epoch"]}
                              Remote Epoch: {self.blockchain_info_remote["epoch"]}
                              ''')
            logging.error(f'''Difference in Epoch for Aptos Validator''')
            logging.error(f'''Validator Epoch: {self.blockchain_info_vald["epoch"]} Remote Node Peers: {self.blockchain_info_remote["epoch"]}''')
        logging.info(f'''Validator Epoch: {self.blockchain_info_vald["epoch"]} Remote Node Epoch: {self.blockchain_info_remote["epoch"]}''')

    def monitor(self):
        while True:
            if self.get_blockchain_info():
                self.alert_BlockNum()
                self.alert_EpochDiff()
                logging.info("Successful monitor cycle")
            else:
                logging.error("One monitor cycle has failed due to RPC Error")
                send_msg(self.config["chat_id"], f'RPC Error the following url is down: {self.error_url}')
            time.sleep(120)


zill = zillmon()
zill.read_config()

@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    reply(message, """\
Hi there, I am Aptmon.
I am here to monitor you Aptos Validator node
""")

@bot.message_handler(commands=['status'])
def send_status(message):
    zill.get_blockchain_info()
    reply(message, "Validator Status: \n" + str(zill.blockchain_info_vald))

@bot.message_handler(commands=['rstatus'])
def send_remote_status(message):
    zill.get_blockchain_info()
    reply(message, "Remote Node Status: \n" + str(zill.blockchain_info_remote))

def start_monitoring():
    bot.send_message(zill.config["chat_id"], f"Monitoring Validator: {zill.config['vald_url']}")
    zill.monitor()

monitorThread = threading.Thread(target=start_monitoring)
monitorThread.start()
try:
    bot.infinity_polling()
except Exception as e:
    logging.error("Infinity Polling Error")
    bot.send_message(zill.config["chat_id"], f"Infinity Polling error: Restart the service")
    logging.error(str(e))
