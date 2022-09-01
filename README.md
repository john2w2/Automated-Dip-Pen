# Setup

1. (Optional) Create virtual environment: `python -m venv venv`
2. Activate venv: `venv\Scripts\activate`
3. Install packages: `pip install -r requirements.txt`
   1. Note: you may need to download the latest version of Python
   2. To update pip, run `python -m pip install --upgrade pip`


# Development
1. Clone repo
2. Switch to branch `dev` or create new branch with `git checkout -b new_branch_name`
3. Open a pull request to `main` when ready, never push to `main` directly
4. Wait for pull request to be approved and merged

- (Optional) Delete a branch: `git branch -d branch_name`


# Protocol

## Calibration
1. Calibrate stage (set stage to origin)
2. Calibrate Elveflow pressure system
3. Calibrate arm positions (TODO: manual for now, automated later)
4. Calibrate camera (check imaging is clear)
5. Calibrate devices
   1. Chip
   2. Well Plate

### Chip Procedure
1. Print droplet (burst, 50 drops) to glass slide
2. Move stage to align camera view with droplet, then set position
   - This offset between camera and printer head is now saved
3. Repeat steps 1-2 as many times as necessary, printing a single drop for accurate offset

### Well Plate Procedure: (wip)
1. Move camera over to top left of well plate
2. Run well center detection algorithm to get location of first well's center (under camera)
3. The offset (previously calculated in Chip Procedure) still applies here, so now we also know location of first well's center (under printer head)

# Warnings
1. Elveflow pressure system will suck in air/water when software is disconnected. Make sure cap is on
2. Printer head is fragile
3. Do not remove printer container by pulling on the clear plastic piping! Slide the printer out with fingernails
