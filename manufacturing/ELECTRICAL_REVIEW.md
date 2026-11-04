# Luca electrical review — 2026-11-03 — HOLD

No final manufacturing exports were produced following this review. The earlier
Gerbers are superseded candidates and must not be ordered. Original design files
were preserved. This report reviews the saved files, not unsaved editor state.

## Load calculations

Using the stated 0.9 A rated and 2.7 A stall current per servo:

| Load | Rated-current sum | Stall-current sum |
| --- | ---: | ---: |
| One three-servo leg | 2.7 A | 8.1 A |
| Twelve servos | 10.8 A | 32.4 A |

These are arithmetic design cases, not measured walking/startup waveforms.
The Raspberry Pi adds 25.5 W at the requested 5.1 V/5 A operating point.
At an assumed 90% converter efficiency this is about 2.55 A from 11.1 V,
or 3.15 A from 9 V. Actual minimum operating battery voltage and efficiency
must be specified. Servo plus Pi battery current is about 13.35 A at the first
case, excluding other loads, converter losses beyond the assumption, and peaks.

3 mm wide, 70 um copper has approximately 8.2 milliohms per 100 mm at 20 C,
using bulk copper resistivity 1.724e-8 ohm-m. Such a 100 mm segment carrying
10.8 A dissipates about 0.96 W; at 32.4 A it dissipates about 8.6 W while that
current persists. The return path adds resistance and heating. This is NOT a
temperature-rise/current-rating certification. The current layout's long paths,
1 mm auxiliary branches, terminal ratings, and switch loop need coordination
with measured peaks and protective-device clearing times.

## Findings

1. **Servo adapter current limit.** Waveshare's official FAQ specifies maximum
   withstand current of 5 A for Bus Servo Adapter (A). The complete servo power
   must not traverse that adapter for the stated load envelope. Separate fused
   power injection to the legs is needed while retaining the appropriate signal
   bus and common reference. Shared servo-positive wiring must not reconnect
   independently fused leg branches downstream of their fuses.
   Source: https://docs.waveshare.com/Bus_Servo_Adapter_A/FAQ

2. **Fuse roles and ratings unresolved.** On the actual PCB, F1 is the common
   battery fuse, F2 feeds J2 servo power, F5 feeds J7 auxiliary-buck input, and F7
   feeds J10 Pi-buck input. They are NOT four independent leg fuses. A 5 A F1
   cannot support the 10.8 A aggregate servo rated-current case. Equal 5 A
   upstream/downstream fuses do not establish selective coordination. One leg's
   8.1 A stall is 162% of a 5 A fuse and lies in the manufacturer's cautioned
   prolonged-overload region. Slow-blow does not imply protection of a 5 A
   adapter against these overloads.

3. **Bel fuse package mismatch.** The proposed 0680H5000-05 is 2410 SMD;
   PCB F1/F2 are Keystone mini-blade holders and F5/F7 are 5x20 mm Schurter
   cylindrical holders. None accepts the proposed part. Replacing these with
   SMD fuses requires local footprint and routing changes; SMD pads cannot rely
   on the old through-hole pads to connect both copper layers.

   Bel lists the 5 A version at 125 VDC / 500 A interrupt rating, with an
   additional 72 VDC / 5000 A series rating. Its table specifies up to 120 s
   clearing at 200% rated current; average curves do not prove a worst-case
   clearing time at 162%. The 5 A entry lists nominal melting I-squared-t values
   of 24 A-squared-s at 10In and 26 A-squared-s below 10 ms. These are melting,
   not complete worst-case clearing-energy guarantees. Prospective battery fault
   current and full wire/trace damage coordination remain unverified.
   Source: https://www.belfuse.com/media/datasheets/products/circuit-protection/ds-CP-0680H-series.pdf

4. **Battery C rating does not establish short-circuit current.** 2.2 Ah x 35C
   equals a stated 77 A discharge figure, not a bound on prospective fault
   current. Interrupting capability requires battery/wiring fault data.

5. **Voltage compatibility.** Waveshare specifies 6–12.6 V for the 12 V ST3215,
   so 12.6 V charged battery is at the stated upper limit. Regeneration and
   wiring transients need checking; no extra voltage margin is established.
   Source: https://docs.waveshare.com/ST3215_Servo

6. **XT60 not physically approved.** PCB J1 pad 1 is VBAT_RAW and pad 2 GND,
   with 7.2 mm pitch and 4.5 mm drill holes. The installed KiCad footprint
   description calls XT60-M female, conflicting with the proposed male wording.
   AMASS documentation distinguishes wire and board variants; pitch alone is
   insufficient. Exact ordered connector drawing and actual battery mating
   contacts/polarity must be checked. No polarity change was made.
   Sources: installed Connector_AMASS footprint and
   https://www.china-amass.com/public/upload/20260207/7fa24f5a6f35ec66c7a115c07a34ab06.pdf

7. **Pi buck remains provisional.** Pololu #5571 is fixed 5.0 V, not 5.1 V.
   Its advertised 6 A is specified at 42 V input and achievable continuous
   output depends on input voltage and thermal conditions. Validate full load
   at the battery's actual minimum/maximum voltage, including wiring losses,
   cooling, Pi connector voltage, and USB-C source/cable current advertisement.
   Merely fitting a USB-C plug does not verify the Pi 5 A power arrangement.
   Source: https://www.pololu.com/product/5571/specs

8. **Grounding corrected but not thermally certified.** The fabrication candidate
   adds a 3 mm J2 return. All power-connector ground pads connect after removing
   sub-1 mm tracks from the audit graph. No copper zones exist. This confirms a
   continuous wider route, not temperature rise or transient ground impedance.

## Schematic/PCB disagreement: release blocker

Saved schematic exported to schematic-review.net:
- F1 common battery fuse, Q1 reverse-polarity stage, D1 gate clamp, R1 gate bias.
- SW1 switches protected supply to SERVO_V+.
- F2/F3/F4/F5 feed four leg outputs J2/J3/J4/J5.
- No F7, J7, J10, J11 Pi/aux buck arrangement.

Actual PCB:
- Q1/D1/R1/SW1 absent; J3 is instead a two-wire series switch loop.
- F2 feeds one SERVO output J2.
- F5 feeds J7 AUX_BUCK; F7 feeds J10 PI_BUCK_INTERFACE.
- J5 and J11 connect buck return/output paths; not four protected leg outputs.

Thus a clean PCB DRC does not certify the saved schematic's intended circuit.
User selected the current PCB servo/auxiliary/Pi topology as authoritative.
Keep J3 as the series switch loop and retain the servo, auxiliary-buck and
Pi-buck branches. The saved four-leg schematic is not the authority for these
edits and must be reconciled to the selected PCB circuit before release.
Servo power-injection wiring remains unresolved because the adapter's 5 A
power path cannot carry the stated aggregate load. Do not commit fuse ratings
or final exports until that branch load and wiring arrangement is resolved.
The Pi buck connector must be clearly labeled as BATTERY INPUT TO EXTERNAL BUCK,
not regulated 5 V, and receive its own coordinated branch protection.

## Release gates

- Schematic authority resolved: current PCB servo/auxiliary/Pi arrangement.
- Resolve adapter/power-injection wiring and reconcile the saved schematic.
- Assign fuse roles and validate load profiles, clearing curves, wire gauges,
  trace thermal response, switch DC rating, and terminal-block current ratings.
- Confirm the exact XT60 board part and the buck/USB-C arrangement.
- Then update the existing design locally: fuse footprints, branch connector,
  necessary copper/vias, labels, and schematic correspondence.
- Finally run ERC, schematic parity, DRC and physical fit review before new
  final Gerber/drill exports. Existing candidates are on hold.
