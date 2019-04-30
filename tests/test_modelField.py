import uuid
from unittest import TestCase

from fsmodels.models import BaseModel, Field, ModelField, ValidationError


class TestModelField(TestCase):

    def test_validate(self):
        class Profile(BaseModel):
            id = Field(required=True, default=uuid.uuid4)
            first_name = Field(required=True)
            last_name = Field(required=True)

        class User(BaseModel):
            id = Field(required=True, default=uuid.uuid4)
            username = Field(required=True)
            password = Field(required=True)
            profile = ModelField(Profile, required=True)

        profile = Profile(first_name='Billy')
        user = User(username='bmayes', password='password', profile=profile)
        with self.assertRaises((ValidationError, )):
            user.validate(raise_error=True)

        profile = Profile(first_name='Billy', last_name='Mayes')
        user = User(username='bmayes', password='password', profile=profile)
        self.assertTrue(user.is_valid, 'ModelField should not raise an error')
