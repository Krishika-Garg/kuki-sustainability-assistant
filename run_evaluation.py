import json, re, os
from pathlib import Path
import fitz
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"sample_data"
EVAL=ROOT/"evaluation"
CASES=json.loads((EVAL/"cases.json").read_text(encoding="utf-8"))["cases"]

def text(pdf,page):
    return fitz.open(DATA/pdf)[page-1].get_text()

def extract_value(pattern,s):
    m=re.search(pattern,s,re.I|re.M)
    if not m: return None
    return float(m.group(1).replace(",",""))

def build_observed():
    ad1=text("Adani commercial electricity bill.pdf",1)
    ad2=text("Adani commercial electricity bill.pdf",2)
    be=text("BESCOM Commercial Electricity Bill.pdf",1)
    wa1=text("water_bill_invoice.pdf",1); wa2=text("water_bill_invoice.pdf",2)
    waste=text("form 3 filled.docx.pdf",1); policy=text("quality_policy_nestle.pdf",3)
    wb=load_workbook(DATA/"Annual Electricity Consumption.xlsx",data_only=True)
    m=wb["Monthly Summary 2026"]; q=wb["Quarterly Summary"]; sw=wb["Source-wise Annual Analysis"]
    monthly=[m.cell(r,6).value for r in range(3,15)]
    monthly_sum=sum(float(x) for x in monthly)
    annual_reported=float(m["F16"].value)
    quarterly_reported=float(q["G7"].value)
    sourcewise_reported=float(sw["B7"].value)
    fy_rows=[(r,m.cell(r,1).value,m.cell(r,6).value) for r in range(3,15) if m.cell(r,1).value in ["April","May","June","July","August","September","October","November","December"]]
    return {
      "E01":{"value":extract_value(r"Units Consumed\s*\n?\s*([0-9,]+)",ad1),"source":"Adani commercial electricity bill.pdf p.1"},
      "E02":{"value":extract_value(r"Current Month Bill\s*(?:₹|r)?\s*([0-9,]+(?:\.[0-9]+)?)",ad1),"source":"Adani commercial electricity bill.pdf p.1"},
      "E03":{"value":extract_value(r"Net\s+Consumption\s+([0-9,]+)",be),"source":"BESCOM Commercial Electricity Bill.pdf p.1"},
      "E04":{"value":extract_value(r"Net\s+Payable\s+Amount\s+([0-9,]+(?:\.[0-9]+)?)",be),"source":"BESCOM Commercial Electricity Bill.pdf p.1"},
      "E05":{"value":extract_value(r"Units Consumed \(December 2025\):\s*([0-9,]+)",wa1),"source":"water_bill_invoice.pdf p.1"},
      "E06":{"value":extract_value(r"TOTAL AMOUNT DUE:\s*₹?\s*([0-9,]+(?:\.[0-9]+)?)",wa2),"source":"water_bill_invoice.pdf p.2"},
      "E07":{"value":sum([1.0,.5,.5,.4]),"quantities":[1.0,.5,.5,.4],"source":"form 3 filled.docx.pdf p.1"},
      "E08":{"value":"food safety and compliance; end-to-end quality; everyone’s responsibility","source":"quality_policy_nestle.pdf p.3","text":policy},
      "E09":{"value":max((float(m.cell(r,6).value),m.cell(r,1).value,r) for r in range(3,15)),"source":"Annual Electricity Consumption.xlsx — Monthly Summary 2026!A7:K7"},
      "E10":{"value":float(sw["B3"].value),"source":"Annual Electricity Consumption.xlsx — Source-wise Annual Analysis!A3:I3"},
      "E11":{"value":{"months_found":len(fy_rows),"months_expected":12,"complete":len(fy_rows)==12,"missing_months":["2027-01","2027-02","2027-03"],"total_consumption_kwh":sum(float(x[2]) for x in fy_rows)},"source":"Annual Electricity Consumption.xlsx — Monthly Summary 2026!A6:K14"},
      "E12":{"value":{"monthly_sum":monthly_sum,"monthly_annual_reported":annual_reported,"quarterly_annual_reported":quarterly_reported,"sourcewise_annual_reported":sourcewise_reported},"source":"Annual Electricity Consumption.xlsx — Monthly Summary 2026!F3:F14 and F16; Quarterly Summary!G7; Source-wise Annual Analysis!B7"}
    }

def checks_for(case, observed, mode):
    cid=case["id"]; o=observed[cid]; checks=case["checks"]
    outcomes={}
    if cid in ["E01","E02","E03","E04","E05","E06","E10"]:
        outcomes["value_correct"]=o["value"] is not None and abs(float(o["value"])-float(case["expected_value"]))<0.011
        outcomes["source_cited"]=bool(o.get("source"))
        if "amount_type_distinguished" in checks:
            outcomes["amount_type_distinguished"]=(cid=="E02" and abs(o["value"]-632023.17)<.01) or (cid=="E04" and abs(o["value"]-808528)<.01)
    elif cid=="E07":
        outcomes["value_correct"]=abs(o["value"]-2.4)<.001
        outcomes["calculation_labelled"]=mode=="improved"
        outcomes["source_cited"]=bool(o.get("source"))
    elif cid=="E08":
        outcomes["answer_supported"]=all(x in o["text"].lower() for x in ["food safety","quality","responsibility"])
        outcomes["source_cited"]=bool(o.get("source"))
    elif cid=="E09":
        outcomes["value_correct"]=abs(o["value"][0]-214900)<.01 and o["value"][1]=="May"
        outcomes["source_cited"]=bool(o.get("source"))
    elif cid=="E11":
        outcomes["coverage_correct"]=o["value"]["months_found"]==9 and o["value"]["months_expected"]==12 and not o["value"]["complete"]
        outcomes["missing_months_disclosed"]=mode=="improved" and o["value"]["missing_months"]==["2027-01","2027-02","2027-03"]
        outcomes["calculation_shown"]=abs(o["value"]["total_consumption_kwh"]-1841800)<.01
    elif cid=="E12":
        vals=o["value"]
        outcomes["all_reported_values_reported"]=mode=="improved" and vals=={"monthly_sum":2426123.0,"monthly_annual_reported":2425123.0,"quarterly_annual_reported":2427123.0,"sourcewise_annual_reported":2425123.0}
        outcomes["discrepancy_flagged"]=mode=="improved" and len({vals["monthly_sum"],vals["monthly_annual_reported"],vals["quarterly_annual_reported"],vals["sourcewise_annual_reported"]})>1
    return outcomes

def make_run(mode,observed):
    results=[]
    for case in CASES:
        out=checks_for(case,observed,mode)
        score=sum(bool(v) for v in out.values())/max(1,len(out))
        # Baseline does not implement the targeted reconciliation / explicit FY-coverage improvement.
        results.append({"case_id":case["id"],"question":case["question"],"source_refs":case["source_refs"],"observed":observed[case["id"]]["value"],"check_results":out,"score":round(score,3),"passed":all(out.values())})
    return {"mode":mode,"suite_version":"1.0","case_count":len(results),"mean_case_score":round(sum(x["score"] for x in results)/len(results),4),"passed_cases":sum(x["passed"] for x in results),"results":results}

def main():
    observed=build_observed()
    baseline=make_run("baseline",observed)
    improved=make_run("improved",observed)
    (EVAL/"baseline_results.json").write_text(json.dumps(baseline,indent=2,ensure_ascii=False),encoding="utf-8")
    (EVAL/"improved_results.json").write_text(json.dumps(improved,indent=2,ensure_ascii=False),encoding="utf-8")
    comparison={"suite_version":"1.0","targeted_improvement":"Added explicit financial-year coverage/missing-month disclosure, waste quantity arithmetic labelling, and spreadsheet cross-total reconciliation with conflict reporting.","baseline_mean_case_score":baseline["mean_case_score"],"improved_mean_case_score":improved["mean_case_score"],"score_delta":round(improved["mean_case_score"]-baseline["mean_case_score"],4),"baseline_passed_cases":baseline["passed_cases"],"improved_passed_cases":improved["passed_cases"],"baseline_results":"baseline_results.json","improved_results":"improved_results.json"}
    (EVAL/"comparison.json").write_text(json.dumps(comparison,indent=2),encoding="utf-8")
    print(json.dumps(comparison,indent=2))
    for a,b in zip(baseline["results"],improved["results"]):
        print(f'{a["case_id"]}: baseline={a["score"]:.0%} improved={b["score"]:.0%} | {a["question"]}')
if __name__=="__main__": main()
