<img src="custom_components/avfallskaraborg/brand/icon.png" alt="" width="96" align="right">

# Avfall & Återvinning Skaraborg — Home Assistant integration

Waste collection dates for addresses served by [Avfall & Återvinning Skaraborg][aos],
pulled from the same backend as the "Se tömningsdagar för sophämtning" widget on
their website.

Covers the member municipalities: Falköping, Gullspång, Hjo, Karlsborg, Skara,
Skövde, Tibro and Töreboda.

## Entities

One device per configured address, with:

| Entity | Type | Value |
| --- | --- | --- |
| `sensor.<address>_<bin_type>` | date | Next pickup date for that bin (one per bin, e.g. Brännbart, Matavfall, Plast/Kartong) |
| `sensor.<address>_nasta_tomning` | date | Earliest upcoming pickup across all bins |
| `sensor.<address>_dagar_till_nasta_tomning` | duration (days) | `0` means today |
| `calendar.<address>_tomningar` | calendar | One all-day event per upcoming pickup |

Each per-bin sensor carries `bin_type`, `days_to_pickup` and `formatted`
(the Swedish date string, e.g. `4 september`) as attributes. The next-pickup
sensor carries `bins` — every fraction collected on that date.

## Install

**HACS** — add this repository as a custom repository of type *Integration*,
install it, restart Home Assistant.

**Manual** — copy `custom_components/avfallskaraborg` into your
`config/custom_components/` directory and restart.

Then go to *Settings → Devices & Services → Add Integration* and search for
**Avfall & Återvinning Skaraborg**. Type part of your street address (at least
three characters), pick your address from the list, and you're done.

Requires Home Assistant 2025.2 or newer.

### Options

The polling interval defaults to 6 hours and can be changed (1–48 h) under the
integration's *Configure*. *Reconfigure* lets you point an existing entry at a
different address without losing history.

## Example automation

Remind yourself the evening before a pickup:

```yaml
automation:
  - alias: "Ta ut soporna"
    triggers:
      - trigger: time
        at: "18:00:00"
    conditions:
      - condition: template
        value_template: >
          {{ state_attr('sensor.storgatan_11_nasta_tomning', 'days_to_pickup') == 1 }}
    actions:
      - action: notify.mobile_app
        data:
          message: >
            Imorgon töms:
            {{ state_attr('sensor.storgatan_11_nasta_tomning', 'bins') | join(', ') }}
```

## Brand icon

`custom_components/avfallskaraborg/brand/` ships the integration's icon
(`icon.png` 256×256, `icon@2x.png` 512×512, plus the `icon.svg` it is rendered
from). Home Assistant 2026.3 and newer serve brand images straight from the
integration folder, so no submission to [home-assistant/brands][brands] is
needed — and that repository no longer accepts custom integrations. On older
cores the icon is simply not shown.

Re-render the PNGs after editing the SVG:

```console
rsvg-convert -w 256 -h 256 custom_components/avfallskaraborg/brand/icon.svg \
  -o custom_components/avfallskaraborg/brand/icon.png
rsvg-convert -w 512 -h 512 custom_components/avfallskaraborg/brand/icon.svg \
  -o custom_components/avfallskaraborg/brand/icon@2x.png
```


## How it works, and its limits

The integration calls two undocumented endpoints on `gullspang.avfallsapp.se`
(the Nova backend behind the official *Avfallsappen Skaraborg* app):

- `GET /api/nova/v1/next-pickup/search?address=…` — address lookup
- `POST /api/nova/v1/next-pickup/address?plant_id=…` — next pickup per bin

Both require a bearer token and an app identifier that the public web widget
ships in its own JavaScript bundle; they are shared by all users, not personal
credentials. Nothing about your account or invoices is read.

Consequences worth knowing:

- **Only the next pickup per bin is available.** There is no full-year schedule
  in this API, so the calendar cannot look further ahead than the next date for
  each fraction.
- **This is not a public API.** It can change or start rejecting the shared
  token without notice. If every entity goes unavailable at once, that is the
  likely cause.
- The `plant_id` is a freshly encrypted blob on every search response, but old
  values keep working, so the one captured at setup is stored and reused.

[aos]: https://www.avfallskaraborg.se/
[brands]: https://github.com/home-assistant/brands
