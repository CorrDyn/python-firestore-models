import os
import time
import uuid

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

    def test__field_names(self):

        class MyModel(models.BaseModel):
            test_field1 = models.Field()
            test_field2 = models.Field()
            test_field3 = models.Field()

        test = MyModel()
        # fields defined in the class scope are stored privately and can be listed by calling _get_fields
        self.assertTrue(all([field in test._field_names for field in ['test_field1', 'test_field2', 'test_field3']]))

    def test__model_field_names(self):

        class MyModel1(models.BaseModel):
            test_field = models.Field()

        class MyModel2(models.BaseModel):
            test_model_field = models.ModelField(MyModel1)

        test = MyModel2()
        # fields defined in the class scope are stored privately and can be listed by calling _get_fields
        self.assertTrue(all([field in test._model_field_names for field in ['test_model_field']]))

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

    def test_is_valid(self):
        class MyModel(models.BaseModel):
            test_field1 = models.Field(required=True)
            test_field2 = models.Field(required=True, default=time.time)
            test_field3 = models.Field(required=False)
            test_field4 = models.Field(required=True, validation=lambda x: (
            isinstance(x, int), {'detail': 'test_field4 must be an int.'}))

        self.assertFalse(MyModel().is_valid, 'is_valid is not failing invalid model instances')
        self.assertTrue(MyModel(test_field1=1, test_field4=7).is_valid, 'is_valid not passing valid model instances')

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

    def test_from_dict(self):

        class MyModel(models.BaseModel):
            one = models.Field()
            two = models.Field()
            three = models.Field()
            four = models.Field()

        my_instance = MyModel()
        my_instance.from_dict({'one': 1, 'two': 2, 'three': 3, 'four': 4})
        my_instance_dict = my_instance.to_dict()

        for i, key in enumerate(['one', 'two', 'three', 'four']):
            self.assertEqual(my_instance_dict[key], i + 1)


should_skip = not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', False)


@skipIf(should_skip, 'Google Application Credentials could not be determined from the environment.')
class TestModel(TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestModel, cls).setUpClass()

        class MyModel(models.Model):
            one = models.Field(default=1)

            class Meta:
                collection = 'my-model'
                model_name = 'my_model'

        cls.MyModel = MyModel

    def test__meta_fields(self):

        my_instance = self.MyModel()

        self.assertEqual(my_instance._collection, 'my-model', 'Meta fields not working')
        self.assertEqual(my_instance._model_name, 'my_model', 'Meta fields not working')

    def test_save_delete_retrieve(self):
        my_instance = self.MyModel()
        my_instance.save()

        my_dict = my_instance.to_dict()
        remote_dict = my_instance.retrieve()

        for key, value in my_dict.items():
            self.assertEqual(value, remote_dict[key], 'remote value did not equal local value.')

        my_instance.delete()

        self.assertEqual(my_instance.retrieve(), {}, 'remote instance should be empty dict after delete.')
