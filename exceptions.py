class HomeworkException(Exception):
    pass


class TokenException(HomeworkException):
    pass


class ApiException(HomeworkException):
    pass


class TypeException(HomeworkException):
    pass


class SendMessageException(HomeworkException):
    pass


class DataException(HomeworkException):
    pass
