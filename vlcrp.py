import asyncio
import aiohttp
from PyRP import rp
import json
import addict
import xmltodict
import datetime

with open('config.json') as f:
    config = addict.Dict(json.load(f))

loop = asyncio.ProactorEventLoop()  # NOTE: Doesn't work on UNIX

rpc = rp.DiscordRPC(str(config.discord.client_id), loop, False)
ip = config.vlc.ip

async def get_data():
    try:
        auth = aiohttp.BasicAuth('', config.vlc.password)
        async with aiohttp.ClientSession(auth=auth) as cs:
            async with cs.get(f'http://{ip}/requests/status.xml') as r:
                text = await r.text()
    except aiohttp.client_exceptions.ClientConnectorError:
        return None

class Track:  # Todo for Py3.7: Turn into dataclass
    def __init__(self, filename, artist=None, album=None, title=None, length: int = None, now: int = None, state=None):
        self.filename = filename
        self.artist = artist
        self.album = album
        self.title = title
        self.length = length
        self.state = state
        self.now = now

async def send_rp_data(trk, stopped):
    payload = addict.Dict({
        "details": "",
        "assets": {
            'large_text': 'VLC Media Player',
            'large_image': 'cone'
        },
    })

    if not stopped:
        filename = trk.filename
        title = trk.title
        name = title or filename
        current = trk.length - trk.now
        playing = (trk.state == 'playing')
        album = trk.album
        payload.details = f"{'' if not trk.artist else f'{trk.artist} - '}{name}"
        payload.state = album if album else ('Playing' if playing else 'Paused')
        payload.assets.small_text = 'Playing' if playing else 'Paused'
        payload.assets.small_image = 'play' if playing else 'pause'
    else: 
        payload.details = stopped.title()

    await rpc.send_rich_presence(payload.to_dict())

def parse(thing):
    a = ['album', 'filename', 'date', 'artist', 'title']
    b = addict.Dict()
    if isinstance(thing, addict.Dict):
        try:
            awau = a.index(thing['@name'])
            b[a[awau]] = thing['#text']
        except ValueError:
            return None
        return b
    for i in thing:
        i = addict.Dict(i)
        try:
            awau = a.index(i['@name'])
            b[a[awau]] = i['#text']
        except Exception:
            continue
    return b


async def run():
    print('''VLC Media Player - Rich Presence for Discord
by ry00001
This software is open-source
Starting up...''')
    await rpc.start()
    while True:
        try:
            data = await get_data()
            if data is None:
                print('VLC exit detected. Exiting...')
                rpc.close()
                break
            data = addict.Dict(xmltodict.parse(data)).root
            if data.state == 'stopped':
                await send_rp_data(None, 'stopped')
                continue
            thing = parse(data.information.category[0].info)
            if thing is None:
                continue
            title = thing.title
            filename = thing.filename
            artist = thing.artist
            date = thing.date
            album = thing.album
            total = int(data.length)
            now = int(data.time)
            state = data.state
            track = Track(filename, title=title, now=now, length=total, state=state, artist=artist, album=album)
            await send_rp_data(track, False)
            await asyncio.sleep(1)
        except RuntimeError:
            print('Shutting down...')
            rpc.close()
            break

try:
    loop.run_until_complete(run())
except:
    pass

