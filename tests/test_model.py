import os
import time

from fsmodels import models
from unittest import TestCase, skipIf


class TestBaseModel(TestCase):

    def test___init__(self):

        class MyModel(models.BaseModel):
            test_field = models.Field(required=True)

        # should be no issues here
        test = MyModel(test_field=7)

        # by default we do not validate until Field.validate is called, so this does not complain about the
        # required field
        test = MyModel(test_field=None)

        # however, if we choose to validate on init, an error will be raised for None when required=True
        with self.assertRaises((models.ValidationError, )):
            test = MyModel(test_field=None, _validate_on_init=True)

    def test__get_fields(self):

        class MyModel(models.BaseModel):
            test_field1 = models.Field()
            test_field2 = models.Field()
            test_field3 = models.Field()

        test = MyModel()
        # fields defined in the class scope are stored privately and can be listed by calling _get_fields
        self.assertTrue(all([field in test._get_fields() for field in ['_test_field1', '_test_field2', '_test_field3']]))

    def test_validate(self):

        class MyModel(models.BaseModel):
            test_field1 = models.Field(required=True)
            test_field2 = models.Field(required=True, default=time.time)
            test_field3 = models.Field(required=False)
            test_field4 = models.Field(required=True, validation=lambda x: (isinstance(x, int), {'detail': 'test_field4 must be an int.'}))

        # required fields are... required
        MyModel(test_field1=1, test_field4=7, _validate_on_init=True)  # this is okay
        with self.assertRaises((models.ValidationError, )):
            MyModel(_validate_on_init=True)  # this is not.

        # defaults should work
        defaults_work = MyModel()
        self.assertAlmostEqual(defaults_work.test_field2, time.time(), 2, 'defaults do not work.')

        # validation can pass and fail
        MyModel(test_field1=1, test_field4=7, _validate_on_init=True)
        with self.assertRaises((models.ValidationError, )):
            MyModel(test_field1=1, test_field4=7.0, _validate_on_init=True)

    def test_to_dict(self):

        class MyModel(models.BaseModel):
            one = models.Field(default=1)
            two = models.Field(default=2)
            three = models.Field(default=3)
            four = models.Field(default=4)

        my_instance = MyModel()
        my_instance_dict = my_instance.to_dict()

        for i, key in enumerate(['one', 'two', 'three', 'four']):
            self.assertEqual(my_instance_dict[key], i + 1)


class TestModel(TestCase):

    should_skip = not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', False)

    class MyModel(models.Model):
        one = models.Field(default=1)

        class Meta:
            collection = 'my-model'

    @skipIf(should_skip, 'Google Application Credentials could not be determined from the environment.')
    def test__meta_fields(self):

        my_instance = TestModel.MyModel()

        self.assertEqual(my_instance._collection, 'my-model', 'Meta fields not working')

    @skipIf(should_skip, 'Google Application Credentials could not be determined from the environment.')
    def test_save(self):
        my_instance = TestModel.MyModel()
        my_instance.save()

        self.assertEquals(my_instance.collection.get(my_instance.id), )
