# The sort-of docs

## Class `Request`
**Parameters:**
- `requestType: str` - Request type. Only required element of a request.
- `requestData: dict = None` - Optional request data object.

## Class `RequestStatus`
**Parameters:**
- `result: bool = False` - Boolean status of the request's result.
- `code: int = 0` - Integer status of the request's result.
- `comment: str = None` - Text comment if the request failed.

## Class `RequestResponse`
**Parameters:**
- `requestType: str` - The type of request that was made.
- `requestStatus: RequestStatus = RequestStatus()` - [`RequestStatus`](#class-requeststatus) object.
- `responseData: dict = None` - Request response data object if any was returned.

### `def has_data(self):`

- Returns `bool` | `True` if there is a response data object, `False` if not.

### `def ok(self):`

- Returns `bool` | `True` if the request succeeded, `False` if not.

## Class `WebSocketClient`

### `def __init__(self, host: str = 'localhost', port: int = 4444, password: str = None, identification_parameters: IdentificationParameters = IdentificationParameters(), call_poll_delay: int = 100):`

- `host` | Host to connect to. Can be a hostname or IP address.
- `port` | Port that the obs-websocket server is listening on.
- `password` | The password set on the obs-websocket server (if any).
- `identification_parameters` | An IdentificationParameters() object with session parameters to be set during identification.
- `call_poll_delay` | When using the `obsws.call()` function, you may set the time that simpleobsws waits after every check for new responses.

### `async def connect(self):`

- Returns `bool` | `True` if connected, `False` if not. Exceptions may still be raised by `websockets`.

Connect to the configured obs-websocket server. The library will automatically begin the identification handshake once connected.

### `async def wait_until_identification(self, timeout: int = 10):`

- Returns `bool` | `True` if identified, `False` if the timeout was reached.

Wait for the identification handshake to complete, or until the timeout is reached.

- `timeout` | Time to wait until giving up (does not close the websocket connection).

### `async def disconnect(self):`

- Returns `bool` | `True` if disconnected, `False` if *already disconnected*.

Disconnect from the obs-websocket server. Once disconnected, the server may be connected to again using `connect()`.

### `async def call(self, request: Request, timeout: int = 15):`

- Returns `RequestResponse` | Object with populated response data.

Make a request to the obs-websocket server and return the response.

- `request` | The request object to perform the request with.
- `timeout` | How long to internally poll for obs-websocket responses before giving up and throwing a `MessageTimeout` error.

### `async def emit(self, request: Request)`

- Returns nothing.

Similar to the `call()` function, but does not poll for a websocket response, and does not return any values.

- `request` | The request object to emit to the server

### `def register_event_callback(self, callback, event: str = None):`

- Returns nothing.

Register a callback function for an obs-websocket event. *Must* be a coroutine.

- `callback` | Callback to an async handler function. See examples for more info.
- `event` | Event name to trigger the callback. If not specified, all obs-websocket events will be sent to the callback.

### `def deregister_event_callback(self, callback, event = None):`

- Returns nothing.

Similar to `register()`, but deregisters a callback function from obs-websocket. Requires matching `function` and `event` parameters to the original callback registration.