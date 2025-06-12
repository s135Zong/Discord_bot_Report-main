# ** author: Nazome-Tamaki **
#v--------------Discord_import--------------v#
import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound
#v---------------Other_import---------------v#
import asyncio
import datetime
import json
import os
#v------------Data_preprocessing------------v#
with open('Discord_bot_Report\json\setting.json', 'r', encoding='utf8') as jfile:
    setting_json = json.load(jfile)
#-----------------------------------------------------------------------------------------------
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='&', help_command=None, intents=discord.Intents.all())
    
    async def setup_hook(self):
        now = datetime.datetime.now()

        print(f'{now} @Report >> Report is onlineing <<')
        cmds_path = './Discord_bot_Report/cmds'
        folders = await asyncio.to_thread(os.listdir, cmds_path)

        for foldername in folders:
            folder_path = os.path.join(cmds_path, foldername)
            if not os.path.isdir(folder_path):
                continue
                
            files = await asyncio.to_thread(os.listdir, folder_path)
            for filename in files:
                if filename.endswith('.py'):
                    await self.load_extension(f'cmds.{foldername}.{filename[:-3]}')
        print(f'{now} @Report >> Report is ready <<')

        await self.tree.sync()

    async def on_ready(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='N/A'))



bot = Bot()



@bot.event
async def on_command_error(error): # 忽視指令錯誤報錯資訊
    if isinstance(error, CommandNotFound):
        return
    raise error
#-----------------------------------------------------------------------------------------------
if __name__=='__main__':
    bot.run(setting_json['TOKEN'])