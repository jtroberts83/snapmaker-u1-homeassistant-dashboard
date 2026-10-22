# Changelog

Every change to this repo is committed with a version bump (semantic versioning: MAJOR.MINOR.PATCH). The current version is in [`VERSION`](VERSION).

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
