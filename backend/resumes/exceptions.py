class ResumeFileError(Exception):
    """Uploaded file is not acceptable (wrong type, too big, corrupted). The API rejects it with 400."""


class ResumeParseError(Exception):
    """File is valid, but readable text could not be extracted from it."""


class NoTextFoundError(ResumeParseError):
    """File opened fine but contains no usable text (for example a scanned image)."""