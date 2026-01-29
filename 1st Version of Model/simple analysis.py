# %%
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind

# %%
# Load the CSV file
file_path = "/Users/mj/Downloads/UpdatedDataFile.csv"
df = pd.read_csv(file_path)

# %%
#  Convert date columns
df['Start date'] = pd.to_datetime(df['Start date'], dayfirst=True, errors='coerce')
df['End date'] = pd.to_datetime(df['End date'], dayfirst=True, errors='coerce')

# %%
# 1. Count unique and total PersonIDs
unique_ids = df['PersonID'].nunique()
total_rows = df.shape[0]
print(f"Total rows: {total_rows}")
print(f"Unique PersonIDs: {unique_ids}")

# %%
# 2. Summary statistics (full dataset)
summary_stats = df[['Age', 'BMI', 'Weight', 'MNA']].agg(['mean', 'std'])
print("\n Summary statistics (mean, std):")
print(summary_stats)

# %%
# 3. Gender distribution
gender_counts = df['Gender'].value_counts()
print("\n Gender distribution:")
print(gender_counts)

# %%
# 4. Correlation matrix (all records)
correlation_matrix = df[['Age', 'BMI', 'Weight', 'MNA']].corr()
print("\n Correlation matrix:")
print(correlation_matrix)

# %%
# Set seaborn style
sns.set(style="whitegrid")

# %%
# 5. Scatter plot: BMI vs Weight by Gender
plt.figure(figsize=(8, 6))
sns.scatterplot(data=df, x='Weight', y='BMI', hue='Gender', palette='Set1', alpha=0.6)
plt.title('Scatter plot of BMI vs Weight by Gender (Full Data)')
plt.xlabel('Weight (kg)')
plt.ylabel('BMI')
plt.legend(title='Gender')
plt.tight_layout()
plt.show()

# %%
# 6. Boxplot: BMI by Gender
plt.figure(figsize=(6, 5))
sns.boxplot(x='Gender', y='BMI', data=df, palette='Set2')
plt.title('Boxplot of BMI by Gender')
plt.tight_layout()
plt.show()

# %%
# 7. Boxplot: Weight by Gender
plt.figure(figsize=(6, 5))
sns.boxplot(x='Gender', y='Weight', data=df, palette='Set3')
plt.title('Boxplot of Weight by Gender')
plt.tight_layout()
plt.show()

# %%
# 8. Pairplot – All Records
sns.pairplot(df[['Age', 'BMI', 'Weight', 'MNA', 'Gender']], hue='Gender', palette='Set1', diag_kind='hist')
plt.suptitle("Pairplot of Numerical Variables by Gender (All Records)", y=1.02)
plt.show()

# %%
# 9. T-test: BMI difference between Male and Female
bmi_male = df[df['Gender'] == 'Male']['BMI'].dropna()
bmi_female = df[df['Gender'] == 'Female']['BMI'].dropna()

t_stat, p_value = ttest_ind(bmi_male, bmi_female, equal_var=False)
print(f"\n T-test for BMI difference between genders (All Records):\nT-statistic = {t_stat:.3f}, P-value = {p_value:.3f}")

if p_value < 0.05:
    print(" Statistically significant difference in BMI between genders.")
else:
    print(" No statistically significant difference in BMI between genders.")

# 日期轉換
df['Start date'] = pd.to_datetime(df['Start date'], dayfirst=True, errors='coerce')
df['End date'] = pd.to_datetime(df['End date'], dayfirst=True, errors='coerce')

# 確保時間排序
df = df.sort_values(by=['PersonID', 'Start date'])

# 建立 Care Duration（期間長度）
df['Care_Duration'] = (df['End date'] - df['Start date']).dt.days

# %%
# 1️⃣ 全體病人的 BMI vs Care Duration（散點 + 回歸線）
plt.figure(figsize=(8,6))
sns.scatterplot(data=df, x='Care_Duration', y='BMI', hue='Gender', alpha=0.6)
sns.regplot(data=df, x='Care_Duration', y='BMI', scatter=False, color='red')
plt.title("BMI vs Care Duration")
plt.xlabel("Care Duration (days)")
plt.ylabel("BMI")
plt.legend(title='Gender')
plt.tight_layout()
plt.show()

# %%
# 2️⃣ 全體病人的 Weight vs Care Duration（散點 + 回歸線）
plt.figure(figsize=(8,6))
sns.scatterplot(data=df, x='Care_Duration', y='Weight', hue='Gender', alpha=0.6)
sns.regplot(data=df, x='Care_Duration', y='Weight', scatter=False, color='blue')
plt.title("Weight vs Care Duration")
plt.xlabel("Care Duration (days)")
plt.ylabel("Weight (kg)")
plt.legend(title='Gender')
plt.tight_layout()
plt.show()

# %%
# 3️⃣ 單一病人的時間序列圖（示例 PersonID = 第一個）
sample_id = df['PersonID'].iloc[0]
df_sample = df[df['PersonID'] == sample_id]

fig, ax1 = plt.subplots(figsize=(10,5))
ax1.set_title(f"BMI & Weight Over Time - PersonID {sample_id}")

# 畫 BMI
ax1.plot(df_sample['Start date'], df_sample['BMI'], marker='o', color='orange', label='BMI')
ax1.set_xlabel("Start Date")
ax1.set_ylabel("BMI", color='orange')
ax1.tick_params(axis='y', labelcolor='orange')

# 畫 Weight（共用 x 軸，右側 y 軸）
ax2 = ax1.twinx()
ax2.plot(df_sample['Start date'], df_sample['Weight'], marker='s', color='green', label='Weight')
ax2.set_ylabel("Weight (kg)", color='green')
ax2.tick_params(axis='y', labelcolor='green')

fig.tight_layout()
plt.show()

# %% Per-patient time series → one page per patient (PDF)
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# 1) Load & prep
file_path = "/Users/mj/Downloads/UpdatedDataFile.csv"
df = pd.read_csv(file_path)

df['Start date'] = pd.to_datetime(df['Start date'], dayfirst=True, errors='coerce')
df['End date']   = pd.to_datetime(df['End date'],   dayfirst=True, errors='coerce')
df = df.sort_values(['PersonID', 'Start date'])

# (optional) keep only patients with >= 2 records so a “trend” exists
min_points = 2
grp_sizes = df.groupby('PersonID').size()
keep_ids = grp_sizes[grp_sizes >= min_points].index
df_plot = df[df['PersonID'].isin(keep_ids)].copy()

# 2) Output
out_dir = os.path.join(os.path.dirname(file_path), "fig_output")
os.makedirs(out_dir, exist_ok=True)
pdf_path = os.path.join(out_dir, "patient_timeseries_BMI_Weight.pdf")

with PdfPages(pdf_path) as pdf:
    for pid, g in df_plot.groupby('PersonID'):
        fig, ax1 = plt.subplots(figsize=(10, 4))  # one figure per patient

        # x = Start date; you can also try End date
        x = g['Start date']

        # BMI (left axis)
        ax1.plot(x, g['BMI'], marker='o', label='BMI')
        ax1.set_xlabel("Start date")
        ax1.set_ylabel("BMI")

        # Weight (right axis)
        ax2 = ax1.twinx()
        ax2.plot(x, g['Weight'], marker='s', linestyle='--', label='Weight')
        ax2.set_ylabel("Weight (kg)")

        # Title/subtitle
        gender = g['Gender'].iloc[0] if 'Gender' in g.columns else 'Unknown'
        age    = g['Age'].iloc[0]    if 'Age' in g.columns    else 'NA'
        ax1.set_title(f"PersonID {pid} — Gender: {gender} | Age: {age}")

        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

print(f"✅ Saved multi-page PDF to: {pdf_path}")

# %%
