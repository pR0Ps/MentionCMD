import znc
import re
import subprocess

class mentioncmd(znc.Module):
    description = "Run a command when you are mentioned or PM'd on IRC"
    module_types = [znc.CModInfo.UserModule, znc.CModInfo.NetworkModule]

    DEBUG = False

    HL_REGEX = r"(\W|\b){}(\W|\b)"

    OPTS = {
        "cmd": ("The command to execute. The network name, channel name, nick and message will be passed as params (in that order)", ""),
        "nick_blacklist": ("Nicks to ignore when they mention/PM you", ""),
        "highlights": ("Extra words/names to be notified about", ""),
        "pm_reply": ("If set, this message will be sent as a reply to users who PM you", "[znc] User is not currently connected but has been notified.")
    }
    CMDS = (
        ("help", "Shows the help text"),
        ("show", "Lists the module's configurable options"),
        ("set", "Set a config option ('set <option> <value>')"),
        ("unset", "Set a config option to '' ('unset <option>')"),
        ("default", "Set a config option back to it's default '' ('default <option>')"),
        ("test", "Send a message for testing purposes ('test <msg>')"),
        ("about", "Show information on this module")
    )

    def PutDebug(self, msg):
        if self.DEBUG:
            self.PutModule(msg)

    def on_away(fcn):
        """Wrapper to disable functionality if the user is connected"""
        def wrapper(self, *args, **kwargs):
            if self.DEBUG or not self.GetNetwork().IsUserAttached():
                return fcn(self, *args, **kwargs)
            else:
                return znc.CONTINUE
        return wrapper

    def send_notification(self, channel, nick, msg):
        """
        Calls the command to send a notification
        Note that all arguments are assumed to be plain strings
        """
        if not self.nv["cmd"]:
            self.PutModule("Error: Command to run not specified")
            return False
        try:
            network = self.GetNetwork().GetName()
            network = network if network else "[No network]"

            channel = channel if channel else "[PM]"

            self.PutDebug("Calling '{}' with args '{}', '{}', '{}', '{}'".format(self.nv["cmd"], network, channel, nick, msg))

            subprocess.call((self.nv["cmd"], network, channel, nick, msg))

            return True
        except Exception as e:
            self.PutModule("Error running cmd: {}".format(str(e)))
            return False

    def reload_config(self):
        """Reload the nv vars and re-make the regexps"""
        for opt, data in self.OPTS.items():
            self.nv[opt] = self.nv.get(opt, data[1])

        hl = self.nv["highlights"]
        self.matches = [re.compile(self.HL_REGEX.format(x), re.IGNORECASE) for x in hl.split(" ")] if hl else []

        self.blacklist = set(self.nv["nick_blacklist"].split(" "))
        self.blacklist.discard("")

    def OnLoad(self, args, message):
        """Initialize the config when the module loads"""
        self.reload_config()

        # Network -> username mapping for the user
        self.usermap = {}
        return True

    def OnClientDisconnect(self):
        """When disconnecting, store the current nick for the network"""
        network = self.GetNetwork()
        self.usermap[network.GetName()] = re.compile(self.HL_REGEX.format(network.GetNick()), re.IGNORECASE)

    @on_away
    def OnChanMsg(self, nick, channel, message):
        """Regular channel message, check for a username or highlight match"""
        message = message.s
        nick = nick.GetNick()
        channel = channel.GetName()

        if nick in self.blacklist:
            self.PutDebug("Ignored msg from '{}' on '{}': {}".format(nick, channel, message))
            return znc.CONTINUE

        name_re = self.usermap.get(self.GetNetwork().GetName(), None)
        to_check = self.matches + ([name_re] if name_re else [])
        if any(filter(lambda x: x.search(message), to_check)):
            self.send_notification(channel, nick, message)
            self.PutDebug("Message matched. msg '{}' on '{}' from '{}'".format(message, channel, nick))
        return znc.CONTINUE

    @on_away
    def OnChanAction(self, nick, channel, message):
        """
        Process action in channel ('/me tests')
        Just reformats the message and passes it to OnChanMsg
        """
        message.s = '* {} {}'.format(nick.GetNick(), message.s)
        return self.OnChanMsg(nick, channel, message)

    @on_away
    def OnPrivMsg(self, nick, message):
        """
        Processes a private message
        Will reply back to the user if 'pm_reply' is set (default)
        """
        message = message.s
        nick = nick.GetNick()
        if nick in self.blacklist:
            self.PutDebug("Ignoring private message from {}: {}".format(nick, message))
            return znc.CONTINUE

        if self.send_notification(None, nick, message) and self.nv["pm_reply"]:
            self.PutIRC("PRIVMSG {} :{}".format(nick, self.nv["pm_reply"]))
        self.PutDebug("Private message received from {}: {}".format(nick, message))
        return znc.CONTINUE

    @on_away
    def OnPrivAction(self, nick, message):
        """
        Process action in private message ('/me tests')
        Just reformats the message and passes it to OnPrivMsg
        """
        message.s = '* {} {}'.format(nick.GetNick(), message.s)
        return self.OnPrivMsg(nick, message)

    def OnModCommand(self, cmd):
        """Process commands sent to the module"""

        self.PutDebug("You said '{}'".format(cmd))
        cmds = cmd.split(" ")
        num = len(cmds)

        if cmds[0] == "help":
            self.PutModule("Commands:")
            tbl = znc.CTable();
            tbl.AddColumn("Command")
            tbl.AddColumn("Description")
            for cmd, desc in self.CMDS:
                tbl.AddRow()
                tbl.SetCell("Command", cmd)
                tbl.SetCell("Description", desc)
            self.PutModule(tbl)

            self.PutModule("Options:")
            tbl = znc.CTable();
            tbl.AddColumn("Option")
            tbl.AddColumn("Description")
            for opt, data in self.OPTS.items():
                tbl.AddRow()
                tbl.SetCell("Option", opt)
                tbl.SetCell("Description", data[0])
            self.PutModule(tbl)

        elif cmds[0] == "show":
            tbl = znc.CTable();
            tbl.AddColumn("Option")
            tbl.AddColumn("Value")
            tbl.AddColumn("Default")

            for opt, data in self.OPTS.items():
                tbl.AddRow()
                tbl.SetCell("Option", opt)
                tbl.SetCell("Value", "'{}'".format(self.nv[opt]) if self.nv[opt] != data[1] else "[default]")
                tbl.SetCell("Default", "'{}'".format(data[1]))

            self.PutModule(tbl)

        elif cmds[0] in ("set", "unset", "default"):
            if cmds[0] == "unset":
                cmds.append("")
                num += 1
            elif cmds[0] == "default":
                cmds.append(self.OPTS.get(cmds[1], (None, ""))[1])
                num += 1

            if num < 3 or cmds[0] != "set" and num > 3:
                self.PutModule("Usage: {} <option>{}".format(cmds[0], " <value>" if cmds[0] == "set" else ""))
            else:
                if cmds[1] in self.OPTS.keys():
                    value = " ".join(cmds[2:])
                    self.nv[cmds[1]] = value
                    self.PutModule("Set '{}' to '{}'".format(cmds[1], value))
                else:
                    self.PutModule("Error: Invalid option name")

            self.reload_config()

        elif cmds[0] == "test":
            temp, self.DEBUG = self.DEBUG, True

            if num < 2:
                self.PutModule("Usage: test <msg>")
            else:
                self.send_notification("#testing", "test_cmd", " ".join(cmds[1:]))

            self.DEBUG = temp
        elif cmds[0] == "about":
            self.PutModule("MentionCMD - https://github.com/pR0Ps/MentionCMD")
            self.PutModule("Made by pR0Ps")
            self.PutModule("Feel free to submit pull requests and bug reports!")
        else:
            self.PutModule("Error: Invalid command, try 'help'")

