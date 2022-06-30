#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from airbyte_cdk.sources.declarative.requesters.retriers.default_retrier import (
    ChainRetrier,
    DefaultRetrier,
    HttpResponseFilter,
    NonRetriableResponseStatus,
    RetryResponseStatus,
    StaticConstantBackoffStrategy,
)


@pytest.mark.parametrize(
    "test_name, http_code, response_headers, should_retry, backoff_time",
    [
        # ("test_bad_gateway", HTTPStatus.BAD_GATEWAY, {}, True, 60),
        # ("test_retry_after", HTTPStatus.BAD_GATEWAY, {"Retry-After": 120}, True, 120),
        # ("test_bad_gateway", HTTPStatus.BAD_GATEWAY, {"X-RateLimit-Reset": 1655804724}, True, 300.0),
    ],
)
@patch("time.time", return_value=1655804424.0)
def test_something(time_mock, test_name, http_code, response_headers, should_retry, backoff_time):
    response_mock = MagicMock()
    response_mock.status_code = http_code
    response_mock.headers = response_headers
    retrier = DefaultRetrier()
    assert retrier.should_retry(response_mock) == should_retry
    assert retrier.backoff_time(response_mock) == backoff_time


@pytest.mark.parametrize(
    "test_name, http_code, retry_response_filter, ignore_response_filter, response_headers, should_retry, backoff_strategy",
    [
        ("test_bad_gateway", HTTPStatus.BAD_GATEWAY, None, None, {}, RetryResponseStatus(None), None),
        (
            "test_bad_gateway_constant_retry",
            HTTPStatus.BAD_GATEWAY,
            None,
            None,
            {},
            RetryResponseStatus(60),
            [StaticConstantBackoffStrategy(60)],
        ),
        ("test_exponential_backoff_returns_none_wait", HTTPStatus.BAD_GATEWAY, None, None, {}, RetryResponseStatus(None), None),
        (
            "test_bad_gateway_constant_retry",
            HTTPStatus.BAD_GATEWAY,
            None,
            None,
            {},
            RetryResponseStatus(None),
            [DefaultRetrier.DEFAULT_BACKOFF_STRATEGSY],
        ),
        ("test_chain_backoff_strategy", HTTPStatus.BAD_GATEWAY, None, None, {}, RetryResponseStatus(None), None),
        (
            "test_bad_gateway_constant_retry",
            HTTPStatus.BAD_GATEWAY,
            None,
            None,
            {},
            RetryResponseStatus(60),
            [DefaultRetrier.DEFAULT_BACKOFF_STRATEGSY, StaticConstantBackoffStrategy(60)],
        ),
        ("test_200", HTTPStatus.OK, None, None, {}, NonRetriableResponseStatus.Ok, None),
        ("test_3XX", HTTPStatus.PERMANENT_REDIRECT, None, None, {}, NonRetriableResponseStatus.Ok, None),
        ("test_403", HTTPStatus.FORBIDDEN, None, None, {}, NonRetriableResponseStatus.FAIL, None),
        (
            "test_403_ignore_error_message",
            HTTPStatus.FORBIDDEN,
            None,
            HttpResponseFilter(error_message_contain="found"),
            {},
            NonRetriableResponseStatus.IGNORE,
            None,
        ),
        (
            "test_403_dont_ignore_error_message",
            HTTPStatus.FORBIDDEN,
            None,
            HttpResponseFilter(error_message_contain="not_found"),
            {},
            NonRetriableResponseStatus.FAIL,
            None,
        ),
        ("test_429", HTTPStatus.TOO_MANY_REQUESTS, None, None, {}, RetryResponseStatus(None), None),
        (
            "test_ignore_403",
            HTTPStatus.FORBIDDEN,
            None,
            HttpResponseFilter(http_codes=[HTTPStatus.FORBIDDEN]),
            {},
            NonRetriableResponseStatus.IGNORE,
            None,
        ),
        (
            "test_403_with_predicate",
            HTTPStatus.FORBIDDEN,
            HttpResponseFilter(predicate="{{ 'code' in decoded_response }}"),
            None,
            {},
            RetryResponseStatus(None),
            None,
        ),
        (
            "test_403_with_predicate",
            HTTPStatus.FORBIDDEN,
            HttpResponseFilter(predicate="{{ 'some_absent_field' in decoded_response }}"),
            None,
            {},
            NonRetriableResponseStatus.FAIL,
            None,
        ),
        (
            "test_retry_403",
            HTTPStatus.FORBIDDEN,
            HttpResponseFilter([HTTPStatus.FORBIDDEN]),
            None,
            {},
            RetryResponseStatus(None),
            None,
        ),
    ],
)
@patch("time.time", return_value=1655804424.0)
def test_default_retrier(
    time_mock, test_name, http_code, retry_response_filter, ignore_response_filter, response_headers, should_retry, backoff_strategy
):
    response_mock = MagicMock()
    response_mock.status_code = http_code
    response_mock.headers = response_headers
    response_mock.json.return_value = {"code": "1000", "error": "found"}
    response_mock.ok = http_code < 400
    retrier = DefaultRetrier(
        retry_response_filter=retry_response_filter, ignore_response_filter=ignore_response_filter, backoff_strategy=backoff_strategy
    )
    assert retrier.should_retry(response_mock) == should_retry
    if isinstance(should_retry, RetryResponseStatus):
        assert retrier.backoff_time(response_mock) == should_retry.retry_in


@pytest.mark.parametrize(
    "test_name, first_retrier_behavior, second_retrier_behavior, expected_behavior",
    [
        ("test_chain_retrier_ok_ok", NonRetriableResponseStatus.Ok, NonRetriableResponseStatus.Ok, NonRetriableResponseStatus.Ok),
        (
            "test_chain_retrier_ignore_fail",
            NonRetriableResponseStatus.IGNORE,
            NonRetriableResponseStatus.FAIL,
            NonRetriableResponseStatus.IGNORE,
        ),
        (
            "test_chain_retrier_fail_ignore",
            NonRetriableResponseStatus.FAIL,
            NonRetriableResponseStatus.IGNORE,
            NonRetriableResponseStatus.IGNORE,
        ),
        (
            "test_chain_retrier_ignore_retry",
            NonRetriableResponseStatus.IGNORE,
            RetryResponseStatus(None),
            NonRetriableResponseStatus.IGNORE,
        ),
        (
            "test_chain_retrier_retry_ignore",
            RetryResponseStatus(None),
            NonRetriableResponseStatus.IGNORE,
            NonRetriableResponseStatus.IGNORE,
        ),
        ("test_chain_retrier_retry_fail", RetryResponseStatus(None), NonRetriableResponseStatus.FAIL, RetryResponseStatus(None)),
        ("test_chain_retrier_fail_retry", NonRetriableResponseStatus.FAIL, RetryResponseStatus(None), RetryResponseStatus(None)),
        ("test_chain_retrier_ignore_ok", NonRetriableResponseStatus.IGNORE, NonRetriableResponseStatus.Ok, NonRetriableResponseStatus.Ok),
        ("test_chain_retrier_ok_ignore", NonRetriableResponseStatus.Ok, NonRetriableResponseStatus.IGNORE, NonRetriableResponseStatus.Ok),
        ("test_chain_retrier_ok_retry", NonRetriableResponseStatus.Ok, RetryResponseStatus(None), NonRetriableResponseStatus.Ok),
        ("test_chain_retrier_retry_ok", RetryResponseStatus(None), NonRetriableResponseStatus.Ok, NonRetriableResponseStatus.Ok),
        ("test_chain_retrier_return_first_retry", RetryResponseStatus(60), RetryResponseStatus(100), RetryResponseStatus(60)),
    ],
)
def test_chain_retrier_first_retrier_ignores_second_fails(test_name, first_retrier_behavior, second_retrier_behavior, expected_behavior):
    first_retier = MagicMock()
    first_retier.should_retry.return_value = first_retrier_behavior
    second_retrier = MagicMock()
    second_retrier.should_retry.return_value = second_retrier_behavior
    second_retrier.should_retry.return_value = second_retrier_behavior
    retriers = [first_retier, second_retrier]
    retrier = ChainRetrier(retriers)
    response_mock = MagicMock()
    response_mock.ok = first_retrier_behavior == NonRetriableResponseStatus.Ok or second_retrier_behavior == NonRetriableResponseStatus.Ok
    assert retrier.should_retry(response_mock) == expected_behavior