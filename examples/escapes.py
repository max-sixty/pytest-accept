def func(a, b):
    r"""
    Example:
    >>> import xarray as xr
    >>> x = func(xr.DataArray([5], dims="a"), xr.DataArray([1], dims="a"))
    >>> s = x.__repr__()
    >>> x
    <xarray.DataArray (a: 1)>
    array([6])
    Dimensions without coordinates: a
    Attributes:
        a:        <xarray.DataArray (a: 1)>\narray([5])\nDimensions without coord...
        b:        <xarray.DataArray (a: 1)>\narray([1])\nDimensions without coord...
    >>> len(s)
    244
    >>> print(s)
    <xarray.DataArray (a: 1)>
    array([6])
    Dimensions without coordinates: a
    Attributes:
        a:        <xarray.DataArray (a: 1)>\narray([5])\nDimensions without coord...
        b:        <xarray.DataArray (a: 1)>\narray([1])\nDimensions without coord...

    >>> print(x.__repr__())
    <xarray.DataArray (a: 1)>
    array([6])
    Dimensions without coordinates: a
    Attributes:
        a:        <xarray.DataArray (a: 1)>\narray([5])\nDimensions without coord...
        b:        <xarray.DataArray (a: 1)>\narray([1])\nDimensions without coord...

    >>> r"testing\ntesting"
    'testing\\ntesting'
    """
    c = a + b
    c = c.assign_attrs(a=a, b=b)
    return c


def raw_string():
    r"""
    >>> "\n"
    '\n'

    """
