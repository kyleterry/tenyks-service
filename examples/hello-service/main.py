from tenyksservice import TenyksService, run_service, FilterChain


class Hello(TenyksService):
    irc_message_filters = {
        'hello': FilterChain([r"^(hi|hello|sup|hey), I'm (?P<name>(.*))$"],
                             direct_only=True),
        'no_direct': FilterChain([r'^non direct match$', ], direct_only=False),
        'private': FilterChain([r'^this is private$', ], private_only=True),
    }

    def handle_hello(self, data, match):
        name = match.groupdict()['name']
        self.logger.debug('Saying hello to {name}'.format(name=name))
        self.send('How are you {name}?!'.format(name=name), data)

    def handle_no_direct(self, data, match):
        self.send('Handled non-direct message', data)

    def handle_private(self, data, match):
        self.send('nice talking with you, {}'.format(data['nick']), data)


def main():
    run_service(Hello)


if __name__ == '__main__':
    main()
