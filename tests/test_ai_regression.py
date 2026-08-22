import pytest
import joblib
from pathlib import Path
import numpy as np
from recongraph.learning.features import extract_feature_vector

MODEL_PATH = Path("models/candidate_model.pkl")

@pytest.fixture(scope="module")
def model():
    if not MODEL_PATH.exists():
        pytest.skip(f"Model not found at {MODEL_PATH}")
    return joblib.load(MODEL_PATH)

def predict_prob(model, pr: dict, gstr2b: dict) -> float:
    features = extract_feature_vector(pr, gstr2b)
    if isinstance(model, dict):
        score = model["classifier"].predict_proba([features])[0][1]
        prob = model["calibrator"].transform([score])[0] if model.get("calibrator") else score
    else:
        prob = model.predict_proba([features])[0][1]
    return float(prob)

def test_exact_match(model):
    pr = {"pr_invoice_no": "INV-123", "pr_gstin": "07ABC", "pr_date": "2026-04-12", "pr_taxable": 500}
    gstr2b = {"gstr2b_invoice_no": "INV-123", "gstr2b_gstin": "07ABC", "gstr2b_date": "2026-04-12", "gstr2b_taxable": 500}
    
    prob = predict_prob(model, pr, gstr2b)
    assert prob >= 0.50, "Exact match should be classified as positive"

def test_fuzzy_ocr_match(model):
    pr = {"pr_invoice_no": "INV-123", "pr_gstin": "07ABC", "pr_date": "2026-04-12", "pr_taxable": 500}
    gstr2b = {"gstr2b_invoice_no": "1NV/123", "gstr2b_gstin": "07ABC", "gstr2b_date": "2026-04-12", "gstr2b_taxable": 500}
    
    prob = predict_prob(model, pr, gstr2b)
    assert prob >= 0.50, "Fuzzy OCR typo should be a match"

def test_hard_negative_sequential_invoice(model):
    pr = {"pr_invoice_no": "INV-123", "pr_gstin": "07ABC", "pr_date": "2026-04-12", "pr_taxable": 500}
    gstr2b = {"gstr2b_invoice_no": "INV-124", "gstr2b_gstin": "07ABC", "gstr2b_date": "2026-04-12", "gstr2b_taxable": 500}
    
    prob = predict_prob(model, pr, gstr2b)
    assert prob < 0.50, "Sequential invoice with exact same amount is a hard negative"

def test_hard_negative_wrong_tax_head(model):
    pr = {"pr_invoice_no": "INV-123", "pr_gstin": "07ABC", "pr_date": "2026-04-12", "pr_taxable": 500, "pr_cgst": 45, "pr_sgst": 45, "pr_igst": 0}
    gstr2b = {"gstr2b_invoice_no": "INV-123", "gstr2b_gstin": "07ABC", "gstr2b_date": "2026-04-12", "gstr2b_taxable": 500, "gstr2b_cgst": 0, "gstr2b_sgst": 0, "gstr2b_igst": 90}
    
    prob = predict_prob(model, pr, gstr2b)
    assert prob < 0.50, "Wrong tax head (CGST/SGST vs IGST) is a strict compliance violation"

def test_hard_negative_different_gstin(model):
    pr = {"pr_invoice_no": "INV-123", "pr_gstin": "07ABC", "pr_date": "2026-04-12", "pr_taxable": 500}
    gstr2b = {"gstr2b_invoice_no": "INV-123", "gstr2b_gstin": "08XYZ", "gstr2b_date": "2026-04-12", "gstr2b_taxable": 500}
    
    prob = predict_prob(model, pr, gstr2b)
    assert prob < 0.10, "Different GSTIN means totally different supplier"
