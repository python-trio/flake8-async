import sys

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


class NoDerive(ExceptionGroup):  # error: 0, "NoDerive", "NoDerive"
    pass


class NoDeriveBE(BaseExceptionGroup):  # error: 0, "NoDeriveBE", "NoDeriveBE"
    pass


class NoDeriveG(ExceptionGroup[Exception]):  # error: 0, "NoDeriveG", "NoDeriveG"
    pass


import exceptiongroup as eg


class NoDeriveQ(eg.ExceptionGroup):  # error: 0, "NoDeriveQ", "NoDeriveQ"
    pass


class _Mixin: ...


class MultiBase(_Mixin, ExceptionGroup):  # error: 0, "MultiBase", "MultiBase"
    pass


# safe - overrides derive
class HasDerive(ExceptionGroup):
    def derive(self, excs):
        return HasDerive(self.message, excs)


class HasDeriveBE(BaseExceptionGroup):
    def derive(self, excs):
        return HasDeriveBE(self.message, excs)


class HasDeriveG(ExceptionGroup[Exception]):
    def derive(self, excs):
        return HasDeriveG(self.message, excs)


# async derive is weird but counts
class AsyncDer(ExceptionGroup):
    async def derive(self, excs):  # type: ignore
        return AsyncDer(self.message, excs)


# not an ExceptionGroup subclass
class NotAnEG(Exception):
    pass


# nested class
class Outer:
    class InnerNo(ExceptionGroup):  # error: 4, "InnerNo", "InnerNo"
        pass

    class InnerHas(ExceptionGroup):
        def derive(self, excs):
            return Outer.InnerHas(self.message, excs)
