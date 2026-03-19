from .subpkg.helpers import helper_value


def build_message() -> str:
    return f"service:{helper_value()}"

