MentionCMD
==========

MentionCMD is a Python module for the [ZNC](http://znc.in) IRC bouncer. Its
purpose is to notify users that are disconnected from the bouncer when they are
mentioned or PM'd.

MentionCMD looks at the IRC traffic, figures out when the user has been
mentioned, and runs a configurable shell command. It's the users responsibility
to do something useful with the command.

Installation
------------
1. Make sure [`modpython`](http://wiki.znc.in/Modpython) is loaded
2. Drop the `mentioncmd.py` file in the ZNC modules directory.
3. Load the module using `/msg *status loadmodule mentioncmd`
    - By default, the module is loaded at the user level so the user will get
      notifications for all networks they are connected to.
    - To load the module at a network level insted use
      `/msg *status loadmodule --type=network mentioncmd`

Configuration
-------------
To see a list of commands and configuration options, type `/msg *mentioncmd help`

At bare minimum, the `cmd` option will need to be configured to point to an
external script so MentionCMD has something to run.

For example, setting `cmd` by typing
`/msg *mentioncmd set cmd /var/lib/znc/.znc/notify.sh` will cause `mentioncmd`
to execute the following command:

```bash
/var/lib/znc/.znc/notify.sh <network> <channel> <nick> <msg>
```

There are a few other options that can be set including auto-replies and words
to look for. See the help text for more information.
