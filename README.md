# Survey Planner

A stand alone version of the Survey Planner element of [this larger workflow](https://www.droneboatfleet.com/anchorhold-web-viewer/)

Plan side scan sonar surveys of inland water. Fetches a lake outline from the
USGS National Hydrography Dataset, lets you mark where a boat can launch from shore, and turns it into straight survey lines
exportable to GPX or QGroundControl.

<img width="1920" height="1080" alt="surveyplanner" src="https://github.com/user-attachments/assets/b6e67ee9-b97a-465b-b6c3-e31f47d6cee4" />


## Run

Download the folder from
[Releases](https://github.com/maxschwartziv/shoalmark-survey-planner/releases),
unzip it anywhere, and run `SurveyPlanner.exe`.

Windows flags any unsigned executable the first time it runs, through
SmartScreen. Nothing is wrong with the download: Windows is reporting that
it has not seen the file before. **More info**, then **Run anyway**.

From source instead:

```
pip install -r requirements.txt
python survey_planner.py
```

`run.bat` does the same and installs what is missing on the first run.
`selftest.bat` runs the whole engine against a real lake without opening a
window, which is the quickest way to tell whether an install works.

## Use

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

The outline is saved alongside your export so a plan can be
reopened with no network.

**Getting around the map.** Wheel zooms about the cursor — about the cursor,
not the centre, so you are not chasing the thing you are looking at back into
view. Middle-drag pans; left-click is left alone because that is how access
points and regions get placed. *Reset view* returns to the whole waterbody, and
loading a new one resets it too. The matplotlib toolbar's own pan and zoom
still work.

**2. Shore access** Tick *Click the map to mark access* and click where you
can put a boat in.

**Access points are remembered against the water they belong to.** They are
saved to `%LOCALAPPDATA%\SurveyPlannerccess`

*Save shoreline…* also writes them into the file itself, and opening such a
file adopts them back into the store.

**3. Region of interest.** Tick *Click to draw a region*, click the corners,
right-click to close. Lines are then built only inside it.

**4. No-go areas.** Places the boat must not go. Tick *Click to draw a no-go
area*, click the corners, right-click to close. *Find in imagery* fills the list from
satellite imagery — see below.

*Save no-go areas…* writes them two places at once: a store beside the program
keyed to the waterbody, so fetching the same lake next season brings them back
unasked, and a file you choose, so you can hand them to somebody else. Stored
as lon/lat rings, so a file survives a different local frame. *Load…* reads one
back.

**Re-compute outline from imagery** (in *1. Water*) traces the shoreline off
satellite imagery instead of trusting the drawn one, and *Find in imagery* (in
*4. No-go areas*) lists what that trace cut out. Both run the same pass: Otsu
threshold on brightness.  WIP, confirm the outline was drawn correctly

**5. Parameters.**

```
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
```

**6. Plan.** Press *Compute*. Generates a complete survey plan for the region.

**7. Export.** GPX and `.plan` are written one file per day; GeoJSON is the
whole plan for GIS.

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

**Water with no route to a launch is dropped.** Shrinking a lake by the setback
and cutting no-go areas out of it routinely leaves pieces that no longer touch.
Least-cost routing does not fail when asked to reach one — land is expensive in
the cost grid, not forbidden, so it buys its way across. Those pieces are found
and left out, with the acreage reported.

## Errors

An unhandled error shows a dialog with the cause and appends the full traceback
to `%LOCALAPPDATA%\SurveyPlanner\errors.log`.

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

## Build

```
pip install pyinstaller
python build.py
```

The result is `dist\SurveyPlanner\`, about 188 MB, which zips for a
release. Most of that is scikit-image and SciPy, which cannot be left out:
the least-cost routing that keeps a transit on the water is theirs.

`python build.py --onefile` produces a single file instead. It starts more
slowly, because it unpacks itself into a temporary folder on every launch.
## Where It Fits

Part of the [AnchorHold](https://github.com/maxschwartziv/anchorhold-web-viewer)
pipeline, which plans a survey, builds charts from the recording, and draws
them in a browser offline. The plans this writes are flown by
[Shoalmark ASV](https://www.droneboatfleet.com/shoalmark-asv/). Planning is
useful on its own, so this repository stands alone.

## Licence

[MIT](LICENSE). Copyright (c) 2026 Maximilian K Schwartz IV.
