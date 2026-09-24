"""
Script to generate answering files for all 20 Benchmark Cases as required by the Hackathon.
Reads benchmark_cases.json and uses the agent to generate full records.
"""
import json
import os
from pathlib import Path
from agent.agent import create_agent, run_investigation

INPUT_DIR = Path('cases/inputs')
OUTPUT_DIR = Path('cases/outputs')

def main():
    print("="*60)
    print("GENERATING 20 BENCHMARK CASE ANSWER FILES")
    print("="*60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(INPUT_DIR / 'benchmark_cases.json', 'r') as f:
        cases = json.load(f)
        
    agent = create_agent()
    
    for case in cases:
        case_id = case['case_id']
        print(f"Processing {case_id}...")
        
        result = run_investigation(case, executor=agent)
        
        # Write to txt answer file
        file_path = OUTPUT_DIR / f"{case_id}_Answer.txt"
        with open(file_path, 'w', encoding='utf-8') as out:
            out.write(f"FRAUD INVESTIGATION RECORD: {case_id}\n")
            out.write(f"Account: {case['account_id']}\n")
            out.write(f"Transaction: {case['transaction_id']}\n")
            out.write(f"Trigger: {case['description']}\n")
            out.write("="*60 + "\n\n")
            out.write(result)
            out.write("\n\n" + "="*60 + "\n")
            out.write("Case Status: PENDING ANALYST REVIEW\n")
            
        print(f"  ✓ Saved to {file_path.name}")
        
    print("\nAll 20 case files generated in cases/outputs/")

if __name__ == '__main__':
    main()
