from tenyksservice import TenyksService, run_service


class Hello(TenyksService):
    direct_only = True
    irc_message_filters = {
        'hello': [r"^(?i)(hi|hello|sup|hey), I'm (?P<name>(.*))$"]
    }

    def handle_hello(self, data, match):
        name = match.groupdict()['name']
        self.logger.debug('Saying hello to {name}'.format(name=name))
        self.send('How are you {name}?!'.format(name=name), data)


def main():
    run_service(Hello)


if __name__ == '__main__':
    main()
