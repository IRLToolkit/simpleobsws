import asyncio
import simpleobsws

loop = asyncio.get_event_loop()
ws = simpleobsws.obsws(host='127.0.0.1', port=4444, password='MYSecurePassword', loop=loop) # Every possible argument has been passed, but none are required. See lib code for defaults.

async def on_event(data):
    print('New event! Type: {} | Raw Data: {}'.format(data['update-type'], data)) # Print the event data. Note that `update-type` is also provided in the data

async def on_switchscenes(data):
    print('Scene switched to "{}". It has these sources: {}'.format(data['scene-name'], data['sources']))

loop.run_until_complete(ws.connect())
ws.register(on_event) # By not specifying an event to listen to, all events are sent to this callback.
ws.register(on_switchscenes, 'SwitchScenes')
loop.run_forever()
