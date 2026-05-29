Given these categories, sub-categories, and definitions, how would you categorize the following text according to the following scale?

Where
-1 means the text is irrelevant for the category
1 is strongly against
2 is against
3 is neutral
4 is support
5 is strong support

GENERAL RULES:
- Score every subcategory.
- Use -1 if irrelevant/not discussed.
- Use definitions and scoring guides strictly.
- Score stance, not topic salience.
- Criticism of insufficient policy often indicates support for stronger policy.
- Use 3 only when the subcategory is discussed but the stance is neutral, balanced, or unclear.
- Do not invent a stance if the passage is merely silent.
- Treat each subcategory independently.
- Return valid JSON only.
- Do not include markdown, commentary, or explanations outside the JSON.

IMPORTANT:
Score based on the SPEAKER'S POSITION toward the subcategory.

CRITICISM RULE:
Criticism of the EU for failing to uphold
a value or policy goal generally indicates
SUPPORT for that value or policy goal,
not opposition.

Example:
"Europe has failed to defend democracy"
→ support for democracy / EU values

Output format:
{
  "results": [
    {
      "passage_id": "<id>",
      "scores": {
        "<subcategory_id>": {
          "score": <integer>
        }
      }
    }
  ]
}