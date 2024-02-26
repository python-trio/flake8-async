# type: ignore
from urllib3 import PoolManager


async def foo():
    foo = PoolManager()
    foo.request("OPTIONS")  # ASYNC211: 4, 'foo.request'
    foo.request("GET")  # ASYNC211: 4, 'foo.request'
    foo.request("HEAD")  # ASYNC211: 4, 'foo.request'
    foo.request("POST")  # ASYNC211: 4, 'foo.request'
    foo.request("PUT")  # ASYNC211: 4, 'foo.request'
    foo.request("DELETE")  # ASYNC211: 4, 'foo.request'
    foo.request("TRACE")  # ASYNC211: 4, 'foo.request'
    foo.request("CONNECT")  # ASYNC211: 4, 'foo.request'
    foo.request("PATCH")  # ASYNC211: 4, 'foo.request'

    foo.request("PUT", ...)  # ASYNC211: 4, 'foo.request'
    request("PUT")
    foo.request()
    foo.request(..., "PUT")
    foo.request("put")  # ASYNC211: 4, 'foo.request'
    foo.request("sPUTnik")
    foo.request(None)
    foo.request(put)
    foo.request(PUT)
    foo.request("REQUEST")  # not an HTTP verb
