# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class Ppdv(Component):
    """A Ppdv component.
ExampleComponent is an example component.
It takes a property, `label`, and
displays it.
It renders an input with the property `value`
which is editable by the user.

Keyword arguments:

- id (string; optional)

- sensorData (list of dicts; optional)

    `sensorData` is a list of dicts with keys:

    - id (number; required)

    - name (string; required)

    - value (number; required)"""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'ppdv'
    _type = 'Ppdv'
    @_explicitize_args
    def __init__(self, id=Component.UNDEFINED, sensorData=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'sensorData']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'sensorData']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(Ppdv, self).__init__(**args)
