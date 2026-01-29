import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind

# Load the CSV file
file_path = "/Users/mj/Downloads/UpdatedDataFile.csv"  
df = pd.read_csv(file_path)

# 1. Count unique PersonID
unique_person_ids = df['PersonID'].nunique()
print(f"Number of unique PersonID: {unique_person_ids}")

# 2. Remove duplicate PersonID entries, keep the first record
df_unique = df.drop_duplicates(subset=['PersonID'])

# 3. Summary statistics
summary_stats = df_unique[['Age', 'BMI', 'Weight', 'MNA']].agg(['mean', 'std'])
print("\nMean and standard deviation for numerical variables:")
print(summary_stats)

# 4. Gender distribution
gender_counts = df_unique['Gender'].value_counts()
print("\nGender distribution:")
print(gender_counts)

# 5. Correlation matrix
correlation_matrix = df_unique[['Age', 'BMI', 'Weight', 'MNA']].corr()
print("\nCorrelation matrix:")
print(correlation_matrix)

# Visualization
sns.set(style="whitegrid")

# 6. Scatter plot: BMI vs Weight
plt.figure(figsize=(8,6))
sns.scatterplot(data=df_unique, x='Weight', y='BMI', hue='Gender', palette='Set1')
plt.title('Scatter plot of BMI vs Weight by Gender')
plt.xlabel('Weight')
plt.ylabel('BMI')
plt.legend(title='Gender')
plt.show()

# 7. Boxplot: BMI by Gender
plt.figure(figsize=(6,5))
sns.boxplot(x='Gender', y='BMI', data=df_unique, palette='Set2')
plt.title('Boxplot of BMI by Gender')
plt.xlabel('Gender')
plt.ylabel('BMI')
plt.show()

# 8. Boxplot: Weight by Gender
plt.figure(figsize=(6,5))
sns.boxplot(x='Gender', y='Weight', data=df_unique, palette='Set3')
plt.title('Boxplot of Weight by Gender')
plt.xlabel('Gender')
plt.ylabel('Weight')
plt.show()

# 9. Pairplot
sns.pairplot(df_unique[['Age', 'BMI', 'Weight', 'MNA', 'Gender']], hue='Gender', palette='Set1', diag_kind='hist')
plt.suptitle('Pairplot of Numerical Variables by Gender', y=1.02)
plt.show()

# 10. T-test for BMI by Gender
bmi_male = df_unique[df_unique['Gender'] == 'Male']['BMI'].dropna()
bmi_female = df_unique[df_unique['Gender'] == 'Female']['BMI'].dropna()
t_stat, p_value = ttest_ind(bmi_male, bmi_female, equal_var=False)
print(f"\nT-test for BMI difference between genders:\n t-statistic = {t_stat:.3f}, p-value = {p_value:.3f}")

if p_value < 0.05:
    print("There is a statistically significant difference in BMI between genders.")
else:
    print("No statistically significant difference in BMI between genders was found.")
