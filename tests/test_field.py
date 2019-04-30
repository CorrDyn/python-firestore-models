import time
from unittest import TestCase

from fsmodels.models import Field, ValidationError


def generic_validator(x):
    return x == 1, {'detail': 'x must be 1.'}


class TestField(TestCase):

    def test___init__(self):

        # no required fields
        f = Field()

        with self.assertRaises((ValidationError,)):
            # validation must be callable
            Field(validation=1)

        # validation can be None or a function that returns a tuple(boolean, dict)
        f = Field(validation=generic_validator)

    def test_validate(self):

        f = Field(default=1, required=True)
        with self.assertRaises((ValidationError,)):
            # if the field is required, value passed to validate cannot be None
            f.validate(None)

        f2 = Field(required=False)
        # if the field is not required then the value passed to validate can be None
        f2.name = 'named'
        self.assertTrue(f2.validate(None)[0], "Field.validate did not return true.")

        with self.assertRaises((ValidationError,)):
            # field value must return True from validation function
            f = Field(validation=generic_validator)
            f.validate(2)

        f = Field(validation=generic_validator)
        # alternatively, we can prevent validation from raising an error.
        self.assertFalse(f.validate(None, raise_error=False)[0], "Field.validate function should return false.")

    def test_default(self):

        f = Field()
        # default is none by default
        self.assertIsNone(f.default())

        f = Field(default=1)
        # Field.default() should return simple values
        self.assertEqual(f.default(), 1, "Field.default does not return default parameter")

        f = Field(default=time.time)
        # Field.default() can be passed as a callable argument
        self.assertAlmostEqual(f.default(), time.time(), 1, "Field.default does not call default function.")

        f = Field(default=lambda x, y=1: x*y)
        # Field.default() can have arbitrary arguments and keyword arguments according to the user-defined parameter.
        self.assertEqual(f.default(2, y=3), 6, "Field.default does not accept arbitrary args and kwargs.")




