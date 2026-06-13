# Third-Party Notices

This project includes text-normalization code and finite-state transducer assets under `backend/tn/`. Several files in that tree carry Apache-2.0 copyright headers from their upstream source.

Model weights are not included in this repository. The model download helper references public ModelScope model IDs and downloads the required ASR, VAD, and punctuation models into the local `models/` directory.

Before publishing a release, review upstream licenses for:

- FunASR
- ModelScope
- WeTextProcessing/text-normalization assets under `backend/tn/`
- Chart.js copied under `frontend/lib/chart.min.js`
