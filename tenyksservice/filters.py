import re

from .packages import six


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


class RegexpFilterChain(FilterChain):
    pass
