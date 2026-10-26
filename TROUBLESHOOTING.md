# Troubleshooting

Find your symptom below. Most problems come from a wrong entity prefix, a missing printer IP, or Home Assistant not having been fully restarted.

- [Camera](#camera)
- [Sensors show unavailable / unknown](#sensors-show-unavailable--unknown)
- [Filament shows "No filament set" or "Sensor not found"](#filament-shows-no-filament-set-or-sensor-not-found)
- [Entity not found / custom element missing](#entity-not-found--custom-element-missing)
- [Thumbnail and placeholders](#thumbnail-and-placeholders)
- [Stage banner looks wrong](#stage-banner-looks-wrong)
- [Print previews (second angle and layer by layer)](#print-previews-second-angle-and-layer-by-layer)
- [Toolhead colors, ACTIVE label and the elapsed line](#toolhead-colors-active-label-and-the-elapsed-line)
- [Page background not applying](#page-background-not-applying)
- [Emails and notifications](#emails-and-notifications)
- [Entities the dashboards expect](#entities-the-dashboards-expect)

## Camera

**Picture freezes or goes blank after a minute or two.** The U1 only streams `monitor.jpg` while a client has recently asked it to. The keep-alive script (`scripts/snapmaker_camera_pulse.py`) sends that request every few minutes through the `camera_keepalive` automation.

1. Confirm the script is in `/config/scripts/` and the `shell_command` from the package is loaded.
2. **"Action shell_command.send_snapmaker_pulse not found"** means you have not done a *full restart* (Settings, System, Restart Home Assistant) since adding the package. A quick reload is not enough.
3. Run the script by hand (from the Terminal add-on): `python3 /config/scripts/snapmaker_camera_pulse.py <PRINTER_IP>`.
   - A reply starting `Raw Printer Output:` with a JSON `result` means it worked.
   - **"No API key found"**: add `snapmaker_api_key: <your key>` to `/config/secrets.yaml` (INSTALL.md step 6b).
   - **"WebSocket handshake refused"**: the API key or the printer IP is wrong. Re-copy the key from `http://<PRINTER_IP>`.
   - **"Connection Error"**: Home Assistant cannot reach the printer on port 80. Check the IP and network.
   - Connects but still no picture: the firmware may use a different method or parameters. Open `http://<PRINTER_IP>/` in a browser, open the developer tools Network tab, and watch the websocket messages the Snapmaker web UI sends when you open the camera view. Copy the method name and params into the script.
3c. **The dashboard camera is blank or shows a broken picture.** The card uses `/config/www/snapmaker-cam.html` (copy it from `www/`) and loads `http://<printer-ip>/server/files/camera/monitor.jpg` straight from the printer. It will not work if Home Assistant is opened over https (the browser blocks the http picture) or from outside your network; use `camera_view: auto` with a normal `picture-entity` card for that case.
3b. **The camera entity is fine but the dashboard picture barely updates.** The card must use `camera_view: auto` (it refreshes about every 10 seconds); `live` can stick on a stale frame for a camera that only serves still pictures. Dashboards from v1.11.1 on already use `auto`.
4. Check `http://<PRINTER_IP>/server/files/camera/monitor.jpg` directly in a browser. If you see an image right after running the script, the keep-alive is fine and the problem is the Generic Camera setup (still image URL, frame rate 1).

> The script uses the `camera.start_monitor` method with `domain: lan`, authenticated with your printer's API key. If a firmware update changes it, adjust it as above and please open an issue or PR with the working values.

## Sensors show unavailable / unknown

- **Entities restored: true / unavailable.** Check the printer's IP address is filled in everywhere: the Moonraker integration and every `resource:` URL in the package (`customize.py` does this for you).
- Wrong prefix: open Developer Tools, States, search for `3d_printer` and compare with the prefix you used. Re-run `customize.py` or find and replace.
- Template sensors only appear after a full restart; Developer Tools, YAML, Check configuration must pass first.
- Trend and peak sensors (`derivative`, trigger-based) need a few minutes of data before they show a value.
- The REST filament sensors need the printer powered on and reachable from Home Assistant.

## Filament shows "No filament set" or "Sensor not found"

- **"Sensor not found"**: the 12 REST filament sensors are missing or named differently. Confirm they exist in Developer Tools, States (`sensor.snapmaker_u1_tool_1_filament_color`, and so on).
- **"No filament set"**: the printer reports no filament for that tool. The data comes from `print_task_config`, which is filled when a job is sliced with filament info (Snapmaker Orca/Luban) or when the spool is registered on the printer. Test: `http://<PRINTER_IP>:7125/printer/objects/query?print_task_config` should list `filament_color_rgba`, `filament_type` and `filament_vendor`.
- Toolheads with an unregistered spool report `NONE`; that is expected.

## Entity not found / custom element missing

- **"Custom element doesn't exist: mushroom-template-card"** or **card-mod**: install *Mushroom* and *card-mod* from HACS, Frontend, then hard-refresh the browser (Ctrl+Shift+R) or clear the app cache on your phone.
- **"Entity not found"**: compare the names with [the list below](#entities-the-dashboards-expect).

## Thumbnail and placeholders

- The live thumbnail comes from the Moonraker `thumbnail` camera and exists only while a file is loaded.
- When a print finishes, the `save_thumbnail` automation copies the thumbnail to `/config/www/` so the dashboard can keep showing it through cooling and ready stages. If the saved copy never appears, check the automation ran (Settings, Automations, open it, Traces) and that `/config/www/` exists.
- The placeholder is shown when there is no job and no saved copy.
- The camera placeholder shows when the camera entity is `unavailable` or `unknown`.

## Stage banner looks wrong

Stages are decided by `sensor.snapmaker_u1_print_stage`:

| Stage | Rule |
|---|---|
| Preparing | filename present, layer 0 |
| Printing | layer above 0 |
| Cooling Bed | print complete, bed above 104 F (40 C) |
| Ready | complete, bed at or below 104 F |
| Waiting for new print job | ready for 30 minutes or more |

If it sticks, check Developer Tools, States for that sensor and its `ready_since` attribute. The dashboard also computes a fallback if the sensor is unavailable.

## Print previews (second angle and layer by layer)

The two extra previews are drawn by `scripts/snapmaker_gcode_preview.py`, started by the *Print Previews* automation at the start of a print, when it finishes, and every 5 minutes in between. It downloads the print's G-code from the printer, draws the tool paths, and saves `snapmaker_u1_model_angle.png` and `snapmaker_u1_progress.png` in `/config/www/`.

- **Both previews show a blank dark picture, or the old print.** The picture is drawn a few seconds to a minute after the print starts (longer for a very large file). Wait, then refresh the browser. Check that the two files exist and have a recent time in `/config/www/`.
- **"Action shell_command.snapmaker_gcode_preview not found".** The `shell_command` line is missing from your configuration, or Home Assistant has not had a full restart since you added it.
- **Nothing is created.** Run it by hand from the Terminal add-on: `python3 /config/scripts/snapmaker_gcode_preview.py <PRINTER_IP> --foreground`. It prints what it is doing, or the error (for example it cannot reach the printer on port 7125, or the file could not be downloaded). Also look at `/config/.snapmaker_preview/last_error.log`.
- **"no extruding moves found".** The G-code uses a style the script doesn't understand. Open an issue with the first few hundred lines of the file.
- **Layers fill in too early or too late.** The progress is taken from how far through the file the printer is. If your printer does not report that, it uses the current layer number instead.
- **Supports show (or don't hide) in the layer view.** Supports are drawn by default. Add `--progress-hide-supports` (and `--model-hide-supports` for the other picture) to the `snapmaker_gcode_preview` line and fully restart. It works only if the G-code has `;TYPE:Support` / `;TYPE:Support interface` comments; check with a text editor. Without them, nothing can be hidden.
- **Previews are in the wrong colors, or the old gradient.** Colors come from `print_task_config` on the printer (test: `http://<PRINTER_IP>:7125/printer/objects/query?print_task_config`), else from the `filament_colour` line the slicer writes in the G-code. If neither exists, or `--generic-colors` is set, the height gradient is used. Black filament is lightened a little on purpose.
- **Very large files look sparse.** Above about 350,000 line segments the script draws every second or third layer to stay quick.
- **The preview doesn't rotate.** It cycles slicer thumbnail, second angle and layer view every 6 seconds each, as a CSS animation in the dashboard card; it needs card-mod from HACS. The slicer thumbnail side comes from the printer's own thumbnail.

## Toolhead colors, ACTIVE label and the elapsed line

**Toolhead column colors.** A toolhead counts as *heating* when its temperature is rising by more than 2 °F per minute **and** its heater power is 10 % or more; *cooling* when falling by more than 2 °F per minute at 120 °F or above; *holding* at 150 °F or above otherwise; *sleeping* below that. Column background: slate red when heating or when holding above 350 °F, slate blue for cooling or other holding, slate gray when sleeping. The red **TOOLHEAD n - ACTIVE** label appears only while holding above 350 °F. To change these limits, edit the numbers in `dashboards/*.yaml` (search for `350`, `150` and `pw >= 10`).

**"ELAPSED hh:mm" line missing.** It needs the `started_at` attribute on `sensor.YOURPRINTER...print_stage` (the print-stage sensor in `packages/snapmaker_u1.yaml`). Check it in Developer Tools, States. If the attribute is missing, you are on an older copy of the sensor: update it and reload template entities. The attribute is empty until a print starts after the update, and the line shows only while preparing, printing, paused (ELAPSED) or cooling and ready (PRINT TOOK). Elapsed is wall-clock time, so pauses count, and a Home Assistant restart in the middle of a print can reset it.

**Countdown looks wrong by a factor of 60.** The countdown reads `slicer_print_time_left_estimate` and converts using the sensor's unit (hours, minutes or seconds). If the sensor has no unit, values under 100 are treated as hours and larger ones as seconds.

**Screen keeps going to sleep.** The optional `www/snapmaker-keep-awake.js` only works when Home Assistant is opened over HTTPS or at localhost, not at `http://<ip>:8123` (see INSTALL.md section 11). Open the browser console and look for `[snapmaker-keep-awake]`.

## Timelapse videos

- **"No timelapse videos found".** The printer only records a video when timelapse is switched on for the print. Check `http://<PRINTER_IP>:7125/server/files/list?root=camera` in a browser; it should list `.mp4` files (the U1 keeps them in a read-only file root called `camera`). If the root name is different on your firmware, check `http://<PRINTER_IP>:7125/server/files/roots` and change `root=camera` and `/server/files/camera/` in the package.
- **"Printer not connected".** The REST sensor `sensor.YOURPRINTER...timelapse_files` is unavailable: wrong IP in the package, or the printer is off. It refreshes every 5 minutes, so a new video appears within about 5 minutes of the print finishing.
- **The link plays the video instead of saving it.** The browser opens the file in its player; use its download button or right-click, Save video as. A page on another address cannot force a download, so this is normal.
- **Home Assistant warns about large attributes.** The timelapse list is stored as an attribute and grows with every video (the printer also lists the cover pictures). To keep the database small, add `sensor.snapmaker_u1_timelapse_files` to your `recorder:` `exclude:` entities.

## Second printer

- **Printer 2 pictures or sensors show printer 1's data.** Make sure the second printer's files are the `_printer2` ones from `customize.py` (they use `snapmaker_u1_2_*` names) and that you did a full restart after adding the second package.
- **Camera keep-alive fails for printer 2 with "No API key found".** Add `snapmaker_api_key_2: <key>` to `/config/secrets.yaml`; the second shell command passes `--secret snapmaker_api_key_2`.
- **Previews for printer 2 never appear.** Run `python3 /config/scripts/snapmaker_gcode_preview.py <PRINTER2_IP> --tag 2 --foreground`. It writes `snapmaker_u1_2_model_angle.png` and `snapmaker_u1_2_progress.png` and keeps its cache in `/config/.snapmaker_preview_2`.

## Page background not applying

The background is set on the view (`background:` in the dashboard YAML). Make sure the dashboard is in YAML/raw mode with the view intact, and that you pasted the whole file. Alternatives are in `docs/background_options.html`.

## Emails and notifications

- **Gmail rejects login**: use a 16-character *App Password* (needs 2-Step Verification), not your normal password. SMTP: `smtp.gmail.com`, port 587, STARTTLS.
- **No image in the email**: confirm the camera entity name in the automation matches your camera.
- **The email photo is missing, old or shows an empty bed.** The photo is taken by the *Final Snapshot* automation at 99 % progress and saved to `/media/snapmaker_u1_done.jpg`. Check that automation is on, that `/media` exists (INSTALL.md section 7), and look at its trace after a print. A print that jumps from under 99 % straight to complete still triggers it, but a very short print may be photographed late.
- **Phone push has no image/tap action**: the plain notify entity route does not support them; use the mobile app `notify.mobile_app_*` service if you want those.
- Check Settings, Automations, Traces for the failing step.

## Entities the dashboards expect

All use your prefix (shown here as `YOURPRINTER`, for example `snapmaker_u1`).

**Buttons:** `button.YOURPRINTER_emergency_stop`, `button.YOURPRINTER_pause_print`, `button.YOURPRINTER_resume_print`

**Camera:** `camera.YOURPRINTER_thumbnail` (plus your live camera)

**Sensors:** `sensor.YOURPRINTER_` followed by: `bed_temperature`, `cavity_temp`, `current_layer`, `current_print_state`, `extruder_power`, `extruder1_power`, `extruder2_power`, `extruder3_power`, `extruder_temperature`, `extruder1_temperature`, `extruder2_temperature`, `extruder3_temperature`, `filament_used`, `filename`, `memory_used`, `print_time_left`, `slicer_print_time_left_estimate`, `progress`, `total_layer`, `totals_filament_used`, `totals_jobs`, `totals_print_time`
