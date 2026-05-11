# security/policy_engine.py
class DummyEngine:
    def describe(self):
        return "Permissive Dummy Policy Engine"

def get_policy_engine():
    return DummyEngine()
