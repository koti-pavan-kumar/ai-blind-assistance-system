"""
╔══════════════════════════════════════════════════════════════╗
║     BLIND ASSISTANCE SYSTEM                                  ║
║     Model   : YOLO11s (2024) via Ultralytics                 ║
║     Speech  : gTTS pre-cached (Telugu/Hindi) + SAPI (English)║
║     Features: Direction · Count · Priority · Danger Beep    ║
║               CLAHE low-light enhancement                    ║
║               Multilingual: English / Telugu / Hindi         ║
╚══════════════════════════════════════════════════════════════╝

INSTALL (run once):      
    pip install ultralytics opencv-python pywin32 gtts pygame

HOW TO RUN:
    python main.py
    Press Q to quit.

HOW TO CHANGE LANGUAGE:
    Find the line:  LANGUAGE = "en"
    Change to:
        LANGUAGE = "en"   → English  (offline, Windows SAPI)
        LANGUAGE = "te"   → Telugu   (internet needed at startup only)
        LANGUAGE = "hi"   → Hindi    (internet needed at startup only)

HOW IT WORKS FOR EMBEDDED HARDWARE (Raspberry Pi):
    - At startup, system downloads and caches all phrases as MP3 files
    - After startup caching is done, internet is no longer needed
    - All detections play from local cache — fully real-time
    - On Raspberry Pi: replace win32com SAPI with espeak-ng for English
"""

import cv2
import time
import threading
import queue
import winsound
import pythoncom
import os
import tempfile
from collections import defaultdict
from ultralytics import YOLO

# ═══════════════════════════════════════════════════════
#  CHANGE LANGUAGE HERE
#  "en" = English | "te" = Telugu | "hi" = Hindi
# ═══════════════════════════════════════════════════════
LANGUAGE = "en"

# ═══════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════
CONFIDENCE_THRESHOLD = 0.40
NMS_IOU_THRESHOLD    = 0.45
SPEAK_INTERVAL       = 3
DANGER_INTERVAL      = 2
NO_OBJ_INTERVAL      = 10
CAMERA_INDEX         = 0
CAMERA_WIDTH         = 640
CAMERA_HEIGHT        = 480
LOG_MAX_LINES        = 5
SPEECH_FRAME_SKIP    = 3

# ═══════════════════════════════════════════════════════
#  TRANSLATION TABLE
# ═══════════════════════════════════════════════════════
TRANSLATIONS = {
    "en": {
        "startup"    : "Blind assistance system ready.",
        "stopped"    : "System stopped.",
        "path_clear" : "Path is clear.",
        "very_close" : "very close",
        "nearby"     : "nearby",
        "ahead"      : "ahead",
        "on_left"    : "on your left",
        "on_right"   : "on your right",
        "center"     : "ahead",
        "warning"    : "{} very close {}!",
        "caution"    : "{} very close {}!",
    },
    "te": {
        "startup"    : "అంధుల సహాయ వ్యవస్థ సిద్ధంగా ఉంది.",
        "stopped"    : "వ్యవస్థ ఆపబడింది.",
        "path_clear" : "మార్గం స్పష్టంగా ఉంది.",
        "very_close" : "చాలా దగ్గరగా",
        "nearby"     : "సమీపంలో",
        "ahead"      : "ముందు",
        "on_left"    : "మీ ఎడమవైపు",
        "on_right"   : "మీ కుడివైపు",
        "center"     : "ముందు",
        "warning"    : "{} చాలా దగ్గరగా {} {}!",
        "caution"    : "{} చాలా దగ్గరగా {} {}!",
    },
    "hi": {
        "startup"    : "नेत्रहीन सहायता प्रणाली तैयार है।",
        "stopped"    : "सिस्टम बंद हो गया।",
        "path_clear" : "रास्ता साफ है।",
        "very_close" : "बिल्कुल पास",
        "nearby"     : "पास में",
        "ahead"      : "आगे",
        "on_left"    : "आपके बाईं ओर",
        "on_right"   : "आपके दाईं ओर",
        "center"     : "आगे",
        "warning"    : " {} बिल्कुल पास {}!",
        "caution"    : " {} बिल्कुल पास {}!",
    },
}

T        = TRANSLATIONS[LANGUAGE]
USE_GTTS = LANGUAGE in ("te", "hi")

# ═══════════════════════════════════════════════════════
#  OBJECT NAMES — LOCAL TRANSLATIONS
#  Only COCO-detectable objects included.
#  keys/charger/window/classroom NOT in COCO — excluded.
# ═══════════════════════════════════════════════════════
CACHE_OBJECTS = [
    "person", "chair", "dining table", "laptop", "bottle",
    "car", "truck", "bus", "motorcycle", "bicycle",
    "cell phone", "keyboard", "mouse", "remote", "book",
    "backpack", "cup", "tv", "bed", "couch"
]

TELUGU_OBJECT_NAMES = {
    "person": "వ్యక్తి", "chair": "కుర్చీ", "dining table": "టేబుల్",
    "laptop": "లాప్టాప్", "bottle": "బాటిల్", "car": "కారు",
    "truck": "ట్రక్కు", "bus": "బస్సు", "motorcycle": "మోటర్ సైకిల్",
    "bicycle": "సైకిల్", "cell phone": "ఫోన్", "keyboard": "కీబోర్డ్",
    "mouse": "మౌస్", "remote": "రిమోట్", "book": "పుస్తకం",
    "backpack": "బ్యాగ్", "cup": "కప్పు", "tv": "టీవీ",
    "bed": "మంచం", "couch": "సోఫా",
}

HINDI_OBJECT_NAMES = {
    "person": "व्यक्ति", "chair": "कुर्सी", "dining table": "मेज",
    "laptop": "लैपटॉप", "bottle": "बोतल", "car": "कार",
    "truck": "ट्रक", "bus": "बस", "motorcycle": "मोटरसाइकिल",
    "bicycle": "साइकिल", "cell phone": "फोन", "keyboard": "कीबोर्ड",
    "mouse": "माउस", "remote": "रिमोट", "book": "किताब",
    "backpack": "बैग", "cup": "कप", "tv": "टीवी",
    "bed": "बिस्तर", "couch": "सोफा",
}

def get_object_name(label):
    """Returns translated object name for current language."""
    if LANGUAGE == "te":
        return TELUGU_OBJECT_NAMES.get(label, label)
    elif LANGUAGE == "hi":
        return HINDI_OBJECT_NAMES.get(label, label)
    return label

# ═══════════════════════════════════════════════════════
#  DANGER & OBSTACLE CLASSES
# ═══════════════════════════════════════════════════════
DANGER_CLASSES = {
    "car", "truck", "bus", "motorcycle", "bicycle",
    "train", "fire hydrant", "stop sign"
}
OBSTACLE_CLASSES = {
    "person", "chair", "couch", "dining table", "bed",
    "toilet", "bench", "potted plant",
    "refrigerator", "oven", "sink", "tv"
}

BOX_COLORS = {
    "very_close": (0,   0,   255),
    "nearby":     (0, 165,   255),
    "ahead":      (0, 200,     0),
}
DANGER_BOX_COLOR = (0, 0, 180)

# ═══════════════════════════════════════════════════════
#  CLAHE — Low-Light Enhancement
# ═══════════════════════════════════════════════════════
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

def apply_clahe(frame):
    lab          = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b      = cv2.split(lab)
    l_enhanced   = clahe.apply(l)
    enhanced_lab = cv2.merge((l_enhanced, a, b))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

# ═══════════════════════════════════════════════════════
#  gTTS PRE-CACHE SYSTEM
#  Generates all common phrases as MP3 at startup.
#  Internet required only during build_cache().
#  All runtime detections play from local files — no lag.
# ═══════════════════════════════════════════════════════
phrase_cache = {}
cache_dir    = tempfile.mkdtemp(prefix="blind_assist_cache_")

def gtts_generate(text, filepath):
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=LANGUAGE, slow=False)
        tts.save(filepath)
        return True
    except Exception as e:
        print(f"[gTTS] Failed: '{text}' — {e}")
        return False

def build_cache():
    """
    Pre-generates MP3s for all common detection phrases.
    20 objects x 3 proximities x 3 directions = 180 phrases
    + fixed phrases (startup, stopped, path clear) = 183 total
    Internet needed only here — rest of runtime is offline.
    """
    if not USE_GTTS:
        return

    proximities = [T["very_close"], T["nearby"], T["ahead"]]
    directions  = [T["on_left"],    T["center"], T["on_right"]]
    fixed       = [T["startup"],    T["stopped"], T["path_clear"]]
    total       = len(fixed) + len(CACHE_OBJECTS) * len(proximities) * len(directions)
    done        = 0

    print(f"\n[CACHE] Building {LANGUAGE.upper()} phrase cache — {total} phrases...")
    print("[CACHE] Internet required only during this step.\n")

    for phrase in fixed:
        fp = os.path.join(cache_dir, f"phrase_{done}.mp3")
        if gtts_generate(phrase, fp):
            phrase_cache[phrase] = fp
        done += 1

    for obj_en in CACHE_OBJECTS:
        obj_local = get_object_name(obj_en)
        for prox in proximities:
            for dirn in directions:
                phrase    = f"{obj_local} {prox} {dirn}"
                cache_key = f"{obj_en}|{prox}|{dirn}"
                fp        = os.path.join(cache_dir, f"phrase_{done}.mp3")
                if gtts_generate(phrase, fp):
                    phrase_cache[cache_key] = fp
                done += 1
                if done % 30 == 0:
                    print(f"[CACHE] {done}/{total} done...")

    print(f"[CACHE] Complete. {len(phrase_cache)} phrases ready.\n")

def play_mp3(filepath):
    try:
        import pygame
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"[PLAY ERROR] {e}")

def gtts_live(text):
    """On-demand gTTS for uncached phrases. ~500ms delay."""
    try:
        from gtts import gTTS
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".mp3", dir=cache_dir)
        tmp.close()
        tts = gTTS(text=text, lang=LANGUAGE, slow=False)
        tts.save(tmp.name)
        play_mp3(tmp.name)
        os.remove(tmp.name)
    except Exception as e:
        print(f"[gTTS LIVE ERROR] {e}")

# ═══════════════════════════════════════════════════════
#  SPEECH ENGINE
#  English  → Windows SAPI  (offline, instant)
#  Telugu   → pre-cached gTTS MP3 (instant after startup)
#  Hindi    → pre-cached gTTS MP3 (instant after startup)
# ═══════════════════════════════════════════════════════
speech_queue     = queue.Queue(maxsize=1)
announcement_log = []

def speech_worker():
    pythoncom.CoInitialize()
    sapi_speaker = None

    if not USE_GTTS:
        try:
            import win32com.client
            sapi_speaker = win32com.client.Dispatch("SAPI.SpVoice")
            sapi_speaker.Rate   = 1
            sapi_speaker.Volume = 100
        except Exception as e:
            print(f"[SAPI ERROR] {e}")
    else:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    while True:
        item = speech_queue.get()
        if item is None:
            break

        text, cache_key = item
        print(f"[SPEAK] {text}")

        ts = time.strftime("%H:%M:%S")
        announcement_log.append(f"{ts}  {text}")
        if len(announcement_log) > LOG_MAX_LINES:
            announcement_log.pop(0)

        if USE_GTTS:
            # Try cache first — instant playback
            lookup = cache_key if cache_key else text
            if lookup in phrase_cache:
                play_mp3(phrase_cache[lookup])
            else:
                gtts_live(text)   # fallback for uncached
        else:
            if sapi_speaker:
                try:
                    sapi_speaker.Speak(text, 1 | 2)
                    while sapi_speaker.Status.RunningState == 2:
                        time.sleep(0.05)
                except Exception as e:
                    print(f"[SPEECH ERROR] {e}")

        speech_queue.task_done()

    pythoncom.CoUninitialize()

speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()

def speak(text, cache_key=None):
    while not speech_queue.empty():
        try:
            speech_queue.get_nowait()
            speech_queue.task_done()
        except Exception:
            pass
    try:
        speech_queue.put_nowait((text, cache_key))
    except queue.Full:
        pass

def danger_beep():
    threading.Thread(
        target=lambda: winsound.Beep(1000, 350),
        daemon=True
    ).start()

# ═══════════════════════════════════════════════════════
#  BUILD CACHE — must run before model loads
# ═══════════════════════════════════════════════════════
build_cache()

# ═══════════════════════════════════════════════════════
#  LOAD YOLO11s
# ═══════════════════════════════════════════════════════
print("=" * 60)
print("  BLIND ASSISTANCE SYSTEM")
print(f"  Language   : {LANGUAGE.upper()}")
print("  Loading YOLO11s model...")
print("=" * 60)

model = YOLO("yolo11s.pt")

print(f"  Model      : YOLO11s  |  mAP: 47.0%")
print(f"  Classes    : {len(model.names)}")
print(f"  Confidence : {CONFIDENCE_THRESHOLD}")
print(f"  NMS IoU    : {NMS_IOU_THRESHOLD}")
print(f"  Resolution : {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
print(f"  CLAHE      : Enabled")
print(f"  TTS        : {'gTTS pre-cached' if USE_GTTS else 'Windows SAPI (offline)'}")
print("=" * 60)

cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

frame_width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
frame_area   = frame_width * frame_height

print(f"\n  Actual resolution : {frame_width}x{frame_height}")
print(f"[INFO] System running. Press Q to quit.\n")

speak(T["startup"], cache_key=T["startup"])

# ═══════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════
def get_proximity_key(box_area, frame_area):
    ratio = box_area / frame_area
    if ratio > 0.25:
        return "very_close"
    elif ratio > 0.08:
        return "nearby"
    return "ahead"

def get_direction_key(x_center, frame_width):
    third = frame_width / 3
    if x_center < third:
        return "on_left"
    elif x_center < 2 * third:
        return "center"
    return "on_right"

def get_priority(label):
    if label in DANGER_CLASSES:
        return 0
    elif label in OBSTACLE_CLASSES:
        return 1
    return 2

def get_best_detection(detected_info):
    """
    Returns (label, prox_key, dir_key) for the single most
    important object — highest priority, largest box.
    Keeps speech short and clear for blind users.
    """
    sorted_labels = sorted(detected_info.keys(), key=get_priority)
    label         = sorted_labels[0]
    best          = max(detected_info[label], key=lambda d: d["box_area"])
    return label, best["prox_key"], best["direction"]

def build_announcement(label, prox_key, dir_key):
    """
    Returns (spoken_text, cache_key) for the given detection.
    cache_key is used to look up pre-cached MP3.
    """
    obj_name  = get_object_name(label)
    proximity = T[prox_key]
    direction = T[dir_key]
    text      = f"{obj_name} {proximity} {direction}"
    cache_key = f"{label}|{proximity}|{direction}"
    return text, cache_key

def draw_log(frame, log_list, frame_height):
    for i, entry in enumerate(reversed(log_list)):
        y = frame_height - 40 - (i * 22)
        if y < 10:
            break
        cv2.putText(frame, entry, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (180, 180, 180), 1, cv2.LINE_AA)

# ═══════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════
last_spoken_set  = set()
last_spoken_time = 0
last_danger_time = 0
last_no_obj_time = 0
frame_counter    = 0


def get_telugu_verb(label):
    """
    Returns correct Telugu verb based on object type.
    person → ఉన్నారు (living, respectful)
    everything else → ఉంది (non-living)
    """
    if label == "person":
        return "ఉన్నారు"
    return "ఉంది"
# ═══════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════
while True:
    loop_start = time.time()
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Camera disconnected.")
        break

    frame_counter += 1
    height, width  = frame.shape[:2]

    enhanced_frame = apply_clahe(frame)

    results = model(
        enhanced_frame,
        verbose=False,
        conf=CONFIDENCE_THRESHOLD,
        iou=NMS_IOU_THRESHOLD
    )[0]

    detected_info = defaultdict(list)

    for box in results.boxes:
        class_id        = int(box.cls)
        label           = model.names[class_id]
        conf            = float(box.conf)
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        w               = x2 - x1
        h               = y2 - y1
        box_area        = w * h
        x_center        = x1 + w // 2

        prox_key  = get_proximity_key(box_area, frame_area)
        direction = get_direction_key(x_center, width)

        detected_info[label].append({
            "conf"      : conf,
            "box_area"  : box_area,
            "prox_key"  : prox_key,
            "direction" : direction,
            "coords"    : (x1, y1, x2, y2),
            "is_danger" : label in DANGER_CLASSES,
        })

    # ── Draw boxes ─────────────────────────────────────
    for label, entries in detected_info.items():
        for det in entries:
            x1, y1, x2, y2 = det["coords"]
            prox_key        = det["prox_key"]
            conf            = det["conf"]
            direction       = det["direction"]

            if det["is_danger"]:
                color     = DANGER_BOX_COLOR
                thickness = 3
            else:
                color     = BOX_COLORS.get(prox_key, (0, 200, 0))
                thickness = 3 if prox_key == "very_close" else 2

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            cv2.putText(frame,
                        f"{label} | {T[prox_key]} | {T[direction]} ({conf:.0%})",
                        (x1, max(y1 - 8, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, color, 2)

    # ── HUD ────────────────────────────────────────────
    elapsed          = time.time() - loop_start
    fps              = round(1 / elapsed, 1) if elapsed > 0 else 0
    total_detections = sum(len(v) for v in detected_info.values())

    cv2.putText(frame, f"FPS: {fps}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"Objects: {total_detections}",
                (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"Lang: {LANGUAGE.upper()} | Conf: {CONFIDENCE_THRESHOLD} | CLAHE: ON",
                (10, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
    cv2.putText(frame, "BLIND ASSISTANCE SYSTEM  |  YOLO11s  |  2024",
                (10, height - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    draw_log(frame, announcement_log, height)
    cv2.imshow("Blind Assistance System", frame)

    # ── Voice + Danger logic every SPEECH_FRAME_SKIP ───
    current_time = time.time()

    if frame_counter % SPEECH_FRAME_SKIP == 0:

        if detected_info:
            detected_labels = set(detected_info.keys())
            new_objects     = detected_labels - last_spoken_set
            time_ok         = (current_time - last_spoken_time) > SPEAK_INTERVAL

            danger_close = [
                lbl for lbl in detected_labels
                if lbl in DANGER_CLASSES
                and any(d["prox_key"] == "very_close" for d in detected_info[lbl])
            ]
            very_close = [
                lbl for lbl in detected_labels
                if any(d["prox_key"] == "very_close" for d in detected_info[lbl])
            ]

            if danger_close and (current_time - last_danger_time) > DANGER_INTERVAL:
                danger_beep()
                target    = danger_close[0]
                dir_key   = detected_info[target][0]["direction"]
                obj_name  = get_object_name(target)
                verb = get_telugu_verb(target) if LANGUAGE == "te" else ""
                msg  = T["warning"].format(obj_name, verb, T[dir_key]) if LANGUAGE == "te" else T["warning"].format(obj_name, T[dir_key])
                speak(msg, cache_key=None)
                print(f"[DANGER]  {msg}")
                last_danger_time = current_time
                last_spoken_time = current_time
                last_spoken_set  = detected_labels

            elif very_close and (current_time - last_danger_time) > DANGER_INTERVAL:
                danger_beep()
                target   = very_close[0]
                dir_key  = detected_info[target][0]["direction"]
                obj_name = get_object_name(target)
                verb = get_telugu_verb(target) if LANGUAGE == "te" else ""
                msg  = T["caution"].format(obj_name, verb, T[dir_key]) if LANGUAGE == "te" else T["caution"].format(obj_name, T[dir_key])
                speak(msg, cache_key=None)
                print(f"[CLOSE]   {msg}")
                last_danger_time = current_time
                last_spoken_time = current_time
                last_spoken_set  = detected_labels

            elif new_objects or time_ok:
                label, prox_key, dir_key = get_best_detection(dict(detected_info))
                text, cache_key          = build_announcement(label, prox_key, dir_key)
                speak(text, cache_key=cache_key)
                print(f"[SPEAK]   {text}")
                last_spoken_set  = detected_labels
                last_spoken_time = current_time

        else:
            print("[INFO] No object detected")
            if (current_time - last_no_obj_time) > NO_OBJ_INTERVAL:
                speak(T["path_clear"], cache_key=T["path_clear"])
                print(f"[INFO]    {T['path_clear']}")
                last_no_obj_time = current_time
            last_spoken_set = set()

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Cleanup ────────────────────────────────────────────
speak(T["stopped"], cache_key=T["stopped"])
time.sleep(1)
speech_queue.put(None)
cap.release()
cv2.destroyAllWindows()

for f in phrase_cache.values():
    try:
        os.remove(f)
    except Exception:
        pass
try:
    os.rmdir(cache_dir)
except Exception:
    pass

print("\n[INFO] System stopped cleanly.")
