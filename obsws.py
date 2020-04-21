import asyncio
import websockets
import base64
import hashlib
import json
import uuid
import time
import sys

async def obsws_init_connection(uri, password=None):
    global ws
    ws = await websockets.connect(uri)
    request_id = str(uuid.uuid1())
    requestpayload = {'message-id':request_id, 'request-type':'GetAuthRequired'}
    await ws.send(json.dumps(requestpayload))
    result = json.loads(await ws.recv())
    if result['status'] != 'ok':
        raise Exception('OBSWS Error: {}'.format(result['error']))
    if result['authRequired']:
        if password == None:
            raise Exception('A password is required but was not provided')
        secret = base64.b64encode(hashlib.sha256((password + result['salt']).encode('utf-8')).digest())
        auth = base64.b64encode(hashlib.sha256(secret + result['challenge'].encode('utf-8')).digest()).decode('utf-8')
        auth_payload = {"request-type": "Authenticate", "message-id": str(uuid.uuid1()), "auth": auth}
        await ws.send(json.dumps(auth_payload))
        result = json.loads(await ws.recv())
        if result['status'] != 'ok':
            raise Exception('OBSWS Error: {}'.format(result['error']))
    global ws_answers
    ws_answers = {}
    loop.create_task(obsws_recv_task())

async def obsws_call(request_type, data=None, timeout=30):
    global ws_answers
    if type(data) != dict and data != None:
        raise Exception('Input data must be valid dict object')
    request_id = str(uuid.uuid1())
    requestpayload = {'message-id':request_id}
    requestpayload['request-type'] = request_type
    if data != None:
        for key in data.keys():
            requestpayload[key] = data[key]
    await ws.send(json.dumps(requestpayload))
    waittimeout = time.time() + timeout
    await asyncio.sleep(0.05)
    while time.time() < waittimeout:
        if request_id in ws_answers:
            returndata = ws_answers.pop(request_id)
            returndata.pop('message-id')
            return returndata
        await asyncio.sleep(0.1)
    raise Exception('The request with type {} timed out after () seconds.'.format(request_type, timeout))
    

async def obsws_recv_task():
    global ws_answers
    try:
        while ws.open:
            message = ''
            message = await ws.recv()
            if not message:
                continue
            result = json.loads(message)
            if 'update-type' in result:
                update_type = result['update-type']
                del result['update-type']
                await obsws_handle_event(update_type, result)
            elif 'message-id' in result:
                ws_answers[result['message-id']] = result
            else:
                print('Unknown message: {}'.format(result))
    except:
        pass
    print('OBSWS connection has been closed.')
    raise KeyboardInterrupt


async def obsws_handle_event(update_type, data=None):
    pass
    print(update_type)
    print(data)

async def test_task():
    await asyncio.sleep(2)
    print(await obsws_call('ListSceneCollections'))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(obsws_init_connection('ws://127.0.0.1:4444', 'ttpass'))
    loop.create_task(test_task())
    loop.run_forever()
