import ssl
import typing
from collections.abc import Callable
from importlib import metadata
from typing import Any, Literal

import httpx2
import pydantic
from httpcore2 import SOCKET_OPTION
from httpx2._auth import Auth  # noqa: F401
from httpx2._client import USE_CLIENT_DEFAULT, UseClientDefault
from httpx2._config import Proxy, Timeout  # noqa: F401
from httpx2._models import Cookies, Headers, Request  # noqa: F401
from httpx2._types import (
    AuthTypes,
    CertTypes,
    CookieTypes,
    HeaderTypes,
    ProxyTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestExtensions,
    RequestFiles,
    TimeoutTypes,
)
from httpx2._urls import URL, QueryParams  # noqa: F401


class HttpxRequestParameters(pydantic.BaseModel):
    content: RequestContent | None = None
    data: RequestData | None = None
    files: RequestFiles | None = None
    json_data: pydantic.JsonValue | None = pydantic.Field(
        default=None,
        alias="json",
    )
    params: QueryParamTypes | None = None
    headers: HeaderTypes | None = None
    cookies: CookieTypes | None = None
    auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT
    follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT
    timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT
    extensions: RequestExtensions | None = None

    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
    )


class TransportParameters(pydantic.BaseModel):
    verify: ssl.SSLContext | str | bool = True
    cert: CertTypes | None = None
    trust_env: bool = True
    http1: bool = True
    http2: bool = False
    limits: httpx2.Limits | None = None
    proxy: ProxyTypes | None = None
    uds: str | None = None
    local_address: str | None = None
    retries: int = 0
    socket_options: typing.Iterable[SOCKET_OPTION] | None = None

    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
    )


class RequestSender:
    """
    A class that sends requests from a given service.

    Attempts to reuse the same client for multiple requests,
    but if the client is not available, it will create a new one.

    Parameters
    - service_name (str, no-arg method that returns str): The name of the service to send requests from
    - base_url (str, None): Optional base URL to send requests to.
    """

    __client_storage: dict[str, httpx2.Client] = {}
    __async_client_storage: dict[str, httpx2.AsyncClient] = {}

    def __init__(
        self: "RequestSender",
        service_name: str | Callable[..., str] = "Undefined",
        base_url: str | None = None,
        timeout: Timeout = Timeout(timeout=30.0),
        verify: bool = True,
        client_kwargs: dict[str, Any] | None = None,
        transport_kwargs: TransportParameters | dict[str, Any] | None = None,
    ):
        if callable(service_name):
            service_name = service_name()
        self.service_name = service_name
        self.base_url = base_url

        self.additional_args = {
            "timeout": timeout,
            "verify": verify,
        }
        if client_kwargs is not None:
            self.additional_args.update(client_kwargs)
        if transport_kwargs is not None:
            if isinstance(transport_kwargs, TransportParameters):
                transport_kwargs = transport_kwargs.model_dump()

            self.additional_args["transport"] = httpx2.HTTPTransport(
                **transport_kwargs,
            )

    def send(
        self: "RequestSender",
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        url: "str",
        params: HttpxRequestParameters | None = None,
        *,
        use_base_url: bool = True,
    ) -> "httpx2.Response":
        """
        Send a request to the given URL using the specified method.
        In return you get an httpx Response.
        """
        params = params or HttpxRequestParameters()

        client = self.__get_sync_client(
            service_name=self.service_name,
            additional_args=self.additional_args,
        )

        if use_base_url and self.base_url is not None:
            url = f"{self.base_url}{url}"

        return client.request(
            method=method,
            url=url,
            **params.model_dump(
                by_alias=True,
            ),
        )

    async def send_async(
        self: "RequestSender",
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        url: "str",
        params: HttpxRequestParameters | None = None,
        *,
        use_base_url: bool = True,
    ) -> "httpx2.Response":
        """
        ! Async method !
        Send a request to the given URL using the specified method.
        In return you get an httpx Response.
        """
        params = params or HttpxRequestParameters()

        client = self.__get_async_client(
            service_name=self.service_name,
            additional_args=self.additional_args,
        )

        if use_base_url and self.base_url is not None:
            url = f"{self.base_url}{url}"

        return await client.request(
            method=method,
            url=url,
            **params.model_dump(
                by_alias=True,
            ),
        )

    @staticmethod
    def _make_headers(
        service_name: str,
        request_method: Literal["async", "sync"] = "async",
    ) -> dict:
        """Returns default headers to use for the requests"""
        package_name = __package__ or "request-sender"
        try:
            version = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            version = "0.0.0"

        return {
            "User-Agent": f"{package_name}/{version}",
            "X-Service-Name": service_name,
            "X-Request-Method": request_method,
        }

    @classmethod
    def __get_sync_client(
        cls: type["RequestSender"],
        service_name: str,
        additional_args: dict[str, Any] | None = None,
    ) -> httpx2.Client:
        """
        Returns a sync client for the given service name.
        You can define default timeout for the requests, which is set to 30 seconds by default.
        """
        if additional_args is None:
            additional_args = {}

        if client := cls.__client_storage.get(service_name, None):
            if not client.is_closed:
                return client

        cls.__client_storage[service_name] = httpx2.Client(
            headers=cls._make_headers(
                service_name=service_name,
                request_method="sync",
            ),
            **additional_args,
        )

        return cls.__client_storage[service_name]

    @classmethod
    def __get_async_client(
        cls: type["RequestSender"],
        service_name: str,
        additional_args: dict[str, Any] | None = None,
    ) -> httpx2.AsyncClient:
        """
        Returns an async client for the given service name.
        You can define default timeout for the requests, which is set to 30 seconds by default.
        """
        if additional_args is None:
            additional_args = {}

        if client := cls.__async_client_storage.get(service_name, None):
            if not client.is_closed:
                return client

        cls.__async_client_storage[service_name] = httpx2.AsyncClient(
            headers=cls._make_headers(
                service_name=service_name,
                request_method="async",
            ),
            **additional_args,
        )

        return cls.__async_client_storage[service_name]
