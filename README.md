## python-firestore-models

This library serves as a wrapper around Google's Firestore. It implements validation, type checking facilities, 
and relational (work in progress) model logic.

## When to Use

When you want a simple abstraction layer on top of Firestore to help you keep track of entities and their relationships,
the way you would achieve it with an ORM. The library's API borrows several design paradigms from Django's ORM, because 
I like Django's ORM.

## Installation
`pip install <library_name>`


## Basic Usage

### Environment
You will need to set up your environment in the usual way to have access to your resources on
Google Cloud Platform.

```
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/credentials.json'
```

If you do not have this variable set, model instances will log a warning, and nothing will
actually work with Firestore.

### Creating, Fetching, and Deleting
```
from fsmodels.models import Model
from fsmodels.fields import Field

def is_valid_string(value):
    return value is None or isinstance(value, str), f'value must be str, cannot be {value}'


class User(Model):

    username = Field(required=True)
    password = Field(required=True)
    first_name = Field(required=True, default='Billy')
    last_name = Field(validation=is_valid_string)
    created_date = Field(default=time.time)
    
    
my_user = User(username='user1', password='goodpassword')
my_user.save() # automatically generates a new id and creates this user in firestore.
my_user.retrieve() # returns a dict of the record in firestore
my_user.delete() # deletes the record in firestore with my_user.id


my_user2 = User(username='user2') # validation functions are not called on __init__ by defalt
my_user2.save() # raises a validation error; password is a required field.
```

### Edit Existing
```
user = User(id='my_id') 

# retrieve ignores everything about the local model instance other than the id 
user.retrieve(overwrite_local=True)

print(user.to_dict()) # see what was in firestore
user.first_name = 'a different name'
user.save()
```

### Delete Existing
```
user = User(id='my_id') 
 
user.delete()
```

## Advanced Usage
### One to One Relationships

```
import uuid

from fsmodels.models import Model
from fsmodels.fields import Field, ModelField, IDField

def uuid_as_str():
    return str(uuid.uuid4())

class Profile(Model):
    id = IDField(required=True, default=uuid_as_str)
    first_name = Field(required=True)
    last_name = Field(required=True)

class User(Model):
    id = IDField(required=True, default=uuid_as_str)
    username = Field(required=True)
    password = Field(required=True)
    profile = ModelField(Profile, required=True)
    
profile = Profile(first_name='Billy', last_name='Mayes')
# will save both the profile and the user
user = User(username='bmayes', password='plaintextpassword', profile=profile)

print(user.retrieve())
#{'profile': {'id': 'bd3ca41a-b6c4-4249-ac48-eb05db79bb3d',
#  'first_name': 'Billy',
#  'last_name': 'Mayes'},
# 'password': 'plaintextpassword',
# 'username': 'bmayes',
# 'profile_id': 'bd3ca41a-b6c4-4249-ac48-eb05db79bb3d',
# 'id': '1e586d79-f2c0-4618-a7f7-95308a54298e'}

print(profile.retrieve())
#{'user_id': '1e586d79-f2c0-4618-a7f7-95308a54298e',
# 'first_name': 'Billy',
# 'last_name': 'Mayes',
 ```
 
 ### One to Many Relationships
 Planned.
 
 ### Overriding Defaults
```
# model_name in error messages and collection name in firestore is my_model1
class MyModel1(Model):
    first_name = Field(required=True)
    last_name = Field(required=True)
    
    class Meta:
        model_name = 'Profiles'
        
# model_name in error messages and collection name in firestore is MY-MODEL-2
class MyModel2(Model):
    first_name = Field(required=True)
    last_name = Field(required=True)
    
    class Meta:
        model_name = 'MY-MODEL-2'
        
# model_name in error messages is my_model3 and collection name in firestore is mY-mODeL-3
class MyModel3(Model):
    first_name = Field(required=True)
    last_name = Field(required=True)
    
    class Meta:
        collection = 'mY-mODeL-3'
```
 
### Using Google's firestore API
```
class MyModel1(Model):
    first_name = Field(required=True)
    last_name = Field(required=True)

m = MyModel1()

# same as google.cloud.firestore
m.firestore
# same as google.cloud.firestore.Client()
m.db
# same as google.cloud.firestore.Client().collection(m._collection) where m._collection in this case is my_model1
m.collection

# you can do stuff like
for record in m.collection.get():
    print(record.to_dict())
```