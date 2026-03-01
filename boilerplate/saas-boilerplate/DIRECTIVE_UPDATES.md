# Directive Updates - Auto-Loader Integration

**All 4 directives updated to reflect auto-loader architecture.**

---

## What Changed

### Before (v1.0)
Directives instructed Claude/FO to:
1. Create routes/pages
2. Import them in main.py/App.js
3. Register them manually
4. Configure routing

**Problem:** Manual integration for every file.

### After (v2.0)
Directives now instruct Claude/FO to:
1. Create routes/pages
2. Done

**Benefit:** Zero integration. Files auto-load.

---

## Files Updated

### 1. BUILD_DIRECTIVE.md ✅
**Added:**
- ⚡ CRITICAL section at top
- "Auto-Loader - Zero Integration Required"
- List of what NOT to do
- Verification section showing logs
- Updated examples

**Key Change:**
```markdown
❌ DO NOT edit main.py
❌ DO NOT import routes
❌ DO NOT call app.include_router()

✅ Just drop files in business/backend/routes/
✅ They auto-load
```

### 2. backend_directive.md ✅
**Added:**
- ⚡ CRITICAL section at top
- "No Integration Required" warnings
- Auto-loader explanation

**Removed:**
- Import instructions
- Registration instructions
- Manual configuration steps

**Key Change:**
```python
# Old instruction:
# "Import your route in main.py"

# New instruction:
# "Files auto-load. Don't touch main.py"
```

### 3. frontend_directive.md ✅
**Added:**
- ⚡ CRITICAL section at top
- "No Integration Required" warnings
- Auto-loader explanation

**Removed:**
- Route definition instructions
- App.js edit instructions
- Manual routing steps

**Key Change:**
```jsx
// Old instruction:
// "Add <Route> in App.js"

// New instruction:
// "Files auto-load. Don't touch App.js"
```

### 4. testing_directive.md ✅
**Added:**
- Note about auto-loader architecture
- Explanation that tests don't need imports either

**Updated:**
- Test examples to match auto-loader pattern

---

## Consistency Check

**All directives now say:**

✅ Files auto-load from business/
✅ Do NOT edit main.py or App.js
✅ Do NOT import or register
✅ Just create files and start server

**No conflicting instructions.**

---

## Example: Claude Reads Directives

**Scenario:** AF shell script asks Claude to build InboxTamer schedule feature.

**Claude reads:**
1. BUILD_DIRECTIVE.md → "Auto-loader, no integration"
2. backend_directive.md → "Auto-loader, no integration"
3. frontend_directive.md → "Auto-loader, no integration"

**Claude generates:**
```python
# business/backend/routes/schedule.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/list")
def list_schedules():
    return []
```

**Claude does NOT:**
- Edit main.py
- Import anything
- Register anything

**Result:** File auto-loads on startup. Works immediately.

---

## Directive Flow for AF Scripts

```bash
#!/bin/bash
# af-build.sh

BUSINESS="InboxTamer"
SCHEDULE_JSON="tier2_mvp.json"

# Pass directives to Claude
claude --context directives/BUILD_DIRECTIVE.md \
       --context directives/backend_directive.md \
       --context directives/frontend_directive.md \
       --schedule "$SCHEDULE_JSON" \
       "Build InboxTamer schedule feature in business/"

# Claude reads all 3 directives
# All say: "Auto-loader, no integration"
# Claude generates files in business/
# Does NOT edit boilerplate
# Done
```

---

## Testing Updated Directives

**Give Claude the directives:**
```bash
claude --context directives/BUILD_DIRECTIVE.md \
       --context directives/backend_directive.md \
       "Create email rules API for InboxTamer"
```

**Expected behavior:**
1. ✅ Creates business/backend/routes/email_rules.py
2. ✅ Includes router = APIRouter()
3. ✅ Does NOT edit main.py
4. ✅ Does NOT import anything

**Wrong behavior (if directives not updated):**
1. ❌ Creates route file
2. ❌ Edits main.py to import
3. ❌ Adds app.include_router() call
4. ❌ Breaks auto-loader

---

## Version History

**v1.0 (Original):**
- Manual integration
- Import/register every file
- Edit main.py/App.js per business

**v2.0 (Auto-Loader):**
- Zero integration
- Drop files, they work
- Never touch main.py/App.js

**Directives Updated:** v2.0 - Feb 11, 2025

---

## Summary

**All 4 directives now consistently instruct:**

1. Create files in business/
2. Don't integrate
3. Done

**No conflicting instructions. Claude will not try to edit main.py or App.js.**

**Ready for AF automation. 🚀**
