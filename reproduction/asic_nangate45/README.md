# ASIC-flow area estimates (synthesis only, no place-and-route)

Yosys 0.33 with the open NanGate 45 nm library, typical corner. Put the library at
`lib/nangate45_typ.lib` (e.g. `NangateOpenCellLibrary_typical.lib` from OpenROAD-flow-scripts,
`flow/platforms/nangate45/lib/`).

| file | what |
|---|---|
| `synth_p36.ys` | the phase-36 board design (probe + 4x4 mesh), mapped to NanGate45; run from this folder |
| `synth_generic.ys` | the same design to generic gates |
| `idreg.v`, `idreg_area.ys`, `e0/e1/e4.stat` | one identity register with a 0-, 1- and 4-bit epoch |
| `AREA_SUMMARY.txt` | the numbers used in the paper |

The router's tristate crossbar (`crossbar_type 0`) is converted to logic with `tribuf -formal`
before `synth`, as an FPGA flow would; without it Yosys collapses the crossbar to wires.

Results: one router 18,435 um^2; a 4-bit identity register 30.3 um^2; a 1-bit epoch adds
7.45 um^2 (0.040% of a router), a 4-bit epoch 29.8 um^2 (0.16%).

A gate-level simulation of the generic netlist did not reproduce the RTL record stream (the RTL
itself reproduces it in both Icarus and Verilator), so no gate-level equivalence is claimed; only
the area numbers are used.
