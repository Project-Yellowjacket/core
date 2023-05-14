import array
from typing import Any, Literal, Protocol, TypeAlias, TypeVar, overload, runtime_checkable

import uarray

_OpenTextModeUpdating: TypeAlias = Literal[
    "r+",
    "+r",
    "rt+",
    "r+t",
    "+rt",
    "tr+",
    "t+r",
    "+tr",
    "w+",
    "+w",
    "wt+",
    "w+t",
    "+wt",
    "tw+",
    "t+w",
    "+tw",
    "a+",
    "+a",
    "at+",
    "a+t",
    "+at",
    "ta+",
    "t+a",
    "+ta",
    "x+",
    "+x",
    "xt+",
    "x+t",
    "+xt",
    "tx+",
    "t+x",
    "+tx",
]
_OpenTextModeWriting: TypeAlias = Literal["w", "wt", "tw", "a", "at", "ta", "x", "xt", "tx"]
_OpenTextModeReading: TypeAlias = Literal["r", "rt", "tr", "U", "rU", "Ur", "rtU", "rUt", "Urt", "trU", "tUr", "Utr"]
_OpenTextMode: TypeAlias = _OpenTextModeUpdating | _OpenTextModeWriting | _OpenTextModeReading

_OpenBinaryModeUpdating: TypeAlias = Literal[
    "rb+",
    "r+b",
    "+rb",
    "br+",
    "b+r",
    "+br",
    "wb+",
    "w+b",
    "+wb",
    "bw+",
    "b+w",
    "+bw",
    "ab+",
    "a+b",
    "+ab",
    "ba+",
    "b+a",
    "+ba",
    "xb+",
    "x+b",
    "+xb",
    "bx+",
    "b+x",
    "+bx",
]
_OpenBinaryModeWriting: TypeAlias = Literal["wb", "bw", "ab", "ba", "xb", "bx"]
_OpenBinaryModeReading: TypeAlias = Literal["rb", "br", "rbU", "rUb", "Urb", "brU", "bUr", "Ubr"]
_OpenBinaryMode: TypeAlias = _OpenBinaryModeUpdating | _OpenBinaryModeReading | _OpenBinaryModeWriting

AnyStr_co = TypeVar("AnyStr_co", str, bytes, covariant=True)

@runtime_checkable
class PathLike(Protocol[AnyStr_co]):
    def __fspath__(self) -> AnyStr_co: ...

StrOrBytesPath: TypeAlias = str | bytes | PathLike[str] | PathLike[bytes]
_OpenFile: TypeAlias = StrOrBytesPath | int
AnyPath: TypeAlias = str | bytes | PathLike[str] | PathLike[bytes]
FdOrAnyPath: TypeAlias = int | AnyPath

ReadableBuf: TypeAlias = bytearray | array.array[Any] | memoryview | bytes
AnyReadableBuf = TypeVar("AnyReadableBuf", bytearray, array.array, memoryview, bytes)
UAnyReadableBuf = TypeVar("UAnyReadableBuf", bytearray, uarray.array, memoryview, bytes)

WritableBuf: TypeAlias = bytearray | array.array[Any] | memoryview
AnyWritableBuf = TypeVar("AnyWritableBuf", bytearray, array.array, memoryview)
UAnyWritableBuf = TypeVar("UAnyWritableBuf", bytearray, uarray.array, memoryview)

@runtime_checkable
class AbstractBlockDev(Protocol):
    """
    Block devices
    -------------

    A block device is an object which implements the block protocol. This enables a
    device to support MicroPython filesystems. The physical hardware is represented
    by a user defined class. The :class:`AbstractBlockDev` class is a template for
    the design of such a class: MicroPython does not actually provide that class,
    but an actual block device class must implement the methods described below.

    A concrete implementation of this class will usually allow access to the
    memory-like functionality of a piece of hardware (like flash memory). A block
    device can be formatted to any supported filesystem and mounted using ``os``
    methods.

    See :ref:`filesystem` for example implementations of block devices using the
    two variants of the block protocol described below.

    .. _block-device-interface:

    Simple and extended interface
    .............................

    There are two compatible signatures for the ``readblocks`` and ``writeblocks``
    methods (see below), in order to support a variety of use cases.  A given block
    device may implement one form or the other, or both at the same time. The second
    form (with the offset parameter) is referred to as the "extended interface".

    Some filesystems (such as littlefs) that require more control over write
    operations, for example writing to sub-block regions without erasing, may require
    that the block device supports the extended interface.
    """

    @overload
    def readblocks(self, block_num: int, buf: bytearray, /) -> None:
        """
        The first form reads aligned, multiples of blocks.
        Starting at the block given by the index *block_num*, read blocks from
        the device into *buf* (an array of bytes).
        The number of blocks to read is given by the length of *buf*,
        which will be a multiple of the block size.

        The second form allows reading at arbitrary locations within a block,
        and arbitrary lengths.
        Starting at block index *block_num*, and byte offset within that block
        of *offset*, read bytes from the device into *buf* (an array of bytes).
        The number of bytes to read is given by the length of *buf*.
        """
    @overload
    def readblocks(self, block_num: int, buf: bytearray, offset: int, /) -> None:
        """
        The first form reads aligned, multiples of blocks.
        Starting at the block given by the index *block_num*, read blocks from
        the device into *buf* (an array of bytes).
        The number of blocks to read is given by the length of *buf*,
        which will be a multiple of the block size.

        The second form allows reading at arbitrary locations within a block,
        and arbitrary lengths.
        Starting at block index *block_num*, and byte offset within that block
        of *offset*, read bytes from the device into *buf* (an array of bytes).
        The number of bytes to read is given by the length of *buf*.
        """
    @overload
    def writeblocks(self, block_num: int, buf: bytes | bytearray, /) -> None:
        """
        The first form writes aligned, multiples of blocks, and requires that the
        blocks that are written to be first erased (if necessary) by this method.
        Starting at the block given by the index *block_num*, write blocks from
        *buf* (an array of bytes) to the device.
        The number of blocks to write is given by the length of *buf*,
        which will be a multiple of the block size.

        The second form allows writing at arbitrary locations within a block,
        and arbitrary lengths.  Only the bytes being written should be changed,
        and the caller of this method must ensure that the relevant blocks are
        erased via a prior ``ioctl`` call.
        Starting at block index *block_num*, and byte offset within that block
        of *offset*, write bytes from *buf* (an array of bytes) to the device.
        The number of bytes to write is given by the length of *buf*.

        Note that implementations must never implicitly erase blocks if the offset
        argument is specified, even if it is zero.
        """
    @overload
    def writeblocks(self, block_num: int, buf: bytes | bytearray, offset: int, /) -> None:
        """
        The first form writes aligned, multiples of blocks, and requires that the
        blocks that are written to be first erased (if necessary) by this method.
        Starting at the block given by the index *block_num*, write blocks from
        *buf* (an array of bytes) to the device.
        The number of blocks to write is given by the length of *buf*,
        which will be a multiple of the block size.

        The second form allows writing at arbitrary locations within a block,
        and arbitrary lengths.  Only the bytes being written should be changed,
        and the caller of this method must ensure that the relevant blocks are
        erased via a prior ``ioctl`` call.
        Starting at block index *block_num*, and byte offset within that block
        of *offset*, write bytes from *buf* (an array of bytes) to the device.
        The number of bytes to write is given by the length of *buf*.

        Note that implementations must never implicitly erase blocks if the offset
        argument is specified, even if it is zero.
        """
    @overload
    def ioctl(self, op: int, arg: int, /) -> int | None:
        """
        Control the block device and query its parameters.  The operation to
        perform is given by *op* which is one of the following integers:

          - 1 -- initialise the device (*arg* is unused)
          - 2 -- shutdown the device (*arg* is unused)
          - 3 -- sync the device (*arg* is unused)
          - 4 -- get a count of the number of blocks, should return an integer
            (*arg* is unused)
          - 5 -- get the number of bytes in a block, should return an integer,
            or ``None`` in which case the default value of 512 is used
            (*arg* is unused)
          - 6 -- erase a block, *arg* is the block number to erase

        As a minimum ``ioctl(4, ...)`` must be intercepted; for littlefs
        ``ioctl(6, ...)`` must also be intercepted. The need for others is
        hardware dependent.

        Prior to any call to ``writeblocks(block, ...)`` littlefs issues
        ``ioctl(6, block)``. This enables a device driver to erase the block
        prior to a write if the hardware requires it. Alternatively a driver
        might intercept ``ioctl(6, block)`` and return 0 (success). In this case
        the driver assumes responsibility for detecting the need for erasure.

        Unless otherwise stated ``ioctl(op, arg)`` can return ``None``.
        Consequently an implementation can ignore unused values of ``op``. Where
        ``op`` is intercepted, the return value for operations 4 and 5 are as
        detailed above. Other operations should return 0 on success and non-zero
        for failure, with the value returned being an ``OSError`` errno code.
        """
    @overload
    def ioctl(self, op: Literal[4, 5], arg: int, /) -> int:
        """
        Control the block device and query its parameters.  The operation to
        perform is given by *op* which is one of the following integers:

          - 1 -- initialise the device (*arg* is unused)
          - 2 -- shutdown the device (*arg* is unused)
          - 3 -- sync the device (*arg* is unused)
          - 4 -- get a count of the number of blocks, should return an integer
            (*arg* is unused)
          - 5 -- get the number of bytes in a block, should return an integer,
            or ``None`` in which case the default value of 512 is used
            (*arg* is unused)
          - 6 -- erase a block, *arg* is the block number to erase

        As a minimum ``ioctl(4, ...)`` must be intercepted; for littlefs
        ``ioctl(6, ...)`` must also be intercepted. The need for others is
        hardware dependent.

        Prior to any call to ``writeblocks(block, ...)`` littlefs issues
        ``ioctl(6, block)``. This enables a device driver to erase the block
        prior to a write if the hardware requires it. Alternatively a driver
        might intercept ``ioctl(6, block)`` and return 0 (success). In this case
        the driver assumes responsibility for detecting the need for erasure.

        Unless otherwise stated ``ioctl(op, arg)`` can return ``None``.
        Consequently an implementation can ignore unused values of ``op``. Where
        ``op`` is intercepted, the return value for operations 4 and 5 are as
        detailed above. Other operations should return 0 on success and non-zero
        for failure, with the value returned being an ``OSError`` errno code.
        """
    @overload
    def ioctl(self, op: Literal[1, 2, 3, 6], arg: int, /) -> int | None:
        """
        Control the block device and query its parameters.  The operation to
        perform is given by *op* which is one of the following integers:

          - 1 -- initialise the device (*arg* is unused)
          - 2 -- shutdown the device (*arg* is unused)
          - 3 -- sync the device (*arg* is unused)
          - 4 -- get a count of the number of blocks, should return an integer
            (*arg* is unused)
          - 5 -- get the number of bytes in a block, should return an integer,
            or ``None`` in which case the default value of 512 is used
            (*arg* is unused)
          - 6 -- erase a block, *arg* is the block number to erase

        As a minimum ``ioctl(4, ...)`` must be intercepted; for littlefs
        ``ioctl(6, ...)`` must also be intercepted. The need for others is
        hardware dependent.

        Prior to any call to ``writeblocks(block, ...)`` littlefs issues
        ``ioctl(6, block)``. This enables a device driver to erase the block
        prior to a write if the hardware requires it. Alternatively a driver
        might intercept ``ioctl(6, block)`` and return 0 (success). In this case
        the driver assumes responsibility for detecting the need for erasure.

        Unless otherwise stated ``ioctl(op, arg)`` can return ``None``.
        Consequently an implementation can ignore unused values of ``op``. Where
        ``op`` is intercepted, the return value for operations 4 and 5 are as
        detailed above. Other operations should return 0 on success and non-zero
        for failure, with the value returned being an ``OSError`` errno code.
        """
