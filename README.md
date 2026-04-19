# AI Blind Assistance System

A real-time object detection system that announces detected objects
by voice to help visually impaired people navigate independently.

Built as a solo project and presented at TechFest 2026 —
Pace Institute of Technology & Sciences, Andhra Pradesh.

> **Note:** Core decisions — model selection, danger priority logic,
> proximity detection, CLAHE enhancement, multilingual support,
> and physical prototype — designed by me. Code developed with AI assistance.
 
---

## Demo

![Demo](demo.png)

---

## How It Works

A USB webcam captures live video. YOLO11s detects objects in each frame.
The system calculates how close each object is and which direction it is in,
then announces it by voice instantly.

**Voice output examples:**
- *"Person nearby on your left"*
- *"Car very close ahead"*
- *"Warning! Car very close on your right!"* + beep alert
- *"Path is clear."*

---

## Features

- Real-time object detection via YOLO11s (80 COCO classes, mAP 47.0%)
- CLAHE low-light enhancement — improves detection in dim conditions
- Proximity detection — Very Close / Nearby / Ahead
- Direction detection — Left / Center / Right
- Danger priority system — vehicles spoken first with beep alert
- Object counting — "2 persons ahead" not "person, person"
- Multilingual voice output — English / Telugu / Hindi
- Pre-cached gTTS phrases — zero lag during runtime
- Queue-based threading — zero speech overlap
- Live announcement log on screen

---

## Multilingual Support

| Language | Engine | Internet Required |
|---|---|---|
| English | Windows SAPI (offline) | No |
| Telugu | gTTS pre-cached at startup | Startup only |
| Hindi | gTTS pre-cached at startup | Startup only |

To change language — open `main.py` and change:
```python
LANGUAGE = "en"   # "en" / "te" / "hi"
```

---

## Performance

| Metric | Value |
|---|---|
| Model | YOLO11s |
| mAP (COCO) | 47.0% |
| Confidence Threshold | 0.40 |
| NMS IoU | 0.45 |
| Input Resolution | 640x480 |
| FPS — Good Lighting | 26 |
| FPS — Dim Lighting | 20 |
| FPS — Very Dark | 8+ |
| Voice Response Latency | <300ms |

---

## Tech Stack

- Python 3.11
- YOLO11s via Ultralytics
- OpenCV (cv2)
- Windows SAPI — win32com (English TTS)
- gTTS + pygame (Telugu / Hindi TTS)
- NumPy
- Threading + Queue

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/koti-pavan-kumar/ai-blind-assistance-system
cd ai-blind-assistance-system
```

**2. Install dependencies**
```bash
pip install ultralytics opencv-python pywin32 gtts pygame
```

**3. Run**
```bash
python main.py
```
Or double-click `START.bat` on Windows.

Press `Q` to quit.

> `yolo11s.pt` auto-downloads (~19.4 MB) on first run.

---

## Known Limitations

- Windows only (SAPI dependency for English)
- Telugu / Hindi require internet at startup for phrase caching
- Cannot detect keys, charger, window — not in COCO dataset
- FPS drops in very dark conditions
- No depth sensor — proximity estimated from bounding box size only

---

## Roadmap

- [ ] Port to Raspberry Pi 5 for standalone use
- [ ] Replace SAPI with espeak-ng for cross-platform support
- [ ] Add ultrasonic ground sensor for step/edge detection
- [ ] 3D printed housing — target cost under ₹15,000

---

## Author

**Pavan Kumar Koti**
B.Tech AI/ML — Pace Institute of Technology & Sciences, Andhra Pradesh
[GitHub](https://github.com/koti-pavan-kumar)
