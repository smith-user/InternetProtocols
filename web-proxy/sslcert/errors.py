from proxy.errors import ProxyError


class SSlContextError(ProxyError):
    message = 'SSlContextError(ProxyError): context creation error. \n' \
              '\t{}'

    def __init__(self, message):
        self.message = self.message.format(message)
        super().__init__(self.message)
