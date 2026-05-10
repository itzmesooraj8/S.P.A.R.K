## 2024-05-10 - Login Password Toggle Accessibility
**Learning:** The password visibility toggle on the Login page (using Eye/EyeOff icons) lacked an accessible `aria-label`, meaning screen readers had no context for the button's action.
**Action:** Always add dynamic `aria-label` attributes to icon-only toggle buttons (e.g., `aria-label={state ? "Hide" : "Show"}`) to ensure keyboard and screen reader accessibility.
