from __future__ import unicode_literals

import shlex
from prompt_toolkit.completion import Completer, Completion


__all__ = ["CommandCompleter"]


slist   = lambda l:    sorted(l, key=lambda s: s.casefold())
wfilter = lambda l, w: [x for x in l if w is None or x.startswith(w)]


def get_tokens(text, suffix=("", "\"", "'")):
    """ Recursive token split function handling ' and ". """
    try:
        return shlex.split(text + suffix[0])
    except ValueError:
        return get_tokens(text, suffix[1:])
    except IndexError:
        return []


class CommandCompleter(Completer):
    """ Completer for console's commands and arguments. """
    def get_completions(self, document, complete_event):
        # this completion method handles the following formats:
        #  1) COMMAND VALUE        ; e.g. create my-project
        #  2) COMMAND OPTION VALUE ; e.g. set LHOST 192.168.1.1
        # first, tokenize document.text and initialize some shorcut variables
        _ = document.text
        tokens = get_tokens(_)
        l = len(tokens)
        ts = len(_) - len(_.rstrip(" "))  # trailing spaces
        try:
            cmd, t1, t2 = tokens + [None] * (3 - l)
        except:     # occurs when l > 3 ; no need to complete anything as it
            return  #  corresponds to an invalid command
        bc = len(document.text_before_cursor)
        it = len(_) - bc > 0
        o1 = len(cmd) + 1 - bc if cmd else 0
        o2 = len(cmd) + len(t1 or "") + 2 - bc if cmd and t2 else 0
        _ = self.console.commands
        c = _[cmd]() if cmd in _ else None
        cmds = slist(_.keys())
        nargs = len(c.args) if c is not None else 0
        # then handle tokens ;
        # when no token is provided, just yield the list of available commands
        if l == 0:
            for _ in cmds:
                yield Completion(_, start_position=0)
        # when one token is provided, handle format:
        #   [PARTIAL_]COMMAND ...
        elif l == 1:
            # when a partial token is provided, yield the list of valid commands
            if ts == 0 and c not in cmds:
                for _ in wfilter(cmds, cmd):
                    yield Completion(_, start_position=-bc)
            # when a valid command is provided, yield the list of valid options
            #  or values, depending on the type of command
            elif ts > 0 and c is not None:
                if nargs == 1:    # COMMAND VALUE
                    for _ in slist(c.complete_values() or []):
                        yield Completion(_, start_position=0)
                # e.g.  set  ---> ["WORKSPACE", ...]
                elif nargs == 2:  # COMMAND OPTION VALUE
                    for _ in slist(c.complete_options() or []):
                        yield Completion(_, start_position=0)
        # when two tokens are provided, handle format:
        #   COMMAND [PARTIAL_](OPTION ...|VALUE)
        elif l == 2 and c is not None:
            # when a partial value token is given, yield the list of valid ones
            # e.g.  select my-pro  ---> ["my-project", ...]
            if nargs == 1 and ts == 0:
                for _ in wfilter(slist(c.complete_values() or []), t1):
                    yield Completion(_, start_position=o1)
            # when a partial option token is given, yield the list of valid ones
            # e.g.  set W  ---> ["WORKSPACE"]
            elif nargs == 2 and ts == 0:
                for _ in wfilter(slist(c.complete_options() or []), t1):
                    yield Completion(_, start_position=o1)
            # when a valid option token is given, yield the list of values
            # e.g.  set WORKSPACE  ---> ["/home/user/...", "..."]
            elif nargs == 2 and ts > 0 and t1 in c.options:
                for _ in slist(c.complete_values(t1) or []):
                    yield Completion(_, start_position=0)
        # when three tokens are provided, handle format:
        #   COMMAND OPTION [PARTIAL_]VALUE
        elif l == 3 and c is not None and t1 in c.options:
            if nargs == 2 and ts == 0:
                for _ in wfilter(slist(c.complete_values(t1) or []), t2):
                    yield Completion(_, start_position=o2)
        # handle no other format
