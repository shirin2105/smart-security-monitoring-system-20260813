import unittest

from app.cv.phase7c_tracking.owner_association import (
    OwnerAssociation,
    OwnerAssociator,
)
from app.cv.phase7c_tracking.phase7c_types import OwnerAssociationState


class NearestOwnerStub:
    def associate(self, luggage_trajectory, person_trajectories):
        return OwnerAssociation(
            luggage_track_id=2_000_001,
            person_track_id=None,
            association_score=None,
            last_near_timestamp=None,
        )


class OwnerAssociationContractTests(unittest.TestCase):
    def test_protocol_and_unresolved_state(self):
        associator = NearestOwnerStub()
        self.assertIsInstance(associator, OwnerAssociator)
        result = associator.associate([], [])
        state = OwnerAssociationState(**result.__dict__)
        self.assertEqual(state.luggage_track_id, 2_000_001)
        self.assertIsNone(state.person_track_id)
        self.assertIsNone(state.association_score)
        self.assertIsNone(state.last_near_timestamp)


if __name__ == "__main__":
    unittest.main()
