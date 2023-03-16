class EndpointError(Exception):
    def __init__(self, response):
        message = (
            f'Endpoint {response.url} not available. '
            f'API response code: {response.status_code}]'
        )
        super().__init__(message)


class HavingStatusError(Exception):
    def __init__(self, text):
        message = (
            f'Parsing the API response: {text}'
        )
        super().__init__(message)


class ResponseFormatError(Exception):
    def __init__(self, text):
        message = (
            f'API response check: {text}'
        )
        super().__init__(message)
