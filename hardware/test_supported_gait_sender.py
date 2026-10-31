import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supported_gait_sender import exchange, neutral_steps


class FakePort:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.writes = []

    def write(self, value): self.writes.append(value)
    def flush(self): pass
    def readline(self): return next(self.responses, b'')


def test_exchange_ignores_telemetry_before_ack():
    port = FakePort([b'LIVE,1,2100,2101,120,31\n', b'OK,GOAL,1,2101\n'])
    exchange(port, 'GOAL,1,2101', 'OK,GOAL,1,2101', .1)
    assert port.writes == [b'GOAL,1,2101\n']


def test_neutral_interpolation_limits_step():
    previous = {1: 100, 2: 250}
    target = {1: 300, 2: 100}
    for row in neutral_steps(previous, target):
        assert all(abs(row[sid] - previous[sid]) <= 4 for sid in row)
        previous = row
    assert previous == target
