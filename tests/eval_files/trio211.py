# type: ignore
from urllib3 import PoolManager


async def foo():
    foo = PoolManager()
    foo.request("OPTIONS")  # TRIO211: 4, 'foo.request'
    foo.request("GET")  # TRIO211: 4, 'foo.request'
    foo.request("HEAD")  # TRIO211: 4, 'foo.request'
    foo.request("POST")  # TRIO211: 4, 'foo.request'
    foo.request("PUT")  # TRIO211: 4, 'foo.request'
    foo.request("DELETE")  # TRIO211: 4, 'foo.request'
    foo.request("TRACE")  # TRIO211: 4, 'foo.request'
    foo.request("CONNECT")  # TRIO211: 4, 'foo.request'
    foo.request("PATCH")  # TRIO211: 4, 'foo.request'

    foo.request("PUT", ...)  # TRIO211: 4, 'foo.request'
    request("PUT")
    foo.request()
    foo.request(..., "PUT")
    foo.request("put")  # TRIO211: 4, 'foo.request'
    foo.request("sPUTnik")
    foo.request(None)
    foo.request(put)
    foo.request(PUT)
    foo.request("REQUEST")  # not an HTTP verb
