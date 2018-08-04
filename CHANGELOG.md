# Tenyks Service CHANGELOG (Python version)

## 2.2.0

* Adding support for conversation contexts. Currently one is included called
  ExpirableContext that has a timeout option and will expire after timeout.
* Fixed double logging issue.
* Fixed a recursion problem with recurring tasks. Changed this from a tail call
  recursive function to a while True: loop.
* Deprecated FilterChain.
* Added RegexpFilterChain that extends FilterChain currently. This allows for
  more filter chain classes to be added in the future that do other things besides
  match using regular expressions

## 1.9

No breaking changes. Everything should work the same. You can even remove all
your `def handler(...): pass` methods :^).

* You are no longer required to have a `self.handle` method attached to your
  service class. Previously it would raise a NotImplementedError if you didn't
  have one.
* Moved all command parsing in the `self.run` method into a command handler
  paradigm. This will allow me to easily track down bugs and add more
  functionality without worrying about breaking a nasty if/else structure.
* General clean up and annotations.
* Python 3 support :^).
* New API method! You can attach your own handlers to the command system by
  calling `self.add_command_handler('COMMANDNAME', self.my_command_handler)`.
  `self.my_command_handler` should take `data` as an arg.
