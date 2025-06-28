from errbot import BotPlugin, botcmd

class MyPriorLife(BotPlugin):
    @botcmd
    def mypriorlife(self, msg, args):
        """Responds with 'In My Prior Life I was a Cat ! Now I am a Bot!'"""
        return "In My Prior Life I was a Cat ! Now I am a Bot!"