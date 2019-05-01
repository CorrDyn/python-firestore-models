import re
import logging
import functools

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def snake_case(string):
    """
    Turn CamelCase strings to snake_case equivalent
    :param string: string to be converted
    :return: converted string

    Example: snake_case('CamelCase') == 'camel_case'
    """
    s1 = first_cap_re.sub(r'\1_\2', string)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def skip_if(condition, reason: str = ''):
    """
    Wrapper to prevent calling of a function if condition is True

    :param condition: condition on which to skip the function
    :param reason: why we are skipping
    :return: returns function that executes the original function or skips it, depending on the condition


    Example:

    @skip_if(os.environ['SHOULD_SKIP'])
    def do_thing():
        print('okay')

    do_thing() # warning log that it was skipped and then returns None
    """
    def _skip_if(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if condition:
                logging.warning(f'Skipping {func.__name__}: {reason}')
                return None
            else:
                return func(*args, **kwargs)
        return wrapper
    return _skip_if
