from errbot import BotPlugin, botcmd

class TryMe(BotPlugin):
    @botcmd
    def tryme(self, msg, args):
        """Responds with 'It Works!'"""
        return "It Works!"