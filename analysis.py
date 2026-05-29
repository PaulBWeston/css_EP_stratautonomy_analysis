### ANALYSIS

# Speech data is retrieved in 
#   europarl_speeches.py
# LLM scoring is completed in
#   prompt_LLM.py
# speaker data is retrieved in
#   get_speaker_data.py



##### Clean main dataset

import pandas as pd

# Load partial scored file
df = pd.read_excel("css_scored_samples_with_llm_vpartial.xlsx")

# Load randomized sample scored file
df = pd.read_excel("css_scored_samples_with_llm_vrandom.xlsx")

# Identify score columns
score_cols = [col for col in df.columns if col.endswith("_score")]

print("Rows before cleaning:", len(df)) # Rows before cleaning: 29674
print("Score columns found:", len(score_cols)) # Score columns found: 18

# Keep only rows where at least one score column is non-null
df_scored = df[df[score_cols].notna().any(axis=1)].copy()

print("Rows with at least one LLM score:", len(df_scored)) # Rows with at least one LLM score: 16320

# Deduplicate
# Prefer speech_event_id if available, otherwise use speech_id/doc_id/text combo
if "speech_event_id" in df_scored.columns:
    df_scored = df_scored.drop_duplicates(subset=["speech_event_id"])
elif "speech_id" in df_scored.columns:
    df_scored = df_scored.drop_duplicates(subset=["speech_id"])
else:
    df_scored = df_scored.drop_duplicates(subset=["doc_id", "text"])

print("Rows after deduplication:", len(df_scored)) # Rows after deduplication: 1389

# Optional: remove evidence columns if present
evidence_cols = [col for col in df_scored.columns if col.endswith("_evidence")]
df_scored = df_scored.drop(columns=evidence_cols, errors="ignore")

# Save cleaned file
df_scored.to_excel("css_scored_samples_with_llm_vrandom_cleaned.xlsx", index=False)

print("Saved cleaned dataset.")


#### Look at speaker reference dataset
## Partial run:
# df_cleaned = pd.read_excel("css_scored_samples_with_llm_vpartial_cleaned.xlsx")
# df_speaker = pd.read_csv("europarl_speakers_small_vfinal.csv")

# Full random sample:
df_cleaned = pd.read_excel("css_scored_samples_with_llm_vrandom_cleaned.xlsx")
df_speaker = pd.read_csv("europarl_speakers_random_v1_wlookup.csv")


print(df_speaker.head())
print(df_cleaned.head())

#### Analysis

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.pyplot as plt
import numpy as np

def plot_heatmap(data, title, colorbar_label, fmt=".1f", figsize=(18, 8)):
    # row sample sizes
    party_counts = df.groupby("EP_party").size()
    y_labels = [
        f"{party} (n={int(party_counts.get(party, 0))})"
        for party in data.index
    ]

    fig, ax = plt.subplots(figsize=figsize)

    im = ax.imshow(data, aspect="auto")

    ax.set_xticks(np.arange(len(data.columns)))
    ax.set_xticklabels(
        data.columns,
        rotation=45,
        ha="right",
        rotation_mode="anchor"
    )

    ax.set_yticks(np.arange(len(data.index)))
    ax.set_yticklabels(y_labels)

    # numbers in cells
    for r in range(data.shape[0]):
        for c in range(data.shape[1]):
            value = data.iloc[r, c]
            if pd.notna(value):
                ax.text(
                    c, r,
                    format(value, fmt),
                    ha="center",
                    va="center",
                    fontsize=8
                )

    plt.colorbar(im, ax=ax, label=colorbar_label)
    ax.set_title(title, fontsize=14, pad=16)

    plt.subplots_adjust(left=0.22, bottom=0.32, right=0.95, top=0.90)
    plt.show()


def plot_heatmap(data, title, colorbar_label, note=None, fmt=".1f", figsize=(18, 8)):
    party_counts = df.groupby("EP_party").size()
    y_labels = [f"{party} (n={int(party_counts.get(party, 0))})" for party in data.index]

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(data, aspect="auto")

    ax.set_xticks(np.arange(len(data.columns)))
    ax.set_xticklabels(data.columns, rotation=45, ha="right", rotation_mode="anchor")

    ax.set_yticks(np.arange(len(data.index)))
    ax.set_yticklabels(y_labels)

    for r in range(data.shape[0]):
        for c in range(data.shape[1]):
            value = data.iloc[r, c]
            if pd.notna(value):
                ax.text(c, r, format(value, fmt), ha="center", va="center", fontsize=8)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(
        colorbar_label,
        rotation=270,
        labelpad=28
)
    ax.set_title(title, fontsize=15, pad=16)

    if note:
        ax.set_xlabel(note, labelpad=18)

    plt.subplots_adjust(left=0.24, bottom=0.34, right=0.95, top=0.90)
    plt.show()

# ----------------------------
# 1. Merge speaker info
# ----------------------------

# Keep only relevant speaker columns
speaker_lookup = df_speaker[
    ["speaker_id", "ep_party"]
].rename(columns={
    "ep_party": "EP_party"
})

# Make sure IDs match types
df_cleaned["speaker_id"] = df_cleaned["speaker_id"].astype(str)
speaker_lookup["speaker_id"] = speaker_lookup["speaker_id"].astype(str)

# Merge
df = df_cleaned.merge(
    speaker_lookup,
    on="speaker_id",
    how="left"
)

# After merge
print(df["EP_party"].isna().mean())
print(df["EP_party"].isna().sum())

# Inspect unmatched speaker IDs
unmatched = df[df["EP_party"].isna()][["speaker_id", "speaker_id", "text"]].head(20)
print(unmatched)

# WE FILTER OUT THOSE SPEAKERS WITHOUT PARTIES
# THESE ARE MAINLY INSTITUTIONAL SPEAKERS, E.G.
# Member of the Commission
# President-in-Office of the Council
# President
# Vice-President of the Commission
df = df[df["EP_party"].notna()].copy()

len(df) # 15332

df.head(10)
df.columns

print(df["EP_party"].value_counts(dropna=False))

df.loc[df["EP_party"].isna(), "group_id"].value_counts(dropna=False).head(30)

# ----------------------------
# 2. Identify score columns
# ----------------------------

score_cols = [
    col for col in df.columns
    if col.endswith("_score")
]

print(score_cols)

# Cleaner labels for plotting
pretty_names = {
    col: col.replace("_score", "").replace("_", " ")
    for col in score_cols
}

# ----------------------------
# 3. Heatmap 1: Mean stance
# ----------------------------

stance_df = df.copy()

# Replace -1 with NaN
# (irrelevant speeches excluded)
stance_df[score_cols] = (
    stance_df[score_cols]
    .replace(-1, np.nan)
)

mean_stance = (
    stance_df
    .groupby("EP_party")[score_cols]
    .mean()
)

# Rename columns nicely
mean_stance.columns = [
    pretty_names[c]
    for c in mean_stance.columns
]

party_order = [
    "The Left",
    "Greens/EFA",
    "S&D",
    "Renew Europe",
    "EPP",
    "ECR",
    "ID",
    "PfE",
    "ESN",
    "Non-attached"
]


mean_stance = mean_stance.reindex(party_order)
# mean_salience = mean_salience.reindex(party_order)

# Plot



# plot_heatmap(
#     mean_stance,
#     "Party Group × Strategic Autonomy Stance",
#     "Mean stance score",
#     fmt=".2f"
# )

plot_heatmap(
    mean_stance,
    "Mean Strategic Autonomy Position by European Parliament Party Group",
    "Mean stance score",
    note="Stance scale: 1 = strong opposition, 3 = neutral/descriptive, 5 = strong support",
    fmt=".2f"
)

# ----------------------------
# 4. Heatmap 2: Topic salience
# ----------------------------

salience_df = df.copy()

# Mentioned if score != -1
for col in score_cols:
    salience_df[col] = (
        salience_df[col] != -1
    ).astype(int)

mean_salience = (
    salience_df
    .groupby("EP_party")[score_cols]
    .mean()
)

# Convert to percentages
mean_salience = mean_salience * 100

mean_salience.columns = [
    pretty_names[c]
    for c in mean_salience.columns
]


mean_salience = mean_salience.reindex(party_order)

plot_heatmap(
    mean_salience,
    "Party Group × Strategic Autonomy Topic Salience",
    "% speeches mentioning topic",
    fmt=".0f"
)

plot_heatmap(
    mean_salience,
    "Strategic Autonomy Issue Salience by European Parliament Party Group",
    "Speeches mentioning subcategory (%)",
    note="Salience is measured as the percentage of speeches with a non-irrelevant score.",
    fmt=".0f"
)



import matplotlib.pyplot as plt
import pandas as pd

# -----------------------------
# Categories to visualize
# -----------------------------

plot_categories = {
    "NATO_cooperation_score": "NATO Cooperation",
    # "EU_defence_capacity_score": "EU Defence Capacity",
    "De-militarization_score": "De-militarization",
    "Pro_free_trade_score": "Free Trade",
    "Protectionism_score": "Protectionism",
    "EU_values_score": "EU Values",
    "Digital_innovation_and_AI_score": "Digital Innovation" 

}


# -----------------------------
# Make plots
# -----------------------------

score_cols = [
    col for col in df.columns
    if col.endswith("_score")
]

print(score_cols)

from pathlib import Path

output_dir = Path("box_jitter_plots_vrandom")
output_dir.mkdir(exist_ok=True)

for col, pretty_name in plot_categories.items():

    temp = df.copy()

    # Exclude irrelevant speeches
    temp = temp[temp[col] != -1]

    # Drop missing parties
    temp = temp[temp["EP_party"].notna()]

    # Enforce ideological order
    temp["EP_party"] = pd.Categorical(
        temp["EP_party"],
        categories=party_order,
        ordered=True
    )

    temp = temp.sort_values("EP_party")

    fig, ax = plt.subplots(figsize=(10, 6))

    temp.boxplot(
        column=col,
        by="EP_party",
        ax=ax,
        grid=False
    )

    ax.set_title(
        f"Distribution of {pretty_name} Scores by EP Party Group",
        fontsize=14
    )

    ax.set_xlabel("European Parliament Party Group")
    ax.set_ylabel("Score")

    ax.set_ylim(0.5, 5.5)
    ax.set_yticks([1,2,3,4,5])

    plt.suptitle("")  # remove pandas default title

    plt.xticks(rotation=35, ha="right")

    plt.tight_layout()
    plt.show()


#### JITTER PLOTS

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plot_categories = {
    "NATO_cooperation_score": "NATO Cooperation",
    # "EU_defence_capacity_score": "EU Defence Capacity",
    "De-militarization_score": "De-militarization",
    "Pro_free_trade_score": "Free Trade",
    "Protectionism_score": "Protectionism",
    "EU_values_score": "EU Values",
    "Digital_innovation_and_AI_score": "Digital Innovation" 

}


for col, pretty_name in plot_categories.items():

    temp = df.copy()

    # Exclude irrelevant speeches
    temp = temp[temp[col] != -1]

    temp = temp[temp["EP_party"].notna()]

    # Ideological order
    temp["EP_party"] = pd.Categorical(
        temp["EP_party"],
        categories=party_order,
        ordered=True
    )

    temp = temp.sort_values("EP_party")

    # Sample sizes
    counts = temp.groupby("EP_party").size()

    fig, ax = plt.subplots(figsize=(12, 6))

    # Boxplot
    temp.boxplot(
        column=col,
        by="EP_party",
        ax=ax,
        grid=False,
        showfliers=False
    )

    # Jittered dots
    for i, party in enumerate(party_order, start=1):

        party_data = temp[
            temp["EP_party"] == party
        ][col]

        if len(party_data) == 0:
            continue

        x_jitter = np.random.normal(
            loc=i,
            scale=0.06,
            size=len(party_data)
        )

        ax.scatter(
            x_jitter,
            party_data,
            alpha=0.35,
            s=18
        )

    # Sample sizes in x labels
    labels = [
        f"{party}\n(n={int(counts.get(party,0))})"
        for party in party_order
    ]

    ax.set_xticklabels(
        labels,
        rotation=35,
        ha="right"
    )

    ax.set_title(
        f"Distribution of {pretty_name} Scores by EP Party Group",
        fontsize=14
    )

    ax.set_xlabel(
        "European Parliament Party Group"
    )

    ax.set_ylabel("Score")

    ax.set_ylim(0.5, 5.5)
    ax.set_yticks([1,2,3,4,5])

    plt.suptitle("")
    plt.tight_layout()

    filename = col.replace("_score", "").lower() + "_box_jitter.png"
    plt.savefig(output_dir / filename, dpi=300, bbox_inches="tight")

    plt.show()



############################
###### REGRESSION
    ########################


import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

output_dir = Path("mention_stance_plots")
output_dir.mkdir(exist_ok=True)

key_categories = {
    "NATO_cooperation_score": "NATO Cooperation",
    # "EU_defence_capacity_score": "EU Defence Capacity",
    "De-militarization_score": "De-militarization",
    "Pro_free_trade_score": "Free Trade",
    "Protectionism_score": "Protectionism",
    "EU_values_score": "EU Values",
    "Digital_innovation_and_AI_score": "Digital Innovation" 
}

party_order = [
    "The Left",
    "Greens/EFA",
    "S&D",
    "Renew Europe",
    "EPP",
    "ECR",
    "ID",
    "Non-attached"
]


for col, pretty_name in key_categories.items():

    temp = df[df["EP_party"].notna()].copy()

    temp["mentioned"] = (temp[col] != -1).astype(int)

    summary = (
        temp.groupby("EP_party")["mentioned"]
        .mean()
        .reindex(party_order)
        * 100
    )

    counts = (
        temp.groupby("EP_party")["mentioned"]
        .size()
        .reindex(party_order)
    )

    labels = [
        f"{party}\n(n={int(counts.get(party, 0))})"
        for party in party_order
    ]

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(labels, summary)

    ax.set_title(
        f"Mention Rate of {pretty_name} by EP Party Group",
        fontsize=14
    )
    ax.set_ylabel("Speeches mentioning subcategory (%)")
    ax.set_xlabel("European Parliament Party Group")
    ax.set_ylim(0, 100)

    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()

    filename = col.replace("_score", "").lower() + "_mention_rate.png"
    plt.savefig(output_dir / filename, dpi=300, bbox_inches="tight")

    plt.show()





from statsmodels.miscmodels.ordinal_model import OrderedModel

temp = df[
    (df["NATO_cooperation_score"] != -1) &
    (df["EP_party"].notna())
].copy()

party_dummies = pd.get_dummies(
    temp["EP_party"],
    drop_first=True
)

X = party_dummies

y = temp["NATO_cooperation_score"]

model = OrderedModel(
    y,
    X,
    distr="logit"
)

result = model.fit()

print(result.summary())


summary_df = pd.DataFrame({
    "Party": result.params.index,
    "Coefficient": result.params.values,
    "P_value": result.pvalues.values
})

# Remove threshold rows
summary_df = summary_df[
    ~summary_df["Party"].str.contains("/")
]

# Add significance stars
def stars(p):
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    return ""

summary_df["Sig"] = summary_df["P_value"].apply(stars)

summary_df = summary_df.sort_values(
    "Coefficient",
    ascending=False
)

print(summary_df)




##### REGRESSSION TRY NYMBER 2

score_cols = [
    col for col in df.columns
    if col.endswith("_score")
]

print(score_cols)

for score_col in score_cols:
    temp = df.copy()

    temp[score_col] = pd.to_numeric(temp[score_col], errors="coerce")

    temp = temp[
        temp["EP_party"].notna() &
        temp[score_col].notna() &
        (temp[score_col] != -1)
    ].copy()

    print(score_col, f"usable stance rows = {len(temp)}")

len(df) # 15332
len(temp) # 6


import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.miscmodels.ordinal_model import OrderedModel
from patsy import dmatrix
import matplotlib.pyplot as plt

output_dir = Path("ordinal_regression_results")
output_dir.mkdir(exist_ok=True)

table_output_dir = output_dir / "tables"
table_output_dir.mkdir(exist_ok=True)

all_results = []

party_order = [
    "The Left",
    "Greens/EFA",
    "S&D",
    "Renew Europe",
    "EPP",
    "ECR",
    "ID",
    "PfE",
    "ESN",
    "Non-attached"
]

party_counts = df.groupby("EP_party").size()
print(party_counts)
print(sorted(df["EP_party"].dropna().unique()))

for score_col in score_cols:

    print(f"Running: {score_col}")

    temp = df.copy()

    temp[score_col] = pd.to_numeric(temp[score_col], errors="coerce")

    temp = temp[
        temp["EP_party"].notna() &
        temp[score_col].notna() &
        (temp[score_col] != -1)
    ].copy()

    temp[score_col] = temp[score_col].astype(int)

    print(f"Usable stance rows: {len(temp)}")

    if len(temp) < 100:
        print(f"Skipping {score_col}: too few stance rows")
        continue

    # Drop tiny groups if desired
    temp = temp[
        temp["EP_party"].isin(party_order)
    ]

    # ordered party factor
    temp["EP_party"] = pd.Categorical(
        temp["EP_party"],
        categories=party_order
    )

    # ----------------------------------
    # EFFECT CODING (grand mean)
    # ----------------------------------

    X = dmatrix(
        "C(EP_party, Sum)",
        temp,
        return_type="dataframe"
    )

    # remove intercept
    X = X.drop(columns=["Intercept"])

    y = temp[score_col]

    try:

        model = OrderedModel(
            y,
            X,
            distr="logit"
        )

        result = model.fit(method="bfgs", disp=False)

        params = result.params
        pvals = result.pvalues
        std_err = result.bse
        conf = result.conf_int()

        result_df = pd.DataFrame({
            "subcategory": score_col,
            "party": params.index,
            "coef": params.values,
            "std_err": std_err.values,
            "z": result.tvalues,
            "p_value": pvals.values,
            "ci_lower": conf[0].values,
            "ci_upper": conf[1].values
        })

        # remove thresholds
        # result_df = result_df[
        #     ~result_df["party"].str.contains("/")
        # ]

        result_df = result_df[
           ~result_df["party"].str.match(r"^\d+/\d+$")
        ]

        # clean party names
        result_df["party"] = (
            result_df["party"]
            .str.replace(r"C\(EP_party, Sum\)\[S\.", "", regex=True)
            .str.replace("]", "", regex=False)
        )

        # odds ratios
        result_df["odds_ratio"] = np.exp(result_df["coef"])
        result_df["or_lower"] = np.exp(result_df["ci_lower"])
        result_df["or_upper"] = np.exp(result_df["ci_upper"])

        all_results.append(result_df)

        ####SAVE TABLE
        pretty_name = (
        score_col
        .replace("_score", "")
        .replace("_", " ")
        )

        display_table = result_df[
            ["party", "coef", "std_err", "z", "p_value"]
        ].copy()

        display_table.columns = [
            "Variable",
            "Coef",
            "Std Err",
            "z",
            "p-value"
        ]

        pd.set_option("display.float_format", "{:.12f}".format)

        # print(display_table)

        # display_table = display_table.round(3)

        display_table.to_excel(
            table_output_dir /
            f"{score_col.replace('_score','').lower()}_regression_table.xlsx",
            index=False
        )

        print("\n")
        print(pretty_name.upper())
        print(display_table)
        print("\n")


        # ----------------------------------
        # Odds ratio plot
        # ----------------------------------

        plot_df = result_df.sort_values("coef")

        fig, ax = plt.subplots(figsize=(8, 6))

        ax.errorbar(
            plot_df["odds_ratio"],
            plot_df["party"],
            xerr=[
                plot_df["odds_ratio"] - plot_df["or_lower"],
                plot_df["or_upper"] - plot_df["odds_ratio"]
            ],
            fmt="o"
        )

        ax.axvline(
            1,
            linestyle="--"
        )

        pretty_name = (
            score_col
            .replace("_score", "")
            .replace("_", " ")
        )

        ax.set_title(
            f"Ordinal Regression: {pretty_name}"
        )

        ax.set_xlabel(
            "Odds Ratio (relative to EP mean)"
        )

        plt.tight_layout()

        filename = (
            score_col
            .replace("_score", "")
            .lower()
            + "_odds_ratio_plot.png"
        )

        plt.savefig(
            output_dir / filename,
            dpi=300,
            bbox_inches="tight"
        )

        plt.close()

    except Exception as e:
        print(f"Failed {score_col}: {e}")