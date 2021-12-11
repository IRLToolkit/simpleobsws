# The sort-of docs


## Enum `RequestBatchExecutionType`
**Identifiers:**
- `SerialRealtime = 0`
- `SerialFrame = 1`
- `Parallel = 2`


## Class `IdentificationParameters`
**Parameters:**
- `ignoreNonFatalRequestChecks: bool = None` - See [here](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#identify-opcode-1). Leave `None` for default
- `eventSubscriptions: int = None` - See [here](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#identify-opcode-1). Leave `None` for default


## Class `Request`
**Parameters:**
- `requestType: str` - Request type. Only required element of a request
- `requestData: dict = None` - Optional request data object
- `inputVariables: dict = None` - Optional input variables, only used in serial request batches
- `outputVariables: dict = None` - Optional output variables, only used in serial request batches


## Class `RequestStatus`
**Parameters:**
- `result: bool = False` - Boolean status of the request's result
- `code: int = 0` - Integer status of the request's result
- `comment: str = None` - Text comment if the request failed


## Class `RequestResponse`
**Parameters:**
- `requestType: str` - The type of request that was made
- `requestStatus: RequestStatus = RequestStatus()` - [`RequestStatus`](#class-requeststatus) object
- `responseData: dict = None` - Request response data object if any was returned

### `def has_data(self):`
- Returns `bool` | `True` if there is a response data object, `False` if not

### `def ok(self):`
- Returns `bool` | `True` if the request succeeded, `False` if not


## Class `WebSocketClient`

### `def __init__(self, url: str = "ws://localhost:4444", password: str = '', identification_parameters: IdentificationParameters = IdentificationParameters()):`

- `url` - WebSocket URL to reach obs-websocket at
- `password` - The password set on the obs-websocket server (if any)
- `identification_parameters` - An IdentificationParameters() object with session parameters to be set during identification

### `async def connect(self):`

- Returns `bool` - `True` if connected, `False` if not. Exceptions may still be raised by `websockets`

Connect to the configured obs-websocket server. The library will automatically begin the identification handshake once connected.

### `async def wait_until_identified(self, timeout: int = 10):`

- Returns `bool` - `True` if identified, `False` if the timeout was reached

Wait for the identification handshake to complete, or until the timeout is reached.

- `timeout` - Time to wait until giving up (does not close the websocket connection)

### `async def disconnect(self):`

- Returns `bool` - `True` if disconnected, `False` if *already disconnected*

Disconnect from the obs-websocket server. Once disconnected, the server may be connected to again using `connect()`.

### `async def call(self, request: Request, timeout: int = 15):`

- Returns `RequestResponse` - Object with populated response data

Make a request to the obs-websocket server and return the response.

- `request` - The request object to perform the request with
- `timeout` - How long to wait for obs-websocket responses before giving up and throwing a `MessageTimeout` error

### `async def emit(self, request: Request)`

- Returns nothing

Similar to the `call()` function, but does not wait for an obs-websocket response.

- `request` - The request object to emit to the server

### `async def call_batch(self, requests: list, timeout: int = 15, halt_on_failure: bool = None, execution_type: RequestBatchExecutionType = None, variables: dict = None):`

- Returns list of `RequestResponse`

Call a request batch, which is to be completed all at once by obs-websocket. Feed it a list of requests, and it will return a list of results.

- `requests` - List of requests to perform
- `timeout` - How long to wait for the request batch to finish before giving up and throwing a `MessageTimeout` error
- `halt_on_failure` - Tells obs-websocket to stop processing the request batch if one fails. Only available in serial modes
- `execution_type` - `RequestBatchExecutionType` to use to process the batch
- `variables` - Batch variables to use. Only available in serial modes

### `async def emit_batch(self, requests: list, halt_on_failure: bool = None, execution_type: RequestBatchExecutionType = None):`

- Returns nothing

Similar to the `call_batch()` function, but does not wait for an obs-websocket response.

- `requests` - List of requests to perform
- `halt_on_failure` - Tells obs-websocket to stop processing the request batch if one fails. Only available in serial modes
- `execution_type` - `RequestBatchExecutionType` to use to process the batch
- `variables` - Batch variables to use. Only available in serial modes

### `def register_event_callback(self, callback, event: str = None):`

- Returns nothing

Register a callback function for an obs-websocket event. *Must* be a coroutine.

Note about callbacks: simpleobsws inspects the number of parameters of the callback to determine how to formulate its arguments. Here is the behavior:
  - 1 parameter - Raw payload
  - 2 parameters - event type, event data
  - 3 parameters - event type, event intent, event data

- `callback` - Callback to an async handler function. See examples for more info
- `event` - Event name to trigger the callback. If not specified, all obs-websocket events will be sent to the callback

### `def deregister_event_callback(self, callback, event = None):`

- Returns nothing

Similar to `register()`, but deregisters a callback function from obs-websocket. Requires matching `function` and `event` parameters to the original callback registration.

### `def is_identified(self):`

- Returns `bool` - `True` if connected and identified, `False` if not identified

Pretty simple one.
