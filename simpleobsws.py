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
        return self.responseData != None

    def ok(self):
        return self.requestStatus.result

class MessageTimeout(Exception):
    pass
class EventRegistrationError(Exception):
    pass
class NotIdentifiedError(Exception):
    pass

class WebSocketClient:
    def __init__(self,
        url: str = "ws://localhost:4444",
        password: str = '',
        identification_parameters: IdentificationParameters = IdentificationParameters(),
        call_poll_delay: int = 100
    ):
        self.url = url
        self.password = password
        self.identification_parameters = identification_parameters
        self.call_poll_delay = call_poll_delay / 1000
        self.loop = asyncio.get_event_loop()

        self.ws = None
        self.answers = {}
        self.identified = False
        self.recv_task = None
        self.hello_message = None
        self.event_callbacks = []

    async def connect(self):
        if self.ws != None and self.ws.open:
            log.debug('WebSocket session is already open. Returning early.')
            return False
        self.answers = {}
        self.recv_task = None
        self.identified = False
        self.hello_message = None
        self.ws = await websockets.connect(self.url, max_size=2**23)
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
        self.identified = False
        self.recv_task = None
        self.hello_message = None
        return True

    async def call(self, request: Request, timeout: int = 15):
        if not self.identified:
            raise NotIdentifiedError('Calls to requests cannot be made without being identified with obs-websocket.')
        request_id = str(uuid.uuid1())
        request_payload = {
            'op': 6,
            'd': {
                'requestType': request.requestType,
                'requestId': request_id
            }
        }
        if request.requestData != None:
            request_payload['d']['requestData'] = request.requestData
        log.debug('Sending Request message:\n{}'.format(json.dumps(request_payload, indent=2)))
        await self.ws.send(json.dumps(request_payload))
        wait_timeout = time.time() + timeout
        await asyncio.sleep(self.call_poll_delay / 2)
        while time.time() < wait_timeout:
            if request_id in self.answers:
                ret = self.answers.pop(request_id)
                return self._build_request_response(ret)
            await asyncio.sleep(self.call_poll_delay)
        raise MessageTimeout('The request with type {} timed out after {} seconds.'.format(request.requestType, timeout))

    async def emit(self, request: Request):
        if not self.identified:
            raise NotIdentifiedError('Emits to requests cannot be made without being identified with obs-websocket.')
        request_id = str(uuid.uuid1())
        request_payload = {
            'op': 6,
            'd': {
                'requestType': request.requestType,
                'requestId': 'emit_{}'.format(request_id)
            }
        }
        if request.requestData != None:
            request_payload['d']['requestData'] = request.requestData
        log.debug('Sending Request message:\n{}'.format(json.dumps(request_payload, indent=2)))
        await self.ws.send(json.dumps(request_payload))

    async def call_batch(self, requests: list, timeout: int = 15, halt_on_failure: bool = False):
        if not self.identified:
            raise NotIdentifiedError('Calls to requests cannot be made without being identified with obs-websocket.')
        request_batch_id = str(uuid.uuid1())
        request_batch_payload = {
            'op': 8,
            'd': {
                'requestId': request_batch_id,
                'haltOnFailure': halt_on_failure,
                'requests': []
            }
        }
        for request in requests:
            request_payload = {
                'requestType': request.requestType
            }
            if request.requestData != None:
                request_payload['requestData'] = request.requestData
            request_batch_payload['d']['requests'].append(request_payload)
        log.debug('Sending Request batch message:\n{}'.format(json.dumps(request_batch_payload, indent=2)))
        await self.ws.send(json.dumps(request_batch_payload))
        wait_timeout = time.time() + timeout
        await asyncio.sleep(self.call_poll_delay / 2)
        while time.time() < wait_timeout:
            if request_batch_id in self.answers:
                response = self.answers.pop(request_batch_id)
                ret = []
                for result in response['results']:
                    ret.append(self._build_request_response(result))
                return ret
            await asyncio.sleep(self.call_poll_delay)
        raise MessageTimeout('The batch request timed out after {} seconds.'.format(request, timeout))

    async def emit_batch(self, requests: list, halt_on_failure: bool = False):
        if not self.identified:
            raise NotIdentifiedError('Emits to requests cannot be made without being identified with obs-websocket.')
        request_batch_id = str(uuid.uuid1())
        request_batch_payload = {
            'op': 8,
            'd': {
                'requestId': 'emit_{}'.format(request_batch_id),
                'haltOnFailure': halt_on_failure,
                'requests': []
            }
        }
        for request in requests:
            request_payload = {
                'requestType': request.requestType
            }
            if request.requestData != None:
                request_payload['requestData'] = request.requestData
            request_batch_payload['d']['requests'].append(request_payload)
        log.debug('Sending Request batch message:\n{}'.format(json.dumps(request_batch_payload, indent=2)))
        await self.ws.send(json.dumps(request_batch_payload))

    def register_event_callback(self, callback, event = None):
        if not inspect.iscoroutinefunction(callback):
            raise EventRegistrationError('Registered functions must be async')
        else:
            self.event_callbacks.append((callback, event))

    def deregister_event_callback(self, callback, event = None):
        for c, t in self.event_callbacks.copy():
            if (c == callback) and (event == None or t == event):
                self.event_callbacks.remove((c, t))

    def _get_hello_data(self):
        return self.hello_message

    def _build_request_response(self, response: dict):
        ret = RequestResponse(response['requestType'], responseData = response.get('responseData'))
        ret.requestStatus.result = response['requestStatus']['result']
        ret.requestStatus.code = response['requestStatus']['code']
        ret.requestStatus.comment = response['requestStatus'].get('comment')
        return ret

    async def _send_identify(self, password, identification_parameters):
        if self.hello_message == None:
            return
        identify_message = {'op': 1, 'd': {}}
        identify_message['d']['rpcVersion'] = RPC_VERSION
        if 'authentication' in self.hello_message:
            secret = base64.b64encode(hashlib.sha256((self.password + self.hello_message['authentication']['salt']).encode('utf-8')).digest())
            authentication_string = base64.b64encode(hashlib.sha256(secret + (self.hello_message['authentication']['challenge'].encode('utf-8'))).digest()).decode('utf-8')
            identify_message['d']['authentication'] = authentication_string
        if self.identification_parameters.ignoreInvalidMessages != None:
            identify_message['d']['ignoreInvalidMessages'] = self.identification_parameters.ignoreInvalidMessages
        if self.identification_parameters.ignoreNonFatalRequestChecks != None:
            identify_message['d']['ignoreNonFatalRequestChecks'] = self.identification_parameters.ignoreNonFatalRequestChecks
        if self.identification_parameters.eventSubscriptions != None:
            identify_message['d']['eventSubscriptions'] = self.identification_parameters.eventSubscriptions
        log.debug('Sending Identify message:\n{}'.format(json.dumps(identify_message, indent=2)))
        await self.ws.send(json.dumps(identify_message))

    async def _ws_recv_task(self):
        while self.ws.open:
            message = ''
            try:
                message = await self.ws.recv()
                if not message:
                    continue
                incoming_payload = json.loads(message)

                log.debug('Received message:\n{}'.format(json.dumps(incoming_payload, indent=2)))

                op_code = incoming_payload['op']
                data_payload = incoming_payload['d']
                if op_code == 7 or op_code == 9: # RequestResponse or RequestBatchResponse
                    if data_payload['requestId'].startswith('emit_'):
                        continue
                    self.answers[data_payload['requestId']] = data_payload
                elif op_code == 5: # Event
                    for callback, trigger in self.event_callbacks:
                        if trigger == None:
                            self.loop.create_task(callback(data_payload['eventType'], data_payload.get('eventData')))
                        elif trigger == data_payload['eventType']:
                            self.loop.create_task(callback(data_payload.get('eventData')))
                elif op_code == 0: # Hello
                    self.hello_message = data_payload
                    await self._send_identify(self.password, self.identification_parameters)
                elif op_code == 3: # Identified
                    self.identified = True
                else:
                    log.warning('Unknown OpCode: {}'.format(op_code))
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                log.debug('The WebSocket connection was closed. Code: {} | Reason: {}'.format(self.ws.close_code, self.ws.close_reason))
                break
            except json.JSONDecodeError:
                continue
        self.identified = False
