The descriptions on the grid specifications can be found here. It is assumed that a corresponding `pypower` case file has been called so that repeated specifications such as branch resistance and reactance are not repeated.

There are six types of entries in the configuration file: bus, load, solar, wind, gen, and branch

- Entry bus

| Name | type | Description |
| --- | --- | --- |
| shunt | bool | If the bus has a shunt capacitor |

- Entry load

| Name | type | Description |
| --- | --- | --- |
| cls_ratio | float | the cost of load shedding with respect to the maximum in cv |
| max_default_ratio | float | load penetration level: the maximum total load with respect to the maximum total generation (including renewable). Maximum: 1 |

- Entry solar: left as {} if no solar

| Name | type | Description |
| --- | --- | --- |
idx | list of int | the bus idx of the solar panel (start from 1) |
default_ratio | list of float | solar peneration lavel: the default solar generation with respect to the maximum total generation (including renewable). Maximum: 1 |
csc_ratio | float | the cost of solar curtailment with respect to the maximum in cv |

- Entry wind: left as {} if no wind

| Name | type | Description |
| --- | --- | --- |
idx | list of int | the bus idx of the wind turbine (start from 1) |
default_ratio | list of float | wind peneration level: the default wind generation with respect to the maximum total generation (including renewable). Maximum: 1 |
cwc_ratio | float | the cost of wind curtailment with respect to the maximum in cv |

- Entry gen

| Name | type | Description |
| --- | --- | --- |
| cf | list of float | the fixed cost of the generator when its on |
| cv | list of float | the variable cost of the generator |
| cv2 | list of float | the quadratic variable cost of the generator |
| cu | list of float | the start up cost of the generator |
| cd | list of float | the shut down cost of the generator |
| ces_ratio | list of float | the energy storage cost of the generator with respect to the maximum in cv |
| ru_ratio | float or list of float | the ramp up ratio of the generator with respect to the maximum pgmax |
| rsu_ratio | float or list of float | the ramp start up ratio of the generator with respect to the maximum pgmax |
| rd_ratio | float or list of float | the ramp down ratio of the generator with respect to the maximum pgmax |
| rsd_ratio | float or list of float | the ramp shut down ratio of the generator with respect to the maximum pgmax |
| rued_ratio | float or list of float | at the ED stage, the ramp up ratio of the generator with respect to the maximum pgmax |
| rded_ratio | float or list of float | at the ED stage, the ramp down ratio of the generator with respect to the maximum pgmax |
| pgmax | list of float | the maximum power output of the generator (can be {}) |

- Entry branch

| Name | type | Description |
| --- | --- | --- |
| pfmax | list of float | the maximum power flow of the branch |
| shift_angle | list of float | the shift angle of the branch |