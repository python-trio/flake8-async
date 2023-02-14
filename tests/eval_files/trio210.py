# type: ignore
import urllib

import httpx
import requests
import urllib3


async def foo():
    requests.get()  # TRIO210: 4, 'requests.get'
    requests.get(...)  # TRIO210: 4, 'requests.get'
    requests.get
    print(requests.get())  # TRIO210: 10, 'requests.get'
    # fmt: off
    print(requests.get(requests.get()))# TRIO210: 10, 'requests.get' # TRIO210: 23, 'requests.get'
    # fmt: on

    requests.options()  # TRIO210: 4, 'requests.options'
    requests.head()  # TRIO210: 4, 'requests.head'
    requests.post()  # TRIO210: 4, 'requests.post'
    requests.put()  # TRIO210: 4, 'requests.put'
    requests.patch()  # TRIO210: 4, 'requests.patch'
    requests.delete()  # TRIO210: 4, 'requests.delete'
    requests.foo()

    httpx.options("")  # TRIO210: 4, 'httpx.options'
    httpx.head("")  # TRIO210: 4, 'httpx.head'
    httpx.post("")  # TRIO210: 4, 'httpx.post'
    httpx.put("")  # TRIO210: 4, 'httpx.put'
    httpx.patch("")  # TRIO210: 4, 'httpx.patch'
    httpx.delete("")  # TRIO210: 4, 'httpx.delete'
    httpx.foo()

    urllib3.request()  # TRIO210: 4, 'urllib3.request'
    urllib3.request(...)  # TRIO210: 4, 'urllib3.request'
    request()

    urllib.request.urlopen("")  # TRIO210: 4, 'urllib.request.urlopen'
    request.urlopen()  # TRIO210: 4, 'request.urlopen'
    urlopen()  # TRIO210: 4, 'urlopen'

    r = {}
    r.get("not a sync http client")
