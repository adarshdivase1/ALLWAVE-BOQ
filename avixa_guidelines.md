# AV Design Guidelines for BOQ Generation (Based on AVIXA Standards)

This document provides a structured framework for generating a Bill of Quantities (BOQ) for various meeting spaces. The logic is based on globally recognized AVIXA standards to ensure system performance, reliability, and a high-quality user experience.

---

## 📝 Core Logic for the BOQ Generator

The fundamental principle is to categorize rooms by **size and function**. For each category, AVIXA standards dictate specific requirements for audio, video, and control. The generator should first determine the room type and number of participants to select the appropriate template.

---

### **Level 1: Huddle Room (2-4 People)**

This space prioritizes simplicity, ease of use, and a low barrier to starting a meeting. The design is typically centered around an all-in-one solution.

* **🖥️ Visual System:**
    * **Primary Display:** 1 x Commercial Display.
        * *AVIXA Guideline (DISCAS Standard):* The display height should be roughly 1/4 to 1/8 of the distance to the farthest viewer. For a typical 2-meter viewing distance, this translates to a **55" to 65" display**.
    * **Camera:** 1 x Wide-Angle Camera.
        * *AVIXA Guideline:* Must capture all participants without distortion. Look for a **Field of View (FOV) of 110° or greater**. This is almost always part of an all-in-one video bar.

* **🔊 Audio System:**
    * **Microphone & Speakers:** 1 x All-in-One Video Bar.
        * *AVIXA Guideline:* Audio must be clear and intelligible. Modern video bars use **beamforming microphone arrays** to focus on the speaker and have integrated speakers sufficient for small rooms. The mic pickup range should be at least **4 meters**.

* **🔌 Connectivity & Control:**
    * **Primary Connection:** 1 x BYOD (Bring Your Own Device) Kit.
        * *AVIXA Guideline:* The user experience should be seamless. A **single-cable solution like USB-C** (which carries video, USB for peripherals, and power) is ideal. A fallback of HDMI + USB is also common.
    * **Control (for dedicated room systems):** 1 x Touch Controller.
        * *AVIXA Guideline:* If the room has a dedicated computer (e.g., a Zoom Room), a touch panel (like a Poly TC8/TC10 or Logitech Tap) is required for one-touch meeting control.

* **🔩 Infrastructure:**
    * **Mounting:** 1 x Professional Display Wall Mount.

---

### **Level 2: Medium Conference Room (5-12 People)**

This space requires higher performance and dedicated equipment. All-in-one solutions are no longer sufficient.

* **🖥️ Visual System:**
    * **Primary Display:** 1 or 2 x Commercial Displays.
        * *AVIXA Guideline (DISCAS):* With a longer viewing distance (4-6 meters), display size increases to **75" to 86"**.
        * **Dual Displays** are highly recommended to show remote participants on one screen and content on the other, improving meeting equity.
    * **Camera:** 1 x PTZ (Pan-Tilt-Zoom) Camera.
        * *AVIXA Guideline:* The camera must be able to frame the entire room and zoom in on individual speakers. Look for **auto-framing and speaker-tracking** features.

* **🔊 Audio System:**
    * **Audio Processor:** 1 x Digital Signal Processor (DSP).
        * *AVIXA Guideline:* This is **non-negotiable** for rooms of this size. The DSP manages echo cancellation, microphone mixing, and equalization to ensure clear audio for remote participants.
    * **Microphones:** 2-4 x Ceiling or Tabletop Microphones.
        * *AVIXA Guideline (Audio Coverage Uniformity):* Microphone placement must provide even coverage for every seat. **Ceiling microphones** offer a cleaner look, while **tabletop microphones** can provide slightly better performance.
    * **Speakers:** 2-4 x Ceiling or Wall-Mounted Speakers.
        * *AVIXA Guideline:* Display speakers are inadequate. Use distributed speakers to ensure the audio level is uniform (**within +/- 3dB**) across the entire seating area.
    * **Amplifier:** 1 x Amplifier to power the speakers.

* **🔌 Connectivity & Control:**
    * **System Core:** 1 x Dedicated Room Codec/PC (e.g., for Microsoft Teams Rooms or Zoom Rooms).
    * **BYOD Input:** 1 x HDMI/USB Wall or Table Plate.
    * **Wireless Sharing:** 1 x Wireless Presentation System (e.g., Barco ClickShare).
    * **Control:** 1 x 10" Touch Panel Controller.

* **🔩 Infrastructure:**
    * **Equipment Housing:** 1 x Equipment Rack or Credenza.
    * **Mounting:** 2 x Professional Display Wall Mounts, 1 x Camera Mount.
    * **Cabling:** Structured cabling for audio, video, network, and control.

---

### **Level 3: Large Boardroom or Training Room (12+ People)**

This is a mission-critical space requiring the highest performance, reliability, and flexibility.

* **🖥️ Visual System:**
    * **Displays:** 2 x Large Format Displays (**86" or 98"**) or 1 x Fine-Pitch LED Video Wall. For training rooms, a **laser projector with an ALR (Ambient Light Rejecting) screen** is also a primary option.
    * **Cameras:** 1-2 x Cameras.
        * *AVIXA Guideline:* A multi-camera system is often required. One camera frames the entire room, while a second, **speaker-tracking camera** automatically follows the active speaker.

* **🔊 Audio System:**
    * **Audio Processor:** 1 x Advanced DSP with networking capabilities (e.g., Dante or AVB).
    * **Microphones:** 1 x Ceiling Microphone Array System.
        * *AVIXA Guideline:* A steerable array (like a Shure MXA920) is the best practice. It creates multiple virtual microphone lobes that can be aimed at seating areas, providing superior coverage and a clean aesthetic.
    * **Speakers:** 6-12 x Ceiling Speakers, configured in zones.
    * **Voice Lift (Optional):** For very large rooms, a voice lift system (sound reinforcement) may be needed. This involves carefully mixing microphone audio back into the room's speakers so people in the back can hear people in the front.

* **🔌 Connectivity & Control:**
    * **Control System:** 1 x Advanced Control Processor (e.g., Crestron, Q-SYS).
    * **User Interface:** 1 x 10" Touch Panel, programmed with a custom UI that may also control lighting, shades, and other room functions.
    * **Connectivity:** Multiple input points at the conference table and a primary lectern, plus a high-performance wireless sharing system.

* **🔩 Infrastructure:**
    * **Equipment Housing:** 1 x Full-Size (24U-42U) AV Equipment Rack with cooling and power management.
    * **Mounting:** All necessary heavy-duty mounts, including ceiling plates for microphones and projectors.
