import logging
logging.basicConfig(level=logging.DEBUG)
import asyncio
import simpleobsws

parameters = simpleobsws.IdentificationParameters(ignoreNonFatalRequestChecks = False) # Create an IdentificationParameters object (optional for connecting)

ws = simpleobsws.WebSocketClient(url = 'ws://localhost:4444', password = 'test', identification_parameters = parameters) # Every possible argument has been passed, but none are required. See lib code for defaults.

async def make_request():
    await ws.connect() # Make the connection to obs-websocket
    await ws.wait_until_identified() # Wait for the identification handshake to complete

    requests = []

    requests.append(simpleobsws.Request('GetVersion')) # Build a Request object, then append it to the batch
    requests.append(simpleobsws.Request('GetStats')) # Build another request object, and append it

    ret = await ws.call_batch(requests, halt_on_failure = False) # Perform the request batch

    for result in ret:
        if ret.ok(): # Check if the request succeeded
            print("Request succeeded! Response data: {}".format(ret.responseData))

    await ws.disconnect() # Disconnect from the websocket server cleanly

asyncio.run(make_request())
