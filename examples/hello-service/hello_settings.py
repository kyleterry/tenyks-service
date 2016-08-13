DEBUG = True
SERVICE_NAME = 'hello'
SERVICE_VERSION = '0.1.1'
SERVICE_UUID = '273b62ad-a99d-48be-8d80-ccc55ef688b4'
SERVICE_DESCRIPTION = 'Hello service will let you greet Tenyks'

##############################################################################
# The following setting defines a ZMQ connection. `out` is the connection used
# to send things to the bot and `in` is the connection we want to use to
# recieve messages
#
# This setting is required.

ZMQ_CONNECTION = {
    'out': 'tcp://localhost:61124',
    'in': 'tcp://localhost:61123'
}
##############################################################################
