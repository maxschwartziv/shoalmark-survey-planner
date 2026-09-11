# Survey Planner

Plan side scan sonar surveys of inland water. Fetches a lake outline from the
USGS National Hydrography Dataset, lets you mark where a boat can actually get
in, and turns it into straight survey lines split into workable outings —
exportable to GPX or QGroundControl.

## Running It

Download the folder from
[Releases](https://github.com/maxschwartziv/shoalmark-survey-planner/releases),
unzip it anywhere, and run `SurveyPlanner.exe`. No Python, no install.

From source instead:

```
pip install -r requirements.txt
python survey_planner.py
```

`run.bat` does the same and installs what is missing on the first run.
`selftest.bat` runs the whole engine against a real lake without opening a
window, which is the quickest way to tell whether an install works.

## Using it

**1. Water.** Paste a Google Maps pin and press *Find nearest lake or river*,
or open a polygon you already have — `.json` saved by this program, `.geojson`,
or `.shp` (which needs `pip install pyshp`).
Most shapes work — the URL bar, a *share* link, right-click *what's here*,
`lat, lon` typed by hand, even degrees-minutes-seconds. Shortened `goo.gl`
links carry no coordinate until they are opened, so those are refused with an
explanation rather than a shrug.

**When several waterbodies are found**, they are all drawn and you click the
one you want — anywhere inside it, or nearest it if it is small. Each outline
is one shape the NHD publishes, labelled with its name, area and distance from
your pin; the one your pin landed inside says so. Ponds under five acres are
drawn unlabelled but stay clickable. A left click picks; if none of them is the
water you meant, edit the pin and search again.

Both NHD polygon layers are searched — **12 for lakes and ponds, 9 for rivers
wide enough to be mapped as areas** — and results come back nearest first. If
the pin lands inside one body that one is used; otherwise you choose, with the
distance shown. The outline is saved alongside your export so a plan can be
reopened with no network.

**Getting around the map.** Wheel zooms about the cursor — about the cursor,
not the centre, so you are not chasing the thing you are looking at back into
view. Middle-drag pans; left-click is left alone because that is how access
points and regions get placed. *Reset view* returns to the whole waterbody, and
loading a new one resets it too. The matplotlib toolbar's own pan and zoom
still work.

**Imagery sharpens as you zoom in.** The first fetch covers the whole
waterbody, and the tile budget forces the zoom down to suit it — so on a long
reservoir the overview is necessarily coarse and zooming in only magnifies
those pixels. Once a smaller patch is on screen the same budget buys a much
finer zoom, so it is fetched again: Indian Lake starts at tile zoom 16 and
reaches 19 zoomed in. The refetch waits for the view to settle, since a spin of
the wheel is a dozen view changes in a second and each would otherwise queue
its own fetch of several hundred tiles. Panning off the fetched patch refetches
at the same detail rather than running into blank background. Zooming back out
keeps the finer tiles; *Reset view* reloads the overview.

**Map detail follows the extent.** A lake two miles across gets every service
road; a forty-mile river gets highways only. Asking for every class over that
river returned thousands of named lanes — a slow query and a map buried under
its own labels. Names are rationed further at draw time: the twenty longest
roads are labelled, biggest class first, and the rest drawn unnamed. Satellite
tiles already scale the same way, dropping zoom to stay inside a tile budget.

**2. Shore access** Tick *Click the map to mark access* and click where you
can put a boat in. **The mark snaps onto the shoreline** — a click is never
exactly on the line, and a point a few feet inland reads as dry ground while
one a few feet out reads as a boat already afloat.

Mark them yourself. **Nothing in a shoreline polygon knows whether you can
stand somewhere**: it may be private land, brush, a steep bank or a fence. If
you compute a plan with no access points marked, the planner falls back to
positions derived from visibility so it has somewhere to work from, and says
so — but those are geometry, not places anyone has been.

**Access points are remembered against the water they belong to.** They are
saved to `%LOCALAPPDATA%\SurveyPlannerccess` under a key built from the
waterbody's name and the centre of its outline, so fetching the same lake next
season brings back the ramps you already found — including the ones that turned
out to be somebody's garden. That is slow work done once; it should not have to
be repeated because the line spacing changed.

*Save shoreline…* also writes them into the file itself, and opening such a
file adopts them back into the store.

**3. Region of interest.** Tick *Click to draw a region*, click the corners,
right-click to close. Lines are then built only inside it. The setback still
applies — a region drawn across the bank does not license running aground.
*Clear region* goes back to the whole lake.

**4. No-go areas.** Places the boat must not go. Tick *Click to draw a no-go
area*, click the corners, right-click to close. *Find in imagery* fills the list from
satellite imagery — see below.

No-go areas are cut out of the water before anything is planned, so no survey
line and no transit enters one. **Min distance from no-go** is a margin of
their own, separate from the shore setback because the reasons differ: the bank
is about depth, a dock is about the things around it you cannot see — mooring
lines, cables, a swim ladder, a boat on the far side of it. It defaults to
25 ft.

*Save no-go areas…* writes them two places at once: a store beside the program
keyed to the waterbody, so fetching the same lake next season brings them back
unasked, and a file you choose, so you can hand them to somebody else. Stored
as lon/lat rings, so a file survives a different local frame. *Load…* reads one
back.

**Re-compute outline from imagery** (in *1. Water*) traces the shoreline off
satellite imagery instead of trusting the drawn one, and *Find in imagery* (in
*4. No-go areas*) lists what that trace cut out. Both run the same pass: Otsu
threshold on brightness, take the connected dark region that is the lake, read
its outline off the pixels. Open water is dark and almost everything else —
docks, piers, moored boats, sand, grass, trees — is not.

The NHD polygon is still used for two things it is good at: choosing which dark
region is the lake, and bounding how far the answer may move (80 ft by default,
so a shadowed wood costs you a few feet but cannot annex a field).

On Indian Lake this finds 199 docks, 45 piers and 21 other objects — about 6
acres — plus three pieces of a different kind: **5.7 acres where the NHD
outline claims water and the imagery shows dry land**, including a cove with
houses in it and the dam. Those are labelled *shoreline correction* and kept
out of the no-go list, because the fix for them is a better outline, not a
no-go area the size of a cove.

The whole pass takes about 6 seconds on a 306-acre lake at 1.5 ft/pixel
(25.6 megapixels). The dialog reports each stage by name with a percentage,
elapsed time and an estimate — imagery fetch, threshold, speckle, lake, trace,
compare — and is cancellable throughout.

**Both failure modes are silent.** Sun glint and whitecaps are bright, so they
read as structures. Shadow on land is dark, so it reads as water — a dock in
shadow leaves nothing to see, and on Indian Lake several dark-roofed
boathouses are missed a few feet from pale ones that are found. And Esri
publishes no capture date in the tile, so nothing here can tell you whether
you are looking at last spring or 2015. Check the list.

**5. Parameters.**

| setting | what it does |
|---|---|
| Line spacing | Distance between survey lines. |
| Min distance from shore | Hard limit; lines are built 6 ft inside it so the rule survives GPS error. |
| Boat speed | Used only to turn distance into hours. |
| Max / min hours per day | Outings are cut to fit. Only the last may be short — see below. |
| Bearing | Blank uses the lake's long axis — fewest turns, longest runs. |
| Square blocks | Cut the water into squares about one day in size and work the nearest to the launch first, rather than running transects the length of the lake. |
| Only water in sight | Pair each block with the nearest marked position that can actually see it, and leave out water nobody can watch. |
| Sight range | 0 means land is the only thing that blocks the view. Set a number to cap it — a small boat at a third of a mile is a dot, whatever the geometry says. |
| Cover this % of the water | Survey less than all of it. The blocks dropped are the ones furthest from a launch, where the trip out costs more than the ground is worth. |
| Shore-following first transect | A curved first pass hugging the bank, then the grid. |
| Turn limit | Degrees of heading change per 10 m the shore pass may use. |
| Orthogonal pass | A second set at 90°, with its own spacing. |

**6. Plan.** Press *Compute*. It runs on a worker
thread with a cancellable progress dialog, because on a lake with several
launches it takes tens of seconds and a frozen window is indistinguishable from
a crash. The table lists each day; click a row to show
that day alone. The status line reports closest approach to shore and the worst
turn — both are checked, not assumed.

**7. Export.** GPX and `.plan` are written one file per day; GeoJSON is the
whole plan for GIS.

## The view is the region

Nothing off screen is drawn. The shoreline is cut to the viewport with shapely
and the result kept until the view moves; survey lines, roads and no-go areas
are dropped by a bounding-box test before they reach matplotlib. On a body of
90 rings and 18,456 vertices that took a redraw from 100 ms to 64 ms, and
zoomed into one bend only 3 pieces of outline are drawn at all.

**And when no region is drawn, the view is the region.** Zooming in is how
anyone says which part of a river they mean, and it is quicker than drawing a
polygon around it — so Compute plans the water on screen and says it did.
Zoomed out far enough to hold the whole waterbody, nothing changes. This is
also what keeps a sixty-mile river plannable: the part you are looking at is
never sixty miles.

One thing that did not work, recorded so it is not tried again: cropping the
satellite mosaic to the view before drawing it. It is the obvious saving and it
is backwards — a small array has to be upsampled to fill the canvas, which
costs more than downsampling the large one. Measured zoomed in, 208 ms cropped
against 134 ms whole. The imagery is drawn whole on purpose.

## Knowing what Compute will cost

Under the *Compute plan* button is a live estimate — days, miles of line, and
roughly how long the computing itself will take. It follows every parameter, so
you can see what closer spacing or a 90° pass does before waiting for it, and
it is what tells you a region is worth drawing.

It is worked out from areas and lengths alone — no raster, no routing — so it
costs a buffer operation rather than the minutes the real thing takes. The
constants are fitted to seven real runs rather than guessed; the first guesses
were about half the true figures. Days land within about a fifth and the time
within about a quarter:

| case | days est / real | seconds est / real |
|---|---|---|
| plain, 1 launch | 16 / 16 | 24 / 24 |
| shore transect | 18 / 19 | 27 / 33 |
| 90° pass | 24 / 28 | 35 / 37 |
| 3 launches | 13 / 13 | 21 / 18 |
| half the lake | 9 / 8 | 15 / 7 |
| 80 ft spacing | 8 / 10 | 14 / 18 |

**Line of sight is the exception and says so.** It discards whatever no marked
position can see, and how much that is cannot be known without computing the
viewsheds — the very thing the estimate exists to avoid. Untreated it was out
by a factor of two, so the estimate carries a warning instead of a wrong
number.

## Large water

A plan is routed over a grid of 12 ft cells covering the water. That is
affordable for a lake and not for a river: a 28 by 61 mile reach comes to **330
million cells — 2.6 GB for every route it works out**, of which a plan does
hundreds. It does not fail, it swaps, and from the outside that is a hang.

So the size is checked before anything is allocated, and a body too large is
refused in hundredths of a second with the numbers and the remedy: **zoom in and
draw a region of interest over the part you want**. The warning also appears
when the shoreline loads, rather than after a long Compute.

The grid follows the region, not the waterbody. It used to cover the whole
outline whatever region was drawn, which meant the one remedy on offer did not
actually make the plan affordable.

## Choosing line spacing

Side scan is poor directly under the boat — with the water column removed, the
few near-vertical samples get stretched across the widest patch of ground in
the swath — and poor at the far edge, where the return weakens and the
footprint grows. It is good in between.

So spacing should put each line's nadir strip inside a **neighbour's** good
band. Taking the good band as running from one water depth out to 0.6 of the
range setting, that means spacing of roughly

```
    depth  ..  0.6 x range
```

For an 18 ft deep lake surveyed at 72 ft range, anything from 36 to 43 ft gives
every point at least one good look; 40 ft sits in the middle. Wider leaves
strips that only nadir ever covered.

## How a day is routed

Three things are wanted from a day's path and they are one question, not three:
begin at the block nearest the launch, spend as little as possible getting
between blocks, and leave each block at the corner where the next one begins.

Answering the first two greedily and the third not at all gets all three wrong.
A block entered at its cheapest corner finishes at the far one, and the drive
to the next block is then the width of a block. Choosing an entry without
looking at the exit it implies is a local decision to a problem that is not
local.

So the block order is settled first — nearest the launch, then un-crossed by
2-opt, which never moves the first block — and the orientations are settled
afterwards for the whole chain at once. A stack of parallel lines can be run
four ways, and picking one fixes both where the boat enters and where it
leaves; the cheapest set of choices across the day is a shortest path with four
states per run, which is exact and instant at this size.

On Indian Lake, with the 90° pass, that takes the block-to-block hop from a
median of 546 ft to **45 ft** — about one line spacing, which is corners
meeting.

## Day length, and near-shore work first

The maximum is a hard cap. The minimum is met wherever the geometry allows it.

Filling each day to the brim leaves whatever will not fit as the next day, and
the last of those is routinely twenty minutes long. So a day is backed off
until the remainder can stand on its own, and neighbouring days are pooled and
re-cut where that helps. Pairs alone are not enough — a full 2.0 h day beside a
0.4 h one is 2.4 h, which is neither one day inside the cap nor two above the
floor — so the window widens to three days, which has the slack that two do
not. On Indian Lake with the shore transect that takes **24 days with 8 below
the minimum down to 19 days with 3**.

**Those three cannot be fixed.** They cover water that does not touch another
day's, so folding them in would split an outing into two halves sharing a date.
The status line says how many there are and why.

**Near-shore lines are worked first.** A block against the bank has a stack of
lines with the shore at one end and open water at the other, and starting at
the shore end means an outing cut short has already covered the bank — which is
where the docks, drop-offs and structure are. It is priced rather than forced,
so it gives way when the detour is genuinely expensive. Distance from the bank
of a block's first line against its last, on Indian Lake:

| weight | first line | last line | plan |
|---|---|---|---|
| 0 | 155 ft | 121 ft | 86.3 mi |
| 1 | 138 ft | 147 ft | 86.1 mi |
| **5** (default) | **87 ft** | **203 ft** | 87.4 mi |

Putting the bank first costs 1.3% more driving.

## The shore-following transect

Tick *Shore-following first transect* and the plan opens with a curved pass as
close to the bank as the rules allow, then starts the grid.

The navigable boundary — the shoreline already offset inward by the setback —
is not drivable: at Indian Lake it turns **160°** inside 10 m, against a filter
that discards everything over 50. Simplifying it does not help; chords get
shorter but the vertices stay sharp, and it measured 163° at every tolerance
tried.

What works is a morphological opening: erode the water by a radius and dilate
it back. That rounds every corner to at least that radius and drops arms
narrower than twice it — and the radius follows from the rule rather than being
tuned, since a heading change of *limit* over *sample* is an arc of radius
`sample / limit`, or **37.6 ft** for 50° over 10 m. An opening can only shrink
the region, so the setback survives it by construction.

Measured on Indian Lake: **5.2 mi of transect, worst turn 40°** of 50 allowed,
55.9 ft off the bank against a 50 ft setback, nothing over land.

**The transect belongs to the day, not to a day of its own.** It is clipped to
each outing's blocks and worked while the boat is already down that end of the
lake — six miles of perimeter run as its own outing is three hours of nothing
but shoreline, and it leaves the bank unsurveyed on the day the boat is
actually there. On Indian Lake: **5.2 mi of transect spread across 18 of 26
days, none of them shore-only.**

**Each day's grid is squared to that day's own stretch of bank.** The bearing
is the shore's length-weighted direction — bearings doubled before averaging
and halved after, since a line has no front and raw averages cancel. A day
whose bank has a clear direction gets a grid within a few degrees of it; a day
whose two stretches disagree falls back to the lake's bearing rather than
averaging across them, which had put one day's grid 77° across its own shore.
A cove running east and a reach running north are one bearing only on a lake
shaped like a stick.

Turns are reported as two numbers, because two different things are being
asked: a grid line has to be straight, and any turn in it is a fault; a shore
transect is a curve on purpose and only has to stay inside the filter.

## Why the lines are straight

Side scan builds its swath assuming the boat ran straight while it did so. A
curved track smears the image, and the processing discards those pings as a
turn — so a path that follows the shoreline surveys nothing. Every line here
has two endpoints and no turns at all.

## Notes

**NHD was retired on 1 October 2023.** The data is still published but no
longer maintained; new work moves to the 3D Hydrography Program. For a lake
whose outline has not moved this does not matter. For a reservoir drawn down
twenty feet it does, and nothing here can tell you that has happened — check
the outline against recent imagery before trusting it.

**QGroundControl files are plain waypoints, not Survey items.** QGC's Survey
complex item carries a schema that shifts between releases and is strictly
validated — a file that loads on one version is rejected on the next for a
missing key. Waypoints have almost nothing to get wrong, and QGC flies the
lines as planned rather than regenerating its own. The cost is that you cannot
drag the survey polygon inside QGC.

**Every hop is routed over water, and the whole route is checked.** The
straight jump between two survey lines cuts across a peninsula the moment a
lake has one, so a hop that would leave the water is replaced by a least-cost
path that stays on it. The clearance check measures the full mission track —
run out, lines, hops, run home — because the segment that used to cross a dock
belonged to no leg and so was never looked at while every reported number
stayed clean.

**Water with no route to a launch is dropped.** Shrinking a lake by the setback
and cutting no-go areas out of it routinely leaves pieces that no longer touch.
Least-cost routing does not fail when asked to reach one — land is expensive in
the cost grid, not forbidden, so it buys its way across. Those pieces are found
and left out, with the acreage reported.

## When something goes wrong

An unhandled error shows a dialog with the cause and appends the full traceback
to `%LOCALAPPDATA%\SurveyPlanner\errors.log`. Tk's default is to print it to
stderr, which a windowed program has nobody reading — the window just stops
working, which is indistinguishable from a crash and impossible to report. If
you hit one, that file says where.

## Building an executable

```
pip install pyinstaller
build.bat
```

Produces `dist\SurveyPlanner.exe`, standalone.

## Layout

```
survey_planner.py     Tkinter application
planner/
  geometry.py         local feet, bearings, turn angles
  shoreline.py        NHD fetch, save/load, polygon
  plan.py             lines, ordering, days, verification
  access.py           water raster, viewsheds, station suggestion, routing
  nogo.py             islands from the outline, docks from OpenStreetMap
  imagery.py          shoreline traced from satellite imagery
  exporters.py        GPX, QGroundControl .plan, GeoJSON
```

## Building the Executable

```
pip install pyinstaller
python build.py
```

The result is `dist\SurveyPlanner\`, about 188 MB, which zips for a
release. Most of that is scikit-image and SciPy, which cannot be left out:
the least-cost routing that keeps a transit on the water is theirs.
`python build.py --onefile` produces a single file instead, which starts
more slowly because it unpacks itself on every launch.

## Where It Fits

Part of the [AnchorHold](https://github.com/maxschwartziv/anchorhold-web-viewer)
pipeline, which plans a survey, builds charts from the recording, and draws
them in a browser offline. The plans this writes are flown by
[Shoalmark ASV](https://www.droneboatfleet.com/shoalmark-asv/). Planning is
useful on its own, so this repository stands alone.

## Licence

[MIT](LICENSE). Copyright (c) 2026 Maximilian K Schwartz IV.
