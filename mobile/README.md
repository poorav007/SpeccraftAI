# SpecCraft AI — Expo Go Mobile Swipe Reviewer

Lightweight Expo Go companion app for reviewing OpenAPI breaking-change cards (`cards` from `/api/ai/summarize-diff`) with swipe-to-**Approve** / swipe-to-**Block** and persistent `AsyncStorage` review state.

## Quickstart on a Real Phone

1. **Start the SpecCraft backend on all interfaces** (so your phone on the same Wi-Fi can reach your laptop):
   ```powershell
   cd ..\backend
   python -m uvicorn speccraft.api.server:app --host 0.0.0.0 --port 8000
   ```
2. **Find your laptop LAN IP** (`ipconfig` on Windows -> e.g., `192.168.1.42`).
3. **Install & launch Expo Go**:
   ```powershell
   cd ..\mobile
   npm install
   npx expo start
   ```
4. Scan the QR code with **Expo Go** on iOS or Android, tap **LAN IP** in the app header to enter your laptop's IP, or tap **Offline Sample** to demo immediately using `src/sampleCards.json`.

