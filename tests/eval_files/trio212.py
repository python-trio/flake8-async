# type: ignore
import urllib3


async def foo_call():
    client = httpx.Client()
    client.close()  # ASYNC212: 4, "close", "client"
    client.delete()  # ASYNC212: 4, "delete", "client"
    client.get()  # ASYNC212: 4, "get", "client"
    client.head()  # ASYNC212: 4, "head", "client"
    client.options()  # ASYNC212: 4, "options", "client"
    client.patch()  # ASYNC212: 4, "patch", "client"
    client.post()  # ASYNC212: 4, "post", "client"
    client.put()  # ASYNC212: 4, "put", "client"
    client.request()  # ASYNC212: 4, "request", "client"
    client.send()  # ASYNC212: 4, "send", "client"
    client.stream()  # ASYNC212: 4, "stream", "client"

    client.anything()
    client.build_request()
    client.is_closed


async def foo_ann_par(client: httpx.Client):
    client.send(...)  # ASYNC212: 4, "send", "client"


async def foo_ann_par_leftNone(client: None | httpx.Client):
    client.send(...)  # ASYNC212: 4, "send", "client"


async def foo_ann_par_rightNone(client: httpx.Client | None):
    client.send(...)  # ASYNC212: 4, "send", "client"


async def foo_ann_par_optional(client: Optional[httpx.Client]):
    client.send(...)  # ASYNC212: 4, "send", "client"


async def foo_ann_var():
    client: httpx.Client = ...
    client.send()  # ASYNC212: 4, "send", "client"


glob_client = httpx.Client()


async def foo_global_client():
    glob_client.send()  # ASYNC212: 4, "send", "glob_client"


def sync_global_client():
    glob_client.send()


glob_client: int = 4


async def foo_global_client_overriden():
    glob_client.send()


# not implemented
from httpx import Client


async def foo_alias_import():
    client: Client = Client()
    client.send()


# urllib3 pools
async def foo_urllib3():
    c: urllib3.HTTPConnectionPool = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.HTTPSConnectionPool = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.PoolManager = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.ProxyManager = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.connectionpool.ConnectionPool = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.connectionpool.HTTPConnectionPool = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.connectionpool.HTTPSConnectionPool = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.poolmanager.PoolManager = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.poolmanager.ProxyManager = ...
    c.anything()  # ASYNC212: 4, "anything", "c"
    c: urllib3.request.RequestMethods = ...
    c.anything()  # ASYNC212: 4, "anything", "c"

    c: urllib3.anything = ...
    c.anything()
