import sys

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


class NoDerive(ExceptionGroup):  # error: 0, "NoDerive", "NoDerive"
    pass


class NoDeriveBase(BaseExceptionGroup):  # error: 0, "NoDeriveBase", "NoDeriveBase"
    pass


class NoDeriveGeneric(
    ExceptionGroup[Exception]
):  # error: 0, "NoDeriveGeneric", "NoDeriveGeneric"
    pass


import exceptiongroup


class NoDeriveQualified(
    exceptiongroup.ExceptionGroup
):  # error: 0, "NoDeriveQualified", "NoDeriveQualified"
    pass


class SomeMixin: ...


class MultipleBases(
    SomeMixin, ExceptionGroup
):  # error: 0, "MultipleBases", "MultipleBases"
    pass


# safe - overrides derive
class HasDerive(ExceptionGroup):
    def derive(self, excs):
        return HasDerive(self.message, excs)


class HasDeriveBase(BaseExceptionGroup):
    def derive(self, excs):
        return HasDeriveBase(self.message, excs)


class HasDeriveGeneric(ExceptionGroup[Exception]):
    def derive(self, excs):
        return HasDeriveGeneric(self.message, excs)


# async derive is weird but counts
class AsyncDerive(ExceptionGroup):
    async def derive(self, excs):  # type: ignore
        return AsyncDerive(self.message, excs)


# not an ExceptionGroup subclass
class NotAnEG(Exception):
    pass


# nested class
class Outer:
    class InnerNoDerive(ExceptionGroup):  # error: 4, "InnerNoDerive", "InnerNoDerive"
        pass

    class InnerHasDerive(ExceptionGroup):
        def derive(self, excs):
            return Outer.InnerHasDerive(self.message, excs)
