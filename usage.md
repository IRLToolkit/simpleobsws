# The sort-of docs

## Class `obsws`

### `def __init__(self, host='localhost', port=4444, password=None, call_poll_delay=100, loop: asyncio.BaseEventLoop=None):`

- `host` | Host to connect to. Can be a hostname or IP address.
- `port` | Port that the obs-websocket server is listening on.
- `password` | The password set on the obs-websocket server (if any).
- `call_poll_delay` | When using the `obsws.call()` function, you may set the time that simpleobsws waits after every check for new responses.
- `loop` | If you are using your own specific event loop, you may specify it so that simpleobsws submits and runs its tasks in that loop.

### `async def connect(self):`

Connect to the configured obs-websocket server and authenticate if the server requires authentication.

### `async def disconnect(self):`

Disconnect from the obs-websocket server. Once disconnected, the server may be connected to again using `connect()`.

### `async def call(self, request_type, data=None, timeout=15):`

Make a request to the obs-websocket server and return the response.

- `request_type` | The request-type of the request you want to make. Ex. `GetVersion`
- `data` | Optional request data to pass to obs-websocket along with the request. Must be in the form of a [Python dictionary](https://docs.python.org/3/tutorial/datastructures.html#dictionaries).
- `timeout` | How long to internally poll for obs-websocket responses before giving up and throwing a `MessageTimeout` error.

### `async def emit(self, request_type, data=None):`

Similar to the `call()` function, but does not poll for a websocket response, and does not return any values.

### `def register(self, function, event=None):`

Register a callback function for an obs-websocket event. *Must* be a coroutine.

- `function` | Callback to a handler function. See examples for more info.
- `event` | Event to trigger the callback. If `None` is specified, all obs-websocket events will be sent to the callback.

### `def unregister(self, function, event=None):`

Similar to `register()`, but deregisters a callback function from obs-websocket. Requires matching `function` and `event` parameters to the original callback registration.