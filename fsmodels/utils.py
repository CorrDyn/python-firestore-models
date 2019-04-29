import re

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
