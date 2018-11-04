#!/usr/bin/env python3
import hexchat
import smtplib
import ssl
import subprocess
import sys
import time
from email.mime.text import MIMEText
from ssl import Purpose

__module_name__ = 'LockMsg'
__module_author__ = 'Lvl4Sword'
__module_version__ = '1.0.0'
__module_description__ = 'Detects Linux/Windows/Mac lockscreen and e-mails messages'

mac_script = """import Quartz
import sys

all_windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)

display_locked = False
for x in all_windows:
    if x["kCGWindowOwnerName"] == "loginwindow":
        display_locked = True
        break
if display_locked:
    sys.stdout.write('True')
else:
    sys.stdout.write('False')"""

# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List
# used in format_message for self.current_time 
timezone = 'US/Eastern'

# cloaks to pay attention to
login_cloaks = ['unaffiliated/example']

# ['channels'] are where you don't want messages from specific users
# ['channels']['notify'] is where you don't want online/offline from specific users
# ['users'] are where you don't want ANYTHING, BUT online/offline notifcations

# ['channels']['notify'] + ['users'] = no notifcations from them at all
# ( unless you have them on login_cloaks )
blacklisted = {'channels': {'#example': ['example', 'example2'],
                            '#example2': ['example3'],
                            'notify': ['example4']},
               'users': ['example5']}

# E-mail
smtp_server = 'smtp.example.com'
smtp_port = 465
sender = 'sender@example.com'
destination = ['destination@example.com']
sender_password = 'P@55w3rd!'
cipher_choice = 'ECDHE-RSA-AES256-GCM-SHA384'
# LOGIN PLAIN doesn't work for Outlook: 
# https://support.office.com/en-us/article/outlook-com-no-longer-supports-
# auth-plain-authentication-07f7d5e9-1697-465f-84d2-4513d4ff0145

# Bottom of https://en.wikipedia.org/wiki/SMTP_Authentication#Details has more
# LOGIN types
login_auth = 'PLAIN'


class Main():
    def __init__(self):
        self.was_said = None
        self.locked = False
        self.current_time = None
        self.formatted_time = None
        self.current_channel = None
        self.friends_list = []

    def detect_lock_screen(self, word, word_eol, userdata):
        if sys.platform.startswith('win'):
            self.detect_windows(word, word_eol, userdata)
        elif sys.platform.startswith('linux'):
            self.detect_linux(word, word_eol, userdata)
        elif sys.platform.startswith('darwin'):
            self.detect_mac(word, word_eol, userdata)
        else:
            self.locked = False
            print('LockMsg is not officially supported on your system.')
            print('If you\'d like to get official support, file an')
            print('issue at https://github.com/Lvl4Sword/LockMsg/issues')
        if self.locked:
            self.update_info(word, word_eol, userdata)

    def update_info(self, word, word_eol, userdata):
        self.current_time = time.localtime()
        self.formatted_time = time.strftime('%Y-%m-%d %I:%M:%S%p', self.current_time)
        self.current_channel = hexchat.get_info('channel')
        [self.friends_list.append(each.nick) for each in hexchat.get_list('notify')]

    def detect_windows(self, word, word_eol, userdata):
        import ctypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        result = user32.GetForegroundWindow()
        if result == 0:
            self.locked = True
        else:
            self.locked = False

    def detect_linux(self, word, word_eol, userdata):
        import dbus
        session_bus = dbus.SessionBus()
        screensaver_list = ['org.gnome.ScreenSaver',
                            'org.cinnamon.ScreenSaver',
                            'org.kde.screensaver',
                            'org.freedesktop.ScreenSaver']
        for each in screensaver_list:
            try:
                object_path = '/{0}'.format(each.replace('.', '/'))
                get_object = session_bus.get_object(each, object_path)
                get_interface = dbus.Interface(get_object, each)
                status = bool(get_interface.GetActive())
            except dbus.exceptions.DBusException:
                pass
        if status:
            self.locked = True
        else:
            self.locked = False

    def detect_mac(self, word, word_eol, userdata):
        sp = subprocess.run(["/usr/bin/python", "-"],
            input=mac_script,
            capture_output=True,
            check=True,
            encoding="utf_8",
            env={"PYTHONIOENCODING": "utf_8"})

        if sp.stdout == 'True':
            self.locked = True
        else:
            self.locked = False
    
    def channel_action(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0] in self.friends_list:
                try:
                    if word[0].lower() in blacklisted['users']:
                        pass
                    elif word[0].lower() in blacklisted['channels'][self.current_channel]:
                        pass
                except KeyError:
                    self.was_said = '[{0}] [{1}] [ACTION] {2}: {3}'.format(self.formatted_time,
                                                                           self.current_channel,
                                                                           word[0],
                                                                           hexchat.strip(word[1], -1, 3))
                    self.mail_this()

    def channel_action_hilight(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0] in self.friends_list:
                try:
                    if word[0].lower() in blacklisted['users']:
                        pass
                    elif word[0].lower() in blacklisted['channels'][self.current_channel]:
                        pass
                except KeyError:
                    self.was_said = '[{0}] [{1}] [ACTION] {2}: {3}'.format(self.formatted_time,
                                                                           self.current_channel,
                                                                           word[0],
                                                                           hexchat.strip(word[1], -1, 3))
                    self.mail_this()

    def channel_message(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0] in self.friends_list:
                if word[0].lower() not in blacklisted['users']:
                    try:
                        if word[0].lower() in blacklisted['channels'][self.current_channel]:
                            pass
                    except KeyError:
                        self.was_said = '[{0}] [{1}] {2}: {3}'.format(self.formatted_time,
                                                                      self.current_channel,
                                                                      word[0],
                                                                      hexchat.strip(word[1], -1, 3))
                        self.mail_this()

    def channel_msg_hilight(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0].lower() not in blacklisted['users']:
                try:
                    if word[0].lower() in blacklisted['channels'][self.current_channel]:
                        pass
                except KeyError:
                    self.was_said = '[{0}] [{1}] {2}: {3}'.format(self.formatted_time,
                                                                  self.current_channel,
                                                                  word[0],
                                                                  hexchat.strip(word[1], -1, 3))
                    self.mail_this()

    def connected(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            self.was_said = '[{0}] [CONNECTED]'.format(self.formatted_time)
            self.mail_this()

    def join(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0] not in self.friends_list:
                if any([word[2].endswith(each.lower()) for each in login_cloaks]):
                    self.was_said = '[{0}] [JOINED] {1} HOST: {2}'.format(self.formatted_time,
                                                                          word[0],
                                                                          word[2])
                    self.mail_this()

    def notify_online(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0].lower() not in blacklisted['channels']['notify']:
                self.was_said = '[{0}] [JOINED] {1}'.format(self.formatted_time,
                                                            word[0])
                self.mail_this()

    def private_action_to_dialog(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0].lower() not in blacklisted['users']:
                self.was_said = '[{0}] [PM] [ACTION] {1}: {2}'.format(self.formatted_time,
                                                                      word[0],
                                                                      hexchat.strip(word[1], -1, 3))
                self.mail_this()

    def private_message_hilight(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0].lower() not in blacklisted['users']:
                self.was_said = '[{0}] [PM] {1}: {2}'.format(self.formatted_time,
                                                             word[0],
                                                             hexchat.strip(word[1], -1, 3))
                self.mail_this()

    def private_message_to_dialog(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0].lower() not in blacklisted['users']:
                self.was_said = '[{0}] [PM] {1}: {2}'.format(self.formatted_time,
                                                             word[0],
                                                             hexchat.strip(word[1], -1, 3))
                self.mail_this()

    def quit(self, word, word_eol, userdata):
        self.detect_lock_screen(word, word_eol, userdata)
        if self.locked:
            if word[0].lower() not in blacklisted['users']:
                try:
                    if word[0].lower() in blacklisted['channels'][self.current_channel]:
                        pass
                except KeyError:
                    if any([word[2].endswith(each.lower()) for each in login_cloaks]):
                        if word[0] not in self.friends_list:
                            self.was_said = '[{0}] [QUIT] {1} HOST: {2}'.format(self.formatted_time,
                                                                                word[0],
                                                                                word[2])
                            self.mail_this()
                    else:
                        if word[0] in self.friends_list:
                            if word[0].lower() not in blacklisted['channels']['notify']:
                                self.was_said = '[{0}] [QUIT] {1}'.format(self.formatted_time,
                                                                          word[0]) 
                                self.mail_this()

    def mail_this(self):
        subject = '[ALERT: IRC]'
        # typical values for text_subtype are plain, html, xml
        content = '{0}'.format(self.was_said)
        msg = MIMEText(content, _charset='utf-8')
        msg['Subject'] = subject
        msg['From'] = sender
        ssl_context = ssl.create_default_context(purpose=Purpose.SERVER_AUTH)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True
        ssl_context.set_ciphers(cipher_choice)
        ssl_context.options &= ~ssl.HAS_SNI
        ssl_context.options &= ~ssl.OP_NO_COMPRESSION
        # No need to explicitally disable SSLv* as it's already been done
        # https://docs.python.org/3/library/ssl.html#id7
        ssl_context.options &= ~ssl.OP_NO_TLSv1
        ssl_context.options &= ~ssl.OP_NO_TLSv1_1
        ssl_context.options &= ~ssl.OP_SINGLE_DH_USE
        ssl_context.options &= ~ssl.OP_SINGLE_ECDH_USE
        conn = smtplib.SMTP_SSL(smtp_server,
                                port=smtp_port,
                                context=ssl_context)
        conn.esmtp_features['auth'] = login_auth
        conn.login(sender, sender_password)
        try:
            for each in destination:
                conn.sendmail(sender, each, msg.as_string())
        finally:
            conn.quit()
        return hexchat.EAT_NONE

start = Main()
hexchat.hook_print('Channel Action', start.channel_action)
hexchat.hook_print('Channel Action Hilight', start.channel_action_hilight)
hexchat.hook_print('Channel Message', start.channel_message)
hexchat.hook_print('Channel Msg Hilight', start.channel_msg_hilight)
hexchat.hook_print('Connected', start.connected)
hexchat.hook_print('Join', start.join)
hexchat.hook_print('Notify Online', start.notify_online)
hexchat.hook_print('Notify Offline', start.quit)
hexchat.hook_print('Private Action to Dialog', start.private_action_to_dialog)
hexchat.hook_print('Private Message Hilight', start.private_message_hilight)
hexchat.hook_print('Private Message to Dialog', start.private_message_to_dialog)
hexchat.hook_print('Quit', start.quit)
