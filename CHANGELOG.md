# Changelog

Every change to this repo is committed with a version bump (semantic versioning: MAJOR.MINOR.PATCH). The current version is in [`VERSION`](VERSION).

## 1.12.0
- Changed: the live camera card is now a small page (`www/snapmaker-cam.html`) that reloads the printer's `monitor.jpg` every 1.5 seconds, instead of the Home Assistant camera card (10 s at best, sometimes stuck). **Copy `www/snapmaker-cam.html` to `/config/www/` and re-paste both dashboards.** Needs Home Assistant to be opened over plain http on your home network; for https or remote use, switch the card back to a `picture-entity` with `camera_view: auto`.

## 1.11.1
- Fix: the live camera card on both dashboards now uses `camera_view: auto` instead of `live`. With a Generic Camera that only serves still pictures, `live` could leave the card showing a stale frame for minutes; `auto` refreshes it about every 10 seconds. Re-paste the dashboards.

## 1.11.0
- Changed: the finished-print photo is now taken at 99 % progress by a new automation (`automations/final_snapshot.yaml`), not when the print completes (the bed has already been lowered by then and the part was out of view). The Print Finished email attaches that saved photo from `/media`. **Add the new automation and update `print_finished.yaml`.**

## 1.10.0
- New: timelapse videos. The package gets a `Snapmaker U1 Timelapse Files` REST sensor (reads the U1's `camera` file root every 5 minutes) and `sensor.snapmaker_u1_latest_timelapse` with download links, and both dashboards get a **Timelapse videos** card (newest video as a download link plus the five before it). **Update the package, restart, then the dashboards.** Second-printer files get their own `snapmaker_u1_2_*` copies automatically.

## 1.9.0
- New: second-printer support. `customize.py` takes `--prefix2 --ip2 --camera2` (or asks) and writes a `_printer2` copy of the package and of every automation (helper sensors `snapmaker_u1_2_*`, pictures `snapmaker_u1_2_*.png`, shell commands `*_2`, secret `snapmaker_api_key_2`), and both dashboards get a view per printer. The camera script gained `--secret NAME` and the preview script `--tag 2`; existing single-printer installs are unaffected. See INSTALL.md section 12.

## 1.8.0
- Changed: the two small preview thumbnails are now ONE larger window on both dashboards that rotates every 6 seconds through the slicer thumbnail, the whole model from a second angle, and the layer-by-layer view, with a small caption on each. **Replace both dashboards** (desktop.yaml, phone.yaml); no change to the script or package.

## 1.7.0
- New: the G-code previews are drawn in the real filament colors of each toolhead (read from the printer's filament settings, falling back to the `filament_colour` line in the G-code), instead of the height gradient. Very dark filaments are lightened so they stay visible. Add `--generic-colors` to go back to the gradient. The cache format changed, so the first preview after updating re-reads the file.

## 1.6.1
- New: `--progress-hide-supports` and `--model-hide-supports` options for the G-code previews hide support structures (needs `;TYPE:Support` comments in the G-code). Supports are still drawn by default. The parsed-file cache format changed, so the first preview after updating re-reads the file.

## 1.6.0
- New: print previews drawn from the G-code (`scripts/snapmaker_gcode_preview.py`, `automations/gcode_preview.yaml`). The slicer thumbnail now swaps every 5 seconds with the whole model from a second angle, and a new preview beside it fills in layer by layer, updated every 5 minutes. On the phone the two previews sit side by side in a row of their own. Needs the new `shell_command.snapmaker_gcode_preview` in the package. Angles are adjustable with command-line options.

## 1.5.1
- Docs and Claude Skill brought up to date: README feature list, new TROUBLESHOOTING section (toolhead colors, ACTIVE label, elapsed line, countdown units, keep-awake), update guidance in INSTALL.md, and skill steps for the new print-stage attributes, optional keep-awake script and updating an existing install.

## 1.5.0
- New: elapsed print time under the countdown ("ELAPSED hh:mm" while printing, "PRINT TOOK hh:mm" during cooling and ready). Uses new `started_at` / `ended_at` attributes on `sensor.snapmaker_u1_print_stage`, so **update the print-stage sensor in packages/snapmaker_u1.yaml** and reload template entities (or restart). Elapsed is wall-clock time since the print started, pauses included.
- Phone dashboard now shows the print thumbnail next to the filename and countdown, like the desktop layout.

## 1.4.0
- New (optional): `www/snapmaker-keep-awake.js` keeps the computer screen awake while the printer dashboard is showing, using the browser Screen Wake Lock API. Setup and limits are in INSTALL.md (section 11).

## 1.3.1
- Fix: "TOOLHEAD n - ACTIVE" now only appears for a toolhead holding above 350 °F (actually in use). A tool parked at a standby temperature such as 158 °F no longer shows ACTIVE.

## 1.3.0
- Dashboards: a toolhead that is heated up and holding steady shows its "TOOLHEAD n" label in red with " - ACTIVE" added. It reverts to the normal label when the toolhead is heating, cooling or sleeping.

## 1.2.3
- Dashboards: the countdown and estimated-completion time now use `sensor.YOURPRINTER_slicer_print_time_left_estimate`, which is more accurate than `print_time_left`. The time conversion now also copes with a sensor that has no unit. The progress-email automation still uses `print_time_left`. Entity lists updated.

## 1.2.2
- Dashboards: a toolhead that is Holding above 350 °F now gets the same red styling as Heating (red column background and red tool card). The label still says Holding.

## 1.2.1
- Fix: an idle toolhead drifting a few degrees (for example from neighbouring heat) was shown as Heating. Heating now also requires heater power of at least 10%, and Cooling only applies at 120 °F and above. Idle toolheads show Sleeping (gray).

## 1.2.0
- Dashboards: each toolhead column's background now follows its state: slate red while heating, slate blue while cooling or holding temperature, slate gray while sleeping/idle.

## 1.1.1
- Camera keep-alive script replaced with the version that works on a real printer: it authenticates to the printer's WebSocket with your API key. The key is read from `/config/secrets.yaml` (`snapmaker_api_key`) and is never stored in the repo. INSTALL.md step 6 and TROUBLESHOOTING.md updated; Claude Skill updated.

## 1.1.0
- New: Claude Skill (`skill/snapmaker-u1-setup/`) that walks users through the install via a Home Assistant MCP connection; README section explains how to install and use it. Docs: corrected the filament sensor example name (`tool_1`).

## 1.0.2
- Docs: desktop screenshot now shows filament type and vendor (PETG, Generic) and colors in each toolhead box; README screenshot note updated.

## 1.0.1
- Dashboards: the status card beside the thumbnail no longer repeats the banner message. It now shows the job name and "Current job" (or "No active job" / "Snapmaker U1 is idle").

## 1.0.0
- Initial release: desktop and phone dashboards, package (sensors/templates), camera keep-alive script, four automations (keep-alive, save thumbnail, print finished, progress emails), `customize.py`, install guide and troubleshooting.
