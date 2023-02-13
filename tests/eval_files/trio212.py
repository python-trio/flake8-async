# type: ignore
import urllib3


async def foo_call():
    client = httpx.Client()
    client.close()  # TRIO212: 4, "close", "client"
    client.delete()  # TRIO212: 4, "delete", "client"
    client.get()  # TRIO212: 4, "get", "client"
    client.head()  # TRIO212: 4, "head", "client"
    client.options()  # TRIO212: 4, "options", "client"
    client.patch()  # TRIO212: 4, "patch", "client"
    client.post()  # TRIO212: 4, "post", "client"
    client.put()  # TRIO212: 4, "put", "client"
    client.request()  # TRIO212: 4, "request", "client"
    client.send()  # TRIO212: 4, "send", "client"
    client.stream()  # TRIO212: 4, "stream", "client"

    client.anything()
    client.build_request()
    client.is_closed


async def foo_ann_par(client: httpx.Client):
    client.send(...)  # TRIO212: 4, "send", "client"


async def foo_ann_par_leftNone(client: None | httpx.Client):
    client.send(...)  # TRIO212: 4, "send", "client"


async def foo_ann_par_rightNone(client: httpx.Client | None):
    client.send(...)  # TRIO212: 4, "send", "client"


async def foo_ann_par_optional(client: Optional[httpx.Client]):
    client.send(...)  # TRIO212: 4, "send", "client"


async def foo_ann_var():
    client: httpx.Client = ...
    client.send()  # TRIO212: 4, "send", "client"


glob_client = httpx.Client()


async def foo_global_client():
    glob_client.send()  # TRIO212: 4, "send", "glob_client"


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
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.HTTPSConnectionPool = ...
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.PoolManager = ...
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.ProxyManager = ...
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.connectionpool.ConnectionPool = ...
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.connectionpool.HTTPConnectionPool = ...
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.connectionpool.HTTPSConnectionPool = ...
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.poolmanager.PoolManager = ...
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.poolmanager.ProxyManager = ...
    c.anything()  # TRIO212: 4, "anything", "c"
    c: urllib3.request.RequestMethods = ...
    c.anything()  # TRIO212: 4, "anything", "c"

    c: urllib3.anything = ...
    c.anything()
