# solardatov@gmail.com

import os
import sys
import signal
import time
import logging
import json
import requests
import subprocess

LOG = logging.getLogger('rsudo')
LOG_FILE = 'rsudo.log'

def sigint_handler(signal, frame):
    LOG.info('Hey, you pressed CTRL-C, starting releasing LOG handlers...')

    for handler in LOG.handlers:
        handler.close()
        LOG.removeFilter(handler)

    LOG.info('Almost done, good luck dude!')

    sys.exit(0)


class RSudoCore:
    def __init__(self, tele_token, admin_username):
        self.tele_token = tele_token
        self.tele_url_prefix_template = 'https://api.telegram.org/bot{}/'
        self.tele_url_prefix = self.tele_url_prefix_template.format(self.tele_token)
        self.tele_last_update_id = 0
        self.admin_username = admin_username

        self.command_map = {
            'uptime': self.uptime ,
            'shutdown': self.shutdown,
            'start': self.help_str,
        }

    def help_str(self):
        help_message = self.make_bold('Hey mr. root, available commands:\n')
        for command in self.command_map:
            help_message += '/' + command + '\n'
        return help_message

    def make_bold(self, text):
        return '*' + text + '*'

    def make_italic(self, text):
        return '_' + text + '_'

    def is_admin(self, update):
        return update['message']['from']['username'] == self.admin_username

    def uptime(self):
        return str(subprocess.run('uptime', stdout=subprocess.PIPE).stdout, 'utf-8')

    def shutdown(self):
        return str(subprocess.run('uptime', stdout=subprocess.PIPE).stdout, 'utf-8')

    def get_updates(self, offset=None):
        url = '{}{}?offset={}'.format(self.tele_url_prefix, 'getUpdates', offset)
        return requests.get(url).json()

    # reply markup TBD
    def send_message(self, chat_id, reply_to_message_id, message, reply_markup=None):
        url = '{}{}?chat_id={}&reply_to_message_id={}&text={}&parse_mode=Markdown'.format(self.tele_url_prefix, 'sendMessage', chat_id, reply_to_message_id, message)
        if reply_markup:
            url += "&reply_markup={}".format(json.dumps(reply_markup))

        return requests.get(url).json()

    def handle_update(self, update):
        try:
            message = update['message']['text']
        except KeyError:
            #ignore callback queries
            return

        if not self.is_admin(update):
            return

        if message[0] == '/':
            command = message[1:]
            if command in self.command_map:
                self.send_message(update['message']['chat']['id'], update['message']['message_id'],
                                  self.command_map[command]())
            else:
                self.send_message(update['message']['chat']['id'], update['message']['message_id'],
                                  'Unknown command: ' + self.make_bold(command))

    def run(self):
        updates = self.get_updates(self.tele_last_update_id + 1)
        if len(updates):
            if updates['ok']:
                updates_list = updates['result']
                for update in updates_list:
                    LOG.info(update)
                    self.tele_last_update_id = update['update_id']
                    self.handle_update(update)


def main():
    # catch CTRL-C
    signal.signal(signal.SIGINT, sigint_handler)

    #setup logging
    LOG.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    log_file = logging.FileHandler(LOG_FILE)
    log_file.setLevel(logging.INFO)
    log_file.setFormatter(formatter)
    LOG.addHandler(log_file)

    log_stdout = logging.StreamHandler()
    log_stdout.setLevel(logging.INFO)
    log_stdout.setFormatter(formatter)
    LOG.addHandler(log_stdout)

    LOG.info('RSudo is starting!')

    bot = RSudoCore(os.environ['TELE_TOKEN'], os.environ['ADMIN_USERNAME'])
    while True:
        bot.run()
        time.sleep(2)


if __name__ == '__main__':
    main()