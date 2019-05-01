class ValidationError(BaseException):
    pass


class _BaseModel:
    # all Model classes will be subclassed from this. Otherwise we would have circular requirements for type hints
    # in methods that required BaseModel as type hints
    def clean(self, *args, **kwargs):
        raise NotImplementedError

    def validate(self, *args, **kwargs):
        raise NotImplementedError

    def save(self, *args, **kwargs):
        raise NotImplementedError

    def retrieve(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        raise NotImplementedError
