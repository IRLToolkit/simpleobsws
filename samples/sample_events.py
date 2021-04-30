import asyncio
import simpleobsws

parameters = simpleobsws.IdentificationParameters(ignoreInvalidMessages=False, ignoreNonFatalRequestChecks=False) # Create an IdentificationParameters object (optional for connecting)
ws = simpleobsws.WebSocketClient(host='localhost', port=4444, password='test', identification_parameters=parameters, call_poll_delay=100) # Every possible argument has been passed, but none are required. See lib code for defaults.

async def on_event(eventData):
    print('New event! Type: {} | Raw Data: {}'.format(eventData['update-type'], eventData)) # Print the event data. Note that `update-type` is also provided in the data

async def on_switchscenes(eventData):
    print('Scene switched to "{}".'.format(eventData['sceneName']))

async def init():
    await ws.connect()
    await ws.wait_until_identified()

loop = asyncio.get_event_loop()
loop.run_until_complete(init())
ws.register_event_callback(on_event) # By not specifying an event to listen to, all events are sent to this callback.
ws.register_event_callback(on_switchscenes, 'SwitchScenes')
loop.run_forever()
