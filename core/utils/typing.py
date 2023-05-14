TYPE_CHECKING_SHIM = False
if TYPE_CHECKING_SHIM:
    from collections.abc import Sequence as Sequence
    from typing import TYPE_CHECKING as TYPE_CHECKING
    from typing import Any as Any
    from typing import ClassVar as ClassVar
    from typing import Generic as Generic
    from typing import Iterable as Iterable
    from typing import TypeAlias as TypeAlias
    from typing import TypeVar as TypeVar
    from typing import cast as cast

    from typing_extensions import Self as Self
else:
    Any = TypeAlias = Self = object
    TYPE_CHECKING = False

    class SpecialFormType:
        def __getitem__(self, items):
            return object

    def cast(x, y):
        return y

    def TypeVar(*_, **__):
        return object()

    Sequence = SpecialFormType()
    Generic = SpecialFormType()
    Iterable = SpecialFormType()
