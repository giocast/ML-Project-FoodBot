import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

def main() -> None:
    data = pd.read_csv(filepath_or_buffer="snack.csv", header=None, sep=";")
    trainSet = []

    # Make the trainset starting from dataset (& data adjustments)
    for index, row in data.iterrows():
        dish = row[5] #ingredients field
        dish = dish.lower()  # lower case

        dish = dish.replace(" ", "") # in order to remove spaces

        dish = ["".join(dish)]  # put all ingredients into a string containing comma sparated elements(ingredients)
        trainSet += dish  # add string to list train set

    print("Train set \n\n", trainSet)

    vectorizer = TfidfVectorizer()  # transform foods in vectors

    # TF-IDF to detect importance of ingredients in foods (TF = Term frequency, IDF = Inverse Document Frequency)
    pd.set_option("display.max_rows", None, "display.max_columns", None)

    matrix = vectorizer.fit_transform(trainSet)
    print("MATRICE VECTORIZER \n\n\n\n",matrix)
    print("\n\n\nSHAPE:::::::", matrix.shape)

    matrix_dense = matrix.todense()
    print("DENSE \n\n", matrix_dense)
    print(matrix_dense.shape)

    print("INGR NAMES::::::::::::", vectorizer.get_feature_names_out())

    #SAVE TFIDF SCORES MATRIX INTO A CSV FILE
    np.savetxt("tfIdfMenuSnack.csv", matrix_dense, delimiter=",", fmt="%.5f")
    np.savetxt("tfIdfIngredientsNamesSnack.txt", vectorizer.get_feature_names_out(), delimiter=" ", fmt="%s")
    np.savetxt("tfIdfDishesNamesSnack.txt", data.iloc[:,3], delimiter=" ", fmt="%s")

    cosineSim = cosine_similarity(matrix_dense, matrix_dense)
    print(cosineSim)

if __name__ == '__main__':
    main()