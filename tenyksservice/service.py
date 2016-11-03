import asyncio
import json
import logging
import re
import warnings

import aiozmq
import zmq

from .config import settings, collect_settings
from .packages import six


class TenyksService:

    irc_message_filters = {}
    name = None
    logger = None
    version = '0.0'
    required_data_fields = ["command", "payload"]
    command_handlers = {}

    def __init__(self, name, settings):
        self.name = name.lower().replace(' ', '')
        self.settings = settings
        self.loop = asyncio.get_event_loop()
        print(self.settings.DEBUG)
        if self.settings.DEBUG:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(self.name)
        for f in self.irc_message_filters.values():
            f._compile_filters()
        self.command_handlers = {}

    async def _zmq_connect(self):
        # setup zmq context
        self.logger.debug('Bootstrapping pubsub')
        in_addr = self.settings.ZMQ_CONNECTION['in']
        out_addr = self.settings.ZMQ_CONNECTION['out']
        self._in = await aiozmq.create_zmq_stream(zmq.SUB,
                                                  connect=in_addr,
                                                  loop=self.loop)
        self._out = await aiozmq.create_zmq_stream(zmq.PUB,
                                                   connect=out_addr,
                                                   loop=self.loop)
        self._in.transport.setsockopt(zmq.SUBSCRIBE, b'')
        await asyncio.sleep(0.5)

    async def hangup(self):
        self.logger.debug("Hanging up with bot.")
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
        await asyncio.sleep(0.5)
        self._in.close()
        self._out.close()
        self.logger.debug("Hung up.")

    async def _register(self, data=None):
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

    async def _help_check(self, data):
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

    async def _privmsg_handler(self, data):
        """
        PRIVMSG handler. This is triggered when a PRIVMSG command is received
        and it looks for a match within the irc_message_filters list of
        compiled regular expressions. If a match is found, it will call the
        matching handler function, otherwise it will just call `self.handler`.
        """
        if self.irc_message_filters and 'payload' in data:
            self.logger.debug('Handling PRIVMSG')
            name, match = await self.search_for_match(data)
            ignore = (hasattr(self, 'pass_on_non_match') and
                      self.pass_on_non_match)
            if match or not ignore:
                await self.delegate_to_handle_method(data, match, name)
        else:
            if hasattr(self, 'handle'):
                self.handle(data, None, None)

    async def run_recurring(self):
        """
        If you define a method on the service called `recurring`, it will run
        for `self.recurring_delay` or 30 seconds. This can be used, as an
        example, to fetch and cache weather data every so often so if a bunch
        of people in a channel ask for weather a lot, it won't count against
        your monthly API hits.
        """
        self.recurring()
        recurring_delay = getattr(self, 'recurring_delay', 30)
        await asyncio.sleep(recurring_delay)
        await self.run_recurring()

    def data_is_valid(self, data):
        return all(map(lambda x: x in data.keys(), self.required_data_fields))

    def add_command_handler(self, command, handlefunc):
        if command in self.command_handlers:
            self.command_handlers[command].append(handlefunc)
        else:
            self.command_handlers[command] = [handlefunc]

    async def _delegate(self, data):
        if data['command'].upper() not in self.command_handlers:
            self.logger.error('Nothing registered to handle {}'
                              .format(data['command']))
            return
        for handler in self.command_handlers[data['command'].upper()]:
            self.logger.debug('delegating message to {}'.format(handler))
            await handler(data)

    async def run(self):
        # Connect to ZMQ
        await self._zmq_connect()

        # Register with tenyks when we come online.
        await self._register()

        # Register base handlers
        self.add_command_handler('PING', self._respond_to_ping)
        self.add_command_handler('HELLO', self._register)
        self.add_command_handler('PRIVMSG', self._help_check)
        self.add_command_handler('PRIVMSG', self._privmsg_handler)

        if hasattr(self, 'recurring'):
            self.loop.create_task(self.run_recurring())

        self.logger.debug('before while loop')
        while True:
            self.logger.debug('after while loop')
            data = await self._in.read()
            jdata = json.loads(data[0].decode('utf-8'))

            self.logger.debug('got {}'.format(jdata))
            if not self.data_is_valid(jdata):
                self.logger.error('message is invalid: {}'.format(jdata))
                continue
            await self._delegate(jdata)

    async def search_for_match(self, data):
        for name, filter_chain in six.iteritems(self.irc_message_filters):
            if filter_chain.direct_only and not data.get('direct', False):
                continue
            if filter_chain.private_only and data.get('from_channel', True):
                continue
            match = filter_chain.attempt_match(data['payload'])
            if match:
                return name, match
        return None, None

    async def delegate_to_handle_method(self, data, match, name):
        if hasattr(self, 'handle_{name}'.format(name=name)):
            callee = getattr(self, 'handle_{name}'.format(name=name))
            callee(data, match)
        else:
            if hasattr(self, 'handle'):
                self.handle(data, match, name)

    async def _respond_to_ping(self, data):
        self.logger.debug("Responding to PING")
        data["command"] = "PONG"
        data["connection"] = ""
        self.send("", data)

    def send(self, message, data=None):
        if data:
            self.logger.debug('sending {}'.format(data))
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
        self._out.write([to_publish.encode('utf-8')])
        self.loop.create_task(self._out.drain())


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
                if isinstance(f, six.string_types):
                    self.compiled_filters.append(re.compile(f).match)
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
    loop = asyncio.get_event_loop()
    service_instance = service_class(settings.SERVICE_NAME, settings)
    for error in errors:
        service_instance.logger.error(error)
    try:
        loop.run_until_complete(service_instance.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(service_instance.hangup())
    loop.close()
