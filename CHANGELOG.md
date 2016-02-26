# Tenyks Service CHANGELOG (Python version)

## 1.9 (NOT RELEASED; UNSTABLE)

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
