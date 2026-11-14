# A6 seed 42 reference

Bolivia_103757. The fixture contains the SHA-256 of the entire 15-channel input, centre-crop logits and a 512 x 512 classification assembled from four independent forwards, with excluded pixels set to 255. It uses the snapshot notebook and original trial 007 training checkpoint, independently of the application model and preprocessing modules. Regenerate with Python 3.11 and the backend dependencies:

```sh
python tests/fixtures/generate_reference.py "../FAST_SCNN improvements/A6 hyperparameter tuning using bayesian"
```
