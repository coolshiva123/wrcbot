from errbot import BotPlugin, botcmd

class Alive(BotPlugin):
    @botcmd
    def alive(self, msg, args):
        """Responds with 'Yes !! I'm alive!'"""
        return "Yes !! I'm alive!"