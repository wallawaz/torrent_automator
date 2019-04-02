def must_be_set(attribute):
    def _must_be_set(_func):
        def wrapper(self, *args):
            already_set = self.__dict__.get(attribute)
            if already_set is None:
                raise Exception("{} must be set before calling {}"
                                .format(attribute, _func))
            return _func(self, *args)
        return wrapper
    return _must_be_set


