import inspect
from typing import Optional, Callable, Tuple

from . utils import snake_case


class ValidationError(BaseException):
    pass


class _BaseModel:
    # all Model classes will be subclassed from this. Otherwise we would have circular requirements for type hints
    # in methods that required BaseModel as type hints
    pass


class Field:

    # name is overwritten by the Model containing the Field instance.
    name = None
    model_name = ''

    def __init__(
            self,
            required: bool = False,
            default=None,
            validation: Optional[Callable[..., Tuple[bool, dict]]] = None):
        """
        :param required: Whether or not the field is required
        :param default: What the field defaults to if no value is set
        :param validation: return true if the value is valid, otherwise return false

        Example:

        def validate_date_created(date_created_value):
            is_valid, error = isint(date_created_value), {}
            if not is_valid:
                error = {'error': 'value of date_created must be an integer number.'}
            return is_valid, error

        date_created = Field(required=True, default=time.time, validation=validate_date_created)
        """
        self.required = required

        # make sure default is always a callable
        if callable(default):
            self._default = default
        else:
            self._default = lambda *args, **kwargs: default

        # validation should either be None or a callable
        if validation is not None:
            if callable(validation):
                self.validation = validation
            else:
                raise ValidationError(f'validation must be a callable, cannot be {validation}')
        else:
            # always passes if validation is None
            self.validation = lambda x: (True, {})

    def validate(self, value, raise_error: bool = True) -> (bool, dict):
        """
        Check that the passed value is not None if the Field instance is required, and calls the `validation`
        function passed via Field.__init___. Raises an error if raise_error is `True` (default).

        :param value: value to validate against the Field specifications
        :param raise_error: whether or not to raise a ValidationError when an error is encountered.
        :return (bool, dict): whether or not there was an error and a dict describing the errors

        Example:

        def validate_date_created(date_created_value):
            is_valid, error = isint(date_created_value), {}
            if not is_valid:
                error = {'error': 'value of date_created must be an integer number.'}
            return is_valid, error

        date_created = Field(required=True, default=time.time, validation=validate_date_created)

        date_created.validate(time.time()) # returns (True, {})
        """
        if self.required and not value:
            message = f'{self.model_name} field {self.name} is required but received no default and no value.'
            if raise_error:
                raise ValidationError(message)
            else:
                return False, {'error': message}

        validation_passed, errors = self.validation(value)

        if raise_error:
            if not validation_passed:
                raise ValidationError(f'{self.model_name} value of {self.name} failed validation.')

        # whether or not the validation passed and useful error information
        return validation_passed, {}

    def default(self, *args, **kwargs):
        """
        Returns the Field instance default. Returns None if the user did not specify a default value or default function.

        :param args: arbitrary arguments to be used to be the default generating function specified in Field.__init__
        :param kwargs: arbitrary kwargs to be used in the default generating function specified in Field.__init__
        :return: the default Field value or the result of the default function

        Example:

        date_created = Field(required=True, default=time.time)

        date_created.default() # returns time.time()
        """
        return self._default(*args, **kwargs)

    def __repr__(self):
        return f'<{self.__class__.__name__} name:{self.name} required:{self.required} default:{self.default} validation:{self.validation.__name__}>'


class ModelField(Field):
    """
    Subclass of Field that makes reference to a subclass of BaseModel.

    Used for one-to-many relationships.
    """

    def __init__(self, model: _BaseModel, **kwargs):
        # keeping track of this stuff so we can emit useful error messages
        self.field_model = model
        self.field_model_name = model.__name__
        super(ModelField, self).__init__(**kwargs)

    def validate(self, model_instance, raise_error: bool = True) -> (bool, dict):
        """
        Check to see that the passed model instance is a subclass of `model` parameter passed into ModelField.__init__,
        then validate the fields of that model as usual. Parallels the validate method of the Field class
        
        :param model_instance: instance of model to validate (parallels `value` in validate method of Field class)
        :param raise_error: whether or not an exception is raised on validation error
        :return (bool, dict): whether or not there was an error and a dict describing the errors
        """
        is_valid_model, is_valid_field, model_errors, field_errors = True, {}, True, {}
        # check that the passed model_instance is a subclass of the prescribed model from __init__
        if isinstance(model_instance, self.field_model):
            is_valid_model, model_errors = model_instance.validate(raise_error)
        # the model instance is not None, this will emit an error. Otherwise, we check the
        # field validation logic to determine whether this is a required field.
        elif model_instance is not None:
            message = f'{self.name} field failed validation. {model_instance} is {model_instance.__class__.__name__}, must be {self.field_model_name}'
            if raise_error:
                raise ValidationError(message)
            else:
                return False, {'error': message}
        if is_valid_model:
            is_valid_field, field_errors = super(ModelField, self).validate(model_instance, raise_error)
        if is_valid_field and is_valid_model:
            return True, {}
        return False, {**model_errors, **field_errors}


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
            # if _validate_on_init:
            #     field.validate(field_value)

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
        for field_name in self._field_names:
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

    def clean(self):
        raise NotImplemented

    def save(self):
        raise NotImplemented


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

    profile.save() # new profile created to collection named "artichoke"
    profile.retrieve() # get newly created profile according to id
    profile.delete() # delete newly created profile according to id


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
        if 'collection' in self._meta_fields:
            self._collection = self.Meta.collection
        else:
            self._collection = snake_case(self.__class__.__name__)

    def _connect_client(self):
        from .firestore import db
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

    def save(self, patch: bool = True, additional_fields: Optional[dict] = None) -> dict:
        """
        Save the record to the relevant collection in firestore (self._collection). If there is an id, it tries to
        fetch the existing record first. If not, it creates a new record.

        :param patch: only update the firestore record according to the values defined on the instance (rather than
                        overwriting the entire to match the instance)
        :param additional_fields: dictionary of any additional fields to be saved on the firestore record that are
                                    not defined explicitly on the model
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
        reverse_id_label = f'{self._collection}_id'
        for model_field_instance_name in self._get_model_fields():
            field_name = model_field_instance_name.lstrip('_')
            record.pop(field_name)  # prevent from saving this information on the record (is that what we want?)
            model_field_value = getattr(self, field_name)
            # sanity check
            assert model_field_value is None or isinstance(model_field_value, BaseModel)
            # save related model field in firestore and give us the id
            model_field_record_id = None if model_field_value is None else str(model_field_value.save(
                additional_fields={reverse_id_label: str(self.id)}
            )['id'])
            related_record_ids[f'{model_field_value._collection}_id'] = model_field_record_id

        record.update(related_record_ids)
        if additional_fields:
            record.update(additional_fields)

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
        if not self.id:
            raise ValidationError(f'Cannot retrieve document for {self._collection}; no id specified.')
        document_dict = self.collection.document(str(self.id)).get().to_dict()
        if document_dict is None:
            return {}
        document_dict.update({'id': self.id})
        if overwrite_local:
            self.from_dict(document_dict)
        return document_dict

    def delete(self) -> dict:
        """
        Deletes the firestore record corresponding to the id defined on the instance

        :return: dictionary describing the result of the delete operation from firestore
        """
        if not self.id:
            raise ValidationError(f'Cannot call delete for {self._collection} document; no id specified.')
        document_ref = self.collection.document(str(self.id))
        return {'result': document_ref.delete()}
