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
