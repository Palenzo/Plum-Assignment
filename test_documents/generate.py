"""Generate realistic OPD prescription + bill documents for manual testing.

Produces text-layer PDFs (read cleanly by the ingestion pipeline) plus one PNG
to exercise the image-OCR path. Each case maps to one of the provided test cases
and drives a specific adjudication outcome.

Run:  ../backend/.venv/Scripts/python.exe generate.py
"""
from __future__ import annotations

import os

import fitz  # PyMuPDF

HERE = os.path.dirname(os.path.abspath(__file__))

INK = (0.12, 0.12, 0.14)
MUTED = (0.42, 0.45, 0.5)
RULE = (0.8, 0.82, 0.85)
ACCENT = (0.16, 0.45, 0.55)

CASES = [
    {
        "dir": "01_approved_consultation",
        "clinic": "City Care Polyclinic", "addr": "12 MG Road, Bengaluru 560001",
        "gstin": "29ABCDE1234F1Z5",
        "doctor": "Dr. Anand Sharma", "qual": "MBBS, MD (General Medicine)",
        "reg": "KA/45678/2015",
        "patient": "Rajesh Kumar", "age": "34", "sex": "M", "date": "01-Nov-2024",
        "diagnosis": "Viral fever",
        "rx": ["Tab. Paracetamol 650mg  —  1 tablet thrice daily x 5 days",
               "Tab. Vitamin C 500mg  —  1 tablet once daily x 7 days"],
        "advice": "Adequate fluids and rest. Review if fever persists beyond 3 days.",
        "tests": ["CBC", "Dengue NS1 Antigen"],
        "bill": [("Consultation Fee", 1000), ("Diagnostic Tests - CBC, Dengue NS1", 500)],
        "expected": "APPROVED  ~Rs.1,350  (10% co-pay of Rs.150)",
        "form": "claim_amount = 1500   |   no hospital / join date",
    },
    {
        "dir": "02_partial_dental_cosmetic",
        "clinic": "SmileWell Dental Care", "addr": "45 Linking Road, Mumbai 400050",
        "gstin": "27PQRST5678U1Z2",
        "doctor": "Dr. Priti Patel", "qual": "BDS, MDS (Endodontics)",
        "reg": "MH/23456/2018",
        "patient": "Priya Singh", "age": "29", "sex": "F", "date": "15-Oct-2024",
        "diagnosis": "Tooth decay (46) requiring root canal treatment",
        "rx": ["Cap. Amoxicillin 500mg  —  1 capsule thrice daily x 5 days",
               "Tab. Ibuprofen 400mg  —  as needed for pain"],
        "advice": "Root canal completed. Whitening done on patient request (elective).",
        "procedures": ["Root canal treatment (46)", "Teeth whitening (cosmetic)"],
        "bill": [("Root Canal Treatment", 8000), ("Teeth Whitening", 4000)],
        "expected": "PARTIAL  ~Rs.8,000  (Teeth Whitening stripped as cosmetic)",
        "form": "claim_amount = 12000   |   no hospital / join date",
    },
    {
        "dir": "03_rejected_mri_no_preauth",
        "clinic": "Sunrise Diagnostics & Clinic", "addr": "8 Banjara Hills, Hyderabad 500034",
        "gstin": "36LMNOP9012Q1Z7",
        "doctor": "Dr. Venkat Rao", "qual": "MBBS, MS (Orthopaedics)",
        "reg": "AP/67890/2017",
        "patient": "Suresh Patil", "age": "47", "sex": "M", "date": "02-Nov-2024",
        "diagnosis": "Suspected lumbar disc herniation (L4-L5)",
        "rx": ["Tab. Aceclofenac 100mg  —  twice daily x 7 days"],
        "advice": "MRI Lumbar Spine advised for confirmation before further management.",
        "tests": ["MRI Lumbar Spine"],
        "bill": [("MRI Scan - Lumbar Spine", 15000)],
        "expected": "REJECTED  PRE_AUTH_MISSING  (MRI/CT need pre-authorisation)",
        "form": "claim_amount = 15000   |   no hospital / join date",
    },
    {
        "dir": "04_rejected_excluded_weightloss",
        "clinic": "Wellness Plus Clinic", "addr": "21 Park Street, Kolkata 700016",
        "gstin": "19GHIJK3456L1Z9",
        "doctor": "Dr. Sandip Banerjee", "qual": "MBBS, DNB (Endocrinology)",
        "reg": "WB/34567/2015",
        "patient": "Anita Desai", "age": "41", "sex": "F", "date": "18-Oct-2024",
        "diagnosis": "Obesity - BMI 35",
        "rx": ["Lifestyle counselling", "Supervised diet plan"],
        "advice": "Bariatric consultation and structured diet plan for weight loss.",
        "procedures": ["Bariatric consultation", "Diet plan (weight loss)"],
        "bill": [("Bariatric Consultation", 3000), ("Diet Plan - Weight Loss Programme", 5000)],
        "expected": "REJECTED  SERVICE_NOT_COVERED  (weight-loss treatments excluded)",
        "form": "claim_amount = 8000   |   no hospital / join date",
    },
    {
        "dir": "05_approved_ayurveda",
        "clinic": "Kerala Ayurveda Kendra", "addr": "3 Marine Drive, Kochi 682031",
        "gstin": "32MNOPQ7890R1Z3",
        "doctor": "Vaidya Krishnan Nair", "qual": "BAMS (Ayurveda)",
        "reg": "AYUR/KL/2345/2019",
        "patient": "Kavita Nair", "age": "52", "sex": "F", "date": "28-Oct-2024",
        "diagnosis": "Chronic joint pain (osteoarthritis, both knees)",
        "rx": ["Maharasnadi Kashayam  —  15ml twice daily before food",
               "Yogaraja Guggulu  —  1 tablet twice daily"],
        "advice": "Panchakarma therapy course advised. Warm fomentation at home.",
        "procedures": ["Panchakarma therapy"],
        "bill": [("Consultation Fee", 1000), ("Panchakarma Therapy Charges", 3000)],
        "expected": "APPROVED  ~Rs.4,000  (alternative medicine, within sub-limit)",
        "form": "claim_amount = 4000   |   no hospital / join date",
    },
    {
        "dir": "06_approved_network_cashless",
        "clinic": "Apollo Hospitals - OPD", "addr": "21 Greams Lane, Chennai 600006",
        "gstin": "33STUVW1234X1Z1",
        "doctor": "Dr. Lakshmi Iyer", "qual": "MBBS, MD (Pulmonology)",
        "reg": "TN/56789/2013",
        "patient": "Deepak Shah", "age": "38", "sex": "M", "date": "03-Nov-2024",
        "diagnosis": "Acute bronchitis",
        "rx": ["Tab. Azithromycin 500mg  —  1 tablet once daily x 3 days",
               "Salbutamol inhaler  —  2 puffs as needed"],
        "advice": "Steam inhalation. Avoid cold exposure. Review after 5 days.",
        "bill": [("Consultation Fee", 1500), ("Medicines - Antibiotics, Bronchodilator", 3000)],
        "expected": "APPROVED  ~Rs.3,600  (Rs.900 network discount, cashless)",
        "form": "claim_amount = 4500   |   hospital = Apollo Hospitals   |   cashless = ON",
    },
]


def _header(page, c, kind: str) -> float:
    page.insert_text((50, 60), c["clinic"], fontsize=18, fontname="hebo", color=ACCENT)
    page.insert_text((50, 78), c["addr"], fontsize=9, fontname="helv", color=MUTED)
    page.insert_text((50, 90), f"GSTIN: {c['gstin']}", fontsize=8, fontname="helv", color=MUTED)
    page.draw_line((50, 102), (545, 102), color=RULE, width=1)
    label = "PRESCRIPTION" if kind == "rx" else "TAX INVOICE / BILL"
    page.insert_text((50, 124), label, fontsize=13, fontname="hebo", color=INK)
    return 150.0


def _line(page, y, label, value, bold_value=False):
    page.insert_text((50, y), label, fontsize=10, fontname="helv", color=MUTED)
    page.insert_text((175, y), value, fontsize=10,
                     fontname="hebo" if bold_value else "helv", color=INK)
    return y + 20


def make_prescription(c) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page()
    y = _header(page, c, "rx")
    page.insert_text((50, y), f"Dr. {c['doctor'].replace('Dr. ', '').replace('Vaidya ', '')}"
                     if False else c["doctor"], fontsize=11, fontname="hebo", color=INK)
    page.insert_text((50, y + 14), c["qual"], fontsize=9, fontname="helv", color=MUTED)
    page.insert_text((50, y + 27), f"Reg. No.: {c['reg']}", fontsize=9, fontname="helv", color=INK)
    page.draw_line((50, y + 40), (545, y + 40), color=RULE, width=0.7)
    y += 62
    y = _line(page, y, "Patient Name", c["patient"], bold_value=True)
    y = _line(page, y, "Age / Sex", f"{c['age']} / {c['sex']}")
    y = _line(page, y, "Date", c["date"])
    y += 6
    y = _line(page, y, "Diagnosis", c["diagnosis"], bold_value=True)
    y += 8
    if c.get("procedures"):
        page.insert_text((50, y), "Procedures", fontsize=10, fontname="helv", color=MUTED)
        for p in c["procedures"]:
            page.insert_text((175, y), f"- {p}", fontsize=10, fontname="helv", color=INK)
            y += 16
        y += 6
    if c.get("tests"):
        page.insert_text((50, y), "Tests advised", fontsize=10, fontname="helv", color=MUTED)
        for t in c["tests"]:
            page.insert_text((175, y), f"- {t}", fontsize=10, fontname="helv", color=INK)
            y += 16
        y += 6
    page.insert_text((50, y), "Rx", fontsize=12, fontname="hebo", color=ACCENT)
    y += 20
    for item in c["rx"]:
        page.insert_text((60, y), f"- {item}", fontsize=10, fontname="helv", color=INK)
        y += 18
    y += 10
    page.insert_text((50, y), "Advice:", fontsize=10, fontname="hebo", color=INK)
    page.insert_text((100, y), c["advice"], fontsize=10, fontname="helv", color=INK)
    y += 50
    page.insert_text((360, y), "_______________________", fontsize=10, color=MUTED)
    page.insert_text((390, y + 16), f"{c['doctor']}", fontsize=9, fontname="hebo", color=INK)
    page.insert_text((390, y + 28), "Signature & Stamp", fontsize=8, fontname="helv", color=MUTED)
    return doc


def make_bill(c) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page()
    y = _header(page, c, "bill")
    y = _line(page, y, "Invoice No.", f"INV-{c['dir'][:2]}-2024-0{c['dir'][1]}")
    y = _line(page, y, "Patient Name", c["patient"], bold_value=True)
    y = _line(page, y, "Date", c["date"])
    y += 10
    # Table header
    page.draw_line((50, y), (545, y), color=RULE, width=0.7)
    y += 16
    page.insert_text((55, y), "Description", fontsize=10, fontname="hebo", color=INK)
    page.insert_text((470, y), "Amount (Rs.)", fontsize=10, fontname="hebo", color=INK)
    y += 8
    page.draw_line((50, y), (545, y), color=RULE, width=0.7)
    y += 20
    total = 0
    for name, amount in c["bill"]:
        page.insert_text((55, y), name, fontsize=10, fontname="helv", color=INK)
        page.insert_text((485, y), f"{amount:,.2f}", fontsize=10, fontname="helv", color=INK)
        total += amount
        y += 20
    page.draw_line((50, y), (545, y), color=RULE, width=0.7)
    y += 20
    page.insert_text((55, y), "TOTAL", fontsize=11, fontname="hebo", color=INK)
    page.insert_text((485, y), f"{total:,.2f}", fontsize=11, fontname="hebo", color=ACCENT)
    y += 50
    page.insert_text((50, y), "This is a computer-generated invoice.", fontsize=8,
                     fontname="helv", color=MUTED)
    return doc


def main() -> None:
    made = []
    for c in CASES:
        folder = os.path.join(HERE, c["dir"])
        os.makedirs(folder, exist_ok=True)
        rx = make_prescription(c)
        rx.save(os.path.join(folder, "prescription.pdf"))
        bill = make_bill(c)
        bill.save(os.path.join(folder, "bill.pdf"))
        made.append(c["dir"])
        rx.close()
        bill.close()

    # One PNG to exercise the image-OCR path (a "photographed" prescription).
    png_case = CASES[0]
    rx = make_prescription(png_case)
    pix = rx[0].get_pixmap(dpi=200)
    pix.save(os.path.join(HERE, png_case["dir"], "prescription.png"))
    rx.close()

    print("Generated documents for:")
    for d in made:
        print(f"  - {d}/  (prescription.pdf + bill.pdf)")
    print(f"  + {png_case['dir']}/prescription.png  (image-OCR sample)")


if __name__ == "__main__":
    main()
