import os
import inspect
from typing import Optional

from fsmodels.common import _BaseModel, ValidationError
from fsmodels.fields import Field, ModelField
from . utils import snake_case, skip_if

# whether we will should try to connect to firestore
CAN_CONNECT = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', False)


class BaseModel(_BaseModel):
    """
    Example:

    class User(BaseModel):
        username = Field(required=True)

    user = User(username='bmayes', _validate_on_init=True)

    """
    id = Field()

    def _get_fields(self) -> frozenset:
        """
        Used to keep track of all Field instances defined on a subclass of BaseModel.

        :return: hashable set (frozenset) of all fields defined on the BaseModel subclass
        """
        field_attr_names = []
        for field_attr_name in dir(self):
            attr = inspect.getattr_static(self, field_attr_name)
            if not isinstance(attr, ModelField) and isinstance(attr, Field):
                field_attr_names.append(field_attr_name)
        # frozenset will always return set items in the same order regardless of the order
        # that they are added. This results in hash-safe sets
        return frozenset(field_attr_names)

    def _get_model_fields(self) -> frozenset:
        """
        Used to keep track of all ModelField instances defined on a subclass of BaseModel.

        :return: hashable set (frozenset) of all ModelFields defined on the BaseModel subclass
        """
        field_attr_names = []
        for field_attr_name in dir(self):
            attr = inspect.getattr_static(self, field_attr_name)
            if isinstance(attr, ModelField):
                field_attr_names.append(field_attr_name)
        # frozenset will always return set items in the same order regardless of the order
        # that they are added. This results in hash-safe sets
        return frozenset(field_attr_names)

    def _set_fields(self, _validate_on_init, kwargs):
        self._field_names = self._get_fields()
        for field_name in self._field_names:
            field = getattr(self, field_name)
            field.model_name = self.__class__.__name__
            field.name = field_name
            field_value = kwargs.get(field_name, field.default())
            # replaces the original field with the corresponding value
            setattr(self, field_name, field_value)
            # actually `Field` instance becomes hidden
            setattr(self, f'_{field_name}', field)
            if _validate_on_init:
                field.validate(field_value)

    def _set_model_fields(self, _validate_on_init, kwargs):
        self._model_field_names = self._get_model_fields()
        for field_name in self._model_field_names:
            field = getattr(self, field_name)
            field.model_name = self.__class__.__name__
            field.name = field_name
            field_value = kwargs.get(field_name, field.default())
            # replaces the original field with the corresponding value
            setattr(self, field_name, field_value)
            # actually `Field` instance becomes hidden
            setattr(self, f'_{field_name}', field)
            if _validate_on_init:
                field.validate(field_value)

    def __init__(self, _validate_on_init: bool = False, **kwargs):
        f"""
        Sets all Field instances defined on a BaseModel subclass as private members to the BaseModel subclass instance.
        Then creates public members with the value of Field<instance>.default(*args, **kwargs)

        :param _validate_on_init: Whether or not to call the .validate() function on init
        :param kwargs: values corresponding to fields defined on the subclass of BaseModel.

        {self.__class__.__doc__}
        """

        self._set_fields(_validate_on_init, kwargs)
        self._set_model_fields(_validate_on_init, kwargs)

    @property
    def is_valid(self):
        return self.validate(raise_error=False)[0]

    def validate(self, raise_error: bool = True) -> (bool, dict):
        """
        Call all the validation methods of the fields defined on the Model subclass and return (True, {}) if they
        are all valid. Otherwise, raises an error (see raise_error) or returns (False, description_of_errors<dict>)

        :param raise_error: whether or not validation errors of Model fields will raise an exception
        :return (bool, dict): whether or not there was an error and a dict describing the errors

        Example:

        class User(BaseModel):
            username = Field(required=True)

        user = User()
        user.validate(raise_error=False) # returns (False, description_of_errors<dict>) because username is required
        """
        error_map = {}
        for field_name in self._field_names.union(self._model_field_names):
            # The `Field` version of the field is now private
            field_obj = getattr(self, f'_{field_name}')
            field_value = getattr(self, field_name)
            is_valid, validation_error = field_obj.validate(field_value, raise_error)
            if not is_valid:
                error_map[field_name] = validation_error
        # whether all fields passed validation, and if not, why not
        model_invalid = bool(error_map)
        if raise_error and model_invalid:
            raise ValidationError(error_map)
        return not model_invalid, error_map

    def to_dict(self) -> dict:
        """
        Determines all Field instances defined on the Model and returns a dictionary with field names as keys and
        field values as values.

        Example:

        class User(BaseModel):
            username = Field(required=True, default=generate_next_username)

        user = User() # username.default() is called on __init__
        user.to_dict() # returns {'username': 'user_n'}

        :return:
        """
        field_tuple = tuple((field_name, getattr(self, field_name)) for field_name in self._field_names.union(self._model_field_names))
        return {
            field_name: field_value.to_dict() if hasattr(field_value, 'to_dict') else field_value
            for field_name, field_value in field_tuple
        }

    def from_dict(self, dict_obj: dict):
        # TODO: Sanity check. Should we discard unused keys or should we raise errors?
        """
        Set the values of fields on the Model instance to correspond to the keys in the dictionary. Mutates the
        Model instance in place and returns nothing.

        :param dict_obj: dict with key, value pairs corresponding to fields defined on the Model
        :return:

        Example:

        class User(BaseModel):
            username = Field(required=True, default=generate_next_username)

        user = User() # username.default() is called on __init__
        user_dict = user.to_dict() #  {'username': 'user_3'}
        user2 = User()
        user2.from_dict(user_dict)
        user2.to_dict() # returns {'username': 'user_3'}

        """
        field_tuple = tuple(
            (field_name, getattr(self, field_name)) for field_name in self._field_names)
        for field_name, _ in field_tuple:
            setattr(self, field_name, dict_obj.get(field_name, None))


class Model(BaseModel):
    # TODO: implement relational firestore logic, add to __doc__
    """
    Connects BaseModel to a firestore collection and implements basic model convenience methods.

    Example:

    class Profile(Model):
        id = Field(required=True, default=uuid.uuid4)
        first_name = Field(required=True)
        last_name = Field(required=True)

        class Meta:
            collection = 'artichoke'

    class User(Model):
        id = Field(required=True, default=uuid.uuid4)
        username = Field(required=True)
        password = Field(required=True)
        profile = ModelField(Profile, required=True)

        class Meta:
            collection = 'okey-dokey'

    profile = Profile(first_name='Billy', last_name='Jean') # default id created on Model instance
    user = User(username='bjean', password='password', profile=profile) # default id created on Model instance

    user.save() # new profile created to collection named "artichoke", new user added to collection named okey-dokey
    user.retrieve() # get newly created user according to id
    user.delete() # delete newly created profile according to id


    """

    class Meta:
        # it's okay if there's no Meta
        pass

    def __init__(self, **kwargs):
        super(Model, self).__init__(**kwargs)
        self._set_meta()
        self._connect_client()

    def _set_meta(self):
        self._meta_fields = [field for field in dir(self.Meta) if not field.startswith('__')]
        if 'model_name' in self._meta_fields:
            self._model_name = self.Meta.model_name
        else:
            self._model_name = snake_case(self.__class__.__name__)
        if 'collection' in self._meta_fields:
            self._collection = self.Meta.collection
        else:
            self._collection = self._model_name

    @skip_if(not CAN_CONNECT, 'Most methods on Model will not work.')
    def _connect_client(self):
        from google.cloud import firestore
        db = firestore.Client()
        self.firestore = firestore
        self.db = db
        self.collection = db.collection(self._collection)

    @staticmethod
    def _document_exists(document) -> bool:
        return bool(document.to_dict())

    def clean(self) -> dict:
        # TODO revisit clean to do more than just validate
        """
        :return:
        """
        self.validate()
        return self.to_dict()

    def save(self, patch: bool = True, additional_fields: Optional[dict] = None, is_child: bool = False) -> dict:
        """
        Save the record to the relevant collection in firestore (self._collection). If there is an id, it tries to
        fetch the existing record first. If not, it creates a new record.

        :param patch: only update the firestore record according to the values defined on the instance (rather than
                        overwriting the entire to match the instance)
        :param additional_fields: dictionary of any additional fields to be saved on the firestore record that are
                                    not defined explicitly on the model
        :param is_child: whether or not the record being saved is a child of another record
        :return: dictionary with id and the result of the write operation from firestore
        """
        record = self.clean()

        # after this if/else branch, we know for sure that self.id will refer to an id in firestore
        if record.get('id', False):
            # remove id from record so it is not saved as an attribute in firestore,
            # use it to get an existing document or create a new document with corresponding ID.
            document_ref = self.collection.document(str(record.pop('id')))
            new_record = not self._document_exists(document_ref.get())
        else:
            new_record = True
            document_ref = self.collection.document()
            self.id = document_ref.id

        # we want to write the related model ids on the saved firestore record
        related_record_ids = {}
        reverse_id_label = f'{self._model_name}_id'
        for model_field_instance_name in self._get_model_fields():
            field_name = model_field_instance_name.lstrip('_')
            model_field_value = getattr(self, field_name)
            # sanity check
            assert model_field_value is None or isinstance(model_field_value, BaseModel)
            # save related model field in firestore and give us the id
            if model_field_value is not None:
                res = model_field_value.save(patch=patch, additional_fields={reverse_id_label: self.id}, is_child=True)
                model_field_record_id = res['id']
                related_record_ids[f'{model_field_value._model_name}_id'] = model_field_record_id

        record.update(related_record_ids)
        if additional_fields:
            record.update(additional_fields)
        # don't want to execute the below logic it if this record is the child of another record... in that case
        # we already know that we need to fetch related fields
        if not is_child:
            # means that the nested related records stored in firestore might not be 100% accurate, and we should
            # do an additional fetch for the related fields
            record.update({'_should_fetch_related': patch and not new_record})

        if not new_record:
            if patch:
                return {'id': self.id, 'result': document_ref.update(record)}
            else:
                return {'id': self.id, 'result': document_ref.set(record)}

        return {'id': self.id, 'result': document_ref.set(record)}

    def retrieve(self, overwrite_local: bool = False) -> dict:
        """
        Retrieve the record corresponding to the id defined on the instance. If overwrite_local is True, the instance
        field values are overwritten with the firestore record values.

        :param overwrite_local: whether or not to overwrite instance field values with firestore field values
        :return:
        """
        id_as_str = None if self.id is None else str(self.id)  # just to be sure that id is a str
        if not id_as_str:
            raise ValidationError(f'Cannot retrieve document for {self._collection}; no id specified.')
        document_dict = self.collection.document(id_as_str).get().to_dict()
        if document_dict is None:
            return {}
        document_dict.update({'id': id_as_str})
        if overwrite_local:
            self.from_dict(document_dict)
        return document_dict

    def delete(self) -> dict:
        """
        Deletes the firestore record corresponding to the id defined on the instance

        :return: dictionary describing the result of the delete operation from firestore
        """

        id_as_str = None if self.id is None else str(self.id)  # just to be sure that id is a str
        if not id_as_str:
            raise ValidationError(f'Cannot call delete for {self._collection} document; no id specified.')
        document_ref = self.collection.document(str(id_as_str))
        return {'result': document_ref.delete()}
