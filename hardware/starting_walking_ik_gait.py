"""Starting Walking IK Gait: 30 mm stroke, 15 mm lift, 4 seconds, 144 Hz.

Generate one offline model-angle cycle. This entry point never commands motors.
"""
import sys

from generate_pi_crawl import main


if __name__ == "__main__":
    # Keep the accepted baseline fixed; only output location/cycle count may vary.
    sys.argv.extend(["--cycle-seconds", "4", "--stroke-mm", "30", "--lift-mm", "15"])
    main()
