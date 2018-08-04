import asyncio

default_expirable_context_timeout = 10


class ExpirableContext:
    def __init__(self, msg, loop=None, timeout=10, logger=None):
        self.msg = msg

        self._expired = False
        self._logger = logger
        self._kv = {}
        self._timeout = timeout
        self._loop = loop
        self._task = self._loop.create_task(self.set_expired_after(self._timeout))

    def __getitem__(self, key):
        return self._kv[key]

    def __setitem__(self, key, value):
        self._kv[key] = value

    def __delitem__(self, key):
        del self._kv[key]

    async def set_expired_after(self, timeout):
        await asyncio.sleep(timeout)

        if self._logger:
            self._logger.debug('context expired')

        self._expired = True

    def reset(self):
        self._task.cancel()
        self._task = self._loop.create_task(self.set_expired_after(self._timeout))

    @property
    def is_expired(self):
        return self._expired
