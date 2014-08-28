# Tenyks Service

This is a python abstraction for creating a
[Tenyks](https://github.com/kyleterry/tenyks) service. This is supposed to
bootstrap all the necessary coroutines and connections needed to communicate
with the IRC bot.

There will be two branches that follow Tenyks. Version 1.x will follow the version
1.x of Tenyks, which currently uses Redis for Pub/Sub. Version 2.x will follow
version 2.x of Tenyks, which is intended to use ZeroMQ as the Pub/Sub
mechanism.

The Primary Tenyks README has more information on how to create a service.


## Install

Pypi: `pip install tenyksservice`  
Git: `git clone https://github.com/kyleterry/tenyks-service; cd tenyks-service;
./setup.py install`

### For Contributing

Git: `git clone https://github.com/kyleterry/tenyks-service; cd tenyks-service;
./setup.py develop`

## Generating settings

`tenyks-service-mkconfig <servicename> > <servicename>_settings.py`

This will also generate a UUID for your service. [Please don't lose
this](http://d315f714-26fh-4346-96a8-11a864cdfcb5.com/) or you will have to
keep purging all the old services registered with Tenyks.

Then, I would set `SERVICE_DESCRIPTION` to something.

## Usage

See [examples](./examples/hello-service).

See the [Tenyks
README](https://github.com/kyleterry/tenyks#lets-make-a-service) section on
making a service.

See [tenyks-contrib](https://github.com/kyleterry/tenyks-contrib). A repo full
of services.
