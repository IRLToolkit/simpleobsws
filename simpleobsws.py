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
    def __init__(self, host='localhost', port=4444, password=None, call_poll_delay=100, loop: asyncio.BaseEventLoop=None):
        self.ws = None
        self.answers = {}
        self.loop = loop or asyncio.get_event_loop()
        self.recv_task = None
        self.event_functions = []
        self.call_poll_delay = call_poll_delay / 1000

        self.host = host
        self.port = port
        self.password = password

    async def connect(self):
        if self.ws != None and self.ws.open:
            raise ConnectionFailure('Server is already connected')
        self.answers = {}
        self.ws = await websockets.connect('ws://{}:{}'.format(self.host, self.port), max_size=2**23)
        self.recv_task = self.loop.create_task(self._ws_recv_task())
        authResponse = await self.call('GetAuthRequired')
        if authResponse['status'] != 'ok':
            await self.disconnect()
            raise ConnectionFailure('Server returned error to GetAuthRequired request: {}'.format(authResponse['error']))
        if authResponse['authRequired']:
            if self.password == None:
                await self.disconnect()
                raise ConnectionFailure('A password is required by the server but was not provided')
            secret = base64.b64encode(hashlib.sha256((self.password + authResponse['salt']).encode('utf-8')).digest())
            auth = base64.b64encode(hashlib.sha256(secret + authResponse['challenge'].encode('utf-8')).digest()).decode('utf-8')
            authResult = await self.call('Authenticate', {'auth':auth})
            if authResult['status'] != 'ok':
                await self.disconnect()
                raise ConnectionFailure('Server returned error to Authenticate request: {}'.format(authresult['error']))

    async def disconnect(self):
        await self.ws.close()
        if self.recv_task != None:
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
        await asyncio.sleep(self.call_poll_delay / 2)
        while time.time() < waittimeout:
            if request_id in self.answers:
                returndata = self.answers.pop(request_id)
                returndata.pop('message-id')
                return returndata
            await asyncio.sleep(self.call_poll_delay)
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
