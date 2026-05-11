# security/action_guard.py
def guard_action(tool_name, **kwargs):
    return True, f"Action {tool_name} allowed by dummy guard.", None

def guard_tool_function(name, func, **kwargs):
    return func
