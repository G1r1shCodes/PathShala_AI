# PathShala AI — Android Development Guide
## Step-by-Step Methodology, Version Decisions & Code Reference

---

## ✅ ANDROID VERSION DECISION

### Target SDK: Android 8.0 (API 26) → Android 15 (API 35)

| Setting          | Value          | Why                                                                                   |
|------------------|----------------|---------------------------------------------------------------------------------------|
| `minSdk`         | **24** (Android 7.0) | Covers 95%+ of the Indian Android market. |
| `targetSdk`      | **35** (Android 15)  | Modern security + behavior fixes |
| `compileSdk`     | **35**               | Gives access to latest APIs while compiling |
| Kotlin Version   | **1.9.20**           | Stable, compatible with Compose 1.5.x |

---

## 🏗️ PROJECT STRUCTURE (New)

```
PathShalaAI/
├── frontend/
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/pathshala/ai/
│   │   │   │   ├── MainActivity.kt              ← Entry point
│   │   │   │   ├── ui/
│   │   │   │   │   ├── PathShalaScreen.kt       ← UI
│   │   │   │   │   ├── MainViewModel.kt         ← State
│   │   │   │   │   └── theme/Theme.kt
│   │   │   │   ├── network/
│   │   │   │   │   └── ApiService.kt            ← Retrofit
│   │   │   │   └── model/
│   │   │   │       └── Models.kt                ← Data
│   │   │   ├── res/
│   │   │   └── AndroidManifest.xml
│   │   └── build.gradle
│   ├── build.gradle
│   └── settings.gradle
└── backend/                                     ← FastAPI Server
```

---

## 📋 RUNNING THE PROJECT

1. **Frontend**: Open the `frontend` folder in Android Studio and click Run.
2. **Backend**: Run `python main.py` inside the `backend` folder.
3. **Integration**: The app is currently configured to use the production URL `https://pathshala-ai.onrender.com/`. 

To test locally, change `BASE_URL` in `ApiService.kt` to `http://10.0.2.2:8000/`.
