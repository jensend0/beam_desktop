# Beam Designer

## Application
- Build a Python desktop application using Tkinter and ttk widgets.
- The app runs in a resizable desktop window; it is not a browser app.

## Purpose
A beam design tool for engineers and students. The user sets up a beam,
places loads on it, and picks a steel or lumber section. The app shows the
shear, moment, and deflection diagrams and checks whether the beam is
strong and stiff enough, updating instantly as anything changes.

## Users
A civil engineering student checking a homework beam, or an engineer
sizing a floor beam or deck joist.

## Inputs
- Design name: optional text field, default "Untitled beam". Used to label
  designs saved by the desktop app.
- Support type: dropdown with Simply supported (default) or Cantilever
  (fixed at the left end).
- Span: 4 to 40 ft, default 20 ft, set with a slider and number box that
  stay in sync.
- Loads, listed in a panel where each can be edited or removed:
  - Point loads: magnitude (kips, downward positive) and position (ft).
    A new point load starts at midspan (at the free end of a cantilever).
    Default magnitude is 1 kip; allow 0 to 100 kips. Position range is
    0 to span ft in 0.25-ft increments. Use a number input and permit
    dragging on the beam, snapping to 0.25 ft.
  - Uniform loads: magnitude (kips/ft) and start and end positions (ft).
    Default magnitude is 1 kip/ft; allow 0 to 10 kip/ft. A new uniform
    load starts at 0 ft and ends at span, with positions ranging from 0 to
    span ft in 0.25-ft increments. Require start <= end.
  - "Add point load" and "Add uniform load" buttons.
  - An explicit remove control for every point and uniform load.
  - Point loads can also be dragged along the beam in the drawing,
    snapping to 0.25 ft.
  - Loads that extend past the end of the beam are cut off at the end.
  - Clamp load positions to the beam endpoints, reject negative magnitudes,
    and show inline validation.
- Material and section, as separate dropdown controls from these tables:
  Steel is the default material and W12x26 is the default section.
  Selecting Douglas Fir-Larch should default to 2x8; switching back to
  Steel should default to W12x26.

  Steel W-shapes (E = 29,000 ksi, allowable bending stress Fb = 30 ksi):

  | Section | Ix (in^4) | Sx (in^3) | Weight (lb/ft) |
  |---------|-----------|-----------|----------------|
  | W8x10   | 30.8      | 7.81      | 10 |
  | W10x12  | 53.8      | 10.9      | 12 |
  | W12x26  | 204       | 33.4      | 26 |
  | W14x22  | 199       | 29.0      | 22 |
  | W16x26  | 301       | 38.4      | 26 |
  | W18x35  | 510       | 57.6      | 35 |
  | W21x44  | 843       | 81.6      | 44 |
  | W24x55  | 1350      | 114       | 55 |

  Douglas Fir-Larch No. 2 lumber (E = 1,600 ksi, Fb = 0.900 ksi):

  | Section | Ix (in^4) | Sx (in^3) |
  |---------|-----------|-----------|
  | 2x8     | 47.63     | 13.14     |
  | 2x10    | 98.93     | 21.39     |
  | 2x12    | 177.98    | 31.64     |

- Deflection limit: radio or dropdown with L/240 and L/360; default L/360.
- Waste factor: slider from 0% to 15%, default 15%. Display the selected
  percentage beside the slider; no waste-factor calculation is currently
  included in beam design checks.
- Self-weight is ignored.

## Calculations
- Sign conventions: x is measured in feet from the left end; downward
  loads are positive, shear is positive upward on the left face, moment is
  positive sagging (tension at the bottom), and deflection y is positive
  downward.
- Reactions from statics. For a simply supported beam, sum vertical forces
  and moments and solve for R_left and R_right. R_left is
  (sum P_i(L - a_i) + sum integral w_i(L - x) dx)/L, with each point load
  P_i at a_i and each uniform load integrated only over the portion on the
  beam. R_right is total downward load minus R_left. For a cantilever,
  the left vertical reaction is the total downward load upward and the left
  fixed-end moment reaction is the sum P_i a_i plus integral w_i x dx,
  with direction counteracting the downward-load moment.
- Shear V(x) and moment M(x) along the beam, at 1 ft spacing or finer,
  plus exactly at every load point and load start/end.
  Maximum shear is the absolute maximum |V(x)|. The shear and moment
  diagrams may also report their signed minimum and maximum values.
  Calculate values exactly at load discontinuities and boundaries, not
  only from 1-ft samples.
- Deflection y(x) by integrating M/EI twice with the boundary conditions
  for the support type (y = 0 at both supports; or y = 0 and slope = 0 at
  the fixed end).
  E is the material modulus from the selected table, I is Ix for the
  selected section, EI is in ksi-in^4, slope is dy/dx, and y is in inches.
  Use consistent unit conversions while integrating M/EI so the result is
  returned in inches.
- Bending stress fb = |M max| x 12 / Sx (ksi). Bending check passes if
  fb <= Fb.
  M max is the absolute maximum moment, Sx is section modulus from the
  selected table, and Fb is 30 ksi for steel or 0.900 ksi for lumber.
  Convert M from kip-ft to kip-in by multiplying by 12, then divide by Sx
  in in^3 to obtain ksi.
- Deflection check passes if |y max| <= L/240 or L/360 (L in inches).
  y max is max |y(x)| and L is span ft x 12, in inches. The deflection
  card ratio is |y max| divided by the allowable deflection.
- Lightest passing section: of the sections in the chosen material, the
  lightest steel section that passes both checks (if two weigh the same,
  the one with the larger Ix), or the first lumber size in the table
  that passes.
  Use Ix and Sx from the selected material table. Include fb/Fb and
  |y max|/allowable deflection as the bending and deflection card ratios.
  If no section passes, display "No passing section" and offer no use-section
  action.
- Units: kips, ft, and kip-ft on screen; inches for deflection.
  Moment is in kip-ft for display, in kip-in for bending stress, span is
  in inches for deflection limits, and EI is in ksi-in^4 for deflection.

## Outputs
- File menu: provide **Save** and **Open** commands. Save writes the current
  beam configuration to a user-selected JSON file; Open restores it from a
  selected file. Include support type, span, material and section,
  deflection limit, and point and uniform loads.
- Export/import design: JSON file actions may also include design name and
  waste factor.
- Design status: briefly confirm successful save, copy, load, or restore
  actions and report an invalid shared URL.
- Calculation report: a report action exports a printable report or opens
  the operating system print flow. The report includes the design
  name, all entered inputs, reactions, maximum shear and moment, maximum
  deflection, bending stress, allowable stress, deflection limit, pass/fail
  statuses, and the current section recommendation.
- A beam drawing with the supports, load arrows (point loads as single
  arrows, uniform loads as a row of small arrows), and the reactions.
- Three diagrams stacked under the beam and lined up with it on the same
  x scale: shear (kips), moment (kip-ft), and deflected shape (in). Each
  diagram is filled and shows its maximum value labeled at its location.
- Moving the mouse over any diagram shows a vertical line across all three
  with the values of V, M, and y at that x.
- Two check cards: Bending and Deflection. Each shows the actual value, the
  allowable value, a bar for the ratio (green under 70%, amber 70-100%,
  red over 100%), and PASS or FAIL.
- A line suggesting the lightest passing section, with a button to use it.
- Everything updates immediately whenever any input changes.

## Look and feel
- Opens with an example already loaded (20 ft simply supported W12x26
  with a 1 kip/ft uniform load over the full span), so it is useful the
  moment it opens.
- Clean and professional desktop interface: light
  background, white cards with soft shadows, one accent color, a modern
  system font, generous spacing. No clutter.
- Inputs in a panel on the left; drawing, diagrams, and checks on the
  right. The layout remains usable when the desktop window is resized.
- Every input has a short label with units. Hovering over a check card
  explains the formula used.

## Validation
1. Simply supported, 20 ft, W12x26, uniform 1 kip/ft over the full span:
   reactions 10 k and 10 k; max shear 10 k; max moment 50.0 kip-ft at
   10 ft; fb = 17.96 ksi; max deflection 0.609 in at 10 ft; L/360 =
   0.667 in; both checks pass.
2. Simply supported, 20 ft, W12x26, point load 10 k at 5 ft: reactions
   7.5 k (left) and 2.5 k (right); max moment 37.5 kip-ft at 5 ft;
   fb = 13.47 ksi; max deflection 0.340 in at 8.82 ft.
3. Cantilever, 10 ft, W12x26, point load 5 k at the free end: reaction
   5 k and fixed-end moment 50 kip-ft; max deflection 0.487 in at the free
   end (PL^3/3EI); L/360 = 0.333 in, so deflection fails.
4. Simply supported 12 ft 2x10 joist, uniform 0.05 kip/ft: max moment
   0.90 kip-ft; fb = 0.505 ksi; max deflection 0.147 in; both pass.

## Out of scope
- Self-weight, shear stress, lateral-torsional buckling, load
  combinations, and continuous beams.

## Resolved notes
- Support type defaults to Simply supported and uses a dropdown.
- Span defaults to 20 ft and uses a synced slider and number box.
- Point loads default to 1 kip, range from 0 to 100 kips, and use 0.25-ft
  positions from 0 to span; they can be entered in a number field or dragged
  on the beam.
- Uniform loads default to 1 kip/ft, range from 0 to 10 kip/ft, and default
  to a full-span distribution from 0 ft to span.
- Load positions clamp to beam endpoints, negative magnitudes show inline
  validation and are rejected, and uniform-load start must not exceed end.
- Each load has an explicit remove control.
- Material and section use separate dropdowns; the default is Steel W12x26,
  switching to Douglas Fir-Larch defaults to 2x8, and switching back to Steel
  defaults to W12x26.
- Deflection limit defaults to L/360 and uses a radio or dropdown control.
- Reset-to-example is not required for the v1 scope.
- Reactions, shear, moment, and deflection use one documented sign convention
  and consistent units, with load discontinuities evaluated exactly.
- Check-card ratios are fb/Fb and |y max|/allowable deflection.
- If no section passes, the app displays "No passing section" and offers no
  use-section action.

## Build stages

### 1. Build the desktop window layout
Create the left input panel and right results area with placeholder beam,
diagrams, cards, and section recommendation. Preload the example values
visually.

Test: The desktop window layout matches the spec and the example values
appear without any calculations running.

### 2. Add working inputs and load management
Implement support, span, loads, material/section, and deflection-limit
controls. Include validation, removing loads, adding loads, and point-load
dragging.

Test: Span slider and number box stay synchronized; load values remain within
range; dragging snaps to 0.25 ft; invalid values show inline errors; and
switching materials selects the correct default section.

### 3. Implement reactions, shear, and moment
Add statics calculations and calculate shear and moment at exact load
boundaries. Render the beam and shear/moment diagrams from real values.

Test: Use the four validation cases, especially the 20-ft uniform load and
10-kip point load. Confirm reaction values, maximum shear, and maximum
moment locations.

### 4. Add deflection and diagram interactions
Integrate moment twice for each support type and calculate deflection in
inches. Add the deflected-shape diagram and synchronized hover cursor across
all diagrams.

Test: The full-span uniform-load deflection is about 0.609 in, the cantilever
gives 0.487 in for the prescribed example, and hovering returns values on
the same beam position for every diagram.

### 5. Add checks and section recommendation
Calculate bending stress, deflection ratios, PASS/FAIL states, check-card
colors, and the lightest passing section. Add the button that applies the
recommendation.

Test: The example cases pass or fail as listed; ratios and card colors update
immediately; lumber and steel recommendations follow the specified rules;
and a case with no passing section shows "No passing section" without a use
button.

### 6. Polish and verify the complete app
Finish window resizing behavior, formula explanations, maximum-value labels,
accessibility, and any remaining visual details.

Test: Test every validation case again, resize the desktop window, use
keyboard controls, and confirm that every input change updates the whole
results area immediately.
