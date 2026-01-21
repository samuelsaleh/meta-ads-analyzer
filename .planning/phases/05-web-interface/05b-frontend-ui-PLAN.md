# Plan: Phase 5b - Frontend UI

## Objective
Create the frontend user interface for the Meta Ads Analyzer web application, enabling browser-based brand analysis.

## Execution Context
- FastAPI backend already running (app.py)
- Routes available: GET /, POST /analyze, GET /health, GET /reports
- Report template exists (templates/report.html)

## Context
**Dependencies:**
- Phase 5a (FastAPI Backend) ✅ Complete
- Jinja2 templates
- Static file serving configured in app.py

**Files to Create:**
1. `templates/index.html` - Landing page with analysis form
2. `templates/error.html` - Error display page
3. `static/style.css` - CSS styling

## Tasks

### Task 1: Create Landing Page (templates/index.html)
**File:** `templates/index.html`

**Requirements:**
- Form with POST action to `/analyze`
- Input field: `brand` (required, text)
- Select field: `country` (optional, values: ALL, FR, US, GB, DE)
- Input field: `max_ads` (optional, number, default 10)
- Submit button with loading state
- Feature cards explaining the tool
- Responsive design

**Template Variables:**
- `request` (required for Jinja2Templates)

### Task 2: Create Error Page (templates/error.html)
**File:** `templates/error.html`

**Requirements:**
- Display error message passed from backend
- Link back to home page
- Consistent styling with landing page

**Template Variables:**
- `request`
- `error` (error message string)

### Task 3: Create CSS Styles (static/style.css)
**File:** `static/style.css`

**Requirements:**
- CSS variables for theming
- Landing page layout (centered, gradient background)
- Form styling (inputs, select, button)
- Loading spinner animation
- Feature cards grid
- Error page styling
- Responsive breakpoints
- Print-friendly styles

### Task 4: Update app.py for Template Rendering
**File:** `app.py`

**Changes:**
- Update GET `/` to render `index.html` template
- Add error handling route that renders `error.html`
- Ensure static files are served correctly

### Task 5: Test Full User Flow
**Steps:**
1. Start server: `uvicorn app:app --host 0.0.0.0 --port 8002`
2. Open browser: `http://localhost:8002`
3. Verify landing page renders
4. Submit form with brand name
5. Verify report is generated and displayed
6. Test error handling with invalid input

## Verification

### Checklist
- [ ] Landing page renders at http://localhost:8002
- [ ] Form accepts brand name input
- [ ] Country dropdown works
- [ ] Max ads input works
- [ ] Submit button shows loading state
- [ ] Form submission triggers analysis
- [ ] Report is displayed after analysis
- [ ] Error page displays on failure
- [ ] CSS styles load correctly
- [ ] Responsive design works on mobile

### Test Commands
```bash
# Start server
uvicorn app:app --host 0.0.0.0 --port 8002

# Test landing page
curl -s http://localhost:8002/ | grep "Meta Ads Analyzer"

# Test form submission (downloads report)
curl -X POST http://localhost:8002/analyze -F "brand=Nike" -F "max_ads=2"
```

## Success Criteria
1. User can access landing page in browser
2. User can submit brand for analysis via form
3. Analysis results display as HTML report
4. Errors display user-friendly messages
5. UI is styled and responsive

## Output
- `templates/index.html` - Landing page
- `templates/error.html` - Error page
- `static/style.css` - Styles
- Updated `app.py` - Template rendering

## Estimated Time
30-45 minutes

## Next Phase
Phase 6: Testing - End-to-end testing and error handling verification
