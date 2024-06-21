from init import *
import os,traceback,pathlib,logging,datetime,sys,time,aiofiles,os,aiohttp,urllib.parse,ipaddress,aiohttp.web,markdown,base64
import nio.crypto,ai.llm
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
loop = None
lastsend = None
class BotData(Config):
    def __init__(self, room, **kwargs) -> None:
        super().__init__(room, **kwargs)
async def handle_message_openai(room,server,message,match):
    try:
        if not hasattr(server,'_model'):
            wol = None
            if hasattr(server,'wol'):
                wol = server.wol
            apikey = None
            if hasattr(server,'apikey'):
                apikey = server.apikey
            server._model = ai.llm.model(server.model,api=server.url,wol=wol,apikey=apikey)
        server._model.system = server.system
        #ensure variables
        if not hasattr(server,'history_count'):
            server.history_count = 15
        try: int(server.history_count)
        except: server.history_count = 0
        try: server.threading = server.threading.lower() == 'true' or server.threading == 'on'
        except: server.threading = True
        await bot.api.async_client.set_presence('unavailable','')
        #get History
        events = await get_room_events(bot.api.async_client,room.room_id,int(server.history_count*2))
        thread_rel = None
        if 'm.relates_to' in message.source['content'] and server.threading:
            thread_rel = message.source['content']['m.relates_to']['event_id']
        history = []
        if not server.threading or thread_rel:
            for event in events:
                if isinstance(event, nio.RoomMessageText):
                    if (thread_rel\
                    and 'm.relates_to' in event.source['content']\
                    and (event.source['content']['m.relates_to']['event_id'] == thread_rel)
                        ) or not thread_rel and 'm.relates_to' not in event.source['content']:
                        if event.sender == message.sender:
                            history.insert(0,{"role": "user", "content": event.body})
                        elif event.sender == bot.api.creds.username\
                        and not event.body.startswith('change-setting ')\
                        and not event.body.startswith('add-model '):
                            history.insert(0,{"role": "assistant", "content": event.body})
                    elif event.source['event_id'] == thread_rel:
                        history.insert(0,{"role": "user", "content": event.body})
                if len(history)>int(server.history_count):
                    break
        if len(history)>0:
            history.pop()
        images = []
        if match:
            words = match.args()
            if words == [] or words[0] != match.command():
                words = [match.command()]+words
        elif hasattr(message,'url'):
            words = ['what','shows','this','image','?']
            target_folder = configpath / 'files' / room.room_id[1:room.room_id.find(':')-2] / message.event_id
            with open(target_folder / message.body, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
            images.append(encoded_string)
        #ask model
        if hasattr(server,'keep_alive'):
            server._model.kwargs['keep_alive'] = server.keep_alive
        """
        for param in ['seed']:
            if hasattr(server,param):
                ajson[param] = getattr(server,param)
        for param in ['temperature','top_p','max_tokens','frequency_penalty','presence_penalty']:
            if hasattr(server,param):
                try:
                    ajson[param] = float(getattr(server,param))
                except: logging.warning('failed to set parameter:'+param)
        """
        res = await bot.api.async_client.room_typing(room.room_id,True,timeout=300000)
        message_p = await server._model.query(' '.join(words),history,images=images)
        if not thread_rel:
            thread_rel = message.event_id
        if message_p:
            msgc = {
                    "msgtype": "m.text",
                    "body": message_p,
                    "format": "org.matrix.custom.html",
                    "formatted_body": markdown.markdown(message_p,
                                                        extensions=['fenced_code', 'nl2br'])
                }
            if server.threading:
                msgc['m.relates_to'] = {
                        "event_id": thread_rel,
                        "rel_type": "m.thread",
                        "is_falling_back": True,
                        "m.in_reply_to": {
                            "event_id": message.event_id
                        }
                    }
            await bot.api.async_client.room_send(room.room_id,'m.room.message',msgc)
    except BaseException as e:
        logger.error(str(e), exc_info=True)
        await bot.api.send_text_message(room.room_id,str(e))
    await bot.api.async_client.room_typing(room.room_id,False,0)
async def handle_message_comfui(room,server,message,match):
    async def check_param(param_name):
        if not hasattr(server,'history_count'):
            server.history_count = 15
        try: int(server.history_count)
        except: server.history_count = 0
        try: server.threading = server.threading.lower() == 'true' or server.threading == 'on'
        except: server.threading = True
        events = await get_room_events(bot.api.async_client,room.room_id,int(server.history_count*2))
        name_found = False
        msgc = {
                "msgtype": "m.text",
            }
        if thread_rel:
            msgc['m.relates_to'] = {
                    "event_id": thread_rel,
                    "rel_type": "m.thread",
                    "is_falling_back": True,
                    "m.in_reply_to": {
                        "event_id": message.event_id
                    }
                }
        if not server.threading or thread_rel:
            for event in reversed(events):
                if isinstance(event, nio.RoomMessageText):
                    if (thread_rel\
                    and 'm.relates_to' in event.source['content']\
                    and event.source['content']['m.relates_to']['event_id'] == thread_rel
                        ) or not thread_rel and 'm.relates_to' not in event.source['content']:
                        if name_found:
                            return event.body
                        if param_name in event.body:
                            name_found = True
        msgc['body'] = 'please enter variable '+str(param_name)
        await bot.api.async_client.room_send(room.room_id,'m.room.message',msgc)
        return False
    try:
        response_json = None
        thread_rel = None
        if 'm.relates_to' in message.source['content'] and server.threading:
            thread_rel = message.source['content']['m.relates_to']['event_id']
        if not thread_rel:
            thread_rel = message.event_id
        workflow = await check_param('workflow')
        if workflow == False: return False
        #get sure system is up
        if hasattr(server,'wol'):
            Status_ok = False
            async def check_status():
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(connect=1)) as session:
                        async with session.post(server.url) as resp:
                            r = await resp.text()
                            return True
                except: pass
                return False
            for a in range(3):
                purl = urllib.parse.urlparse(server.url)
                net = ipaddress.IPv4Network(purl.hostname + '/' + '255.255.255.0', False)
                wol.WakeOnLan(server.wol,[str(net.broadcast_address)])
                for i in range(60):
                    if await check_status() == True:
                        logging.info('client waked up after '+str(i)+' seconds')
                        Status_ok = True
                        break
                if Status_ok: break
            if not Status_ok: 
                await bot.api.send_text_message(room.room_id,'failed to wakeup Server')
                await bot.api.async_client.room_typing(room.room_id,False,0)
                return False

    except BaseException as e:
        logger.error(str(e)+'\n'+str(response_json), exc_info=True)
        await bot.api.send_text_message(room.room_id,str(e))
    await bot.api.async_client.room_typing(room.room_id,False,0)
async def handle_image(room,image):
    try:
        if not hasattr(server,'_model'):
            wol = None
            if hasattr(server,'wol'):
                wol = server.wol
            apikey = None
            if hasattr(server,'apikey'):
                apikey = server.apikey
            server._model = ai.llm.model(server.model,api=server.url,wol=wol,apikey=apikey)
        server._model.system = server.system
        #ensure variables
        if not hasattr(server,'history_count'):
            server.history_count = 15
        try: int(server.history_count)
        except: server.history_count = 0
        try: server.threading = server.threading.lower() == 'true' or server.threading == 'on'
        except: server.threading = True
    
    except BaseException as e:
        logger.error(str(e), exc_info=True)
        await bot.api.send_text_message(room.room_id,str(e))

@bot.listener.on_custom_event(nio.RoomEncryptedMedia)
async def enc_file(room,event):
    try:
        target_folder = configpath / 'files' / room.room_id[1:room.room_id.find(':')-2] / event.event_id
        response = await bot.async_client.download(mxc=event.url)
        pathlib.Path(target_folder).mkdir(parents=True,exist_ok=True)
        async with aiofiles.open(str(target_folder / event.body), "wb") as f:
            await f.write(
                nio.crypto.attachments.decrypt_attachment(
                    response.body,
                    event.source["content"]["file"]["key"]["k"],
                    event.source["content"]["file"]["hashes"]["sha256"],
                    event.source["content"]["file"]["iv"],
                )
            )
        for server in servers:
            if server.room == room.room_id:
                loop = asyncio.get_running_loop()
                api = 'openai'
                if hasattr(server,'api'):
                    api = getattr(server,'api')
                if api == 'openai':
                    loop.create_task(handle_message_openai(room,server,event,None))
    except BaseException as e:
        logger.error(str(e), exc_info=True)
@bot.listener.on_custom_event(nio.RoomMessageMedia)
async def file(room,event):
    try:
        target_folder = configpath / 'files' / room.room_id[1:room.room_id.find(':')-2] / event.event_id
        response = await bot.async_client.download(mxc=event.url)
        pathlib.Path(target_folder).mkdir(parents=True,exist_ok=True)
        async with aiofiles.open(str(target_folder / event.body), "wb") as f:
            await f.write(response.transport_response._body)
        for server in servers:
            if server.room == room.room_id:
                loop = asyncio.get_running_loop()
                api = 'openai'
                if hasattr(server,'api'):
                    api = getattr(server,'api')
                if api == 'openai':
                    loop.create_task(handle_message_openai(room,server,event,None))
    except BaseException as e:
        logger.error(str(e), exc_info=True)
@bot.listener.on_message_event
async def tell(room, message):
    try:
        global servers,lastsend
        logger.info(str(message))
        if not message.body.startswith(prefix) and room.member_count==2:
            message.body = prefix+' '+message.body
        match = botlib.MessageMatch(room, message, bot, prefix)
        match2 = botlib.MessageMatch(room, message, bot, ' * ')
        tuser = None
        if match.is_not_from_this_bot() and room.member_count==2:
            tuser = message.sender
        if match.command("add-model"):
            set_target = None
            for server in servers:
                if server.room == room.room_id:
                    set_target = server
            if not set_target:
                server = BotData(room=room.room_id,
                    url=match.args()[2],
                    model=match.args()[1],
                    system='You are an helpful Assistent!'
                )
            else:
                server = set_target
                server.url = match.args()[2]
                server.model = match.args()[1]
            servers.append(server)
            await save_servers()
            await bot.api.send_text_message(room.room_id, 'ok')
        elif match.command("add-comfui"):
            server = BotData(room=room.room_id,
                url=match.args()[1],
                api='comfui'
            )
            servers.append(server)
            await save_servers()
            await bot.api.send_text_message(room.room_id, 'ok')
        elif match.command("change-setting") or match2.command("change-setting"):
            set_target = None
            if match2.command("change-setting"):
                match = match2
            for server in servers:
                if server.room == room.room_id:
                    set_target = server
            if set_target:
                server = set_target
                tattr = message.body[message.body.find('change-setting')+15:]
                tval = tattr[tattr.find(' ')+1:]
                tattr = tattr[:tattr.find(' ')].replace('\\_','_')
                setattr(server,tattr,tval)
                set_target = server
                await save_servers()
                if match != match2:
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
        elif (match.is_not_from_this_bot() and match.prefix())\
        and match.command("help"):
            pass #ignore help command
        elif match.is_not_from_this_bot(): #regualr message to bot
            for server in servers:
                if server.room == room.room_id:
                    loop = asyncio.get_running_loop()
                    api = 'openai'
                    if hasattr(server,'api'):
                        api = getattr(server,'api')
                    if api == 'openai':
                        loop.create_task(handle_message_openai(room,server,message,match))
                        break
                    elif api == 'comfui':
                        loop.create_task(handle_message_comfui(room,server,message,match))
                        break
    except BaseException as e:
        logger.error(str(e)+'\n'+str(response_json), exc_info=True)
        await bot.api.send_text_message(room.room_id,str(e))
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
@bot.listener.on_message_event
async def bot_help(room, message):
    bot_help_message = f"""
    Help Message:
        prefix: {prefix}
        commands:
            add-model:
                command: add-model model openai-compatible-url
            add-comfui:
                command: add-comfui comfui-base-url
            change-setting:
                command: change-setting setting value
                    settings:
                      - model
                      - system
                      - apikey
                      - threading (bool, answer in threads and use thread content as history)
                      - wol (mac address of system that should be waked up)
                      - history_count (amount of messages sof history send to the model to have context)
                      - temperature
                      - seed
                      - top_p
                      - max_tokens
                      - frequency_penalty
                      - presence_penalty
                      - keep_alive
            help:
                command: help, ?
                description: display help command
                """
    match = botlib.MessageMatch(room, message, bot, prefix)
    if match.is_not_from_this_bot() and (
       match.command("help") 
    or match.command("?")):
        await bot.api.send_text_message(room.room_id, bot_help_message)
async def status_handler(request):
    return aiohttp.web.Response(text="OK")
async def startup():
    for i in range(15):
        await asyncio.sleep(1)
        try:
            if bot.api.async_client.logged_in:
                await bot.api.async_client.set_presence('unavailable','')
                return
        except:pass
async def main():
    try:
        def unhandled_exception(loop, context):
            msg = context.get("exception", context["message"])
            logger.error(f"Unhandled exception caught: {msg}")
            loop.default_exception_handler(context)
            os._exit(1)
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(unhandled_exception)
        app = aiohttp.web.Application()
        app.add_routes([aiohttp.web.get('/status', status_handler)])
        runner = aiohttp.web.AppRunner(app, access_log=None)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner,port=9998)    
        await site.start()
        loop.create_task(startup())
        await bot.main()
    except BaseException as e:
        logger.error('bot main fails:'+str(e),stack_info=True)
        os._exit(1)
asyncio.run(main())