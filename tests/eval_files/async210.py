# type: ignore
import urllib

import httpx
import requests
import urllib3


async def foo():
    requests.get()  # ASYNC210: 4, 'requests.get'
    requests.get(...)  # ASYNC210: 4, 'requests.get'
    requests.get
    print(requests.get())  # ASYNC210: 10, 'requests.get'
    # fmt: off
    print(requests.get(requests.get()))# ASYNC210: 10, 'requests.get' # ASYNC210: 23, 'requests.get'
    # fmt: on

    requests.options()  # ASYNC210: 4, 'requests.options'
    requests.head()  # ASYNC210: 4, 'requests.head'
    requests.post()  # ASYNC210: 4, 'requests.post'
    requests.put()  # ASYNC210: 4, 'requests.put'
    requests.patch()  # ASYNC210: 4, 'requests.patch'
    requests.delete()  # ASYNC210: 4, 'requests.delete'
    requests.foo()

    httpx.options("")  # ASYNC210: 4, 'httpx.options'
    httpx.head("")  # ASYNC210: 4, 'httpx.head'
    httpx.post("")  # ASYNC210: 4, 'httpx.post'
    httpx.put("")  # ASYNC210: 4, 'httpx.put'
    httpx.patch("")  # ASYNC210: 4, 'httpx.patch'
    httpx.delete("")  # ASYNC210: 4, 'httpx.delete'
    httpx.foo()

    urllib3.request()  # ASYNC210: 4, 'urllib3.request'
    urllib3.request(...)  # ASYNC210: 4, 'urllib3.request'
    request()

    urllib.request.urlopen("")  # ASYNC210: 4, 'urllib.request.urlopen'
    request.urlopen()  # ASYNC210: 4, 'request.urlopen'
    urlopen()  # ASYNC210: 4, 'urlopen'

    r = {}
    r.get("not a sync http client")
