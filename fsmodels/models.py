import inspect
from typing import Optional, Callable

from . utils import snake_case


class ValidationError(BaseException):
    pass


class Field:

    # name is overwritten by the Model containing the Field instance.
    name = None

    def __init__(
            self,
            required: bool = False,
            default=None,
            validation: Optional[Callable[..., bool]] = None):
        """
        :param required: Whether or not the field is required
        :param default: What the field defaults to if no value is set
        :param validation: return true if the value is valid, otherwise return false
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
            self.validation = lambda x: True

    def validate(self, value, error=True):
        if self.required and not value:
            raise ValidationError(f'field {self.name} is required but received no default and no value.')

        validation_passed = self.validation(value)

        if error:
            if not validation_passed:
                raise ValidationError(f'value of {self.name} failed validation.')

        return validation_passed

    def default(self, *args, **kwargs):
        return self._default(*args, **kwargs)

    def __repr__(self):
        return f'<{self.__class__.__name__} name:{self.name} required:{self.required} default:{self.default} validation:{self.validation.__name__}>'


class BaseModel:
    id = Field()

    def _get_fields(self):
        field_attr_names = []
        for field_attr_name in dir(self):
            attr = inspect.getattr_static(self, field_attr_name)
            if isinstance(attr, Field):
                field_attr_names.append(field_attr_name)
        # frozenset will always return set items in the same order regardless of the order
        # that they are added. This results in hash-safe sets
        return frozenset(field_attr_names)

    def __init__(self, _validate_on_init=False, **kwargs):

        self._field_names = self._get_fields()
        for field_name in self._field_names:
            field = getattr(self, field_name)
            field.name = field_name
            field_value = kwargs.get(field_name, field.default())
            # replaces the original field with the corresponding value
            setattr(self, field_name, field_value)
            # actually `Field` instance becomes hidden
            setattr(self, f'_{field_name}', field)
            if _validate_on_init:
                field.validate(field_value)

    def validate(self):
        for field_name in self._field_names:
            # The `Field` version of the field is now private
            field_obj = getattr(self, f'_{field_name}')
            field_value = getattr(self, field_name)
            field_obj.validate(field_value)

    def to_dict(self):
        field_tuple = tuple(
            (field_name, getattr(self, field_name)) for field_name in self._field_names)
        return {
            field_name: field_value.to_dict() if hasattr(field_value, 'field_to_dict') else field_value
            for field_name, field_value in field_tuple
        }

    def from_dict(self, dict_obj: dict):
        field_tuple = tuple(
            (field_name, getattr(self, field_name)) for field_name in self._field_names)
        for field_name, _ in field_tuple:
            setattr(self, field_name, dict_obj.get(field_name, None))

    def clean(self):
        raise NotImplemented

    def save(self):
        raise NotImplemented


class Model(BaseModel):
    """
    Connects BaseModel to a firestore collection and implements basic model convenience methods
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
        from . firestore import db
        self.collection = db.collection(self._collection)

    def clean(self) -> dict:
        self.validate()
        return self.to_dict()

    def save(self) -> dict:
        record = self.clean()
        if record.get('id', False):
            # remove id from record so it is not saved as an attribute in firestore,
            # use it to get or create a new document with corresponding ID.
            document_ref = self.collection.document(str(record.pop('id')))
        else:
            document_ref = self.collection.document()
            self.id = document_ref.id

        return {'id': self.id, 'result': document_ref.set(record)}

    def retrieve(self, overwrite_local: bool = False):
        if not self.id:
            raise ValidationError(f'Cannot retrieve document for {self._connection}; no id speficied.')
        document_dict = self.collection.document(str(self.id)).get().to_dict()
        if document_dict is None:
            return None
        document_dict.update({'id': self.id})
        if overwrite_local:
            self.from_dict(document_dict)
        return document_dict

    def delete(self):
        if not self.id:
            raise ValidationError(f'Cannot call delete for {self._connection} document; no id speficied.')
        document_ref = self.collection.document(str(self.id))
        return {'result': document_ref.delete()}
