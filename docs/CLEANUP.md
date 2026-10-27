# Repository cleanup — 2026-10-26

Preserved four useful policies with normalization, evaluations, checksums and
frozen source archives under policies. Saved the user-confirmed rear-left
calibration and representative tracking evidence, alongside original captures.
Kept original CAD and the separate frame V3 revision.

Removed the byte-identical root testing.py duplicate; retained its luca_bus.py
counterpart under hardware/experimental with its historical scope documented.
Moved the root Newton parity result into reports/newton.

Removed obsolete one-off physical test_hip_pitch*, test_joint_nudge,
test_neutral_offset and forced_return_id2 scripts. Current calibrated replay,
ID assignment, telemetry, manual capture and relevant simulation validation
tools remain. Prior tracked versions remain available in Git history.

Deleted derived local transfer staging folders and old robot-dog-*.zip upload
packages under runs after preserving useful policy/source inputs. These are
generated copies, not active replay plans or raw training runs. Environments,
credentials, caches and full runs stay excluded from Git. A local pre-cleanup
source ZIP and removal manifest are retained under ignored runs/maintenance.

Historical RL experiment notes moved to docs/archive; current READMEs/status
describe CUDA training and supported rear-left transfer rather than the earlier
pipeline smoke state. Raw historical encoder observations were not rewritten
as new measurements.
