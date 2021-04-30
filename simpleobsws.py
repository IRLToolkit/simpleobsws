import logging
wsLogger = logging.getLogger('websockets')
wsLogger.setLevel(logging.INFO)
log = logging.getLogger(__name__)
import asyncio
import websockets
import base64
import hashlib
import json
import uuid
import time
import inspect
import enum
from dataclasses import dataclass

RPC_VERSION = 1

@dataclass
class IdentificationParameters:
    ignoreInvalidMessages: bool = None
    ignoreNonFatalRequestChecks: bool = None
    eventSubscriptions: int = None

@dataclass
class Request:
    requestType: str
    requestData: dict = None

@dataclass
class RequestStatus:
    result: bool = False
    code: int = 0
    comment: str = None

@dataclass
class RequestResponse:
    requestType: str
    requestStatus: RequestStatus = RequestStatus()
    responseData: dict = None

    def has_data(self):
        return responseData != None

    def ok(self):
        return requestStatus.result

class MessageTimeout(Exception):
    pass
class EventRegistrationError(Exception):
    pass
class NotIdentifiedError(Exception):
    pass

class WebSocketClient:
    def __init__(self,
        host: str = 'localhost',
        port: int = 4444,
        password: str = '',
        identification_parameters: IdentificationParameters = IdentificationParameters(),
        call_poll_delay=100,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.identification_parameters = identification_parameters
        self.call_poll_delay = call_poll_delay / 1000
        self.loop = asyncio.get_event_loop()

        self.ws = None
        self.answers = {}
        self.identified = False
        self.recv_task = None
        self.event_handlers = []
        self.hello_message = None

    async def connect(self):
        if self.ws != None and self.ws.open:
            log.debug('WebSocket session is already open. Returning early.')
            return False
        self.answers = {}
        self.recv_task = None
        self.identified = False
        self.hello_message = None
        self.ws = await websockets.connect('ws://{}:{}'.format(self.host, self.port), max_size=2**23)
        self.recv_task = self.loop.create_task(self._ws_recv_task())
        return True

    async def wait_until_identified(self, timeout: int = 10):
        if not self.ws.open:
            log.debug('WebSocket session is not open. Returning early.')
            return False
        wait_timeout = time.time() + timeout
        await asyncio.sleep(self.call_poll_delay / 2)
        while time.time() < wait_timeout:
            if self.identified:
                return True
            if not self.ws.open:
                log.debug('WebSocket session is no longer open. Returning early.')
                return False
            await asyncio.sleep(self.call_poll_delay)
        log.warning('Waiting for `Identified` timed out after {} seconds.'.format(timeout))
        return False

    async def disconnect(self):
        if self.recv_task == None:
            log.debug('WebSocket session is not open. Returning early.')
            return False
        self.recv_task.cancel()
        await self.ws.close()
        self.ws = None
        self.answers = {}
        self.recv_task = None
        self.identified = False
        self.hello_message = None
        return True

    async def call(self, request: Request, timeout: int = 15):
        if not self.identified:
            raise NotIdentifiedError('Calls to requests cannot be made without being identified with obs-websocket.')
        request_id = str(uuid.uuid1())
        request_payload = {
            'messageType': 'Request',
            'requestType': request.requestType,
            'requestId': request_id
        }
        if request.requestData != None:
            request_payload['requestData'] = request.requestData
        log.debug('Sending Request message:\n{}'.format(json.dumps(request_payload, indent=2)))
        await self.ws.send(json.dumps(request_payload))
        wait_timeout = time.time() + timeout
        await asyncio.sleep(self.call_poll_delay / 2)
        while time.time() < wait_timeout:
            if request_id in self.answers:
                ret = self.answers.pop(request_id)
                ret.pop('requestId')
                return _build_request_response(ret)
            await asyncio.sleep(self.call_poll_delay)
        raise MessageTimeout('The request with type {} timed out after {} seconds.'.format(request_type, timeout))

    async def emit(self, request: Request):
        if not self.identified:
            raise NotIdentifiedError('Calls to requests cannot be made without being identified with obs-websocket.')
        request_id = str(uuid.uuid1())
        request_payload = {
            'messageType': 'Request',
            'requestType': request.requestType,
            'requestId': 'emit_{}'.format(request_id)
        }
        if request.requestData != None:
            request_payload['requestData'] = request.requestData
        log.debug('Sending Request message:\n{}'.format(json.dumps(request_payload, indent=2)))
        await self.ws.send(json.dumps(request_payload))

    def register_event_callback(self, callback, event = None):
        if not inspect.iscoroutinefunction(callback):
            raise EventRegistrationError('Registered functions must be async')
        else:
            self.event_callbacks.append((callback, event))

    def deregister_event_callback(self, callback, event = None):
        for c, t in self.event_callbacks.copy():
            if (c == callback) and (event == None or t == event):
                self.event_callbacks.remove((c, t))

    def _build_request_response(self, response: dict):
        if 'responseData' in response:
            ret = RequestResponse(response['requestType'], responseData=response['responseData'])
        else:
            ret = RequestResponse(response['requestType'])
        ret.requestStatus.result = response['requestStatus']['result']
        ret.requestStatus.code = response['requestStatus']['code']
        if 'comment' in response['requestStatus']:
            ret.requestStatus.comment = response['requestStatus']['comment']
        return ret

    async def _send_identify(self, password, identification_parameters):
        if self.hello_message == None:
            return
        identify_message = {'messageType': 'Identify'}
        identify_message['rpcVersion'] = RPC_VERSION
        if 'authentication' in self.hello_message:
            secret = base64.b64encode(hashlib.sha256((self.password + self.hello_message['authentication']['salt']).encode('utf-8')).digest())
            authentication_string = base64.b64encode(hashlib.sha256(secret + (self.hello_message['authentication']['challenge'].encode('utf-8'))).digest()).decode('utf-8')
            identify_message['authentication'] = authentication_string
        if self.identification_parameters.ignoreInvalidMessages != None:
            identify_message['ignoreInvalidMessages'] = self.identification_parameters.ignoreInvalidMessages
        if self.identification_parameters.ignoreNonFatalRequestChecks != None:
            identify_message['ignoreNonFatalRequestChecks'] = self.identification_parameters.ignoreNonFatalRequestChecks
        if self.identification_parameters.eventSubscriptions != None:
            identify_message['eventSubscriptions'] = self.identification_parameters.eventSubscriptions
        log.debug('Sending Identify message:\n{}'.format(json.dumps(identify_message, indent=2)))
        await self.ws.send(json.dumps(identify_message))

    async def _ws_recv_task(self):
        while self.ws.open:
            message = ''
            try:
                message = await self.ws.recv()
                if not message:
                    continue
                incoming_message = json.loads(message)

                log.debug('Received message:\n{}'.format(json.dumps(incoming_message, indent=2)))

                if 'messageType' not in incoming_message:
                    log.warning('Received a message which is missing a `messageType`. Will ignore: {}'.format(incoming_message))
                    continue

                message_type = incoming_message['messageType']
                if message_type == 'RequestResponse' or message_type == 'RequestBatchResponse':
                    if incoming_message['requestId'].startswith('emit_'):
                        continue
                    self.answers[incoming_message['requestId']] = incoming_message
                elif message_type == 'Event':
                    for callback, trigger in self.event_callbacks:
                        if trigger == None or trigger == incoming_message['eventType']:
                            self.loop.create_task(callback(incoming_message))
                elif message_type == 'Hello':
                    self.hello_message = incoming_message
                    await self._send_identify(self.password, self.identification_parameters)
                elif message_type == 'Identified':
                    self.identified = True
                else:
                    log.warning('Unknown message type: {}'.format(incoming_message))
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                log.debug('The WebSocket connection was closed. Code: {} | Reason: {}'.format(self.ws.close_code, self.ws.close_reason))
                break
            except json.JSONDecodeError:
                continue
