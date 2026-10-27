# Historical SDK experiment

luca_bus.py is the user's preserved scservo_sdk raw-tick/jog experiment.
Its byte-identical testing.py duplicate was removed. It retains historical
neutral values and requires the optional scservo_sdk package; it is not the
current calibrated controller. Do not treat its raw offsets as current
rear-left calibration or a model-angle mapping. Use calibration_view.py and
supported_replay_view.py for the current workflow. Tests do not execute it.
