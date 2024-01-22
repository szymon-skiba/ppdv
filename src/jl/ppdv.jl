# AUTO GENERATED FILE - DO NOT EDIT

export ppdv

"""
    ppdv(;kwargs...)

A Ppdv component.
ExampleComponent is an example component.
It takes a property, `label`, and
displays it.
It renders an input with the property `value`
which is editable by the user.
Keyword arguments:
- `id` (String; optional)
- `sensorData` (optional): . sensorData has the following type: Array of lists containing elements 'id', 'name', 'value'.
Those elements have the following types:
  - `id` (Real; required)
  - `name` (String; required)
  - `value` (Real; required)s
"""
function ppdv(; kwargs...)
        available_props = Symbol[:id, :sensorData]
        wild_props = Symbol[]
        return Component("ppdv", "Ppdv", "ppdv", available_props, wild_props; kwargs...)
end

