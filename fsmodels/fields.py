from typing import Optional, Callable, Tuple, Type

from fsmodels.common import ValidationError, _BaseModel


class Field:
    """
    Field to be used on a Model

    Example:

    def validate_date_created(date_created_value):
        is_valid, error = isint(date_created_value), {}
        if not is_valid:
            error = {'error': 'value of date_created must be an integer number.'}
        return is_valid, error

    date_created = Field(required=True, default=time.time, validation=validate_date_created)
    """
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

    def __init__(self, model: Type[_BaseModel], **kwargs):
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


class IDField(Field):
    """
    Adds default validation to Field a make sure that the `value` is a string
    """

    def validate(self, value, raise_error: bool = True):
        if value is not None and not isinstance(value, str):
            message = f'{self.model_name} value of {self.name} failed validation; {self.name} must be str instance, not {value.__class__}.'
            if raise_error:
                raise ValidationError(message)
            else:
                return False, message
        return super(IDField, self).validate(value, raise_error=raise_error)
