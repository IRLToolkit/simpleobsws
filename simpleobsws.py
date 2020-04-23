import asyncio
import websockets
import base64
import hashlib
import json
import uuid
import time
import inspect

class ConnectionFailure(Exception):
    pass
class MessageTimeout(Exception):
    pass
class MessageFormatError(Exception):
    pass
class EventRegistrationError(Exception):
    pass

class obsws:
    def __init__(self, host='localhost', port=4444, password=None, loop: asyncio.BaseEventLoop=None):
        self.ws = None
        self.answers = {}
        self.loop = loop or asyncio.get_event_loop()
        self.recv_task = None
        self.event_functions = []

        self.host = host
        self.port = port
        self.password = password

    async def connect(self):
        if self.ws != None and self.ws.open:
            raise ConnectionFailure('Server is already connected.')
        self.ws = await websockets.connect('ws://{}:{}'.format(self.host, self.port))
        requestpayload = {'message-id':'1', 'request-type':'GetAuthRequired'}
        await self.ws.send(json.dumps(requestpayload))
        getauthresult = json.loads(await self.ws.recv())
        if getauthresult['status'] != 'ok':
            raise ConnectionFailure('Server returned error to GetAuthRequired request: {}'.format(getauthresult['error']))
        if getauthresult['authRequired']:
            if self.password == None:
                raise ConnectionFailure('A password is required by the server but was not provided')
            secret = base64.b64encode(hashlib.sha256((self.password + getauthresult['salt']).encode('utf-8')).digest())
            auth = base64.b64encode(hashlib.sha256(secret + getauthresult['challenge'].encode('utf-8')).digest()).decode('utf-8')
            auth_payload = {"request-type": "Authenticate", "message-id": '2', "auth": auth}
            await self.ws.send(json.dumps(auth_payload))
            authresult = json.loads(await self.ws.recv())
            if authresult['status'] != 'ok':
                raise ConnectionFailure('Server returned error to Authenticate request: {}'.format(authresult['error']))
        self.recv_task = self.loop.create_task(self._ws_recv_task())

    async def disconnect(self):
        await self.ws.close()
        self.recv_task.cancel()
        self.recv_task = None

    async def call(self, request_type, data=None, timeout=15):
        if type(data) != dict and data != None:
            raise MessageFormatError('Input data must be valid dict object')
        request_id = str(uuid.uuid1())
        requestpayload = {'message-id':request_id, 'request-type':request_type}
        if data != None:
            for key in data.keys():
                if key == 'message-id':
                    continue
                requestpayload[key] = data[key]
        await self.ws.send(json.dumps(requestpayload))
        waittimeout = time.time() + timeout
        await asyncio.sleep(0.05) # This acts to halve request time on LAN connections for most requests.
        while time.time() < waittimeout:
            if request_id in self.answers:
                returndata = self.answers.pop(request_id)
                returndata.pop('message-id')
                return returndata
            await asyncio.sleep(0.1) # Default timeout period. Change this to adjust the polling period for new messages.
        raise MessageTimeout('The request with type {} timed out after {} seconds.'.format(request_type, timeout))

    async def emit(self, request_type, data=None):
        if type(data) != dict and data != None:
            raise MessageFormatError('Input data must be valid dict object')
        request_id = str(uuid.uuid1())
        requestpayload = {'message-id':'emit_{}'.format(request_id), 'request-type':request_type}
        if data != None:
            for key in data.keys():
                if key == 'message-id':
                    continue
                requestpayload[key] = data[key]
        await self.ws.send(json.dumps(requestpayload))

    def register(self, function, event=None):
        if inspect.iscoroutinefunction(function) == False:
            raise EventRegistrationError('Registered functions must be async')
        else:
            self.event_functions.append((function, event))

    def unregister(self, function, event=None):
        for c, t in self.event_functions:
            if (c == function) and (event == None or t == event):
                self.event_functions.remove((c, t))

    async def _ws_recv_task(self):
        while self.ws.open:
            message = ''
            try:
                message = await self.ws.recv()
                if not message:
                    continue
                result = json.loads(message)
                if 'update-type' in result:
                    for callback, trigger in self.event_functions:
                        if trigger == None or trigger == result['update-type']:
                            self.loop.create_task(callback(result))
                elif 'message-id' in result:
                    if result['message-id'].startswith('emit_'): # We drop any responses to emit requests to not leak memory
                        continue
                    self.answers[result['message-id']] = result
                else:
                    print('Unknown message: {}'.format(result))
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                break
