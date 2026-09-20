# SENTINEL Synthetic Test Dataset

> [!WARNING]
> This dataset contains fictional synthetic documents created for SENTINEL development and testing. It contains no real Aadhaar/PAN documents and no real personally identifiable information.

## Purpose
This dataset is designed to safely test the SENTINEL document forensics pipeline without exposing real PII.

## Structure
- `documents/`: Contains the generated JPG images.
- `metadata.json`: Contains descriptive metadata and intentional variation parameters for each sample.
- `labels.csv`: Contains mapping between files, synthetic IDs, and their expected screening categories.

## Labels
- **LIKELY_AUTHENTIC**: Cleanly generated synthetic image with consistent spacing and layout. (This does NOT imply official government authentication).
- **REVIEW_REQUIRED**: Images subjected to moderate noise, blur, or minor spacing inconsistencies.
- **HIGH_SUSPICION**: Images intentionally manipulated with localized visual splicing or heavy compression artifacts.

## Generation Process
Run the generator using:
\`\`\`bash
python generate_dataset.py
\`\`\`
This will deterministically generate 10 files using the Python `Pillow` library, applying localized filters to simulate forensic anomalies.

## Analysis Instructions
Do NOT import these into the production database automatically. Users should explicitly upload these via the `/analyze` UI or utilize the `tests/test_dataset.py` suite.
