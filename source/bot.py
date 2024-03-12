from init import *
import os,traceback,pathlib,logging,datetime,sys,time,aiofiles,os,aiohttp,urllib.parse,ipaddress
import wol
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
loop = None
lastsend = None
class BotData(Config):
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
        if match.command("add-model"):
            server = BotData(room=room.room_id,
                url=match.args()[2],
                model=match.args()[1],
                system='You are an helpful Assistent!'
            )
            servers.append(server)
            await save_servers()
            await bot.api.send_text_message(room.room_id, 'ok')
        elif match.command("change-setting"):
            set_target = None
            for server in servers:
                if server.room == room.room_id:
                    set_target = server
            if set_target:
                server = set_target
                setattr(server,match.args()[1],' '.join(match.args()[2:]))
                set_target = server
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
        elif match.is_not_from_this_bot(): #regualr message to bot
            for server in servers:
                if server.room == room.room_id:
                    #get sure system is up
                    if hasattr(server,'wol'):
                        Status_ok = False
                        for a in range(3):
                            async def check_status():
                                try:
                                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(connect=1)) as session:
                                        async with session.post(server.url) as resp:
                                            r = await resp.text()
                                            return True
                                except: pass
                                return False
                            purl = urllib.parse.urlparse(server.url)
                            net = ipaddress.IPv4Network(purl.hostname + '/' + '255.255.255.0', False)
                            wol.WakeOnLan(server.wol,[str(net.broadcast_address)])
                            for i in range(60):
                                if await check_status() == True:
                                    logging.info('client waked up after '+str(i)+' seconds')
                                    Status_ok = True
                                    break
                            if Status_ok: break
                    #get sure model is loaded
                    await bot.api.async_client.room_typing(room.room_id,False,0)
                    headers = {"Content-Type": "application/json"}
                    if hasattr(server,'apikey'):
                        headers["Authorization"] = f"Bearer {server.apikey}"
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None)) as session:
                        ajson = {
                            "model": server.model,
                            "messages": [{"role": "system", "content": ""},
                                         {"role": "user", "content": ""}],
                        }
                        async with session.post(server.url+"/chat/completions", headers=headers, json=ajson) as resp:
                            response_json = await resp.json()
                    #ask model
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None)) as session:
                        ajson = {
                            "model": server.model,
                            "messages": [{"role": "system", "content": server.system},
                                         {"role": "user", "content": ' '.join(match.args())}],
                        }
                        if hasattr(server,'temperature'):
                            ajson['temperature'] = server.temperature
                        res = await bot.api.async_client.room_typing(room.room_id,True,timeout=300000)
                        async with session.post(server.url+"/chat/completions", headers=headers, json=ajson) as resp:
                            response_json = await resp.json()
                            await bot.api.send_text_message(room.room_id,response_json["choices"][0]['message']["content"])
    except BaseException as e:
        logger.error(str(e), exc_info=True)
        await bot.api.send_text_message(room.room_id,str(e))
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
          servers.append(BotData(server))
except BaseException as e:
    logger.error('Failed to read data.json:'+str(e))
@bot.listener.on_startup
async def startup(room):
    global loop,servers,news_task,dates_task
    loop = asyncio.get_running_loop()
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
asyncio.run(main())