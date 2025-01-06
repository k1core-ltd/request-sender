from request_sender.sender import RequestSender, Timeout


def test_one_client() -> None:
    service_name = "sender_1"

    sender_1 = RequestSender(
        service_name=service_name,
    )

    response = sender_1.send(
        "GET",
        "https://httpbin.org/get",
    )

    assert response.status_code == 200

    assert response.request.headers["X-Service-Name"] == service_name
    assert response.request.headers["X-Request-Method"] == "sync"


def test_two_clients() -> None:
    sender_1 = RequestSender(
        service_name="sender_1",
    )
    sender_2 = RequestSender(
        service_name="sender_2",
        timeout=Timeout(timeout=1),
    )

    response_1 = sender_1.send(
        "GET",
        "https://httpbin.org/get",
    )
    response_2 = sender_2.send(
        "GET",
        "https://httpbin.org/get",
    )

    assert response_1.status_code == 200
    assert response_2.status_code == 200

    assert response_1.request.headers["X-Service-Name"] == "sender_1"
    assert response_1.request.headers["X-Request-Method"] == "sync"

    assert response_2.request.headers["X-Service-Name"] == "sender_2"
    assert response_2.request.headers["X-Request-Method"] == "sync"

    assert RequestSender._RequestSender__get_sync_client(
        service_name="sender_1",
    ) != RequestSender._RequestSender__get_sync_client(
        service_name="sender_2",
    )
