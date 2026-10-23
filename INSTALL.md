# Install & Setup Guide

This guide takes you from "Home Assistant and a Snapmaker U1" to the full dashboards, live camera,
sensors and notifications. Do the steps **in order**. Each step ends with a quick check so you know it worked
before moving on.

**Time needed:** about 30–45 minutes. **Skill needed:** you can click through Home Assistant's settings and
paste text into a file. No programming.

---

## Contents

0. [Before you start](#0-before-you-start)
1. [Install HACS](#1-install-hacs)
2. [Install Moonraker, Mushroom and card-mod from HACS](#2-install-moonraker-mushroom-and-card-mod-from-hacs)
3. [Connect Home Assistant to your U1](#3-connect-home-assistant-to-your-u1)
4. [Download this repo and fill in your details](#4-download-this-repo-and-fill-in-your-details)
5. [Add the sensors package and restart](#5-add-the-sensors-package-and-restart)
6. [Set up the camera (live view + keep-alive)](#6-set-up-the-camera-live-view--keep-alive)
7. [Create the automations](#7-create-the-automations)
8. [Set up email with Gmail (optional)](#8-set-up-email-with-gmail-optional)
9. [Create the dashboards](#9-create-the-dashboards)
10. [Final checklist](#10-final-checklist)
11. [Customizing](#11-customizing)

---

## 0. Before you start

You need:

- Your U1 powered on and on your network. Find its **IP address** (the printer's touchscreen, Settings → Network, or your router's device list). Write it down. In your router, give the printer a **reserved/fixed IP** so it never changes.
- Your printer's **API key** (needed for the camera keep-alive; you'll copy it in step 6b). You can find it by opening `http://<printer-ip>` in a browser.
- Home Assistant running, and you can sign in as an administrator.
- A way to **edit files in Home Assistant's `/config` folder**. Pick one:
  - **File editor** add-on (Settings → Add-ons → Add-on store → "File editor"), or
  - **Studio Code Server** add-on, or
  - the **Samba share** add-on (then edit from your computer's file browser), or
  - SSH.

> **Tip: how to restart correctly.** Several steps say *"restart Home Assistant"*. Always use
> **Settings → System → (power icon, top right) → Restart Home Assistant → Restart Home Assistant** (a full restart),
> **not** "Reload YAML". New sensors and shell commands are only picked up by a full restart.
> Before restarting, run **Developer Tools → YAML → Check configuration** and fix anything it complains about.

---

## 1. Install HACS

Skip this if HACS is already in your sidebar.

1. Follow the official instructions at **<https://hacs.xyz/docs/use/download/download/>** for your type of Home Assistant.
2. Restart Home Assistant, then **Settings → Devices & services → Add integration → HACS** and sign in with GitHub as HACS asks.

**Check:** "HACS" appears in the left sidebar.

---

## 2. Install Moonraker, Mushroom and card-mod from HACS

You install three things. The first gives Home Assistant your printer's data. The other two draw the dashboards.

### 2a. The Moonraker integration

1. Sidebar → **HACS**.
2. Search for **Moonraker** (by *marcolivierarsenault*) and open it. Click **Download** → **Download**.
   - If search does not find it: **⋮ (top right) → Custom repositories**, add `https://github.com/marcolivierarsenault/moonraker-home-assistant` with type **Integration**, then search again.
3. **Restart Home Assistant.**

### 2b. Mushroom and card-mod (dashboard cards)

1. **HACS** → search **Mushroom** → open it → **Download**.
2. **HACS** → search **card-mod** → open it → **Download**.
3. When HACS asks to reload / refresh the browser, do so. (Press **Ctrl+F5** / **Cmd+Shift+R** in your browser afterward.)

**Check:** HACS → each of the three shows as installed.

---

## 3. Connect Home Assistant to your U1

1. **Settings → Devices & services → Add integration**, search **Moonraker**.
2. Enter:
   - **Host / URL:** your printer's IP address (for example `192.168.1.50`)
   - **Port:** `7125`
   - **API key:** leave empty
   - Choose a **printer name** if asked (for example `Snapmaker U1`). This name decides your entity names, so keep it simple.
3. Finish. A new device appears with many sensors.

### Find your entity prefix (you'll need this in step 4)

Every sensor from the integration starts with the same prefix.

1. **Developer Tools → States**.
2. In "Filter entities" type `current_print_state`.
3. You'll see something like **`sensor.snapmaker_u1_current_print_state`**. Everything between `sensor.` and `_current_print_state` is your **prefix**. In this example it's `snapmaker_u1`. Copy the whole entity ID, you'll paste it into the customize script.

**Check:** `sensor.<prefix>_current_print_state` shows a value like `standby`, `printing` or `complete`, and `sensor.<prefix>_bed_temperature` shows a number.

> The dashboards expect about 25 entities from the integration. If one is missing in your install, [TROUBLESHOOTING.md](TROUBLESHOOTING.md#entities-the-dashboards-expect) lists all of them.

---

## 4. Download this repo and fill in your details

### 4a. Download

On this repository's GitHub page click **Code → Download ZIP**, then unzip it on your computer. (Or `git clone` it.)

### 4b. Fill in your details, easy way (recommended)

You need Python 3 on your computer (Mac/Linux have it; on Windows install it from python.org).

1. Open a terminal in the unzipped folder and run:

   ```
   python3 customize.py
   ```

   (On Windows try `py customize.py`.)
2. Answer the six questions:

   | Question | What to enter |
   |---|---|
   | Printer entity prefix | Paste the full entity ID from step 3, e.g. `sensor.snapmaker_u1_current_print_state` |
   | Printer IP address | e.g. `192.168.1.50` |
   | Camera entity ID | Just press Enter to accept `camera.snapmaker_u1_camera` (you create it in step 6) |
   | Phone notify entity *(optional)* | e.g. `notify.pixel_9`. See how to find it below. Press Enter to skip. |
   | Email notify entity *(optional)* | Created in step 8. You can leave blank now and run the script again later. |
   | Speaker notify entity *(optional)* | A text-to-speech/announce notify entity. Enter to skip. |

3. A **`build/`** folder appears with all your customized files. **Use the files from `build/`** in the steps below.

**Finding your phone's notify entity:** Developer Tools → States → filter `notify.`. Pick the one for your phone (the Home Assistant Companion app creates it). If you only see an action like `notify.mobile_app_<phone>` under Developer Tools → Actions, read the note inside `automations/print_finished.yaml` (the PHONE block shows the older form).

You can run `customize.py` again any time, for example once you've created the email entity.

### 4c. Fill in your details by hand (if you can't run Python)

Open **every file** in `packages/`, `scripts/`, `automations/` and `dashboards/` in a text editor (VS Code, Notepad++, TextEdit in plain-text mode) and use **Find & Replace → Replace all** for each row:

| Find | Replace with | Example |
|---|---|---|
| `YOUR_CAMERA_ENTITY_ID` | your camera entity | `camera.snapmaker_u1_camera` |
| `YOUR_PHONE_NOTIFY` | your phone notify entity | `notify.pixel_9` |
| `YOUR_EMAIL_NOTIFY` | your SMTP notify entity | `notify.my_gmail` |
| `YOUR_SPEAKER_NOTIFY` | your speaker notify entity | `notify.living_room_announce` |
| `YOURPRINTER` | your prefix from step 3 | `snapmaker_u1` |
| `PRINTER_IP` | your printer's IP | `192.168.1.50` |

Do the longer ones first, in the order shown. For anything *optional* you don't use (phone, email, speaker), delete the block in `automations/print_finished.yaml` between its `# BEGIN:NAME` and `# END:NAME` lines.

**Check:** search all your files for `YOUR` and `PRINTER_IP`. Only the comment lines at the top of files may still mention them.

---

## 5. Add the sensors package and restart

A *package* is just a file that bundles related Home Assistant configuration. One file creates all the helper sensors (°F temperatures, print stage, trend sensors, filament colors).

1. In your Home Assistant `/config` folder create two folders if they don't exist: **`packages`** and **`scripts`**, and a third, **`www`**.
2. Open **`configuration.yaml`** and make sure it contains this (add it, or merge it into an existing `homeassistant:` section; there must be only one `homeassistant:` key):

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. Copy **`build/packages/snapmaker_u1.yaml`** into **`/config/packages/`**.
4. Copy **`build/scripts/snapmaker_camera_pulse.py`** and **`build/scripts/snapmaker_gcode_preview.py`** into **`/config/scripts/`**.
5. **Developer Tools → YAML → Check configuration.** It must say *"Configuration will not prevent Home Assistant from starting!"*. If it reports an error, read the line it names and see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
6. **Restart Home Assistant** (full restart, see the tip in step 0). The first restart after creating `www` also makes the `/local/...` web path available, which the thumbnail and snapshots use.

**Check** (Developer Tools → States, filter `snapmaker_u1`). You should see:

- `sensor.snapmaker_u1_bed_temp_f`, `…_cavity_temp_f`, `…_extruder_1_temp_f` … `…_extruder_4_temp_f`
- `sensor.snapmaker_u1_print_stage` (`idle`, `printing`, …)
- `sensor.snapmaker_u1_bed_peak_temp_f`
- `sensor.snapmaker_u1_tool_1_temp_rate` … `tool_4_temp_rate` and `sensor.snapmaker_u1_bed_temp_rate`
- `sensor.snapmaker_u1_tool_1_filament_color`, `…_type`, `…_vendor` (and the same for tools 2–4)

> The rate sensors show *unknown* until the temperatures change a couple of times. The filament sensors read your printer every 30 seconds. If they show *unavailable*, check the printer IP in the package file.

> **Set the filament in the printer.** The color/material shown comes from what you set for each toolhead on the printer's touchscreen (or in Snapmaker Orca's filament sync). Third-party spools without an RFID tag show whatever you entered there.

---

## 6. Set up the camera (live view + keep-alive)

The U1's camera only produces fresh pictures while something keeps asking it to "monitor". You'll create a camera in Home Assistant for the picture, then a tiny script that keeps the camera awake.

### 6a. Create the camera in Home Assistant

1. **Settings → Devices & services → Add integration → Generic Camera.**
2. Fill in:
   - **Still image URL:** `http://<printer-ip>/server/files/camera/monitor.jpg` (no port number)
   - **Stream source URL:** leave empty
   - **Authentication:** none; leave username/password empty
   - **Frame rate:** `1` (if the form offers it; the camera delivers about 1 picture per second)
3. Click **Submit**, then give the camera the name **Snapmaker U1 Camera**. That makes its entity ID `camera.snapmaker_u1_camera`, which is what the files from step 4 expect. If you used another name, use that ID in step 4.

At this point the picture may be broken or frozen. That's expected until the keep-alive runs.

### 6b. Give the script your printer's API key

The printer only accepts the keep-alive from a client that presents its **API key**.

1. In a web browser, open your printer's page: `http://<printer-ip>`. Your API key is shown there (look in the settings/network area; where exactly can vary with the firmware version).
2. Open **`/config/secrets.yaml`** in Home Assistant (File editor or Studio Code Server add-on; create the file if it does not exist) and add one line:

   ```yaml
   snapmaker_api_key: PASTE_YOUR_KEY_HERE
   ```
3. Save. The key stays in `secrets.yaml` on your Home Assistant and is not part of anything you upload or share. **Never put the key into the files of this repo or commit it to GitHub.**

### 6c. Test the keep-alive (script and `shell_command` were installed in step 5)

Step 5 already installed two pieces: the script (`/config/scripts/snapmaker_camera_pulse.py`) and a `shell_command.send_snapmaker_pulse` that runs it with your printer's IP. The script reads the key from `secrets.yaml`.

**Test it:**

1. **Developer Tools → Actions** → choose **`shell_command.send_snapmaker_pulse`** → **Perform action**.
2. Look at the response. A good answer has `returncode: 0` and a `stdout` that starts with `Raw Printer Output:` followed by a JSON reply from the printer, for example:

   ```
   stdout: 'Raw Printer Output: ...{"jsonrpc":"2.0","result":{"state":"success",...},"id":1}'
   returncode: 0
   ```
3. Now open the camera entity (Settings → Entities → *Snapmaker U1 Camera*). You should see the current picture of your printer.

If you see *"Action shell_command.send_snapmaker_pulse not found"*, you haven't done a **full restart** since step 5. If you get `returncode: 1`, or the output says the handshake was refused or no API key was found, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#camera).

### 6d. Keep it alive automatically

You'll do this in step 7 with `automations/camera_keepalive.yaml` (calls the script every minute).

---

## 7. Create the automations

You have five automation files in `build/automations/`. Creating each one is the same routine:

1. **Settings → Automations & scenes → Create automation → Create new automation.**
2. Click **⋮ (top right) → Edit in YAML.**
3. **Delete everything** in the box, **paste the whole contents** of the file, and click **Save**. Give it the name already inside (`alias`).
4. Repeat for each file.

| File | What it does | Needs |
|---|---|---|
| `camera_keepalive.yaml` | Keeps the camera awake (every minute) | step 6 |
| `save_thumbnail.yaml` | Saves a copy of the print preview while printing so it stays visible after the print completes | step 5 |
| `gcode_preview.yaml` | Draws the extra print previews from the G-code: the whole model from a second angle and a layer-by-layer picture that updates every 5 minutes while printing; the dashboard rotates them with the slicer thumbnail in one large preview window | step 5 |
| `print_finished.yaml` | When a print completes, waits for the bed to cool to 40 °C, then emails you the photo and stats, pushes to your phone, adds a Home Assistant notification and announces on a speaker (any part you left blank is already removed) | step 8 for email |
| `progress_emails.yaml` | Emails a snapshot + stats at 1 %, 25 %, 50 % and 75 % | step 8 |

**Check:** the five automations are listed and switched on. The camera keep-alive will now keep your camera picture fresh. The preview pictures appear at the start of your next print (the first one takes a few seconds to a minute to draw, longer for very large files) in `/config/www/` as `snapmaker_u1_model_angle.png` and `snapmaker_u1_progress.png`.

> **Choose the angles.** In `packages/snapmaker_u1.yaml`, add options to the `snapmaker_gcode_preview` line, for example `... PRINTER_IP --model-yaw 145 --model-pitch 32 --progress-yaw -35 --progress-pitch 32`. Yaw 0 looks from the front of the printer, 90 from the left, 180 from the back, -90 from the right. Pitch is how high you look down from (0 level, 90 straight down).
>
> **Hide supports.** Add `--progress-hide-supports` to leave support structures out of the layer-by-layer preview (and `--model-hide-supports` for the second-angle picture). This relies on the slicer writing `;TYPE:Support` comments in the G-code (Orca, Prusa and Cura do); if there are none, supports can't be told apart and everything is drawn. Needs a full restart after changing the line.
>
> **Colors.** Previews use each toolhead's filament color (from the printer, or the G-code header). Add `--generic-colors` for the old blue-to-orange height gradient.

> **Test the print-finished flow without printing:** open the automation → **⋮ → Run actions**. (It will say the print is not complete and stop, which is normal; a real test happens at the end of your next print.)

---

## 8. Set up email with Gmail (optional)

Skip this whole step if you don't want emails. The dashboards and everything else work without it. If you skip it, leave the email answer blank in `customize.py`.

Gmail won't accept your normal password from Home Assistant. You create a special **App password**, a 16-letter password that works only for this purpose and can be revoked any time.

### 8a. Create a Gmail App password

1. Go to <https://myaccount.google.com/security> and sign in.
2. Under **How you sign in to Google**, make sure **2-Step Verification** is **On** (turn it on if not; App passwords require it).
3. Open **<https://myaccount.google.com/apppasswords>** (or search "App passwords" in the settings search box).
4. Enter an app name such as **Home Assistant** and click **Create**.
5. Google shows a **16-character password** once. Copy it now (remove the spaces). You won't see it again.

> Google Workspace (work/school) accounts may have App passwords disabled by an administrator. Use a personal Gmail account in that case, or another mail provider's SMTP settings.

### 8b. Add the SMTP integration

1. **Settings → Devices & services → Add integration → SMTP** (the "SMTP" notification integration).
2. Enter:

   | Field | Value for Gmail |
   |---|---|
   | Server | `smtp.gmail.com` |
   | Port | `587` |
   | Encryption | **STARTTLS** |
   | Username | your full Gmail address |
   | Password | the 16-character App password from 8a |
   | Sender | your Gmail address |
   | Recipient(s) | the address that should get the emails (can be the same) |
   | Sender name | `Snapmaker U1` |
   | Timeout | `5` seconds is fine |

3. Submit. If it reports "authentication failed", re-check the App password (no spaces) and that 2-Step Verification is on.

### 8c. Find the entity and test it

1. **Developer Tools → States**, filter **`notify.`**. The new one is your **email notify entity** (for example `notify.snapmaker_u1_my_gmail`). Copy it.
2. **Developer Tools → Actions → switch to YAML mode** and run this test (use your entity):

   ```yaml
   action: notify.send_message
   target:
     entity_id: notify.YOUR_EMAIL_ENTITY_HERE
   data:
     title: Snapmaker U1 test
     message: If you can read this, email works.
   ```
3. Check your inbox (and spam folder the first time).

### 8d. Put the entity into the automations

Run `python3 customize.py` again with the email entity filled in (or replace `YOUR_EMAIL_NOTIFY` by hand), then re-paste `print_finished.yaml` and `progress_emails.yaml` into their automations.

The progress email's subject is **`U1 3D @ ##% - <file name>`** and the body contains the latest camera snapshot and the printer's stats. The finished email has the photo, status ("safe to remove" or "bed still warm"), layers, filament used and your lifetime totals.

---

## 9. Create the dashboards

You get two dashboards. Make one for each, or only the one you want.

1. **Settings → Dashboards → Add dashboard → New dashboard from scratch.**
2. Title: **Snapmaker U1 Desktop** (or *Phone*). Leave "Show in sidebar" on. **Create.**
3. Open the new dashboard from the sidebar.
4. Click the **pencil** (top right) → **⋮ (top right) → Raw configuration editor.**
   - If it asks you to "take control", accept.
5. **Select all and delete** what's there, then **paste the whole contents** of `build/dashboards/desktop.yaml` (or `phone.yaml`). Click **Save**, then close the editor.

**Tip for phones:** in the Home Assistant Companion app, **Settings → Companion app → Default dashboard** → pick the phone dashboard so it opens right away.

**Check:** the dashboard loads with the banner, camera, toolhead columns and stat cards. If something shows *"Entity not found"* or *"Custom element doesn't exist"*, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 10. Final checklist

- [ ] Moonraker integration shows live values; `sensor.<prefix>_current_print_state` is not `unavailable`
- [ ] All helper sensors from step 5 exist
- [ ] Camera picture refreshes about once a second on the dashboard
- [ ] Four automations created and on
- [ ] (Optional) Test email arrived
- [ ] Dashboards loaded without red error cards
- [ ] Start a short print and watch the banner go **Preparing → Printing**, the toolhead cards change color, and (at the end) **Cooling Bed → Complete – Ready to remove print**, then after 30 minutes **Waiting for new print job…**

---

## 11. Customizing

| I want to… | Do this |
|---|---|
| Change the page background | In `dashboards/*.yaml`, edit the `background:` line near the top. Open `docs/background_options.html` in a browser to preview 8 ready-made options and copy their CSS. |
| Show Celsius instead of Fahrenheit | The sensors in `packages/snapmaker_u1.yaml` convert to °F. Edit the conversion formula and the thresholds (`104`, `150`, `250`…) in the dashboards. |
| Change the bed "safe to remove" temperature | Search the files for `104` (°F; 40 °C). Change it in `packages/snapmaker_u1.yaml`, both dashboards and `automations/print_finished.yaml`. |
| Change the "Waiting for new print job" delay | In `packages/snapmaker_u1.yaml`, edit `>= 1800` (seconds) in the print stage sensor. |
| Change how often the camera is kept awake | In `automations/camera_keepalive.yaml`, change `minutes: "/1"`. |
| Change which stages email you | Edit the `triggers` in `automations/progress_emails.yaml` (the `above:` values are the percentages). |
| Keep the computer screen awake while the dashboard is showing | See [Keep the screen awake](#keep-the-screen-awake-optional) below. |

### Keep the screen awake (optional)

If you leave the desktop dashboard on a monitor, you can stop the screen from dimming or sleeping while it is showing. `www/snapmaker-keep-awake.js` asks the browser for a *screen wake lock* while a Home Assistant tab on your printer dashboard is visible, and lets go when you switch tab or dashboard.

1. Copy `www/snapmaker-keep-awake.js` to `/config/www/` on your Home Assistant (create the `www` folder if it isn't there).
2. Open the file and, if needed, change `PATH_MATCH`. The screen stays awake only when the dashboard's web address contains one of those words. The default `"printer"` matches an address like `/dashboard-printer/overview`.
3. Turn on **Advanced mode** (your profile, bottom left), then **Settings → Dashboards → ⋮ (top right) → Resources → Add resource**. URL: `/local/snapmaker-keep-awake.js`, type **JavaScript module**. Save.
4. Hard-refresh the browser (Ctrl+Shift+R, or Cmd+Shift+R on a Mac).

**Limits to know:**

- Browsers only allow this when Home Assistant is opened over **HTTPS** (Nabu Casa or your own certificate) or at **localhost**. At a plain `http://192.168.x.x:8123` address it does nothing. (Open the browser console and look for `[snapmaker-keep-awake]` to see why.)
- The dashboard tab must be the visible one, and the browser must stay open.
- It keeps the display on; it does not wake a screen that has already gone to sleep.
- It works per browser. For a wall tablet, the Fully Kiosk Browser app (keep-screen-on setting) is the more dependable option. On Windows, the PowerToys *Awake* tool also works without any browser support.

### Updating later

When this repository gets updates: read `CHANGELOG.md` to see what changed, download the repo again, run `customize.py` again, and re-copy the changed files (package → reload template entities or restart; automations and dashboards → re-paste). Some releases add attributes to the print-stage sensor in the package, so always update the package before the dashboards.
