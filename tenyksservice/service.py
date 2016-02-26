import gevent.monkey
gevent.monkey.patch_all()

import json
import logging
import re
import warnings

import gevent
import redis

from .config import settings, collect_settings


class TenyksService(object):

    irc_message_filters = {}
    name = None
    version = '0.0'
    required_data_fields = ["command", "payload"]
    command_handlers = {}

    def __init__(self, name, settings):
        self.channels = [settings.BROADCAST_SERVICE_CHANNEL]
        self.settings = settings
        self.name = name.lower().replace(' ', '')
        self.logger = logging.getLogger(self.name)
        if self.irc_message_filters:
            map(lambda f: f._compile_filters(),
                self.irc_message_filters.values())
        if hasattr(self, 'recurring'):
            gevent.spawn(self.run_recurring)
        self.command_handlers = {}
        self._register_base_handlers()

    def _register_base_handlers(self):
        self.add_command_handler('PING', self._respond_to_ping)
        self.add_command_handler('HELLO', self._register)
        self.add_command_handler('PRIVMSG', self._help_check)
        self.add_command_handler('PRIVMSG', self._privmsg_handler)

    def hangup(self):
        self._hangup()

    def _hangup(self):
        self.logger.debug("Hanging up with bot")
        data = {
            "command": "BYE",
            "payload": "",
            "target": "",
            "connection": "",
            "meta": {
                "name": self.name,
                "version": self.version,
                "UUID": self.settings.SERVICE_UUID,
                "description": self.settings.SERVICE_DESCRIPTION
            }
        }
        self.send('', data)

    def _register(self, data=None):
        """
        Register handler. This is called at the beginning of `run` and when
        a HELLO command is recieved.
        """
        self.logger.debug("Registering with bot")
        data = {
            "command": "REGISTER",
            "payload": "",
            "target": "",
            "connection": "",
            "meta": {
                "name": self.name,
                "version": self.version,
                "UUID": self.settings.SERVICE_UUID,
                "description": self.settings.SERVICE_DESCRIPTION
            }
        }
        self.send('', data)

    def _help_check(self, data):
        """
        Help handler. This is triggered when a PRIVMSG command is received and
        returns help text if the payload is !help and matches the service meta.
        """
        if data['payload'] == '!help {}'.format(self.settings.SERVICE_UUID):
            self.logger.debug("Sending help!")
            data['target'] = data['nick']
            if hasattr(self, "help_text"):
                for line in self.help_text.split('\n'):
                    self.send(line, data)
            else:
                self.send('No help.', data)

    def _privmsg_handler(self, data):
        """
        PRIVMSG handler. This is triggered when a PRIVMSG command is received
        and it looks for a match within the irc_message_filters list of
        compiled regular expressions. If a match is found, it will call the
        matching handler function, otherwise it will just call `self.handler`.
        """
        if self.irc_message_filters and 'payload' in data:
            self.logger.debug('Handling PRIVMSG')
            name, match = self.search_for_match(data)
            ignore = (hasattr(self, 'pass_on_non_match')
                        and self.pass_on_non_match)
            if match or ignore:
                self.delegate_to_handle_method(data, match, name)
        else:
            if hasattr(self, 'handle'):
                gevent.spawn(self.handle, data, None, None)

    def run_recurring(self):
        """
        If you define a method on the service called `recurring`, it will run
        for `self.recurring_delay` or 30 seconds. This can be used, as an
        example, to fetch and cache weather data every so often so if a bunch
        of people in a channel ask for weather a lot, it won't count against
        your monthly API hits.
        """
        self.recurring()
        recurring_delay = getattr(self, 'recurring_delay', 30)
        gevent.spawn_later(recurring_delay, self.run_recurring)

    def data_is_valid(self, data):
        return all(map(lambda x: x in data.keys(), self.required_data_fields))

    def add_command_handler(self, command, handlefunc):
        if command in self.command_handlers:
            self.command_handlers[command].append(handlefunc)
        else:
            self.command_handlers[command] = [handlefunc]

    def _delegate(self, data):
        if data['command'].upper() not in self.command_handlers:
            self.logger.error('Nothing registered to handle {}'.format(data['command']))
            return
        for handler in self.command_handlers[data['command'].upper()]:
            gevent.spawn(handler, data)

    def run(self):
        # register when we come online
        gevent.spawn(self._register)
        r = redis.Redis(**settings.REDIS_CONNECTION)
        pubsub = r.pubsub()
        pubsub.subscribe(self.channels)
        for raw_redis_message in pubsub.listen():
            if raw_redis_message['data'] != 1L:
                data = json.loads(raw_redis_message['data'])
                if not self.data_is_valid(data):
                    self.logger.error('data message is invalid: {}'.format(data))
                    continue
                self._delegate(data)

    def search_for_match(self, data):
        for name, filter_chain in self.irc_message_filters.iteritems():
            if filter_chain.direct_only and not data.get('direct', False):
                continue
            if filter_chain.private_only and data.get('from_channel', True):
                continue
            match = filter_chain.attempt_match(data['payload'])
            if match:
                return name, match
        return None, None

    def delegate_to_handle_method(self, data, match, name):
        if hasattr(self, 'handle_{name}'.format(name=name)):
            callee = getattr(self, 'handle_{name}'.format(name=name))
            gevent.spawn(callee, data, match)
        else:
            if hasattr(self, 'handle'):
                gevent.spawn(self.handle, data, match, name)

    def _respond_to_ping(self, data):
        self.logger.debug("Responding to PING")
        data["command"] = "PONG"
        data["connection"] = ""
        self.send("", data)

    def send(self, message, data=None):
        r = redis.Redis(**settings.REDIS_CONNECTION)
        broadcast_channel = settings.BROADCAST_ROBOT_CHANNEL
        if data:
            to_publish = json.dumps({
                'command': data['command'],
                'payload': message,
                'target': data['target'],
                'connection': data['connection'],
                'meta': {
                    'name': self.name,
                    'version': self.version or 0.0,
                    'UUID': self.settings.SERVICE_UUID,
                    'description': self.settings.SERVICE_DESCRIPTION
                }
            })
        r.publish(broadcast_channel, to_publish)


class FilterChain(object):

    def __init__(self, filters, direct_only=False, private_only=False):
        if direct_only and private_only:
            warnings.warn('private_only implies direct_only')
        self.filters = filters
        self.direct_only = direct_only
        self.private_only = private_only
        self.compiled_filters = []

    def _compile_filters(self):
        if self.filters:
            for f in self.filters:
                if isinstance(f, str) or isinstance(f, unicode):
                    self.compiled_filters.append(
                        re.compile(f).match)
                else:
                    self.compiled_filters.append(f)  # already compiled filters

    def attempt_match(self, message):
        # tried to match message and returns the first one found or None
        for f in self.compiled_filters:
            match = f(message)
            if match:
                return match
        return None


def run_service(service_class):
    errors = collect_settings()
    service_instance = service_class(settings.SERVICE_NAME, settings)
    for error in errors:
        service_instance.logger.error(error)
    try:
        service_instance.run()
    except KeyboardInterrupt:
        service_instance.hangup()
        logger = logging.getLogger(service_instance.name)
        logger.info('exiting')
