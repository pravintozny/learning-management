"""Domain errors raised by the LMS."""


class LMSError(Exception):
    """Base class for all LMS errors."""


class NotFoundError(LMSError):
    pass


class ValidationError(LMSError):
    pass


class DuplicateError(LMSError):
    pass


class PrerequisiteError(LMSError):
    """Student has not completed required prerequisite courses (or they form a cycle)."""


class EnrollmentError(LMSError):
    """Enrollment constraint violated (capacity, duplicate, bad state)."""


class AttemptLimitError(LMSError):
    pass
