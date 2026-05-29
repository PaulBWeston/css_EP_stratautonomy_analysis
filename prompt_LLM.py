from openai import OpenAI
import json
from pathlib import Path
import pandas as pd
import json
import time
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

BASE_DIR = Path.cwd()
# BASE_DIR = Path(__file__).resolve().parents[1]
codebook = (BASE_DIR / "prompt" / "categories.md").read_text(encoding="utf-8")
instructions = (BASE_DIR / "prompt" / "instructions.md").read_text(encoding="utf-8")

## FOR FULL RUN
# df = pd.read_csv("europarl_speeches_2024-2025.csv", engine="python")

# #shuffle the dataframe to get random sample
# random_seed = 42
# df = df.sample(frac=1, random_state=random_seed).reset_index(drop=True)

output_file = "css_scored_samples_with_llm_vrandom.xlsx"

if Path(output_file).exists():
    df = pd.read_excel(output_file)
else:
    df = pd.read_csv("europarl_speeches_2024-2025.csv", engine="python")
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)


# len(df) # 29674


### FOR TESTING
# df = pd.read_excel("css_scored_samples.xlsx")

### Construct Passages to put in prompt
batch_size = 5
start_batch = 2302 * batch_size
for i in range(start_batch, len(df), batch_size):
    batch = df.iloc[i:i+batch_size]

    batch_text = ""

    for _, row in batch.iterrows():
        batch_text += f"""
    PASSAGE_ID: {row['speech_event_id']} 
    TEXT:
    {row['text']}

    """

    # print(batch_text)

    # Combine for full prompt
    prompt = f"""
    {instructions}

    {codebook}

    PASSAGES

    {batch_text}
    """

    # print(prompt)

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a precise political text classifier. Return valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    result_json = json.loads(response.choices[0].message.content)

    for result in result_json["results"]:
        speech_id = result["passage_id"]
        scores = result["scores"]

        row_mask = df["speech_event_id"].astype(str) == str(speech_id)

        for subcategory, values in scores.items():
            score_col = f"{subcategory}_score"
            # evidence_col = f"{subcategory}_evidence"

            df.loc[row_mask, score_col] = values["score"]
            # df.loc[row_mask, evidence_col] = values["evidence"]

    df.to_excel("css_scored_samples_with_llm_vrandom.xlsx", index=False)

    print(f"Finished batch {i // batch_size + 1}")
    time.sleep(0.5)