## 2025-05-10 - [XSS Fix in PersonalAI.tsx]
**Vulnerability:** XSS vulnerability found in `spark src/pages/PersonalAI.tsx` due to the use of `dangerouslySetInnerHTML` on unescaped content (`m.text`).
**Learning:** `dangerouslySetInnerHTML` was used to render raw HTML from an API without sanitization. In React applications, any variable input used with `dangerouslySetInnerHTML` must be sanitized to prevent malicious script injection.
**Prevention:** Use a library like `DOMPurify` to sanitize HTML output before setting it in `dangerouslySetInnerHTML`.
