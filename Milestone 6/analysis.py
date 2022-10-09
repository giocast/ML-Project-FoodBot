import pandas as pd
from scipy.stats import ttest_ind

#FIELDS
# user_telegram_id;
# date;
# scenario;
# macro_categ;
# final_rate_service;
# duration_in_sec;
# pref_elic_duration_in_sec;
# recomm_duration_in_sec;
# number_interactions;
# has_user_perfermed_a_healthy_choice;
# nutri_score;
# fsa_score;
# id_dish_choice;
# user_constraints;
# proposal_random_1;proposal_random_2;proposal_random_3;proposal_random_4;proposal_random_5;
# number_skips;
# number_likes;
# all_dishes_shown_pref_elic;
# url_dishes_pairwise_comparisons;
# final_dish_not_chosen


df = pd.read_csv("ratings.csv", sep=";")


#---------confronti tra scenarios T vs MM

gb = df.groupby(['scenario'])

group_T = gb.get_group("Scenario Textual")
group_MM = gb.get_group("Scenario Multi-modal (Text + Image)")
print(group_T, "\n\n\n\n\n\n", group_MM )

mean_duration_T = group_T["duration_in_sec"].mean()
mean_preference_elicitation_duration_T = group_T["pref_elic_duration_in_sec"].mean()
mean_recommendation_duration_T = group_T["recomm_duration_in_sec"].mean()
mean_n_interactions_T = group_T["number_interactions"].mean()

mean_duration_MM = group_MM["duration_in_sec"].mean()
mean_preference_elicitation_duration_MM = group_MM["pref_elic_duration_in_sec"].mean()
mean_recommendation_duration_MM = group_MM["recomm_duration_in_sec"].mean()
mean_n_interactions_MM = group_MM["number_interactions"].mean()


print("Whole conversation duration: ",mean_duration_T," T, ",mean_duration_MM," MM")
print("-> Duration of two phases: pref. elic. and recomm. ->")
print("Preference elicitation step duration: ",mean_preference_elicitation_duration_T," T, ",mean_preference_elicitation_duration_MM," MM")
print("Recommendation step duration: ",mean_recommendation_duration_T," T, ",mean_recommendation_duration_MM," MM") #1st insight*******
print("N interactions: ",mean_n_interactions_T," T, ",mean_n_interactions_MM," MM")

#ANOVA TEST -> T STATISTIC va bene per confronto di due vettori, per valutare se classi diverse (modalità T e MM) influiscono su certa variabile di test (tempo utilizzo)

vector_duration_T = list(group_T["duration_in_sec"].values)
print("Duration FIRST VECTOR - T ",vector_duration_T)
vector_duration_MM = list(group_MM["duration_in_sec"].values)
print("Duration SECOND VECTOR - MM",vector_duration_MM)

vector_duration_pref_T = list(group_T["pref_elic_duration_in_sec"].values)
print("Pref elic duration FIRST VECTOR - T ",vector_duration_pref_T)
vector_duration_pref_MM = list(group_MM["pref_elic_duration_in_sec"].values)
print("Pref elic duration SECOND VECTOR - MM",vector_duration_pref_MM)

vector_duration_rec_T = list(group_T["recomm_duration_in_sec"].values)
print("Rec duration FIRST VECTOR - T ",vector_duration_rec_T)
vector_duration_rec_MM = list(group_MM["recomm_duration_in_sec"].values)
print("Rec duration SECOND VECTOR - MM",vector_duration_rec_MM)

vector_interactions_T = list(group_T["number_interactions"].values)
print("Interactions FIRST VECTOR - T ",vector_interactions_T)
vector_interactions_MM = list(group_MM["number_interactions"].values)
print("Interactions SECOND VECTOR - MM",vector_interactions_MM)

vector_healthy_choices_T = list(group_T["has_user_perfermed_a_healthy_choice"].values)
print("Healthy choice bool FIRST VECTOR - T ",vector_healthy_choices_T)
vector_healthy_choices_MM = list(group_MM["has_user_perfermed_a_healthy_choice"].values)
print("Healthy choice bool SECOND VECTOR - MM",vector_healthy_choices_MM)


vector_FSA_T = list(group_T["fsa_score"].values)
print("fsa FIRST VECTOR - T ",vector_FSA_T)
vector_FSA_MM = list(group_MM["fsa_score"].values)
print("fsa SECOND VECTOR - MM",vector_FSA_MM)


vector_skips_T = list(group_T["number_skips"].values)
print("n skips FIRST VECTOR - T ",vector_skips_T)
vector_skips_MM = list(group_MM["number_skips"].values)
print("n skips SECOND VECTOR - MM",vector_skips_MM)


print("Results show that the nyll hyphothesis is rejected, so the modality influence the conversation duration? --->",ttest_ind(vector_duration_T, vector_duration_MM))
print("Results show that the nyll hyphothesis is rejected, so the modality influence the preference elicitation step duration? --->",ttest_ind(vector_duration_pref_T, vector_duration_pref_MM))
print("Results show that the nyll hyphothesis is rejected, so the modality influence the recommendation step duration? --->",ttest_ind(vector_duration_rec_T, vector_duration_rec_MM))
#^ 1st insight*******

print("Results show that the nyll hyphothesis is rejected, so the modality influence the number of interaction? --->",ttest_ind(vector_interactions_T, vector_interactions_MM))
print("Results show that the nyll hyphothesis is rejected, so the modality influence the healthuy choices? --->",ttest_ind(vector_healthy_choices_T, vector_healthy_choices_MM))
print("Results show that the nyll hyphothesis is rejected, so the modality influence the fsa score? --->",ttest_ind(vector_FSA_T, vector_FSA_MM))
print("Results show that the nyll hyphothesis is rejected, so the modality influence the number of skips in pref elic? --->",ttest_ind(vector_skips_T, vector_skips_MM))


count_healthy_T = group_T["has_user_perfermed_a_healthy_choice"].value_counts()
print("Occurrency of healthy choices in T",count_healthy_T)
count_healthy_MM = group_MM["has_user_perfermed_a_healthy_choice"].value_counts()
print("Occurrency of healthy choices in MM",count_healthy_MM)