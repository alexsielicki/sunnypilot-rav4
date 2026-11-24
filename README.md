# sunnypilot-rav4

sunnypilot's `tn-prebuilt` (Toyota) build with a few steering-controller patches for a 2021 RAV4 Hybrid (TSS2).
Personal use; not affiliated with sunnypilot or comma.

## Branches

- **`main`**: this README, the patches, and the build workflow. Not installable.
- **`rav4-prebuilt`**: what the car runs. A GitHub Action builds it from the latest
  [sunnypilot/openpilot `tn-prebuilt`](https://github.com/sunnypilot/openpilot/tree/tn-prebuilt) plus every file in
  `patches/`, in name order. Don't commit to it by hand; the next build replaces its contents.

## How the build works

`.github/workflows/build.yml` runs `scripts/build.sh` every 6 hours, on every push that changes `patches/`, and on demand
(Actions > Build rav4-prebuilt > Run workflow).

1. It downloads the newest `tn-prebuilt` snapshot.
2. It applies the patches.
3. It commits the result on top of the previous `rav4-prebuilt` commit and pushes it.

Each commit message records the upstream commit and a hash of the patches, so nothing is rebuilt when neither has changed.

**If a patch no longer applies** after a sunnypilot update, the run fails and `rav4-prebuilt` is left on the last good
build. The car stays on that build until the patch is fixed.

With no patches, the branch is byte-for-byte the same as `tn-prebuilt`; the build checks this.

## Patches

The patches only change Python files, so the prebuilt binaries stay valid and nothing is compiled on the car. Each patch
says what it changes and why at the top.

To make one: change the file in a copy of `tn-prebuilt`, then run `git diff > patches/NN-name.patch`.

## Installing on the car / going back

Any branch name ending in `-prebuilt` makes sunnypilot treat the build as a development branch, the same as `tn-prebuilt`.

- **To switch the car to this build:** point the car's software at this repo's `rav4-prebuilt` branch. The setting is
  `/data/openpilot` origin + branch.
- **To go back:** point it at `sunnypilot/openpilot` `tn-prebuilt` again.

Settings are kept either way.

Toyota's torque and rate limits are enforced by the panda firmware and the car's steering hardware, which these patches
don't touch.

License: MIT, same as sunnypilot (see `LICENSE` on the `rav4-prebuilt` branch).
