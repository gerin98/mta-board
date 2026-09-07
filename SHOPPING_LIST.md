# MTA LED Arrival Board Shopping List

Recommended configuration: a compact 128×32 display made from two 64×32 panels. With 3 mm pixel-pitch panels, the visible display is approximately 15.1 × 3.8 inches.

Prices were checked September 7, 2026 and may change.

## Required

- [ ] **1 × Raspberry Pi Zero 2 W with pre-soldered 40-pin header** — about $20–30
  - The header must already be installed unless you want to solder it yourself.
  - Example: [Adafruit Pi Zero 2 W with Header](https://www.adafruit.com/product/6008) (availability varies; another official Raspberry Pi reseller is fine).
- [ ] **1 × Adafruit RGB Matrix Bonnet for Raspberry Pi** — $14.95
  - [Adafruit product 3211](https://www.adafruit.com/product/3211)
  - Buy the assembled Bonnet, not the solder-required Matrix HAT.
- [ ] **2 × 64×32 HUB75 RGB LED matrix, 3 mm pitch** — $44.95 each / $89.90 total
  - [Adafruit product 2279](https://www.adafruit.com/product/2279)
  - Both panels must have the same resolution, scan type, and preferably the same manufacturer/model.
- [ ] **1 × regulated 5V 10A power supply** — $29.95
  - [Adafruit product 658](https://www.adafruit.com/product/658)
  - Use 5V only—never connect a 9V or 12V supply.
- [ ] **1 × 32GB A2 microSD card** — about $10–15
  - Raspberry Pi OS Lite will be installed on this card.
- [ ] **1 × microSD card reader** — only if the setup computer does not have one.
- [ ] **M3 screws/standoffs and a frame or enclosure** — approximately $20–50
  - Keep the rear of the panels ventilated and prevent exposed power contacts from touching metal.

Estimated electronics total: **$165–180**  
Estimated finished total with mounting/frame: **$190–230**

## Confirm Before Ordering

Adafruit panels normally include the necessary panel power and HUB75 ribbon cables. Verify that the order contains:

- [ ] 2 × short 16-pin HUB75 IDC ribbon cables
- [ ] A power cable/Y-cable with two 4-pin connectors, capable of powering both panels

If using generic panels, purchase those cables separately. Avoid thin breadboard/jumper wires for panel power.

## Optional

- [ ] Tinted or smoked acrylic front panel for improved contrast
- [ ] Small passive heatsink for the Pi Zero 2 W
- [ ] Inline power switch rated for the supply
- [ ] Spare HUB75 ribbon cable
- [ ] Right-angle or short power adapter if enclosure clearance is tight

## Not Needed

- Raspberry Pi 5
- RTC/clock module—the Pi receives time over Wi-Fi
- Separate logic-level converter—the Matrix Bonnet includes one
- Triple Matrix Bonnet—the regular Bonnet supports two horizontally chained panels
- Keyboard or monitor when Raspberry Pi OS is configured for Wi-Fi and SSH during imaging
- Soldering tools when purchasing a Pi with its GPIO header pre-installed

## Smaller Alternative

For a less expensive prototype, use one 64×32 panel and a regulated 5V 4A supply. This saves roughly $55–60, but the 64-pixel width leaves little room for station and destination names.
