from init import *
import pathlib,database,pandas_ta,importlib.util,logging,os,pandas,sqlalchemy.sql.expression,datetime,sys,backtrader,time,aiofiles,random,backtests,os
import managepaper,processpaper,os,traceback
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
loop = None
lastsend = None
class Portfolio(Config):
    def __init__(self, room, **kwargs) -> None:
        super().__init__(room, **kwargs)
@bot.listener.on_message_event
async def tell(room, message):
    try:
        global servers,lastsend
        logger.info(str(message))
        if not message.body.startswith(prefix) and room.member_count==2:
            message.body = prefix+' '+message.body
        match = botlib.MessageMatch(room, message, bot, prefix)
        if (match.is_not_from_this_bot() and match.prefix()):
            res = await bot.api.async_client.room_typing(room.room_id,True,timeout=30000)
        tuser = None
        if match.is_not_from_this_bot() and room.member_count==2:
            tuser = message.sender
        if match.command("change-setting"):
            set_target = None
            for server in servers:
                if server.room == room.room_id and server.name == match.args()[1]:
                    setattr(server,match.args()[2],match.args()[3])
                    set_target = server
                    break
                for apaper in server.papers:
                    if apaper['isin'] == match.args()[1]:
                        apaper[match.args()[2]] = match.args()[3]
                        set_target = apaper
                        break
                if set_target:
                    if tuser:
                        server.client = tuser
                await save_servers()
                await bot.api.send_text_message(room.room_id, 'ok')
        elif (match.is_not_from_this_bot() and match.prefix())\
        and match.command("restart"):
            pf = None
            for server in servers:
                if server.room == room.room_id:
                    pf = server
            if tuser:
                pf.client = tuser
                await save_servers()
            await bot.api.send_text_message(room.room_id, 'exitting...')
            os._exit(0)
    except BaseException as e:
        logger.error(str(e), exc_info=True)
        await bot.api.send_text_message(room,str(e))
    await bot.api.async_client.room_typing(room.room_id,False,0)
datasources = []
strategies = []
connection = None
try:
    logging.basicConfig(level=logging.INFO,format='%(asctime)s:%(levelname)s:%(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    logger.info('starting event loop...')
    loop = asyncio.new_event_loop()
    logger.info('loading config...')
    with open('data.json', 'r') as f:
        nservers = json.load(f)
        for server in nservers:
          servers.append(Portfolio(server))
except BaseException as e:
    logger.error('Failed to read data.json:'+str(e))
@bot.listener.on_startup
async def startup(room):
    global loop,servers,news_task,dates_task
    loop = asyncio.get_running_loop()
    await database.Init(loop)
    loop.create_task(restart_task())
@bot.listener.on_message_event
async def bot_help(room, message):
    bot_help_message = f"""
    Help Message:
        prefix: {prefix}
        commands:
            change-setting:
                command: change-setting setting value
                    settings:
                      - model
                      - system
            help:
                command: help, ?, h
                description: display help command
                """
    match = botlib.MessageMatch(room, message, bot, prefix)
    if match.is_not_from_this_bot() and (
       match.command("help") 
    or match.command("?") 
    or match.command("h")):
        await bot.api.send_text_message(room.room_id, bot_help_message)
async def main():
    try:
        def unhandled_exception(loop, context):
            msg = context.get("exception", context["message"])
            logger.error(f"Unhandled exception caught: {msg}")
            loop.default_exception_handler(context)
            os._exit(1)
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(unhandled_exception)
        await bot.main()
    except BaseException as e:
        logger.error('bot main fails:'+str(e),stack_info=True)
        os._exit(1)
processpaper.bot = bot
processpaper.servers = servers
processpaper.datasources = datasources
processpaper.strategies = strategies
processpaper.save_servers = save_servers
managepaper.bot = bot
managepaper.servers = servers
managepaper.datasources = datasources
managepaper.strategies = strategies
managepaper.save_servers = save_servers
async def restart_task():
    shutdown_time = datetime.datetime.now().replace(hour=7, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    time_until_shutdown = (shutdown_time - datetime.datetime.now()).total_seconds()
    await asyncio.sleep(time_until_shutdown)
    os._exit(1)
asyncio.run(main())