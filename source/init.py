import simplematrixbotlib as botlib,yaml,json,logging,asyncio,nio,pathlib,os,concurrent.futures
configpath = pathlib.Path(__file__).parent
if not (configpath / 'config.yml').exists():
    configpath = configpath.parent
    if not (configpath / 'config.yml').exists():
        if (configpath / 'data' / 'config.yml').exists():
            configpath = configpath / 'data'
        if (configpath.parent / 'data' / 'config.yml').exists():
            configpath = configpath.parent / 'data'
os.chdir(str(configpath))
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)
try: 
    prefix = config['server']['prefix']
except:
    prefix = config['server']['user']
class FailsafeBot(botlib.Bot):
    async def main(self):
        try:
            await super().main()
        except BaseException as e: 
            logging.error(str(e))
        while True:
            logging.error('Server disconnected, reconnecting ...')
            await asyncio.sleep(1)
            await self.async_client.sync_forever(timeout=30000, full_state=True)
creds = botlib.Creds(config['server']['url'], config['server']['user'], config['server']['password'])
bconfig = botlib.Config()
bconfig.encryption_enabled = True
#bconfig.emoji_verify = True
bconfig.ignore_unverified_devices = True
bconfig.store_path = str(configpath / 'crypto_store')
bot = FailsafeBot(creds,bconfig)
class Config(object):
    def __init__(self,room,**kwargs) -> None:
        if isinstance(room, dict):
            self.__dict__.update(room)
        else:
            self.room = room
            self.__dict__.update(kwargs)
loop = None
servers = []
async def save_servers():
    def clean_dict(d):
        cleaned = {}
        for k, v in d.items():
            if not k.startswith("_"):
                if isinstance(v, dict):
                    cleaned[k] = clean_dict(v)
                elif isinstance(v, list):
                    cleaned[k] = [clean_dict(i) if isinstance(i, dict) else i for i in v if not str(i).startswith("_")]
                else:
                    cleaned[k] = v
        return cleaned
    global servers
    sservers = []
    for server in servers:
        ndict = clean_dict(server.__dict__)
        sservers.append(ndict)
    with open('data.json', 'w') as f:
        json.dump(sservers,f, skipkeys=True, indent=4)
def is_valid_event(event):
    events = (nio.RoomMessageFormatted, nio.RedactedEvent)
    events += (nio.RoomMessageMedia, nio.RoomEncryptedMedia)
    return isinstance(event, events)
async def fetch_room_events(
    client,
    start_token: str,
    room,
    direction,
    limit
) -> list:
    events = []
    while len(events)<limit:
        response = await client.room_messages(
            room.room_id, start_token, limit=10, direction=direction
        )
        if len(response.chunk) == 0:
            break
        events.extend(event for event in response.chunk if is_valid_event(event))
        start_token = response.end
    return events
async def get_room_events(client, room, limit = 1):
    sync_resp = await client.sync(
        full_state=True, sync_filter={"room": {"timeline": {"limit": limit}}}
    )
    start_token = sync_resp.rooms.join[room].timeline.prev_batch
    # Generally, it should only be necessary to fetch back events but,
    # sometimes depending on the sync, front events need to be fetched
    # as well.
    events = await fetch_room_events(client,start_token,bot.api.async_client.rooms[room],nio.MessageDirection.back,limit)
    return events
async def run_in_thread(coroutine,sync=False):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Passen Sie die Coroutine an, um sie als Funktion auszuführen
        if sync:
            result = await loop.run_in_executor(executor, coroutine)
        else:
            result = await loop.run_in_executor(executor, lambda: asyncio.run(coroutine))
    return result