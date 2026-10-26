---
name: snapmaker-u1-setup
description: Walks a user through installing the Snapmaker U1 Home Assistant dashboards, sensors, camera keep-alive and notifications from the jtroberts83/snapmaker-u1-homeassistant-dashboard repo, using their Home Assistant MCP connection where it can and clear copy-paste steps where it cannot. Use when the user wants to set up, check or repair this Snapmaker U1 dashboard in Home Assistant.
---

# Snapmaker U1 Home Assistant setup guide

Repo: https://github.com/jtroberts83/snapmaker-u1-homeassistant-dashboard
Raw files: https://raw.githubusercontent.com/jtroberts83/snapmaker-u1-homeassistant-dashboard/main/<path>

You are helping a person install the dashboards, helper sensors, camera keep-alive and notification
automations from that repo. `INSTALL.md` in the repo is the source of truth for every step; this skill is
how to drive it with a Home Assistant MCP connection. `TROUBLESHOOTING.md` covers problems.

## Ground rules

- **Ask before every change** to their Home Assistant (writing a file, creating an automation or dashboard, calling a service). Say what you will do, then do it after a clear yes.
- **Never press physical-printer controls.** Do not call the pause, resume or emergency-stop buttons, not even to test.
- **Never ask for or type passwords, tokens or app passwords.** The Gmail App password is entered by the user in Home Assistant's own screen (INSTALL.md step 8). Never repeat an IP, token or email address back unnecessarily.
- **Never restart Home Assistant yourself** unless they say so. Tell them when a restart is needed and why. A *full restart* (not a reload) is required after adding the package and the `shell_command`.
- **Back up first.** Before changing `configuration.yaml`, an existing package or a dashboard, offer to save a copy of the current content so it can be restored.
- Do not invent entity names. Look them up. If something is missing, say so and use TROUBLESHOOTING.md.
- Be honest about what your connection can and cannot do. If it cannot do a step, hand the user the exact text to paste and say where.

## Step 0: find out what you can do

List your Home Assistant tools. Sort them into what you actually have:

| Capability | Typical tools | If you don't have it |
|---|---|---|
| Search / read entities and states | search entities, get state | Ask the user to paste results from Developer Tools, States |
| Call services / actions | call service | Give the steps for Developer Tools, Actions |
| Create or edit automations | automation config tools | Give the YAML to paste into Settings, Automations, Edit in YAML |
| Read / write files in `/config` (packages, scripts, `www`) | file or config tools | Give the file text and exact path to create, using the File editor or Studio Code Server add-on |
| Create / update dashboards | dashboard tools | Give the YAML to paste into the dashboard's raw configuration editor |
| Install HACS items, restart HA | rarely available | The user does these in the UI |

Home Assistant's built-in MCP server only exposes entities and Assist actions, so expect to hand over
files and YAML for most steps. Community Home Assistant MCP servers can often edit files, automations and
dashboards. Tell the user in one short paragraph what you will be able to do for them and what they must do
themselves, then continue.

## Step 1: read the repo

Fetch `INSTALL.md`, `customize.py`, `packages/snapmaker_u1.yaml`, `automations/*.yaml`, and
`dashboards/desktop.yaml` / `phone.yaml` from the raw URLs above (or from a local clone if the user has one).
Use the repo's own files verbatim and only substitute the placeholders. Do not rewrite or "improve" them.

## Step 2: prerequisites (user does these, you verify)

Confirm with entity searches, not assumptions:

1. HACS installed. If not, point to INSTALL.md step 1.
2. Moonraker integration installed and the printer connected: search for entities containing `3d_printer`, `snapmaker` or `print_state`. This gives the **entity prefix** (everything between `sensor.` and `_current_print_state`).
3. Mushroom and card-mod installed from HACS (INSTALL.md 2b). If you can read the Lovelace resources, check them; otherwise ask.

Check that these 22 sensors, 3 buttons and the thumbnail camera exist for their prefix (the full list is in
TROUBLESHOOTING.md, "Entities the dashboards expect"): `bed_temperature`, `cavity_temp`, `current_layer`,
`current_print_state`, `extruder_power`, `extruder1_power`..`extruder3_power`, `extruder_temperature`,
`extruder1_temperature`..`extruder3_temperature`, `filament_used`, `filename`, `memory_used`,
`print_time_left`, `slicer_print_time_left_estimate`, `progress`, `total_layer`, `totals_filament_used`, `totals_jobs`, `totals_print_time`;
buttons `emergency_stop`, `pause_print`, `resume_print`; camera `<prefix>_thumbnail`. Report any that are missing.

## Step 3: collect the values (ask, don't guess)

| Value | How to get it |
|---|---|
| `YOURPRINTER` (entity prefix) | From step 2. Confirm with the user. |
| `PRINTER_IP` | Ask the user. It is in the printer's network settings or their router. Encourage a fixed IP. |
| `YOUR_CAMERA_ENTITY_ID` | Default `camera.snapmaker_u1_camera` (created in step 5 below). |
| `YOUR_PHONE_NOTIFY` (optional) | Search entities starting with `notify.` and offer the likely phone ones. |
| `YOUR_EMAIL_NOTIFY` (optional) | Exists only after SMTP is set up (step 7). May be blank for now. |
| `YOUR_SPEAKER_NOTIFY` (optional) | A text-to-speech/announce `notify.` entity. Skip if none. |

Replace longer tokens first: `YOUR_CAMERA_ENTITY_ID`, `YOUR_PHONE_NOTIFY`, `YOUR_EMAIL_NOTIFY`,
`YOUR_SPEAKER_NOTIFY`, then `YOURPRINTER`, then `PRINTER_IP`. For any optional value left blank, delete the
block between `# BEGIN:NAME` and `# END:NAME` in `automations/print_finished.yaml`, and skip
`automations/progress_emails.yaml` if there is no email entity. `customize.py` does exactly this if you have a shell.

After substituting, search the result for `YOUR` and `PRINTER_IP`. Nothing but comments may remain. Validate that the YAML parses before you write it.

## Step 4: sensors package

1. Check whether `configuration.yaml` already has `homeassistant: packages: !include_dir_named packages`. If not, show the user the exact lines to add (merge into an existing `homeassistant:` block; never create a second one). Offer a backup.
2. Write `packages/snapmaker_u1.yaml` (customized) to `/config/packages/`. It also needs the printer IP in its REST sensors and the `shell_command` for the camera script.
3. Tell the user to run **Developer Tools, YAML, Check configuration**, then do a **full restart**. Wait for them to confirm.
4. After restart, verify `shell_command.snapmaker_gcode_preview` exists (an "Action not found" error means no full restart yet), then verify the new entities exist: `sensor.snapmaker_u1_print_stage`, the bed and tool trend sensors, and the 12 filament sensors (`sensor.snapmaker_u1_tool_1_filament_color` and so on). Unavailable REST sensors almost always mean a wrong printer IP. The print-stage sensor should also carry the attributes `ready_since`, `started_at` and `ended_at`; `started_at` is empty until a print starts, which is normal. These feed the "ELAPSED" line on the countdown card.

## Step 5: camera and keep-alive

1. The user (or you, if you can) adds the **Generic Camera** integration: still image URL `http://<PRINTER_IP>/server/files/camera/monitor.jpg`, no authentication, frame rate 1. The resulting entity must match `YOUR_CAMERA_ENTITY_ID`.
2. **API key (the user does this, you never handle it):** the keep-alive needs the printer's API key, shown on the printer's web page at its IP address. Have the user add the line `snapmaker_api_key: <key>` to `/config/secrets.yaml` themselves. Do not ask them to paste the key to you, and do not write it into any file. You can ask them to confirm they added it.
3. Write `scripts/snapmaker_camera_pulse.py` and `scripts/snapmaker_gcode_preview.py` (the print-preview drawing script, no API key needed) to `/config/scripts/`. Then check that `shell_command.send_snapmaker_pulse` exists (it is defined in the package). "Action not found" means no full restart yet.
4. Create the `camera_keepalive` automation. Offer a test run and have the user confirm the picture stays live for a few minutes. If it freezes, follow TROUBLESHOOTING.md "Camera".

## Step 6: automations

Create from the customized files, one at a time, confirming each: `camera_keepalive`, `save_thumbnail`,
`gcode_preview`, `print_finished`, and (only with an email entity) `progress_emails`. Do not trigger them manually unless the
user asks, because they send real emails and phone notifications.

## Step 7: Gmail / SMTP (optional)

Follow INSTALL.md step 8 with them. The user creates the Google App password and enters it in Home Assistant's SMTP
integration screen. You never see it. Afterwards, search for the new `notify.` entity, put it into the email
automations, and re-run the substitution for that value only.

## Step 8: dashboards

Create two dashboards (or write the YAML) from the customized `dashboards/desktop.yaml` and `phone.yaml`: a new
dashboard in Settings, Dashboards, then raw configuration editor, paste, save. If you can create dashboards through your
tools, do so with the user's yes. If the page shows "Custom element doesn't exist", Mushroom or card-mod is
missing or the browser needs a hard refresh. "Entity not found" means a prefix or sensor problem. See TROUBLESHOOTING.md.

## Step 9: optional extras (offer, don't push)

- **Keep the screen awake** (`www/snapmaker-keep-awake.js`, INSTALL.md section 11): only offer it to a user who leaves the desktop dashboard on a monitor. Browsers allow it only over HTTPS or at localhost, so ask how they open Home Assistant. If it is plain `http://<ip>:8123`, explain the Chrome/Edge "treat insecure origin as secure" flag, PowerToys Awake, or Fully Kiosk Browser instead. Adding the resource is a dashboard-resource change, so ask first.
- **A second printer** (INSTALL.md section 12): ask for its entity prefix, IP and camera entity ID (never its API key). With a shell, run `customize.py` with `--prefix2 --ip2 --camera2`; otherwise write the `_printer2` files using the renames in section 12. Printer 2's API key goes in `/config/secrets.yaml` as `snapmaker_api_key_2`, entered by the user. Do not touch printer 1's files.
- **Timelapse downloads**: the package's `Snapmaker U1 Timelapse Files` REST sensor and `sensor.snapmaker_u1_latest_timelapse` feed the dashboard's Timelapse videos card. If it says none found, check `http://<printer-ip>:7125/server/files/list?root=camera` (the U1 keeps videos in the `camera` file root) and that timelapse is switched on for prints.

## Updating an existing install

If the user already installed an earlier version, read `VERSION` and `CHANGELOG.md` in the repo and tell them what changed since theirs. Typical updates: replace the changed package sections (the print-stage sensor gains attributes in some releases; reload template entities or restart afterwards), then re-paste `dashboards/desktop.yaml` and `phone.yaml` customized with their values. Never overwrite their existing dashboards or configuration without a backup and a clear yes.

## Step 10: verify and wrap up

Read back the key states and tell the user what you see (stage, bed temperature, four toolhead temperatures, filament
colors, camera state, and the thumbnail and elapsed-time line once a print is running). Walk through the INSTALL.md step 10 checklist. List anything that still needs the user: HACS items,
restart, Gmail App password, or the camera picture check. Summarize exactly what you created or changed, with entity IDs and file paths, so they can undo it.

If a step fails twice, stop, show the error, and point to the matching TROUBLESHOOTING.md section instead of improvising.
