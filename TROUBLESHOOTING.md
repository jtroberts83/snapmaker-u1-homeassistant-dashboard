# Troubleshooting

Find your symptom below. Most problems come from a wrong entity prefix, a missing printer IP, or Home Assistant not having been fully restarted.

- [Camera](#camera)
- [Sensors show unavailable / unknown](#sensors-show-unavailable--unknown)
- [Filament shows "No filament set" or "Sensor not found"](#filament-shows-no-filament-set-or-sensor-not-found)
- [Entity not found / custom element missing](#entity-not-found--custom-element-missing)
- [Thumbnail and placeholders](#thumbnail-and-placeholders)
- [Stage banner looks wrong](#stage-banner-looks-wrong)
- [Page background not applying](#page-background-not-applying)
- [Emails and notifications](#emails-and-notifications)
- [Entities the dashboards expect](#entities-the-dashboards-expect)

## Camera

**Picture freezes or goes blank after a minute or two.** The U1 only streams `monitor.jpg` while a client has recently asked it to. The keep-alive script (`scripts/snapmaker_camera_pulse.py`) sends that request every few minutes through the `camera_keepalive` automation.

1. Confirm the script is in `/config/scripts/` and the `shell_command` from the package is loaded.
2. **"Action shell_command.send_snapmaker_pulse not found"** means you have not done a *full restart* (Settings, System, Restart Home Assistant) since adding the package. A quick reload is not enough.
3. Run the script by hand (from the Terminal add-on): `python3 /config/scripts/snapmaker_camera_pulse.py <PRINTER_IP>`.
   - `"state": "success"` means it worked.
   - `"state": "error"` or no output: the firmware may use a different method or parameters. Open `http://<PRINTER_IP>/` in a browser, open the developer tools Network tab, and watch the websocket messages the Snapmaker web UI sends when you open the camera view. Copy the method name and params into the script.
4. Check `http://<PRINTER_IP>/server/files/camera/monitor.jpg` directly in a browser. If you see an image right after running the script, the keep-alive is fine and the problem is the Generic Camera setup (still image URL, frame rate 1).

> The script is a reconstruction built from the documented `camera.start_monitor` Moonraker method. If your firmware differs, adjust it as above and please open an issue or PR with the working values.

## Sensors show unavailable / unknown

- **Entities restored: true / unavailable.** Check the printer's IP address is filled in everywhere: the Moonraker integration and every `resource:` URL in the package (`customize.py` does this for you).
- Wrong prefix: open Developer Tools, States, search for `3d_printer` and compare with the prefix you used. Re-run `customize.py` or find and replace.
- Template sensors only appear after a full restart; Developer Tools, YAML, Check configuration must pass first.
- Trend and peak sensors (`derivative`, trigger-based) need a few minutes of data before they show a value.
- The REST filament sensors need the printer powered on and reachable from Home Assistant.

## Filament shows "No filament set" or "Sensor not found"

- **"Sensor not found"**: the 12 REST filament sensors are missing or named differently. Confirm they exist in Developer Tools, States (`sensor.snapmaker_u1_tool1_filament_color`, and so on).
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

## Page background not applying

The background is set on the view (`background:` in the dashboard YAML). Make sure the dashboard is in YAML/raw mode with the view intact, and that you pasted the whole file. Alternatives are in `docs/background_options.html`.

## Emails and notifications

- **Gmail rejects login**: use a 16-character *App Password* (needs 2-Step Verification), not your normal password. SMTP: `smtp.gmail.com`, port 587, STARTTLS.
- **No image in the email**: confirm the camera entity name in the automation matches your camera.
- **Phone push has no image/tap action**: the plain notify entity route does not support them; use the mobile app `notify.mobile_app_*` service if you want those.
- Check Settings, Automations, Traces for the failing step.

## Entities the dashboards expect

All use your prefix (shown here as `YOURPRINTER`, for example `basement_ui_3d_printer_1`).

**Buttons:** `button.YOURPRINTER_emergency_stop`, `button.YOURPRINTER_pause_print`, `button.YOURPRINTER_resume_print`

**Camera:** `camera.YOURPRINTER_thumbnail` (plus your live camera)

**Sensors:** `sensor.YOURPRINTER_` followed by: `bed_temperature`, `cavity_temp`, `current_layer`, `current_print_state`, `extruder_power`, `extruder1_power`, `extruder2_power`, `extruder3_power`, `extruder_temperature`, `extruder1_temperature`, `extruder2_temperature`, `extruder3_temperature`, `filament_used`, `filename`, `memory_used`, `print_time_left`, `progress`, `total_layer`, `totals_filament_used`, `totals_jobs`, `totals_print_time`
