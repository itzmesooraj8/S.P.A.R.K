## 2024-05-10 - TaskPanel.tsx render loop calculation

**Learning:** Component `TaskPanel` recalculates `groupedTasks` via an expensive `statuses.reduce` on every render, including typing into the `newTaskTitle` input field.
**Action:** Always verify if expensive loop calculation can be cached using `useMemo` in React components.
