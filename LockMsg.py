#!/usr/bin/env python3
import smtplib
import ssl
import subprocess
import sys
import time
from email.headerregistry import Address
from email.message import EmailMessage
from ssl import Purpose
import hexchat
try:
    from jinja2 import Template
except ModuleNotFoundError:
    jinja_found = False
else:
    jinja_found = True


__module_name__ = 'LockMsg'
__module_author__ = 'Lvl4Sword'
__module_version__ = '3.1.2'
__module_description__ = 'Detects Linux/Windows/Mac lockscreen and e-mails messages'

# cloaks to pay attention to
login_cloaks = ['unaffiliated/example']

# channels you don't want anything from
blocklisted_channels = ['#example']
# users you don't want anything from
blocklisted_users = ['example']
# users in a specific channel you don't want anything from
blocklisted_channel_users = {'#example': 'example'}
# channels you want everything from
allowlisted_channels = ['#example']
# users you want everything from
allowlisted_users = ['example']
# users in a specific channel you want everything from
allowlisted_channel_users = {'#example': 'example'}
# receive an e-mail when the bot connects
connect_email = True

# E-mail
smtp_server = 'smtp.example.com'
smtp_port = 465
sender = 'sender@example.com'
destination = {'destination@example.com': 'Example User'}
sender_password = 'P@55w3rd!'
cipher_choice = 'ECDHE-RSA-AES256-GCM-SHA384'
# LOGIN PLAIN doesn't work for Outlook:
# https://support.office.com/en-us/article/outlook-com-no-longer-supports-
# auth-plain-authentication-07f7d5e9-1697-465f-84d2-4513d4ff0145

# Bottom of https://en.wikipedia.org/wiki/SMTP_Authentication#Details has more
# LOGIN types
login_auth = 'PLAIN'


FREEDESKTOP_SCREENSAVER = ['dbus-send',
                           '--session',
                           '--dest=org.freedesktop.ScreenSaver',
                           '--type=method_call',
                           '--print-reply',
                           '--reply-timeout=1000',
                           '/ScreenSaver',
                           'org.freedesktop.ScreenSaver.GetActive']
GNOME_SCREENSAVER = ['dbus-send',
                     '--session',
                     '--dest=org.gnome.ScreenSaver',
                     '--type=method_call',
                     '--print-reply',
                     '--reply-timeout=1000',
                     '/ScreenSaver',
                     'org.gnome.ScreenSaver.GetActive']
GNOME3_SCREENSAVER = ['dbus-send',
                      '--session',
                      '--dest=org.gnome.ScreenSaver',
                      '--type=method_call',
                      '--print-reply',
                      '--reply-timeout=1000',
                      '/org/gnome/ScreenSaver',
                      'org.gnome.ScreenSaver.GetActive']
KDE_SCREENSAVER = ['dbus-send',
                   '--session',
                   '--dest=org.kde.screensaver',
                   '--type=method_call',
                   '--print-reply',
                   '--reply-timeout=1000',
                   '/ScreenSaver',
                   'org.freedesktop.ScreenSaver.GetActive']
SCREENSAVERS = {'FREEDESKTOP_SCREENSAVER': {'command': FREEDESKTOP_SCREENSAVER},
                'GNOME_SCREENSAVER': {'command': GNOME_SCREENSAVER},
                'GNOME3_SCREENSAVER': {'command': GNOME3_SCREENSAVER},
                'KDE_SCREENSAVER': {'command': KDE_SCREENSAVER}}
JINJA_EMAIL_TEMPLATE = """<html>
    <head></head>
    <body>
        <b>Time:</b> {{current_time}}</br>
        {% if current_channel is not none %}<b>Current Channel</b>: {{current_channel}}</br>{% endif %}
        {% if what is not none %}<b>Type</b>: {{what}}</br>{% endif %}
        {% if username is not none %}<b>Username</b>: {{username}}</br>{% endif %}
        {% if cloak is not none %}<b>Cloak</b>: {{cloak}}</br>{% endif %}
        {% if message is not none %}<b>Message</b>: {{message}}{% endif %}
    <body>
</html>
"""

NO_JINJA_EMAIL_TEMPLATE = """<html>
    <head></head>
    <body>
        <b>Time:</b> {current_time}</br>\n
"""

class Main:
    def __init__(self):
        self.email_template = None
        self.linux_screensaver_command = None
        self.locked = False
        self.friends_list = [each.nick for each in hexchat.get_list('notify')]

    def detect_lock_screen(self):
        if sys.platform.startswith('win'):
            self.detect_windows()
        elif sys.platform.startswith('linux'):
            self.detect_linux()
        elif sys.platform.startswith('darwin'):
            self.detect_mac()
        else:
            self.locked = False
            print('---------------------------------------------------')
            print('---------------------------------------------------')
            print('---------------------------------------------------')
            print('LockMsg is not officially supported on your system.')
            print('-------- If you\'d like official support.. --------')
            print('------- File an issue at the following URL: -------')
            print('--- https://github.com/Lvl4Sword/LockMsg/issues ---')
            print('---------------------------------------------------')
            print('---------------------------------------------------')
            print('---------------------------------------------------')
            time.sleep(60)

    def detect_windows(self):
        import ctypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        result = user32.GetForegroundWindow()
        if result == 0:
            self.locked = True
        else:
            self.locked = False

    def detect_linux(self):
        try:
            check_screensaver = subprocess.check_output(self.linux_screensaver_command).decode().split()[-1]
        except TypeError:
            self.detect_linux_screensaver_command()
        else:
            if check_screensaver == 'true':
                self.locked = True
            elif check_screensaver == 'false':
                self.locked = False
            else:
                print('---------------------------------------------------')
                print('---------------------------------------------------')
                print('---------------------------------------------------')
                print('The screensaver command is giving unexpected output')
                print('----- If you\'re: having issues with setup or -----')
                print('-------- something isn\'t working properly --------')
                print('---- please disable LockMsg and file an issue: ----')
                print('--- https://github.com/Lvl4Sword/LockMsg/issues ---')
                print('---------------------------------------------------')
                print('---------------------------------------------------')
                print('---------------------------------------------------')
                time.sleep(60)

    def detect_linux_screensaver_command(self):
        self.linux_screensaver_command = None
        for x, y in enumerate(SCREENSAVERS):
            try:
                the_command = SCREENSAVERS[y]['command']
                the_output = subprocess.check_output(the_command).decode().split()[-1]
                if the_output in ['false', 'true']:
                    self.linux_screensaver_command = the_command
                    the_name = f' {y} '
                    print('---------------------------------------------------')
                    print('---------------------------------------------------')
                    print('---------------------------------------------------')
                    print('----- The following has been detected as your -----')
                    print('--------------- screesaver command: ---------------')
                    print('{:-^51}'.format(the_name))
                    print('---------------------------------------------------')
                    print('---------------------------------------------------')
                    print('---------------------------------------------------')
            except Exception:
                pass
        if self.linux_screensaver_command is None:
            print('---------------------------------------------------')
            print('---------------------------------------------------')
            print('---------------------------------------------------')
            print('The correct screensaver command could not be found.')
            print('---- Please disable LockMsg and file an issue: ----')
            print('--- https://github.com/Lvl4Sword/LockMsg/issues ---')
            print('---------------------------------------------------')
            print('---------------------------------------------------')
            print('---------------------------------------------------')
            time.sleep(60)

    def detect_mac(self):
        import Quartz
        session_dict = Quartz.CGSessionCopyCurrentDictionary()
        if 'CGSSessionScreenIsLocked' in session_dict.keys():
            self.locked = True
        else:
            self.locked = False

    def check_blocklist(self, the_type, current_channel, username):
        if the_type not in ['notify', 'quit']:
            if username in blocklisted_users or current_channel in blocklisted_channels:
                return True
            try:
                if username in blocklisted_channel_users[current_channel]:
                    return True
            except KeyError:
                pass
        else:
            if username in blocklisted_users:
                return True
        return False

    def check_allowlist(self, the_type, current_channel, username):
        if the_type not in ['notify', 'quit']:
            try:
                if allowlisted_channel_users[current_channel]:
                    return True
            except KeyError:
                pass
            if username in self.friends_list or username in allowlisted_users or current_channel in allowlisted_channels:
                return True
        else:
            if username in self.friends_list or username in allowlisted_users:
                return True
        return False

    def check_important_cloak(self, the_type, cloak):
        if the_type in ['joined', 'notify', 'part' 'quit']:
            if any([cloak.endswith(each.lower()) for each in login_cloaks]):
                return True
            else:
                return False
        else:
            return False

    def return_proper_channel(self, the_type, username):
        if the_type in ['channel', 'hilight', 'joined', 'part', 'quit']:
            return hexchat.get_info('channel')
        elif the_type == 'pm':
            return username
        else:
            return None

    def execute(self, username, cloak, the_type, what, message):
        check_locked = False
        current_channel = None
        if the_type != 'connected':
            username = username.lower()

            current_channel = self.return_proper_channel(the_type, username)
            important_cloak = self.check_important_cloak(the_type, cloak)
            blocklisted = self.check_blocklist(the_type, current_channel, username)

            if not blocklisted:
                allowlisted = self.check_allowlist(the_type, current_channel, username)

                if allowlisted:
                    if the_type == 'joined':
                        if username not in self.friends_list:
                            if important_cloak:
                                check_locked = True
                        else:
                            check_locked = True
                    elif the_type == 'notify':
                        if important_cloak:
                            pass
                        else:
                            check_locked = True
                    elif the_type == 'quit':
                        if important_cloak:
                            check_locked = True
                    elif the_type == 'channel':
                        check_locked = True
                    elif the_type == 'part':
                        check_locked = True
                if the_type in ['hilight', 'pm']:
                    check_locked = True
        else:
            if connect_email:
                check_locked = True

        if check_locked:
            self.detect_lock_screen()
            if self.locked:
                self.prep_mail(current_channel, what, username, cloak, message)

    def channel_action(self, word, word_eol, userdata):
        username = word[0]
        cloak = None
        what = 'ACTION'
        message = hexchat.strip(word[1], -1, 3)
        self.execute(username, cloak, 'channel', what, message)

    def channel_message(self, word, word_eol, userdata):
        username = word[0]
        cloak = None
        what = None
        message = hexchat.strip(word[1], -1, 3)
        self.execute(username, cloak, 'channel', what, message)

    def connected(self, word, word_eol, userdata):
        username = None
        cloak = None
        what = 'CONNECTED'
        message = None
        self.execute(username, cloak, 'connected', what, message)

    def channel_action_hilight(self, word, word_eol, userdata):
        username = word[0]
        cloak = None
        what = 'ACTION'
        message = hexchat.strip(word[1], -1, 3)
        self.execute(username, cloak, 'hilight', what, message)

    def channel_msg_hilight(self, word, word_eol, userdata):
        username = word[0]
        cloak = None
        what = None
        message = hexchat.strip(word[1], -1, 3)
        self.execute(username, cloak, 'hilight', what, message)

    def join(self, word, word_eol, userdata):
        username = word[0]
        cloak = word[2]
        what = 'JOINED'
        message = None
        self.execute(username, cloak, 'joined', what, message)

    def notify_online(self, word, word_eol, userdata):
        username = word[0]
        cloak = word[2]
        what = 'JOINED'
        message = None
        self.execute(username, cloak, 'notify', what, message)

    def private_action_to_dialog(self, word, word_eol, userdata):
        username = word[0]
        cloak = None
        what = 'ACTION'
        message = hexchat.strip(word[1], -1, 3)
        self.execute(username, cloak, 'pm', what, message)

    def private_message_hilight(self, word, word_eol, userdata):
        username = word[0]
        cloak = None
        what = 'PM'
        message = hexchat.strip(word[1], -1, 3)
        self.execute(username, cloak, 'pm', what, message)

    def private_message_to_dialog(self, word, word_eol, userdata):
        username = word[0]
        cloak = None
        what = 'PM'
        message = hexchat.strip(word[1], -1, 3)
        self.execute(username, cloak, 'pm', what, message)

    def quit(self, word, word_eol, userdata):
        username = word[0]
        cloak = word[2]
        what = 'QUIT'
        message = None
        self.execute(username, cloak, 'quit', what, message)

    def part(self, word, word_eol, userdata):
        username = word[0]
        cloak = word[1]
        what = 'LEAVING'
        message = None
        self.execute(username, cloak, 'part', what, message)

    def prep_mail(self, current_channel, what, username, cloak, message):
        current_time = time.strftime('%Y-%m-%d %I:%M:%S%p', time.localtime())
        msg = EmailMessage()
        msg['Subject'] = '[ALERT: IRC]'
        msg['From'] = sender
        msg['To'] = [Address(destination[email], email.split('@')[0], email.split('@')[1]) for email in destination]
        # Not sure if this is actually needed since we're using add_alternative
        # https://docs.python.org/3/library/email.message.html#email.message.EmailMessage.add_alternative
        msg.set_content = ''
        if not jinja_found:
            self.email_template = NO_JINJA_EMAIL_TEMPLATE
            if current_channel is not None:
                self.email_template += f"        <b>Current Channel</b>: {current_channel}</br>\n"
            if what is not None:
                self.email_template += f"        <b>Type</b>: {what}</br>\n"
            if username is not None:
                self.email_template += f"        <b>Username</b>: {{username}}</br>\n"
            if cloak is not None:
                self.email_template += f"        <b>Cloak</b>: {{cloak}}</br>\n"
            if message is not None:
                self.email_template += f"        <b>Message</b>: {message}\n"
            email_template += "    <body>\n" + "</html>"
            msg.add_alternative(email_template, subtype='html')
        else:
            self.email_template = JINJA_EMAIL_TEMPLATE
            data = {'current_time': current_time,
                    'current_channel': current_channel,
                    'what': what,
                    'username': username,
                    'cloak': cloak,
                    'message': message}
            prep_template = Template(self.email_template)
            msg.add_alternative(prep_template.render(data), subtype='html')
        self.mail_this(msg)

    def mail_this(self, msg):
        ssl_context = ssl.create_default_context(purpose=Purpose.SERVER_AUTH)
        # No need to set verify_mode, it's done for us:
        # https://docs.python.org/3/library/ssl.html#ssl.create_default_context
        ssl_context.check_hostname = True
        ssl_context.set_ciphers(cipher_choice)
        ssl_context.options |= ssl.HAS_SNI
        ssl_context.options |= ssl.OP_NO_COMPRESSION
        # No need to explicitally disable SSLv* as it's already been done
        # https://docs.python.org/3/library/ssl.html#id7
        ssl_context.options |= ssl.OP_NO_TLSv1
        ssl_context.options |= ssl.OP_NO_TLSv1_1
        ssl_context.options |= ssl.OP_SINGLE_DH_USE
        ssl_context.options |= ssl.OP_SINGLE_ECDH_USE
        with smtplib.SMTP_SSL(smtp_server, port=smtp_port, context=ssl_context) as conn:
            conn.esmtp_features['auth'] = login_auth
            conn.login(sender, sender_password)
            conn.send_message(msg)
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
hexchat.hook_print('Part', start.part)
hexchat.hook_print('Part with Reason', start.part)
hexchat.hook_print('Private Action to Dialog', start.private_action_to_dialog)
hexchat.hook_print('Private Message Hilight', start.private_message_hilight)
hexchat.hook_print('Private Message to Dialog', start.private_message_to_dialog)
hexchat.hook_print('Quit', start.quit)
