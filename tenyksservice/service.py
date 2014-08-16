import gevent.monkey
gevent.monkey.patch_all()

import json
import re

import gevent
import redis

import logging

from .config import settings, collect_settings


class TenyksService(object):

    irc_message_filters = {}
    name = None
    direct_only = False
    version = '0.0'
    required_data_fields = ["command", "payload"]

    def __init__(self, name, settings):
        self.channels = [settings.BROADCAST_SERVICE_CHANNEL]
        self.settings = settings
        self.name = name.lower().replace(' ', '')
        self.logger = logging.getLogger(self.name)
        if self.irc_message_filters:
            self.re_irc_message_filters = {}
            for name, regexes in self.irc_message_filters.iteritems():
                if name not in self.re_irc_message_filters:
                    self.re_irc_message_filters[name] = []
                if isinstance(regexes, basestring):
                    regexes = [regexes]
                for regex in regexes:
                    if isinstance(regex, str) or isinstance(regex, unicode):
                        self.re_irc_message_filters[name].append(
                            re.compile(regex).match)
                    else:
                        self.re_irc_message_filters[name].append(regex)
        if hasattr(self, 'recurring'):
            gevent.spawn(self.run_recurring)
        self._register()

    def _register(self):
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
        self.send("", data)

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
        self.send("", data)

    def run_recurring(self):
        self.recurring()
        recurring_delay = getattr(self, 'recurring_delay', 30)
        gevent.spawn_later(recurring_delay, self.run_recurring)

    def data_is_valid(self, data):
        return all(map(lambda x: x in data.keys(), self.required_data_fields))

    def run(self):
        r = redis.Redis(**settings.REDIS_CONNECTION)
        pubsub = r.pubsub()
        pubsub.subscribe(self.channels)
        for raw_redis_message in pubsub.listen():
            try:
                if raw_redis_message['data'] != 1L:
                    data = json.loads(raw_redis_message['data'])
                    if not self.data_is_valid(data):
                        raise ValueError
                    if data["command"] == "PING":
                        self.logger.debug("Got PING message; PONGing...")
                        gevent.spawn(self._respond_to_ping, data)
                        continue
                    if data["command"] == "HELLO":
                        self.logger.debug("Got HELLO message; registering...")
                        self._register()
                        continue
                    if self.direct_only and not data.get('direct', None):
                        continue
                    if self.irc_message_filters and 'payload' in data:
                        name, match = self.search_for_match(data['payload'])
                        ignore = (hasattr(self, 'pass_on_non_match')
                                  and self.pass_on_non_match)
                        if match or ignore:
                            self.delegate_to_handle_method(data, match, name)
                    else:
                        gevent.spawn(self.handle, data, None, None)
            except ValueError:
                self.logger.info('Invalid JSON. Ignoring message.')

    def search_for_match(self, message):
        for name, regexes in self.re_irc_message_filters.iteritems():
            for regex in regexes:
                match = regex(message)
                if match:
                    return name, match
        return None, None

    def delegate_to_handle_method(self, data, match, name):
        if hasattr(self, 'handle_{name}'.format(name=name)):
            callee = getattr(self, 'handle_{name}'.format(name=name))
            gevent.spawn(callee, data, match)
        else:
            gevent.spawn(self.handle, data, match, name)

    def handle(self, data, match, filter_name):
        raise NotImplementedError('`handle` needs to be implemented on all '
                                  'TenyksService subclasses.')

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
                    "UUID": self.settings.SERVICE_UUID,
                    "description": self.settings.SERVICE_DESCRIPTION
                }
            })
        r.publish(broadcast_channel, to_publish)


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
