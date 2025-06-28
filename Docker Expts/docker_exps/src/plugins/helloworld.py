from errbot import BotPlugin, botcmd

class HelloWorld(BotPlugin):
    @botcmd
    def helloworld(self, msg, args):
        """Responds with 'Hello, World!'"""
        return "Hello, World!"