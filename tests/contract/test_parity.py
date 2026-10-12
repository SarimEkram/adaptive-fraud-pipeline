"""Online vs offline parity (ADR-0006). The single most important test in the repo.

TODO(phase 4): generate a sequence of events, then
  1. replay offline: in-memory states, compute_features then update_state
  2. replay online: through CardStateStore against a real Redis (to_json / from_json round trip)
  3. assert every feature vector is identical
"""

import pytest


@pytest.mark.xfail(reason="phase 4", strict=False)
def test_online_offline_parity():
    raise NotImplementedError
