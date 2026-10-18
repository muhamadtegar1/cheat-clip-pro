---
fitur: face tracking dan crop vertikal
file_utama: [backend/video_engine.py, backend/routers/media.py, src/components/ClipStudioSection.tsx]
---
# Face tracking

Menentukan titik pusat crop agar wajah pembicara (atau objek penting) tetap di dalam kanvas vertikal. Hasilnya berupa kotak ternormalisasi `{found, cx, cy, w, h}` yang dipakai `build_ffmpeg_filtergraph`.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/video_engine.py` | `detect_speaker_face_box` | L2249-2590 | YuNet (OpenCV DNN) + Haar cascade + saliency/gerak, sampling frame hemat CPU |
| `backend/video_engine.py` | `detect_video_saliency_and_motion_center` | L2172-2246 | Pusat objek dari saliency + gerakan antar frame |
| `backend/video_engine.py` | `detect_image_saliency_center` | L2142-2169 | Saliency satu gambar |
| `backend/video_engine.py` | `detect_speaker_center_ratio` | L2593-2599 | Pembungkus yang hanya mengembalikan `cx` |
| `backend/video_engine.py` | konstanta model | L149-151 | `haarcascade_frontalface_default.xml`, `cascades/face_detection_yunet.onnx` |
| `backend/video_engine.py` | pemanggilan saat render | L3001 | Di dalam `render_clip_to_mp4` bila `enable_face_tracking` atau preset streamer aktif |
| `backend/routers/media.py` | `detect_face` | L386-437 | `GET /api/detect-face` untuk pratinjau di Clip Studio |
| `backend/routers/media.py` | `get_clip_frame` | L370-382 | `GET /api/clip-frame`, frame untuk pratinjau |
| `src/components/ClipStudioSection.tsx` | `fetchFace` | L573-585 | Memanggil `/api/detect-face` saat pratinjau |

## Input / output
- Input: path video segmen, `facecam_position` (`auto`, sudut tertentu), `streamer_preset` (`none`, `split_top_cam`, `pip_corner`).
- Output: kotak wajah ternormalisasi. Default bila tidak ditemukan: `cx=0.5, cy=0.35` (atau `0.85/0.78` untuk preset streamer).

## Risiko
- Proses berat CPU (OpenCV). Commit `40948a5` sudah menurunkan sampling frame untuk server rumahan; menaikkan sampling akan memperlambat render.
- Koordinat diterjemahkan ke ukuran kanvas tetap 1080×1920 di [[render-server]].
- File `backend/cascades/*` dan `backend/haarcascade_frontalface_default.xml` wajib ada. Jangan dihapus saat merapikan repo.

## Terkait
[[index]] · [[render-server]] · [[clip-studio]]
