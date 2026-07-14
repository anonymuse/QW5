# Contract fixtures v1

The `*.valid.json` files are synthetic schema examples. They are not target-cluster,
model, transport, or feasibility evidence.

[`negative-cases.json`](negative-cases.json) defines deterministic mutations over the
valid examples. Validation applies one mutation at a time and requires exactly the
documented schema keyword to reject the documented instance path. This avoids copying
large valid fixtures while keeping every negative case reviewable.
