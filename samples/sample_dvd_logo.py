import logging
logging.basicConfig(level=logging.INFO)
import os
import asyncio
import json
import simpleobsws
import random

password = 'pp123'
url = 'ws://127.0.0.1:4444'

dvdStageSceneName = 'dvd'
dvdStageSourceName = 'dvdIcon'

# Velocity range, in pixels-per-frame
velocityMin = 2.5
velocityMax = 4.5

# =============== NO NEED TO CHANGE ANYTHING BELOW ===============

ws = simpleobsws.WebSocketClient(url=url, password=password)

# Runtime constants
obsXResolution = 0
obsYResolution = 0
sceneItemId = 0

# X and Y values for the true width and height of the scene item
sceneItemWidth = 0
sceneItemHeight = 0

# The "current" position of the scene item on the screen
currentXPosition = 0
currentYPosition = 0

# The starting velocity of the scene item
xTransformVelocity = 3
yTransformVelocity = 3

def is_positive(number):
    return number > 0

async def init():
    await ws.connect()
    await ws.wait_until_identified()
    logging.info('Connected and identified.')

    global obsXResolution
    global obsYResolution
    req = simpleobsws.Request('GetVideoSettings')
    ret = await ws.call(req)
    if not ret.ok():
        logging.error('Failed to fetch OBS info!')
        return False
    obsXResolution = ret.responseData['baseWidth']
    obsYResolution = ret.responseData['baseHeight']

    global sceneItemId
    req = simpleobsws.Request('GetSceneItemId', {'sceneName': dvdStageSceneName, 'sourceName': dvdStageSourceName})
    ret = await ws.call(req)
    if not ret.ok():
        logging.error('Failed to fetch scene item ID!')
        return False
    sceneItemId = ret.responseData['sceneItemId']

    global sceneItemWidth
    global sceneItemHeight
    req = simpleobsws.Request('GetSceneItemTransform', {'sceneName': dvdStageSceneName, 'sceneItemId': sceneItemId})
    ret = await ws.call(req)
    if not ret.ok():
        logging.error('Failed to fetch scene item transform!')
        return False
    cropLeft = ret.responseData['sceneItemTransform']['cropLeft']
    cropRight = ret.responseData['sceneItemTransform']['cropRight']
    cropTop = ret.responseData['sceneItemTransform']['cropTop']
    cropBottom = ret.responseData['sceneItemTransform']['cropBottom']

    # Funky math. In order to get the true width and height of the scene item, we need to take the sum of the source dimensions and the crop values, *then* apply the scale value, as scale is applied last in OBS.
    sceneItemWidth = (ret.responseData['sceneItemTransform']['sourceWidth'] - cropLeft - cropRight) * ret.responseData['sceneItemTransform']['scaleX']
    sceneItemHeight = (ret.responseData['sceneItemTransform']['sourceHeight'] - cropTop - cropBottom) * ret.responseData['sceneItemTransform']['scaleY']

    return True

async def calc_batch():
    global currentXPosition
    global currentYPosition
    global xTransformVelocity
    global yTransformVelocity

    # Generate 180 frame requests (Number can be changed. Smaller is actually generally better.)
    ret = []
    for i in range(180):
        # Apply velocity to the position for the current frame.
        currentXPosition += xTransformVelocity
        currentYPosition += yTransformVelocity

        # If edge is reached, generate a new velocity and reverse direction.
        newVelocity = random.randrange(velocityMin * 100, velocityMax * 100) / 100
        if is_positive(xTransformVelocity) and currentXPosition >= (obsXResolution - sceneItemWidth):
            xTransformVelocity = -newVelocity
        elif not is_positive(xTransformVelocity) and currentXPosition <= 0:
            xTransformVelocity = newVelocity
        if is_positive(yTransformVelocity) and currentYPosition >= (obsYResolution - sceneItemHeight):
            yTransformVelocity = -newVelocity
        elif not is_positive(yTransformVelocity) and currentYPosition <= 0:
            yTransformVelocity = newVelocity

        # Generate the requests for the current frame
        sceneItemTransform = {}
        sceneItemTransform['positionX'] = currentXPosition
        sceneItemTransform['positionY'] = currentYPosition
        ret.append(simpleobsws.Request('SetSceneItemTransform', {'sceneName': dvdStageSceneName, 'sceneItemId': sceneItemId, 'sceneItemTransform': sceneItemTransform}))
        ret.append(simpleobsws.Request('Sleep', {'sleepFrames': 1}))
    return ret

async def update_loop():
    # First, initialize the scene item to the corner of the screen.
    req = simpleobsws.Request('SetSceneItemTransform', {'sceneName': dvdStageSceneName, 'sceneItemId': sceneItemId, 'sceneItemTransform': {'positionX': 0, 'positionY': 0}})
    await ws.call(req)

    # Call a batch, wait for it to finish, then call a new one infinitely.
    while True:
        # Generate a new batch of per-frame requests.
        requests = await calc_batch()
        # Send it, wait for response
        responses = await ws.call_batch(requests, halt_on_failure = True, execution_type = simpleobsws.RequestBatchExecutionType.SerialFrame)
        # Stop sending new requests if they start failing.
        if len(requests) != len(responses):
            logging.warning('Received {} responses for {} requests!'.format(len(responses), len(requests)))
            break

loop = asyncio.get_event_loop()

if not loop.run_until_complete(init()):
    os._exit(1)

loop.create_task(update_loop())

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
except:
    logging.exception('Exception:\n')
finally:
    loop.run_until_complete(ws.disconnect())
