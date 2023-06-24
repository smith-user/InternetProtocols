
class ProxyError(Exception):
    message = 'ProxyError.'


class ProxyOpenError(ProxyError):
    message = 'ProxyOpenError (ProxyError): could not open proxy. {}'

    def __init__(self, message):
        self.message = self.message.format(message)
        super().__init__(self.message)


class ConnectionException(ProxyError):
    message = 'ConnectionException(ProxyError): connection exception. {}'

    def __init__(self, message):
        self.message = self.message.format(message)
        super().__init__(self.message)


class CloseConnection(ConnectionException):
    message = 'CloseConnection (ConnectionException). ' \
              'Unplanned connection close. {}'

    def __init__(self, message):
        self.message = self.message.format(message)
        super().__init__(self.message)


class UnresolvedRequest(ConnectionException):
    message = 'UnresolvedRequest (ConnectionException). {}'

    def __init__(self, message):
        self.message = self.message.format(message)
        super().__init__(self.message)


class IllegalCertificate(ConnectionException):
    message = 'IllegalCertificate (ConnectionException). {}'

    def __init__(self, message):
        self.message = self.message.format(message)
        super().__init__(self.message)


class SSLHandshakeError(ConnectionException):
    message = 'SSLHandshakeError (ConnectionException). {}'

    def __init__(self, message):
        self.message = self.message.format(message)
        super().__init__(self.message)


class HTTPParsingException(ConnectionException):
    message = 'HTTPParsingException (ConnectionException). {}'

    def __init__(self, message):
        self.message = self.message.format(message)
        super().__init__(self.message)
