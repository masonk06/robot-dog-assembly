# Luca four-leg engineering revision — NOT FOR FABRICATION

This revision is derived from the existing PCB and reconciles the saved schematic
to the user-selected servo/auxiliary/Pi topology. The user-approved outline is
88.5 x 60 mm (right edge extended 20 mm). The existing four mounting-hole
positions, J1 battery input, J3 switch loop, J5/J7 auxiliary
interfaces, and J10/J11 Pi interfaces are retained. Original design files remain
unchanged. This is a reviewable engineering revision, not a manufacturing release.

## Circuit and pin assignments

| Part | Role | Positive side | Return |
| --- | --- | --- | --- |
| J1 | Existing XT60 battery input | pad 1 VBAT_RAW | pad 2 GND |
| F1 | Existing common battery fuse holder | VBAT_RAW to VBAT_FUSED | rating TBD; NOT 5 A |
| J3 | Series battery switch loop | pad 1 VBAT_FUSED, pad 2 SERVO_V+ | neither pad is GND |
| F2 / J2 | Adapter supply branch | SERVO_V+ to fused SERVO, J2 pad 1 | J2 pad 2 GND |
| F5 / J7 | Existing external auxiliary buck input | J7 pad 1, fused switched battery | J7 pad 2 GND |
| F7 / J10 | Existing external Pi buck input | J10 pad 1, fused battery before J3 | J10 pad 2 GND |
| F8 / J12 | FL leg, three servos | J12 pad 1 FL_V+ | J12 pad 2 GND |
| F9 / J13 | FR leg, three servos | J13 pad 1 FR_V+ | J13 pad 2 GND |
| F10 / J14 | RL leg, three servos | J14 pad 1 RL_V+ | J14 pad 2 GND |
| F11 / J15 | RR leg, three servos | J15 pad 1 RR_V+ | J15 pad 2 GND |

J7 pad 3 is the auxiliary regulator output returning to J5 pad 1; J7 pad 4 is
GND. J10 pad 3 is the Pi regulator output returning to J11 pad 1; J10 pad 4 is
GND. These four-pin interfaces contain both BATTERY INPUT and REGULATED OUTPUT;
they must not be confused or shorted. The Pi branch remains live when J3 opens,
matching the existing PCB circuit. Auxiliary input is switched by J3.

All four leg fuses are supplied by SERVO_V+, upstream of F2. F2 does not carry
the four legs' combined current. F1, J3, and their main copper do carry aggregate
servo current; Pi current also passes F1 but bypasses J3.

## Parts and physical changes

- F8–F11: Bel 0680H5000-05, 5 A slow-blow, **provisional**. They use the bundled
  local `Luca_Review:Bel_0680H_2410_Engineering` land pattern. This enlarged
  hand-solder pattern is a review candidate, not a verified manufacturer land
  pattern. Verify exact terminal coverage and solder/rework access before release.
- F2/F5/F7: converted from bulky holders to the same SMD package, provisional
  5 A values. F5 and F7 are on B.Cu beneath the auxiliary/Pi connector region;
  verify bottom-side chassis clearance, pin-tip clearance and rework access.
- F1: existing mini-blade holder retained for the larger main-fuse requirement.
  Main-fuse part, holder rating and selective coordination are NOT approved.
- J12–J15: AMASS XT30UPB-M vertical PCB connectors, with 5 mm pad pitch and the
  installed KiCad manufacturer-linked footprint. Published legacy nominal rating
  is 15 A; newer manufacturer catalog lists 20 A under its stated test conditions.
  Use the conservative 15 A figure pending exact purchased-part verification.
  This exceeds 8.1 A arithmetic leg stall, but mating contacts, solder joints,
  wire gauge, ambient temperature and duty cycle still require verification.
- Existing component positions retained except F2/F5/F7 holder replacement.
  The four new leg connectors/fuses occupy the added right-hand area. Verify
  the extra 20 mm fits the chassis and has enough mechanical support for mating
  forces; no existing mounting hole was moved.
  All copper is rerouted in this derived revision because the added branches
  and surface-mount fuse layer restrictions require it.

## Wiring: no alternate positive supply paths

1. Battery positive/negative enter J1; fit the correctly coordinated main fuse.
2. Connect the DC-rated external switch only between J3 pads 1 and 2.
3. Power the adapter through J2, with its ground tied to the PCB common ground.
4. Run each leg connector's own positive and ground pair to that leg. Do not
   route its current through the adapter, another leg, or thin signal wiring.
5. The serial DATA conductor can remain a single daisy chain through all servo
   IDs. Each three-servo leg may keep its internal local power distribution.
6. Between adapter and leg, and between different legs, omit/isolate the V+
   conductor. No factory three-wire cable may bridge independently fused rails.
7. All leg references share ground through their dedicated PCB power returns.
   Additional thin inter-leg ground wires can become unintended parallel servo
   returns; omit those extra links where the star power ground provides the
   reference, or explicitly engineer and fault-rate them. Adapter ground remains
   connected to the common PCB ground. Verify signal integrity on the actual
   harness, including connector orientation and ground continuity.
8. With the battery removed, unplug the leg loads and remove F8–F11. Confirm
   each leg-positive connector is isolated from SERVO_V+, the adapter positive,
   the other three leg positives, and ground. Reconnect one leg harness at a time
   and repeat to detect a hidden V+ bridge. Electronics/capacitors can affect
   continuity readings; identify every unexpected path rather than relying on
   a single beep. Then test initially with a current-limited bench supply.
9. Verify the first servo cable/connector in each leg can carry aggregate current.
   A high-rated PCB connector does not upgrade the stock servo harness. Separate
   local injection to individual servos may be needed while keeping DATA chained.
10. With one leg fuse removed, test DATA-driven backfeed into that unpowered leg.
    Cutting the V+ wire prevents the direct power bypass, but unknown servo input
    clamp circuitry can still leak current from DATA. Check the unpowered rail
    voltage/current and I/O limits; branch data isolation/gating may be needed.
    This behavior is not established by the available servo specifications.

## Electrical review / release gates

One leg: 2.7 A rated-current sum, 8.1 A simultaneous stall-current sum. Four legs:
10.8 A rated sum, 32.4 A stall sum. Actual gait/startup waveforms are not measured.

**5 A slow-blow is not approved.** 8.1 A is 162% of 5 A, in the manufacturer's
cautioned 100–200% sustained-overload range. Bel's maximum 120 s at 200% and
average curves do not establish safe clearing at 162%. Verify the branch harness,
trace temperature, allowable fault duration, ambient derating and worst-case
clearing behavior. An electronic stall timeout/current limit may be required;
none is implemented on this PCB. Do not up-rate the fuse to hide nuisance trips.

The 2 oz / 3 mm main conductors remain a provisional routing choice. Bulk-copper
resistance is about 8.2 milliohm per 100 mm per conductor at 20 C: roughly 0.96 W
at 10.8 A or 8.6 W at 32.4 A for that segment alone. Return copper, pad constrictions,
vias, switch and connector contacts add losses. Neither DRC nor a connected 3 mm
path certifies temperature rise, short-circuit energy withstand, or main-fuse
coordination. Check these at representative operation and sustained-stall cutoff.
Local 2.6 mm pad escapes may be used for up to approximately 3 mm from a pad to
join 3 mm routes. Layer transitions use plated vias and parallel copper spokes;
their plating thickness, sharing and fault-energy capacity remain thermal-review
items. Do not interpret geometric connection as an approved current rating.

Other pending checks: exact XT60 mating polarity/part geometry; exact terminal
block parts/current ratings; J3 switch and wire DC interruption rating; capacitor
voltage/transient margin; USB-C source/cable behavior; Pololu 5.0 V output under
minimum battery voltage/full load/cooling; chassis and harness physical fit.

No final Gerbers or drill files are exported for this revision while these gates
remain open. The earlier manufacturing candidate remains marked DO_NOT_ORDER.

## Primary references

- Servo: https://docs.waveshare.com/ST3215_Servo
- Adapter's 5 A maximum: https://docs.waveshare.com/Bus_Servo_Adapter_A/FAQ
- Fuse: https://www.belfuse.com/media/datasheets/products/circuit-protection/ds-CP-0680H-series.pdf
- Connector: https://www.china-amass.net/xt30upb-m-product/
- Pi buck: https://www.pololu.com/product/5571/specs
- Pi power: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
