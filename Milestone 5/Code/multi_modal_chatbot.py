import logging, csv

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
)

from googletrans import Translator
from difflib import SequenceMatcher
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# _______________________RETURN CODES (useful for identifying next function to be called)_________

CHOICEMODALITY, FUNCTCALLBACK, PROCESSUSERCONSTRAINTS, FUNCTCALLBACK2, AFTERRECOMMENDATION, FINALRATINGS = range(6)

# _______________________GLOBAL VARIABLES_________________________________________________________
# we need to use a GLOBAL DICTIONARY which contains for each key (CHATID/USERID) a dictionary of variables (key) and values valid for that user

# GLOBAL DICT FOR EACH USER (chatid:dictionaryOfVariables)
usersGlobalVariables = {}

menu = []  # list which is filled with all the Piatto objects -> STARTING MENU

# dictionary of macro category names (associate names shown to user with symbolic names in the Piatto object's attribute value)
macroCategNames = {
    "Pasta 🍝": "Pasta",
    "Insalata 🥗": "Salad",
    "Dessert 🧁": "Dessert",
    "Snack 🍟": "Snack"
}


# _______________________CLASS DEFINITION_____________________________________________

class Piatto:
    def __init__(self, numero, nome, ingredienti, immagine, calorie, macroCategoria, servings, totalGramWeight,
                 protein100, carb100, fiber100, sugar100, fat100, satfat100, salt100, kj100, nutri_score, FSAscore, mediaReviews, numeroReviews, idDishUrl):
        self.numero = numero
        self.nome = nome
        self.ingredienti = ingredienti
        self.immagine = immagine
        self.calorie = calorie
        self.macroCategoria = macroCategoria
        self.servings = servings
        self.totalGramWeight = totalGramWeight
        self.protein100 = protein100
        self.carb100 = carb100
        self.fiber100 = fiber100
        self.sugar100 = sugar100
        self.fat100 = fat100
        self.satfat100 = satfat100
        self.salt100 = salt100
        self.kj100 = kj100
        self.nutriScore = nutri_score
        self.FSAscore = FSAscore
        self.mediaReviews = mediaReviews
        self.numeroReviews = numeroReviews
        self.idDishUrl = idDishUrl


# _______________________FUNCTIONS__________________________________________________

# FUNC: fill the list menu with all the available dishes

def creaMenu() -> None:
    datasets = ["pasta.csv", "salad.csv", "dessert.csv", "snack.csv"]

    # I add Piatto objects into the menu by getting all rows of all menu files (one for category)

    line_count = 1  # index of dishes into the menu
    global menu

    # numero, nome, ingredienti, immagine, calorie, macroCategoria, servings, totalGramWeight, protein100, carb100, fiber100, sugar100, fat100, satfat100, salt100, kj100, nutri_score, FSAscore, FSAlabel, mediaReviews, numReviews, idUrlDish
    for urlDataset in datasets:
        csv_file = open(urlDataset)
        csv_reader = csv.reader(csv_file, delimiter=';')

        for row in csv_reader:
            x = row[5]
            x = x.split(',')
            # IMP: there are some ingredients with upper letters, solve with lower() function
            ingrs = [each_string.lower() for each_string in x]
            calor = row[4]
            macroCateg = row[1]
            # numero, nome, ingredienti, immagine, calorie, macroCategoria, servings, totalGramWeight, protein100, carb100, fiber100, sugar100, fat100, satfat100, salt100, kj100, nutri_score, FSAscore, mediaReviews, numeroReviews, idUrl, goodim, badIma
            menu.append(
                Piatto(line_count, row[3], ingrs, row[2], calor, macroCateg, row[6], row[15], row[17], row[18], row[19],
                       row[20], row[21], row[22], row[25], row[26], row[27], row[28], row[30], row[31], row[0]))

            line_count += 1


# FUNC: defines the indexes for reading the dishes of each catagory

def returnIndexesByMacroCateg(macroCateg):
    start = 0
    finish = 0

    # userChoiceMacroCategoryGlobal
    if macroCateg == "Pasta 🍝":
        start = 0
        finish = 499  # 500
    elif macroCateg == "Insalata 🥗":
        start = 500
        finish = 999  # 1000
    elif macroCateg == "Dessert 🧁":
        start = 1000
        finish = 1499  # 1500
    elif macroCateg == "Snack 🍟":
        start = 1500
        finish = 1999  # 2000

    return start, finish


# FUNC: print menu list (for each element print some attribute)

def stampaMenu() -> None:
    for obj in menu:
        print(obj.numero, obj.nome, obj.ingredienti, obj.immagine, obj.calorie, obj.macroCategoria)


# FUNC: print generic list passed as parameter (for each element print some attribute)

def stampaLista(lista) -> None:
    for obj in lista:
        print(obj.numero, obj.nome, obj.ingredienti, obj.immagine, obj.calorie, obj.macroCategoria)


def retLista(obj):
    return str(obj.numero) + " " + obj.nome + " " + obj.FSAscore + " " + obj.nutriScore + " " + obj.macroCategoria


# FUNC: print generic list passed as parameter

def stampaVettore(lista) -> None:
    for obj in lista:
        print(obj)


# FUNC: creates a string of comma separated objects contained in a list

def stampaIngredienti(lista):
    stringa = ''
    for obj in lista:
        stringa = stringa + ', ' + obj
    return stringa


#FUNC: perform similarity evaluation between two strings

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


# *FUNC: first function of the chatbot flow -> first setups and food macro category acquisition

def start(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    userIdentifier = str(user.id)  # str(update.message.chat.id)
    print("A new user joins! USER ID: ", userIdentifier, "\n\n")

    # CRETE A NEW ENTRY FOR USER and assign an empty dictionary that will be filled during chatbot flow
    global usersGlobalVariables
    usersGlobalVariables[userIdentifier] = {}

    # In order to collect data for analysis, we will measure interaction time and number of interaction turns
    usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] = 0
    usersGlobalVariables[str(update.message.from_user.id)]["startSessionDate"] = update.message.date

    reply_keyboard = [['Pasta 🍝'], ['Insalata 🥗'], ['Dessert 🧁'], ['Snack 🍟']]
    welcomeString = 'Ciao!\n' + 'Sono FoodBot e ti aiuterò a trovare il piatto perfetto per te! ' \
                               ' \n\nNota: lancia il comando /cancel per interrompere la conversazione... \n\n' + \
                    'Scegli una categoria di cibo che vorresti mangiare...'

    update.message.reply_text(welcomeString, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                              resize_keyboard=False))

    return CHOICEMODALITY


# *FUNC:  function of the chatbot flow -> define the user modality (T,MM) and constraint acquisition

def choiceModality(update: Update, context: CallbackContext):
    #Here we define the modality (T for pure textual, MM for multi-modal) of interaction with the user
    # and then we ask for dietary constraints...

    global usersGlobalVariables

    usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] = usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] + 1
    usersGlobalVariables[str(update.message.from_user.id)]["userChoiceMacroCategoryGlobal"] = update.message.text
    usersGlobalVariables[str(update.message.from_user.id)]["nextInd"] = 0  # useful in recommendation step

    # Set the index in order to define the modality of sys/user interaction
    # 0 for T
    # 1 for MM

    listOfModalities = ["T", "MM"]
    usersGlobalVariables[str(update.message.from_user.id)]["userChoiceModalityGlobal"] = listOfModalities[1]

    print("User ", str(update.message.from_user.id), " chose ", usersGlobalVariables[str(update.message.from_user.id)]["userChoiceMacroCategoryGlobal"], " category\n")
    print("User ", str(update.message.from_user.id), "is working with modality ", usersGlobalVariables[str(update.message.from_user.id)]["userChoiceModalityGlobal"], "\n")

    usersGlobalVariables[str(update.message.from_user.id)]["keyboardIntolerancesDiseases"] = [
        [InlineKeyboardButton('Lattosio', callback_data='0'), InlineKeyboardButton('Carne', callback_data='1'),
         InlineKeyboardButton('Alcol', callback_data='2')],
        [InlineKeyboardButton('Diabete', callback_data='3'), InlineKeyboardButton('Reflusso', callback_data='4'),
         InlineKeyboardButton('Colest.', callback_data='5')],
        [InlineKeyboardButton('Frutti di mare', callback_data='6')],
        [InlineKeyboardButton('(Fatto)', callback_data='7')]]

    usersGlobalVariables[str(update.message.from_user.id)]["listConstraintsTap"] = []

    reply_markup = InlineKeyboardMarkup(
        usersGlobalVariables[str(update.message.from_user.id)]["keyboardIntolerancesDiseases"])
    update.message.reply_text(
        'Sei allergico a qualcosa o hai qualche patologia? Eventualmente, indica quali utilizzando la pulsantiera. \nClicca su (Fatto) per continuare\n',
        reply_markup=reply_markup
    )

    return FUNCTCALLBACK


#* functions set of the chatbot flow
#*FUNC: callback query function called when user decides to end first constraint acquisition step -> ask for other specific constraints on ingredients

def goToOtherConstraints(update, context):
    global usersGlobalVariables
    #listConstraintsTap check dim and print values

    usersGlobalVariables[str(update.callback_query.from_user.id)]["counterInteractionTurns"] = usersGlobalVariables[str(update.callback_query.from_user.id)]["counterInteractionTurns"] + 1

    if len(usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"]) > 0:
        stringIntol = "Constraints: "
        i = 0
        for elem in usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"]:
            if i != 0:
                stringIntol += ", "+elem
            else:
                stringIntol += elem
            i += 1
        update.callback_query.message.edit_text(traduciEnIt(stringIntol))
        print("User ",str(update.callback_query.from_user.id)," has these contraints -> ", usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"],"\n")

        # bool useful later in why didi you recommend this
        usersGlobalVariables[str(update.callback_query.from_user.id)]["boolFirstConstr"] = True

    else:
        print("User ", str(update.callback_query.from_user.id), " has no constraints \n")
        usersGlobalVariables[str(update.callback_query.from_user.id)]["boolFirstConstr"] = False
    update.effective_message.reply_text('Per piacere, fammi sapere se vuoi evitare qualche ingrediente. Scrivi una lista di ingredienti separati da virgola. \nClicca su '
                             '/noconstraints se non hai alcun vincolo')

    return PROCESSUSERCONSTRAINTS

#*FUNCS: callback query functions called when user clicks on a constraint during first constraint acquisition step

def zero(update, context):
    query = update.callback_query
    reply_markup = ""
    global usersGlobalVariables

    current = usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][0].text

    if current == "Lattosio":
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][0] = InlineKeyboardButton('Lattosio ✅', callback_data='0')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].append("Lactose")
    else:
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][0] = InlineKeyboardButton('Lattosio', callback_data='0')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].remove("Lactose")


    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Sei allergico a qualcosa o hai qualche patologia? Eventualmente, indica quali utilizzando la pulsantiera. \nClicca su (Fatto) per continuare\n",
        reply_markup=reply_markup
    )

    return FUNCTCALLBACK
def one(update, context):
    query = update.callback_query
    reply_markup = ""
    global usersGlobalVariables

    current = usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][1].text

    if current == "Carne":
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][1] = InlineKeyboardButton('Carne ✅', callback_data='1')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].append("Meat")
    else:
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][1] = InlineKeyboardButton('Carne', callback_data='1')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].remove("Meat")


    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Sei allergico a qualcosa o hai qualche patologia? Eventualmente, indica quali utilizzando la pulsantiera. \nClicca su (Fatto) per continuare\n",
        reply_markup=reply_markup
    )

    return FUNCTCALLBACK
def two(update, context):
    query = update.callback_query
    reply_markup = ""
    global usersGlobalVariables

    current = usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][2].text

    if current == "Alcol":
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][2] = InlineKeyboardButton('Alcol ✅', callback_data='2')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].append("Alcohol")
    else:
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][0][2] = InlineKeyboardButton('Alcol', callback_data='2')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].remove("Alcohol")

    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Sei allergico a qualcosa o hai qualche patologia? Eventualmente, indica quali utilizzando la pulsantiera. \nClicca su (Fatto) per continuare\n",
        reply_markup=reply_markup
    )

    return FUNCTCALLBACK
def three(update, context):
    query = update.callback_query
    reply_markup = ""
    global usersGlobalVariables

    current = usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][0].text

    if current == "Diabete":
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][0] = InlineKeyboardButton('Diabete ✅', callback_data='3')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].append("Diabetes")
    else:
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][0] = InlineKeyboardButton('Diabete', callback_data='3')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].remove("Diabetes")

    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Sei allergico a qualcosa o hai qualche patologia? Eventualmente, indica quali utilizzando la pulsantiera. \nClicca su (Fatto) per continuare\n",
        reply_markup=reply_markup
    )

    return FUNCTCALLBACK
def four(update, context):
    query = update.callback_query
    reply_markup = ""
    global usersGlobalVariables

    current = usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][1].text

    if current == "Reflusso":
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][1] = InlineKeyboardButton('Reflusso ✅', callback_data='4')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].append("Reflux")
    else:
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][1] = InlineKeyboardButton('Reflusso', callback_data='4')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].remove("Reflux")

    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Sei allergico a qualcosa o hai qualche patologia? Eventualmente, indica quali utilizzando la pulsantiera. \nClicca su (Fatto) per continuare\n",
        reply_markup=reply_markup
    )

    return FUNCTCALLBACK
def five(update, context):
    query = update.callback_query
    reply_markup = ""
    global usersGlobalVariables

    current = usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][2].text

    if current == "Colest.":
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][2] = InlineKeyboardButton('Colest. ✅', callback_data='5')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].append("Cholesterolemia")
    else:
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][1][2] = InlineKeyboardButton('Colest.', callback_data='5')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].remove("Cholesterolemia")

    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Sei allergico a qualcosa o hai qualche patologia? Eventualmente, indica quali utilizzando la pulsantiera. \nClicca su (Fatto) per continuare\n",
        reply_markup=reply_markup
    )

    return FUNCTCALLBACK
def six(update, context):
    query = update.callback_query
    reply_markup = ""
    global usersGlobalVariables

    current = usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][2][0].text

    if current == "Frutti di mare":
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][2][0] = InlineKeyboardButton('Frutti di mare ✅', callback_data='6')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].append("Seafood")
    else:
        usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"][2][0] = InlineKeyboardButton('Frutti di mare', callback_data='6')
        reply_markup = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)]["keyboardIntolerancesDiseases"])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listConstraintsTap"].remove("Seafood")

    bot = context.bot
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Sei allergico a qualcosa o hai qualche patologia? Eventualmente, indica quali utilizzando la pulsantiera. \nClicca su (Fatto) per continuare\n",
        reply_markup=reply_markup
    )

    return FUNCTCALLBACK

#Useful functions for translating items name and features (that are in english language)
def traduciEnIt(text):
    destination_language = {
        "Italian": "it"
    }
    translator = Translator()
    for key, value in destination_language.items():
        return translator.translate(text, dest=value).text
def traduciItEn(text):
    destination_language = {
        "English": "en"
    }
    translator = Translator()
    for key, value in destination_language.items():
        return translator.translate(text, dest=value).text


# *FUNC: function of the chatbot flow -> process user constraints and filter the menu

def processUserConstraints(update: Update, context: CallbackContext) -> int:
    global usersGlobalVariables
    usersGlobalVariables[str(update.message.from_user.id)]["flagSkippedAl"] = False

    usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] = usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] + 1

    if update.message.text == "/noconstraints":
        usersGlobalVariables[str(update.message.from_user.id)]["flagSkippedAl"] = True

    update.message.reply_text('Processando, attendi per favore...')
    userConstraints = ""

    if usersGlobalVariables[str(update.message.from_user.id)]["flagSkippedAl"] == False:
        # user has constraints on diet. Analyze them
        userText = update.message.text
        # imagine diseases separated by comma
        userConstraints = userText.split(',')
        userConstraints = [traduciItEn(each_string.lower()) for each_string in userConstraints]  # lower case and translate from it to enb
        userConstraints = [each_string.strip() for each_string in userConstraints]  # remove spaces before and after strings
        userConstraints.extend(usersGlobalVariables[str(update.message.from_user.id)]["listConstraintsTap"])  # add tap of user (consraints disease/intol) to ingr to avoid
        usersGlobalVariables[str(update.message.from_user.id)]["memoryConstraints"] = userConstraints

    else:
        userConstraints = usersGlobalVariables[str(update.message.from_user.id)]["listConstraintsTap"]
        usersGlobalVariables[str(update.message.from_user.id)]["memoryConstraints"] = userConstraints


    #We create a new menu (for each user) which is filtered according to her dietary constraints. Our aim is to avoid users to evaluate during preference elicitation next step dishes she can't eat
    #-> we call it MenuAfterConstraintsCheck -> FIRST INITIALIZATION

    usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"] = menu.copy()  # start from the entire menu

    csv_reader = None
    with open('DiseasesIntolerances.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader, None)  # skip the headers
        csv_reader = list(csv_reader)
    for elem in userConstraints:
        # 1 / REMOVE ALL DISHES WITH INGREDIENTS SPECIFIED BY USER -> es zucchini
        for obj in reversed(usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"]):
            cond = True in (similar(elem, el) >= 0.8 for el in obj.ingredienti)  # true se any of them respect condition
            if cond == True:
                # remove the dish
                usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"].remove(obj)

        # 2 / REMOVE ALL DISHES CONTAINING SPECIFIED INGREDIENTS OF DISEASES IN THE DISEASE DATASET
        # scan file of intolerances to check if present a disease/intol like what user has written

        for row in csv_reader:
            nomeDisIntol = row[0]
            if similar(nomeDisIntol, elem) >= 0.7:
                # if found reflux
                ingredientsToAvoid = row[2]

                if ingredientsToAvoid != '':

                    listaIngrAvoid = ingredientsToAvoid.split(',')
                    lungh = len(listaIngrAvoid)

                    # for all not recommended ingredients due to disease/allergy
                    for i in range(0, lungh):
                        ingredToBeRomoved = listaIngrAvoid[i]
                        # reversed to avoid problem with indexes (when removing elements)

                        for obj in reversed(usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"]):
                            # if ingredToBeRomoved in obj.ingredienti:
                            cond = True in (similar(ingredToBeRomoved, el) >= 0.8 for el in obj.ingredienti)  # true if any of them respect condition
                            if cond == True:
                                # at least one respects the condition
                                usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"].remove(obj)  # removed dish with ingredient not avoided

                break  # quit if found similar to that user constraint


    # remove all dishes not belonging to the macro-category chosen by the user

    usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"] = [p for p in usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"] if p.macroCategoria == macroCategNames[usersGlobalVariables[str(update.message.from_user.id)]["userChoiceMacroCategoryGlobal"]]]
    print("User ", str(update.message.from_user.id), " has a new menu of lenght ", len(usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"]), "\n")


    # check if empty menu
    if not usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"]:
        print("(ERROR 1) END OF MENU for user ", str(update.message.from_user.id))
        update.message.reply_text('Mi dispiace...non posso consigliarti alcun piatto')

        #delete data for that user and end the conversation
        del usersGlobalVariables[str(update.message.from_user.id)]
        return ConversationHandler.END

    # NOW MANAGE NEXT STEPS!

    usersGlobalVariables[str(update.message.from_user.id)]["firstUserChoice"] = usersGlobalVariables[str(update.message.from_user.id)]["userChoiceModalityGlobal"]
    user = update.message.from_user

    #In this step we want so administer random dishes to user, one per time and ask her to LIKE or SKIP each one. This preference elicitation step, using Active Learning strategy could help us overcoming the cold start problem. After reached 5 preferences (5 likes) the process ends.

    usersGlobalVariables[str(update.message.from_user.id)]["counterDishesPrefElic"] = 1
    usersGlobalVariables[str(update.message.from_user.id)]["numberSkips"] = 0
    usersGlobalVariables[str(update.message.from_user.id)]["numberLikes"] = 0  # We need to reach 5 ***
    usersGlobalVariables[str(update.message.from_user.id)]["userRates"] = {}

    #In order to reference an inline keyboard (and let us changing its status) we use identifiers
    idKeyb = "keyboardLikeRandDish" + str(usersGlobalVariables[str(update.message.from_user.id)]["counterDishesPrefElic"])

    usersGlobalVariables[str(update.message.from_user.id)][idKeyb] = [[InlineKeyboardButton('Like', callback_data='Like'), InlineKeyboardButton('Skip', callback_data='Skip')]]

    reply_markupN = InlineKeyboardMarkup(usersGlobalVariables[str(update.message.from_user.id)][idKeyb])

    # **********
    usersGlobalVariables[str(update.message.from_user.id)]["dishesToShow"] = len(usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"])

    if usersGlobalVariables[str(update.message.from_user.id)]["dishesToShow"] > 5:
        update.message.reply_text('Da questo momento, ti mostrerò alcuni piatti. Clicca su Like se ti piace un piatto. Premi su Skip altrimenti. \n\nHo bisogno di 5 preferenze per continuare...', reply_markup=ReplyKeyboardRemove())

        usersGlobalVariables[str(update.message.from_user.id)]["startPreferenceElicitationDate"] = update.message.date
        import random
        random.shuffle(usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"])

        nameDish = traduciEnIt(usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.message.from_user.id)]["counterDishesPrefElic"] - 1].nome)
        imgDish = usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.message.from_user.id)]["counterDishesPrefElic"] - 1].immagine

        usersGlobalVariables[str(update.message.from_user.id)]["listaDishesLiked"] = []
        usersGlobalVariables[str(update.message.from_user.id)]["listaDishesShown"] = []
        usersGlobalVariables[str(update.message.from_user.id)]["flagEmergencyRecommendation"] = False

        usersGlobalVariables[str(update.message.from_user.id)]["listaDishesShown"].append(usersGlobalVariables[str(update.message.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.message.from_user.id)]["counterDishesPrefElic"] - 1].idDishUrl)

        if usersGlobalVariables[str(update.message.from_user.id)]["firstUserChoice"] == 'T':
            usersGlobalVariables[str(update.message.from_user.id)]["flagTextualVisualChoice"] = False  # utile dopo, non usato qui
            update.message.reply_text(nameDish, reply_markup=reply_markupN)
        elif usersGlobalVariables[str(update.message.from_user.id)]["firstUserChoice"] == 'MM':
            usersGlobalVariables[str(update.message.from_user.id)]["flagTextualVisualChoice"] = True
            update.message.reply_photo(imgDish, reply_markup=reply_markupN, caption=nameDish)

        return FUNCTCALLBACK2
    else:
        print("(ERROR 2) END OF MENU for user ", str(update.message.from_user.id))
        update.message.reply_text('Mi dispiace...non posso consigliarti alcun piatto')

        del usersGlobalVariables[str(update.message.from_user.id)]
        return ConversationHandler.END



#*FUNCS: callback query functions called when user clicks on Like or Skip during preference elicitation step

def likeDishN(update, context):
    query = update.callback_query
    reply_markup = ""
    global usersGlobalVariables

    idKeyb = "keyboardLikeRandDish" + str(usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"])

    current = usersGlobalVariables[str(update.callback_query.from_user.id)][idKeyb][0][0].text

    if current == "Like":
        usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] = usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"]+1
        stringaLiked = 'Liked 👍 ('+str(usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"])+"/5)"
        usersGlobalVariables[str(update.callback_query.from_user.id)][idKeyb][0][0] = InlineKeyboardButton(stringaLiked, callback_data='Like')
        reply_markup = InlineKeyboardMarkup([[usersGlobalVariables[str(update.callback_query.from_user.id)][idKeyb][0][0]]]) #InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)][idKeyb])

        usersGlobalVariables[str(update.callback_query.from_user.id)]["listaDishesLiked"].append(usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"]-1].numero)
        usersGlobalVariables[str(update.callback_query.from_user.id)]["userRates"][usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"]-1].numero-1] = 5


    bot = context.bot

    bot.edit_message_reply_markup(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        reply_markup=reply_markup
    )

    usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] = usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] + 1

    if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 5:
        update.effective_message.reply_text("Grazie per avermi fornito 5 preferenze! Processando raccomandazioni per te...")
        usersGlobalVariables[str(update.callback_query.from_user.id)]["finishPreferenceElicitationDate"] = update.effective_message.date
        usersGlobalVariables[str(update.callback_query.from_user.id)]["counterInteractionTurns"] = usersGlobalVariables[str(update.callback_query.from_user.id)]["counterInteractionTurns"] + 1

        #CALL FUNCTION FOR PROCESSING
        processing(update, context)
        return AFTERRECOMMENDATION

    else:
        # CONDIZIONE PER CONTROLLARE CHE INDICE NON SIA OLTRE DISPONIBILITA DI MENUAFTER CONSTRAINT
        if (usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] + usersGlobalVariables[str(update.callback_query.from_user.id)]["numberSkips"]) >= usersGlobalVariables[str(update.callback_query.from_user.id)]["dishesToShow"]:
            if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] > 0:
                #GESTIONE USER PROFILE E MESSAGGIO SIMBOLICO E SOPRATTUTTO FLAGS
                stringa="like"
                update.effective_message.reply_text("Ok, hai fornito solo ", usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"], stringa,", che non è abbastanza. Comunque proverò a raccomandarti qualcosa...")
                usersGlobalVariables[str(update.callback_query.from_user.id)]["finishPreferenceElicitationDate"] = update.effective_message.date
                usersGlobalVariables[str(update.callback_query.from_user.id)]["flagEmergencyRecommendation"] = True

                #CALL FUNCTION FOR PROCESSING
                processing(update, context)
                return AFTERRECOMMENDATION

            else:
                print("(ERROR 3) END OF MENU for user ", str(update.callback_query.from_user.id))
                update.effective_message.reply_text('Mi dispiace...non posso consigliarti alcun piatto')

                del usersGlobalVariables[str(update.callback_query.from_user.id)]
                return ConversationHandler.END
        else:
            idKeyb = "keyboardLikeRandDish" + str(usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"])
            usersGlobalVariables[str(update.callback_query.from_user.id)][idKeyb] = [[InlineKeyboardButton('Like', callback_data='Like'),InlineKeyboardButton('Skip', callback_data='Skip')]]
            reply_markupN = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)][idKeyb])

            nameDish = traduciEnIt(usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] - 1].nome)
            imgDish = usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] - 1].immagine

            usersGlobalVariables[str(update.callback_query.from_user.id)]["listaDishesShown"].append(usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] - 1].idDishUrl)

            if usersGlobalVariables[str(update.callback_query.from_user.id)]["firstUserChoice"] == 'T':
                update.effective_message.reply_text(nameDish, reply_markup=reply_markupN)
            elif usersGlobalVariables[str(update.callback_query.from_user.id)]["firstUserChoice"] == 'MM':
                update.effective_message.reply_photo(imgDish, reply_markup=reply_markupN, caption=nameDish)

            return FUNCTCALLBACK2

def skipDishN(update, context):
    usersGlobalVariables[str(update.callback_query.from_user.id)]["numberSkips"] = usersGlobalVariables[str(update.callback_query.from_user.id)]["numberSkips"]+1

    usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] =  usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] + 1

    bot = context.bot
    query = update.callback_query
    reply_markup = InlineKeyboardMarkup([])

    bot.edit_message_reply_markup(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        reply_markup=reply_markup
    )

    if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] <5:

        if (usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] + usersGlobalVariables[str(update.callback_query.from_user.id)]["numberSkips"]) >= usersGlobalVariables[str(update.callback_query.from_user.id)]["dishesToShow"]:

            if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] > 0:
                #GESTIONE USER PROFILE E MESSAGGIO SIMBOLICO E SOPRATTUTTO FLAGS
                stringa=" like"
                risposta = "Ok, hai fornito solo ", usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"], stringa,", che non è abbastanza. Comunque proverò a raccomandarti qualcosa..."
                update.effective_message.reply_text(risposta)
                usersGlobalVariables[str(update.callback_query.from_user.id)]["flagEmergencyRecommendation"] = True
                usersGlobalVariables[str(update.callback_query.from_user.id)]["finishPreferenceElicitationDate"] = update.effective_message.date

                # CALL FUNCTION FOR PROCESSING
                processing(update, context)
                return AFTERRECOMMENDATION

            else:
                print("(ERROR 4) END OF MENU for user ", str(update.callback_query.from_user.id))
                update.effective_message.reply_text('Mi dispiace...non posso consigliarti alcun piatto')

                del usersGlobalVariables[str(update.callback_query.from_user.id)]
                return ConversationHandler.END
        else:
            idKeyb = "keyboardLikeRandDish" + str(usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"])
            usersGlobalVariables[str(update.callback_query.from_user.id)][idKeyb] = [[InlineKeyboardButton('Like', callback_data='Like'),InlineKeyboardButton('Skip', callback_data='Skip')]]
            reply_markupN = InlineKeyboardMarkup(usersGlobalVariables[str(update.callback_query.from_user.id)][idKeyb])

            nameDish = traduciEnIt(usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] - 1].nome)
            imgDish = usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] - 1].immagine

            usersGlobalVariables[str(update.callback_query.from_user.id)]["listaDishesShown"].append(usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"][usersGlobalVariables[str(update.callback_query.from_user.id)]["counterDishesPrefElic"] - 1].idDishUrl)


            if usersGlobalVariables[str(update.callback_query.from_user.id)]["firstUserChoice"] == 'T':
                update.effective_message.reply_text(nameDish, reply_markup=reply_markupN)
            elif usersGlobalVariables[str(update.callback_query.from_user.id)]["firstUserChoice"] == 'MM':
                update.effective_message.reply_photo(imgDish, reply_markup=reply_markupN, caption=nameDish)


            return FUNCTCALLBACK2


# *FUNC: utilizes all the information provided by user for building a user profile and generating a recommendation list sorted wrt cosine similarity with the user profile

def processing(update: Update, context: CallbackContext) -> int:
    global usersGlobalVariables

    # GO TO RECOMMENDATION!!!!

    listOfTuples = list(usersGlobalVariables[str(update.callback_query.from_user.id)]["userRates"].items())

    if usersGlobalVariables[str(update.callback_query.from_user.id)]["flagEmergencyRecommendation"] is True:
        if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 4:
            rate1 = listOfTuples[0][1]  # 5 stars
            rate2 = listOfTuples[1][1]
            rate3 = listOfTuples[2][1]
            rate4 = listOfTuples[3][1]
        elif usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 3:
            rate1 = listOfTuples[0][1]  # 5 stars
            rate2 = listOfTuples[1][1]
            rate3 = listOfTuples[2][1]
        elif usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 2:
            rate1 = listOfTuples[0][1]  # 5 stars
            rate2 = listOfTuples[1][1]
        elif usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 1:
            rate1 = listOfTuples[0][1]  # 5 stars
    else:
        rate1 = listOfTuples[0][1]  # Like = 5 stars
        rate2 = listOfTuples[1][1]
        rate3 = listOfTuples[2][1]
        rate4 = listOfTuples[3][1]
        rate5 = listOfTuples[4][1]


    # GET TF-IDF PREGENERATED MATRIX

    pd.set_option("display.max_rows", None, "display.max_columns", None)

    nameIngredients = []  # to store all names of features...previously stored
    nameDishes = []  # to store all names of dishes of the menu

    tfIdfIngrNames, tfIdfDishesNames, tfIdfMenu = returnFilesNamesByMacroCateg(usersGlobalVariables[str(update.callback_query.from_user.id)]["userChoiceMacroCategoryGlobal"])

    with open(tfIdfIngrNames) as file:
        nameIngredients = file.read().splitlines()
    with open(tfIdfDishesNames) as file:
        nameDishes = file.read().splitlines()

    # Get matrix tfidf PREVIOUSLY PERFORMED and make a dataframe with cols FEATURES and index NAMEDISHES
    import csv
    import numpy
    matrix = numpy.array(list(csv.reader(open(tfIdfMenu, "rt"), delimiter=","))).astype("float")
    df = pd.DataFrame(matrix, columns=nameIngredients, index=nameDishes)

    # HOW TO BUILD THE USER PROFILE:
    #  extract vectors of somministrated dishes and perform a weighted average -> since all rates are 5 WE can consider it as a normal average
    #  FORMULA   --->   (tfidf1 + tfid2 + tfidf3 + tfidf4 +  tfidf5) / 5
    #  LEGEND    --->    tfidfX = vector of dish somministrated
    #
    # example
    #            f1    f2     f3   ...
    # tfidf1     0.3   0.4    1
    # tfidf2     0.4   0.2    0.8
    # tfidf3     0.2   0.4    1
    # tfidf4     0.5   0.3    0.7
    # tfidf5     0.2   0.2    1

    # *************NOW RATES ARE ALL 5 (USER LIKED A DISH -> RATE = 5)**************
    # ([0.3 0.4 0.2] + [0.4 0.2 0.4] + ...  + ..... + ....) /5= we obtain a new vector
    # output = user profile vector

    start, finish = returnIndexesByMacroCateg(usersGlobalVariables[str(update.callback_query.from_user.id)]["userChoiceMacroCategoryGlobal"])

    if usersGlobalVariables[str(update.callback_query.from_user.id)]["flagEmergencyRecommendation"] is True:
        if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 4:
            tfidf1 = df.values[listOfTuples[0][0] - start]
            tfidf2 = df.values[listOfTuples[1][0] - start]
            tfidf3 = df.values[listOfTuples[2][0] - start]
            tfidf4 = df.values[listOfTuples[3][0] - start]

            sumList = [a + b + c + d for a, b, c, d in zip(tfidf1, tfidf2, tfidf3, tfidf4)]
            weightAvg = [elem / 4 for elem in sumList]
            userProfile = weightAvg
            usersGlobalVariables[str(update.callback_query.from_user.id)]["userProfileIngrAndScores"] = list(zip(nameIngredients, userProfile))
            fiveDishes = [listOfTuples[0][0] - start, listOfTuples[1][0] - start, listOfTuples[2][0] - start,
                          listOfTuples[3][0] - start]  # list containing the index of somministrated dishes
            updatedDf = df.drop(df.index[[fiveDishes[0], fiveDishes[1], fiveDishes[2], fiveDishes[3]]])
        elif usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 3:
            tfidf1 = df.values[listOfTuples[0][0] - start]
            tfidf2 = df.values[listOfTuples[1][0] - start]
            tfidf3 = df.values[listOfTuples[2][0] - start]
            sumList = [a + b + c for a, b, c in zip(tfidf1, tfidf2, tfidf3)]
            weightAvg = [elem / 3 for elem in sumList]
            userProfile = weightAvg
            usersGlobalVariables[str(update.callback_query.from_user.id)]["userProfileIngrAndScores"] = list(
                zip(nameIngredients, userProfile))
            fiveDishes = [listOfTuples[0][0] - start, listOfTuples[1][0] - start,
                          listOfTuples[2][0] - start]  # list containing the index of somministrated dishes
            updatedDf = df.drop(df.index[[fiveDishes[0], fiveDishes[1], fiveDishes[2]]])
        elif usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 2:
            tfidf1 = df.values[listOfTuples[0][0] - start]
            tfidf2 = df.values[listOfTuples[1][0] - start]
            sumList = [a + b for a, b in zip(tfidf1, tfidf2)]
            weightAvg = [elem / 2 for elem in sumList]
            userProfile = weightAvg
            usersGlobalVariables[str(update.callback_query.from_user.id)]["userProfileIngrAndScores"] = list(
                zip(nameIngredients, userProfile))
            fiveDishes = [listOfTuples[0][0] - start,
                          listOfTuples[1][0] - start]  # list containing the index of somministrated dishes
            updatedDf = df.drop(df.index[[fiveDishes[0], fiveDishes[1]]])
        elif usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 1:
            tfidf1 = df.values[listOfTuples[0][0] - start]
            userProfile = tfidf1
            usersGlobalVariables[str(update.callback_query.from_user.id)]["userProfileIngrAndScores"] = list(
                zip(nameIngredients, userProfile))
            fiveDishes = [listOfTuples[0][0] - start]  # list containing the index of somministrated dishes
            updatedDf = df.drop(df.index[[fiveDishes[0]]])
    else:
        tfidf1 = df.values[listOfTuples[0][0] - start]
        tfidf2 = df.values[listOfTuples[1][0] - start]
        tfidf3 = df.values[listOfTuples[2][0] - start]
        tfidf4 = df.values[listOfTuples[3][0] - start]
        tfidf5 = df.values[listOfTuples[4][0] - start]
        sumList = [a + b + c + d + e for a, b, c, d, e in zip(tfidf1, tfidf2, tfidf3, tfidf4, tfidf5)]
        weightAvg = [elem / 5 for elem in sumList]

        userProfile = weightAvg

        # Store in a global var the dict ingrNameUssProfile:score
        usersGlobalVariables[str(update.callback_query.from_user.id)]["userProfileIngrAndScores"] = list(zip(nameIngredients, userProfile))

        # [111, 321, 7, 295, 322]
        fiveDishes = [listOfTuples[0][0] - start, listOfTuples[1][0] - start, listOfTuples[2][0] - start,
                      listOfTuples[3][0] - start,
                      listOfTuples[4][0] - start]  # list containing the index of somministrated dishes

        # def checkIfDuplicates_1(listOfElems):
        #    ''' Check if given list contains any duplicates '''
        #    if len(listOfElems) == len(set(listOfElems)):
        #        return False
        #    else:
        #        return True

        # print("Check for duplicates, this created problems in the past", checkIfDuplicates_1(list(df.index)))

        # Removed the 5 rows from the dataframe of item profiles
        updatedDf = df.drop(df.index[[fiveDishes[0], fiveDishes[1], fiveDishes[2], fiveDishes[3], fiveDishes[4]]])

    # Create user profile dataframe
    userProfileDf = pd.DataFrame([userProfile], columns=nameIngredients, index=["User profile"])

    # Add user profile to item profiles dataframe in order to compute the cosine similarity
    if not userProfileDf.empty:
        updatedDf2 = pd.concat([updatedDf, userProfileDf])
    else:
        updatedDf2 = updatedDf.append(pd.DataFrame([userProfile], columns=nameIngredients), ignore_index=True)
        if updatedDf2.empty:
            # A series object with the same index as DataFrame
            updatedDf2 = updatedDf.append(pd.Series(userProfile, index=nameIngredients), ignore_index=True)

    # Perform cosine similarity
    cosineSim = cosine_similarity(updatedDf2)

    # recommendation list to be generated
    recommendation = []

    if usersGlobalVariables[str(update.callback_query.from_user.id)]["flagEmergencyRecommendation"] is True:
        if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 4:
            usProfCosSimItemProf = cosineSim[496]
        if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 3:
            usProfCosSimItemProf = cosineSim[497]
        if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 2:
            usProfCosSimItemProf = cosineSim[498]
        if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] == 1:
            usProfCosSimItemProf = cosineSim[499]
    else:
        # get last row (the user profile cos sim with other rows ... NB we have removed X (1 up to 5) rows -> -numeroLikes
        usProfCosSimItemProf = cosineSim[495]  # -numeroLikes get the last row of cosine similarity matrix: compared user profile with all other item profiles

    # create a list that matches name of dishes and cosine similarity weight
    for name, cosine in zip(updatedDf2.index, usProfCosSimItemProf):
        recommendation.append((name, cosine))

    recommendation.pop()  # remove the last element (the one representing the user profile = 1)

    # we obtain a list of dishes with cosine similarity scores THAT SHOULD BE SORTED BY DECREASING ORDER OF THE SCORES

    # SCAN RECOMMENDATION LIST TO REMOVE DISHES THAT ARE NOT PREESENT IN MENUAFTER CONSTRAINTS (BECAUSE WE USE THE TFIDF MATRIX PREGENERATED
    # IT'S MORE EFFICIENT INSTEAD OF PERFORMING IT EVERYTIME...Scan reversed recommendation list and remove disehs (we have already the finished recommendation list to be shown)

    # Rare problem: the recommendation list is empty (SEE DOWN)


    # GO TO NEXT STEPS


    # _____________________SECTION USEFUL FOR RECOMMENDATION EXPLANATION____________________________________

    import numpy as np

    # Sort by score
    sortedIngrAndScoreList = sorted(usersGlobalVariables[str(update.callback_query.from_user.id)]["userProfileIngrAndScores"], key=lambda x: x[1], reverse=True)

    # Define a threshold for recommendation explanation step AS average of TfIdf scores
    tresholdTfIdf = np.average([x[1] for x in usersGlobalVariables[str(update.callback_query.from_user.id)]["userProfileIngrAndScores"]])

    # get top n features of tf idf that are over the treshold! (later check the ones that are in the dish)
    ingrTfIdfOverTreshold = [elem[0] for elem in sortedIngrAndScoreList if elem[1] >= tresholdTfIdf]

    # global ingrTfIdfOverTresholdWithSpaces
    usersGlobalVariables[str(update.callback_query.from_user.id)]["ingrTfIdfOverTresholdWithSpaces"] = [getNameWithSpaces(elem, usersGlobalVariables[str(update.callback_query.from_user.id)]["userChoiceMacroCategoryGlobal"]) for elem in ingrTfIdfOverTreshold]

    # ____________________________________________ END ______________________________________________________


    nomiDishes = returnNamesDishMenuAfterConstr(macroCategNames[usersGlobalVariables[str(update.callback_query.from_user.id)]["userChoiceMacroCategoryGlobal"]],update)

    recommendation = [elem for elem in recommendation if elem[0] in nomiDishes]

    # Sort recommendation list by cosine scores
    recommendation.sort(key=lambda y: y[1], reverse=True)

    # propose a dish (first of recomm list generated......)
    # now use fitered menu obtained with intol check ::incaseskipintolstartfromstartmenu::

    if len(recommendation) == 0:
        print("(ERROR 5) END OF MENU for user ", str(update.message.from_user.id))
        update.message.reply_text('Mi dispiace...non posso consigliarti alcun piatto')

        del usersGlobalVariables[str(update.message.from_user.id)]
        return ConversationHandler.END


    # REALLY IMPORTANT STEP

    # function that turn the list of (name,cosine) in a list of sorted (same order) corresponding Piatto objects

    # RECOMMENDATION LIST (SORTED FROM THE MOST SIMILAR DISH TO USER PROFILE)
    usersGlobalVariables[str(update.callback_query.from_user.id)]["recommendationObjectList"] = turnToupleNameCosineListIntoObjectsList(recommendation)

    # RECOMMENDATION LIST SORTED USING FSA SCORE (SORTED FROM THE HEALTHIEST DISH)
    usersGlobalVariables[str(update.callback_query.from_user.id)]["recommendationObjectListSortedFSA"] = sortByFSA(usersGlobalVariables[str(update.callback_query.from_user.id)]["recommendationObjectList"])

    # Show the first dish of the rec list
    usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"] = usersGlobalVariables[str(update.callback_query.from_user.id)]["recommendationObjectList"][0]

    raccNome = 'Penso ti potrebbe piacere questo piatto: ' + traduciEnIt(usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].nome)
    update.effective_message.reply_text(raccNome, reply_markup=ReplyKeyboardRemove())
    usersGlobalVariables[str(update.callback_query.from_user.id)]["startPresentationDate"] = update.effective_message.date
    # Find the most similar dish to the proposed one and at the same time the healthiest
    mostSimAndHeal = findMostSimilarAndHealthiest(usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"], update)

    usersGlobalVariables[str(update.callback_query.from_user.id)]["listaDishesPairwiseRecommendation"] = []
    usersGlobalVariables[str(update.callback_query.from_user.id)]["listaDishesPairwiseRecommendation"].append(tuple((usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].idDishUrl, mostSimAndHeal.idDishUrl)))

    if usersGlobalVariables[str(update.callback_query.from_user.id)]["flagTextualVisualChoice"] == True:

        # Case Multi-modal or MM
        raccHealthierNome = 'Ma ti propongo anche una alternativa più salutare: ' + traduciEnIt(mostSimAndHeal.nome)  # BUT I PROPOSE YOU ALSO AN HEARTIER ALTERNATIVE
        update.effective_message.reply_text(raccHealthierNome, reply_markup=ReplyKeyboardRemove())

        # Reply the 2 images pairwise o let the user see the visual comparison
        update.effective_message.reply_media_group([InputMediaPhoto(usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].immagine), InputMediaPhoto(mostSimAndHeal.immagine)])




    else:
        # Case Textual or T

        raccHealthierNome = 'Ma ti propongo anche una alternativa più salutare: ' + traduciEnIt(mostSimAndHeal.nome)
        update.effective_message.reply_text(raccHealthierNome, reply_markup=ReplyKeyboardRemove())



    # _______________________________RECOMMENDATION EXPLANATION______________________

    if usersGlobalVariables[str(update.callback_query.from_user.id)]["flagSkippedAl"] == False or usersGlobalVariables[str(update.callback_query.from_user.id)]["boolFirstConstr"] == True:
        messDis = 'Ti raccomando queste portate di ' + traduciEnIt(str(macroCategNames[usersGlobalVariables[str(update.callback_query.from_user.id)]["userChoiceMacroCategoryGlobal"]]).lower()) + ' perchè so che hai dei vincoli dovuti a: ' + ", ".join([traduciEnIt(x.lower()) for x in usersGlobalVariables[str(update.callback_query.from_user.id)]["memoryConstraints"]])
        update.effective_message.reply_text(messDis)
    else:
        macr = 'Ti raccomando questi piatti perchè so che stai cercando una portata di  ' + str(macroCategNames[usersGlobalVariables[str(update.callback_query.from_user.id)]["userChoiceMacroCategoryGlobal"]]).lower()
        update.effective_message.reply_text(macr)

    listIngrToShow = []
    for elem in usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].ingredienti:
        if elem in usersGlobalVariables[str(update.callback_query.from_user.id)]["ingrTfIdfOverTresholdWithSpaces"]:
            listIngrToShow.append(elem)

    if len(listIngrToShow) > 0:
        messIngrLiked = 'Il primo piatto proposto contiene ingredienti che ti potrebbero piacere: ' + ", ".join([traduciEnIt(x).lower() for x in listIngrToShow])
        update.effective_message.reply_text(messIngrLiked)

    kcalA = usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].calorie
    kjA = usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].kj100
    sugarA = usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].sugar100
    fatA = usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].fat100
    satfatA = usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].satfat100
    saltA = usersGlobalVariables[str(update.callback_query.from_user.id)]["dishToRecommend"].salt100

    kcalB = mostSimAndHeal.calorie
    kjB = mostSimAndHeal.kj100
    sugarB = mostSimAndHeal.sugar100
    fatB = mostSimAndHeal.fat100
    satfatB = mostSimAndHeal.satfat100
    saltB = mostSimAndHeal.salt100

    messHealthExplanation = 'Il secondo piatto proposto ha: \n';
    initLen = len(messHealthExplanation)

    if int(kcalB) < int(kcalA):
        messHealthExplanation += '• meno calorie (' + kcalB + ' Kcal) rispetto al primo (' + kcalA + ' Kcal) \n'
    if float(sugarB) < float(sugarA):
        messHealthExplanation += '• meno zuccheri rispetto al primo \n'
    if float(fatB) < float(fatA):
        messHealthExplanation += '• meno grassi rispetto al primo \n'
    if float(satfatB) < float(satfatA):
        messHealthExplanation += '• meno grassi saturi rispetto al primo \n'
    if float(saltB) < float(saltA):
        messHealthExplanation += '• meno sale rispetto al primo \n'

    if len(messHealthExplanation) > initLen:
        update.effective_message.reply_text(messHealthExplanation)

    usersGlobalVariables[str(update.callback_query.from_user.id)]["tempHealthyAlternative"] = mostSimAndHeal

    # __________________________________ END _______________________________________

    reply_keyboard = [['Mi piace la prima'], ['Mi piace la seconda'], ["Vorrei qualcos'altro..."]]
    update.effective_message.reply_text('Cosa ne pensi delle mie raccomandazioni?',
                                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return AFTERRECOMMENDATION



#*FUNC: function of the chatbot flow -> iterate on user decision after the recommendation (prefer first, second, or want something else -> iteration)

def afterRecommendation(update: Update, context: CallbackContext) -> int:
    global usersGlobalVariables
    userResponse = update.message.text

    usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] = usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] + 1

    if userResponse == 'Mi piace la prima':

        usersGlobalVariables[str(update.message.from_user.id)]["userFinalChoiceDish"] = usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectList"][usersGlobalVariables[str(update.message.from_user.id)]["nextInd"]]
        usersGlobalVariables[str(update.message.from_user.id)]["finalDishNotChosen"] = usersGlobalVariables[str(update.message.from_user.id)]["tempHealthyAlternative"].idDishUrl
        usersGlobalVariables[str(update.message.from_user.id)]["isUserFinalChoiceHealthy"] = False
        usersGlobalVariables[str(update.message.from_user.id)]["finishPresentationDate"] = update.message.date

        update.message.reply_text('Grazie per aver usato questo bot!', reply_markup=ReplyKeyboardRemove())

        reply_keyboard = [['1️⃣'], ['2️⃣'], ['3️⃣'], ['4️⃣'], ['5️⃣']]
        update.message.reply_text('Per favore lascia un feedback!',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

        return FINALRATINGS

    elif userResponse == 'Mi piace la seconda':

        usersGlobalVariables[str(update.message.from_user.id)]["userFinalChoiceDish"] = usersGlobalVariables[str(update.message.from_user.id)]["tempHealthyAlternative"]
        usersGlobalVariables[str(update.message.from_user.id)]["finalDishNotChosen"] = usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectList"][usersGlobalVariables[str(update.message.from_user.id)]["nextInd"]].idDishUrl
        usersGlobalVariables[str(update.message.from_user.id)]["isUserFinalChoiceHealthy"] = True
        usersGlobalVariables[str(update.message.from_user.id)]["finishPresentationDate"] = update.message.date

        update.message.reply_text('Grazie per aver usato questo bot!', reply_markup=ReplyKeyboardRemove())

        reply_keyboard = [['1️⃣'], ['2️⃣'], ['3️⃣'], ['4️⃣'], ['5️⃣']]
        update.message.reply_text('Per favore lascia un feedback!',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

        return FINALRATINGS

    elif userResponse == "Vorrei qualcos'altro...":
        usersGlobalVariables[str(update.message.from_user.id)]["nextInd"]+=1
        #remove usersGlobalVariables[str(update.message.from_user.id)]["tempHealthyAlternative"] from rec list e from health list

        #In order to avid to show always the same alternative, we propose to remove the shown item (since the user has asked for another one, she doesnt like the second dish), so alsways new items are shown
        elemToRemove = usersGlobalVariables[str(update.message.from_user.id)]["tempHealthyAlternative"]
        usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectList"].remove(elemToRemove)
        usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectListSortedFSA"].remove(elemToRemove)

        #check lenght lists
        if len(usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectList"]) != 0:

            if usersGlobalVariables[str(update.message.from_user.id)]["nextInd"] < len(usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectList"])-1:


                usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"] =  usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectList"][usersGlobalVariables[str(update.message.from_user.id)]["nextInd"]]

                raccNome = 'Penso ti potrebbe piacere questo piatto: ' + traduciEnIt(usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].nome)
                update.message.reply_text(raccNome, reply_markup=ReplyKeyboardRemove())

                # Find the most similar dish to the proposed one and at the same time the healthiest
                mostSimAndHeal = findMostSimilarAndHealthiestCopy(usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"], update)

                usersGlobalVariables[str(update.message.from_user.id)]["listaDishesPairwiseRecommendation"].append(tuple((usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].idDishUrl,mostSimAndHeal.idDishUrl)))

                if usersGlobalVariables[str(update.message.from_user.id)]["flagTextualVisualChoice"] == True:
                    # Multi-modal or MM
                    raccHealthierNome = 'Ma ti propongo anche una alternativa più salutare: ' + traduciEnIt(mostSimAndHeal.nome)  # BUT I PROPOSE YOU ALSO AN HEARTIER ALTERNATIVE
                    update.message.reply_text(raccHealthierNome, reply_markup=ReplyKeyboardRemove())

                    # Reply the 2 images pairwise o let the user see the visual comparison
                    update.message.reply_media_group([InputMediaPhoto(usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].immagine),InputMediaPhoto(mostSimAndHeal.immagine)])

                else:
                    # Textual or T

                    raccHealthierNome = 'Ma ti propongo anche una alternativa più salutare: ' + traduciEnIt(mostSimAndHeal.nome)
                    update.message.reply_text(raccHealthierNome, reply_markup=ReplyKeyboardRemove())



                # _______________________________RECOMMENDATION EXPLANATION______________________

                if usersGlobalVariables[str(update.message.from_user.id)]["flagSkippedAl"] == False or usersGlobalVariables[str(update.message.from_user.id)]["boolFirstConstr"] == True:
                    messDis = 'Ti raccomando queste portate di ' + traduciEnIt(str(macroCategNames[usersGlobalVariables[str(update.message.from_user.id)]["userChoiceMacroCategoryGlobal"]]).lower()) + '  perchè so che hai dei vincoli dovuti a: ' + ", ".join([traduciEnIt(x.lower()) for x in usersGlobalVariables[str(update.message.from_user.id)]["memoryConstraints"]])
                    update.message.reply_text(messDis)
                else:
                    macr = 'Ti raccomando questi piatti perchè so che stai cercando una portata di ' + str(macroCategNames[usersGlobalVariables[str(update.message.from_user.id)]["userChoiceMacroCategoryGlobal"]]).lower()
                    update.message.reply_text(macr)

                listIngrToShow = []
                for elem in usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectList"][usersGlobalVariables[str(update.message.from_user.id)]["nextInd"]].ingredienti:
                    if elem in usersGlobalVariables[str(update.message.from_user.id)]["ingrTfIdfOverTresholdWithSpaces"]:
                        listIngrToShow.append(elem)

                if len(listIngrToShow) > 0:
                    messIngrLiked = 'Il primo piatto proposto contiene ingredienti che ti potrebbero piacere: ' + ", ".join([traduciEnIt(x).lower() for x in listIngrToShow])
                    update.message.reply_text(messIngrLiked)


                kcalA = usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].calorie
                kjA = usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].kj100
                sugarA = usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].sugar100
                fatA = usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].fat100
                satfatA = usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].satfat100
                saltA = usersGlobalVariables[str(update.message.from_user.id)]["dishToRecommend"].salt100

                kcalB = mostSimAndHeal.calorie
                kjB = mostSimAndHeal.kj100
                sugarB = mostSimAndHeal.sugar100
                fatB = mostSimAndHeal.fat100
                satfatB = mostSimAndHeal.satfat100
                saltB = mostSimAndHeal.salt100

                messHealthExplanation = 'Il secondo piatto proposto ha: \n';
                initLen = len(messHealthExplanation)

                if int(kcalB) < int(kcalA):
                    messHealthExplanation += '• meno calorie (' + kcalB + ' Kcal) rispetto al primo (' + kcalA + ' Kcal) \n'
                if float(sugarB) < float(sugarA):
                    messHealthExplanation += '• meno zuccheri rispetto al primo \n'
                if float(fatB) < float(fatA):
                    messHealthExplanation += '• meno grassi rispetto al primo \n'
                if float(satfatB) < float(satfatA):
                    messHealthExplanation += '• meno grassi saturi rispetto al primo \n'
                if float(saltB) < float(saltA):
                    messHealthExplanation += '• meno sale rispetto al primo \n'

                if len(messHealthExplanation) > initLen:
                    update.message.reply_text(messHealthExplanation)

                usersGlobalVariables[str(update.message.from_user.id)]["tempHealthyAlternative"] = mostSimAndHeal

                # __________________________________ END _______________________________________

                reply_keyboard = [['Mi piace la prima'], ['Mi piace la seconda'], ["Vorrei qualcos'altro..."]]
                update.message.reply_text('Cosa ne pensi delle mie raccomandazioni?', reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

                return AFTERRECOMMENDATION
            else:
                print("(ERROR 6) EXCEED IN ASKING FOR SOMETHING DIFFERENT for user ", str(update.message.from_user.id))
                update.message.reply_text('Mi dispiace...non posso consigliarti alcun piatto')
                usersGlobalVariables[str(update.message.from_user.id)]["userFinalChoiceDish"] = None
                usersGlobalVariables[str(update.message.from_user.id)]["isUserFinalChoiceHealthy"] = None
                update.message.reply_text('Grazie per aver usato questo bot!', reply_markup=ReplyKeyboardRemove())

                reply_keyboard = [['1️⃣'], ['2️⃣'], ['3️⃣'], ['4️⃣'], ['5️⃣']]
                update.message.reply_text('Per favore lascia un feedback!',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
                return FINALRATINGS
        else:
            print("(ERROR X) EXCEED IN ASKING FOR SOMETHING DIFFERENT for user ", str(update.message.from_user.id))
            update.message.reply_text('Mi dispiace...non posso consigliarti alcun piatto')
            usersGlobalVariables[str(update.message.from_user.id)]["userFinalChoiceDish"] = None
            usersGlobalVariables[str(update.message.from_user.id)]["isUserFinalChoiceHealthy"] = None
            update.message.reply_text('Grazie per aver usato questo bot!', reply_markup=ReplyKeyboardRemove())

            reply_keyboard = [['1️⃣'], ['2️⃣'], ['3️⃣'], ['4️⃣'], ['5️⃣']]
            update.message.reply_text('Per favore lascia un feedback!',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return FINALRATINGS



#FUNC: return name of igredients with space

def getNameWithSpaces(name, macroCateg):

    if macroCateg == "Pasta 🍝":
        categFile = "allIngrPastaSpaces.txt"
    elif macroCateg == "Insalata 🥗":
        categFile = "allIngrSaladSpaces.txt"
    elif macroCateg == "Dessert 🧁":
        categFile = "allIngrDessertSpaces.txt"
    elif macroCateg == "Snack 🍟":
        categFile = "allIngrSnackSpaces.txt"

    lista = []
    with open(categFile) as file:
        nameIngredients = file.read().splitlines()
        lista = [(elem,similar(name,elem)) for elem in nameIngredients]
        listaSorted = sorted(lista, key=lambda x: x[1], reverse=True)

    return listaSorted[0][0]


#FUNC: return list of names of menuafterconstraints items
def returnNamesDishMenuAfterConstr(macroCateg,update):
    lista = []

    for elem in usersGlobalVariables[str(update.callback_query.from_user.id)]["menuAfterConstraintsCheck"]:
        if elem.macroCategoria == macroCateg:
            lista.append(elem.nome)

    return lista


#FUNC: return ojects given name and cosine
def turnToupleNameCosineListIntoObjectsList(lista):
    objectsList = []
    #lista is the sorted list of dishes based on the cosine similarity score
    for name, cosine in lista:
        for elem in menu:
            if name == elem.nome:
                objectsList.append(elem)

    #if(len(objectsList)==len(lista)):
    #   print("ITS OK: correctly turned list of touples (name,cos) in list ob objects")
    return objectsList


#FUNC: sorts the recommendation list by FSA score

def sortByFSA(recList):
    listSortByFSA = recList.copy()
    #Sort recommendation list based on FSA score!
    listSortByFSA.sort(key=lambda x: int(x.FSAscore), reverse=False)
    return listSortByFSA


#FUNC: finds the best item in terms of healthiness and similarity to the actual dish of recommendation list presented to the user

def findMostSimilarAndHealthiest(dishToRecommend,update):
    listaSortFSA = usersGlobalVariables[str(update.callback_query.from_user.id)]["recommendationObjectListSortedFSA"]
    listaRec = usersGlobalVariables[str(update.callback_query.from_user.id)]["recommendationObjectList"]

    indexDishToRecommend = listaRec.index(dishToRecommend)

    tupleIndexes = []

    nElem = len(listaRec)
    # start by NEXT ELEMENT
    for idx in range(indexDishToRecommend+1,nElem):
        elem = listaRec[idx]
        #Valutare di rimuovere elementi considerati PER EVITARE RIDONDANZA, RISCHIO STESSI VALORI
        simInd = listaRec.index(elem)
        healInd = listaSortFSA.index(elem)
        avg = 0.4*simInd + 0.6*healInd
        tupleIndexes.append((elem,avg))

    healthierAlternative = min(tupleIndexes,key = lambda x: x[1])
    return healthierAlternative[0]

def findMostSimilarAndHealthiestCopy(dishToRecommend,update):
    listaSortFSA = usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectListSortedFSA"]
    listaRec = usersGlobalVariables[str(update.message.from_user.id)]["recommendationObjectList"]

    indexDishToRecommend = listaRec.index(dishToRecommend)

    tupleIndexes = []

    nElem = len(listaRec)
    # start by NEXT ELEMENT
    for idx in range(indexDishToRecommend+1,nElem):
        elem = listaRec[idx]
        #Valutare di rimuovere elementi considerati PER EVITARE RIDONDANZA, RISCHIO STESSI VALORI
        simInd = listaRec.index(elem)
        healInd = listaSortFSA.index(elem)
        avg = 0.4*simInd + 0.6*healInd
        tupleIndexes.append((elem,avg))

    healthierAlternative = min(tupleIndexes,key = lambda x: x[1])
    return healthierAlternative[0]


#FUNC: return useful file names given the macrocategory chosen by user

def returnFilesNamesByMacroCateg(macroCateg):
    ingrNames = None
    dishNames = None
    tfIdfMenu = None

    if macroCateg == "Pasta 🍝":
        ingrNames = "tfIdfIngredientsNamesPasta.txt"
        dishNames = "tfIdfDishesNamesPasta.txt"
        tfIdfMenu = "tfIdfMenuPasta.csv"
    elif macroCateg == "Insalata 🥗":
        ingrNames = "tfIdfIngredientsNamesSalad.txt"
        dishNames = "tfIdfDishesNamesSalad.txt"
        tfIdfMenu = "tfIdfMenuSalad.csv"
    elif macroCateg == "Dessert 🧁":
        ingrNames = "tfIdfIngredientsNamesDessert.txt"
        dishNames = "tfIdfDishesNamesDessert.txt"
        tfIdfMenu = "tfIdfMenuDessert.csv"
    elif macroCateg == "Snack 🍟":
        ingrNames = "tfIdfIngredientsNamesSnack.txt"
        dishNames = "tfIdfDishesNamesSnack.txt"
        tfIdfMenu = "tfIdfMenuSnack.csv"

    return ingrNames, dishNames, tfIdfMenu





#rimuovi flag non usati!!!
#inserisci nextind = 0 a choice modality


#*FUNC: function of the chatbot flow -> process all the information to store after the experiment

def finalRatings(update: Update, context: CallbackContext) -> int:

    global usersGlobalVariables

    usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] = usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"] + 1

    scenario = ''
    tinyScenario = ''

    if usersGlobalVariables[str(update.message.from_user.id)]["firstUserChoice"] == 'T':
        scenario = 'Scenario Textual'
        tinyScenario = 'TEXT'
    elif usersGlobalVariables[str(update.message.from_user.id)]["firstUserChoice"] == 'MM':
        scenario = 'Scenario Multi-modal (Text + Image)'
        tinyScenario = 'MM'

    rateUser = update.message.text

    usersGlobalVariables[str(update.message.from_user.id)]["finishSessionDate"] = update.message.date


    from datetime import datetime
    #new_dt = dt_string[:19] TO REMOVE +00:00
    dataFine = datetime.strptime(str(usersGlobalVariables[str(update.message.from_user.id)]["finishSessionDate"])[:19],'%Y-%m-%d %H:%M:%S')
    dataInizio = datetime.strptime(str(usersGlobalVariables[str(update.message.from_user.id)]["startSessionDate"])[:19],'%Y-%m-%d %H:%M:%S')

    dataInizioPrefElic = datetime.strptime(str(usersGlobalVariables[str(update.message.from_user.id)]["startPreferenceElicitationDate"])[:19],'%Y-%m-%d %H:%M:%S')
    dataFinePrefElic = datetime.strptime(str(usersGlobalVariables[str(update.message.from_user.id)]["finishPreferenceElicitationDate"])[:19],'%Y-%m-%d %H:%M:%S')

    dataInizioPresentation = datetime.strptime(str(usersGlobalVariables[str(update.message.from_user.id)]["startPresentationDate"])[:19],'%Y-%m-%d %H:%M:%S')
    dataFinePresentation = datetime.strptime(str(usersGlobalVariables[str(update.message.from_user.id)]["finishPresentationDate"])[:19], '%Y-%m-%d %H:%M:%S')

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    durataConversazione = int((dataFine - dataInizio).total_seconds())
    durataInteraction = int((dataFinePrefElic - dataInizioPrefElic).total_seconds())
    durataPresentation = int((dataFinePresentation - dataInizioPresentation).total_seconds())

    healthyChoice = usersGlobalVariables[str(update.message.from_user.id)]["isUserFinalChoiceHealthy"]

    if healthyChoice is not None:
        healthinessPreferredDishNutri = usersGlobalVariables[str(update.message.from_user.id)]["userFinalChoiceDish"].nutriScore
        healthinessPreferredDishFSA = usersGlobalVariables[str(update.message.from_user.id)]["userFinalChoiceDish"].FSAscore
    else:
        healthinessPreferredDishNutri = None
        healthinessPreferredDishFSA = None

    if healthyChoice is not None:
        idPreferredDish = usersGlobalVariables[str(update.message.from_user.id)]["userFinalChoiceDish"].idDishUrl
    else:
        idPreferredDish = None

    lineaDaInserire = []

    rateUserToSys = ''

    if rateUser == '1️⃣':
        rateUserToSys = '1'
    elif rateUser == '2️⃣':
        rateUserToSys = '2'
    elif rateUser == '3️⃣':
        rateUserToSys = '3'
    elif rateUser == '4️⃣':
        rateUserToSys = '4'
    elif rateUser == '5️⃣':
        rateUserToSys = '5'


    macroCatChoice = macroCategNames[usersGlobalVariables[str(update.message.from_user.id)]["userChoiceMacroCategoryGlobal"]]
    numeroTurni = usersGlobalVariables[str(update.message.from_user.id)]["counterInteractionTurns"]
    constraintsUser = usersGlobalVariables[str(update.message.from_user.id)]["memoryConstraints"]
    #N.B. START BY 0 (index elements in menu per category)
    dishesLikedByUser = list(usersGlobalVariables[str(update.message.from_user.id)]["userRates"].items())
    urlDishesLiked = [ menu[int(item[0])].idDishUrl for item in dishesLikedByUser]
    starsTo5Random = [5] * usersGlobalVariables[str(update.message.from_user.id)]["numberLikes"]
    urlDishesShownToUser = ','.join(str(elem) for elem in usersGlobalVariables[str(update.message.from_user.id)]["listaDishesShown"])
    urlDishesPairwiseRecommendation = ','.join(str(elem[0])+" - "+str(elem[1]) for elem in usersGlobalVariables[str(update.message.from_user.id)]["listaDishesPairwiseRecommendation"])
    finalDishNotChosen = usersGlobalVariables[str(update.message.from_user.id)]["finalDishNotChosen"]
    nSkips = usersGlobalVariables[str(update.message.from_user.id)]["numberSkips"]
    nLikes = usersGlobalVariables[str(update.message.from_user.id)]["numberLikes"]

    #------------------------------------------------------------------------------------------------------------------
    # user_telegram_id;date;scenario;macro_categ;final_rate_service;duration_in_sec;pref_elic_duration_in_sec;recomm_duration_in_sec;number_interactions;has_user_perfermed_a_healthy_choice;nutri_score;fsa_score;id_dish_choice;user_constraints;proposal_random_1;proposal_random_2;proposal_random_3;proposal_random_4;proposal_random_5;number_skips;number_likes;all_dishes_shown_pref_elic;url_dishes_pairwise_comparisons;final_dish_not_chosen
    if nLikes == 5:
        lineaDaInserire = [update.message.from_user.id,dt_string,scenario,macroCatChoice,rateUserToSys,durataConversazione,durataInteraction,durataPresentation,numeroTurni,healthyChoice,healthinessPreferredDishNutri,healthinessPreferredDishFSA,idPreferredDish,','.join(str(elem) for elem in constraintsUser),urlDishesLiked[0],urlDishesLiked[1],urlDishesLiked[2],urlDishesLiked[3],urlDishesLiked[4], nSkips, nLikes, urlDishesShownToUser, urlDishesPairwiseRecommendation, finalDishNotChosen]
    elif nLikes == 4:
        lineaDaInserire = [update.message.from_user.id,dt_string,scenario,macroCatChoice,rateUserToSys,durataConversazione,durataInteraction,durataPresentation,numeroTurni,healthyChoice,healthinessPreferredDishNutri,healthinessPreferredDishFSA,idPreferredDish,','.join(str(elem) for elem in constraintsUser),urlDishesLiked[0],urlDishesLiked[1],urlDishesLiked[2],urlDishesLiked[3],"/", nSkips, nLikes, urlDishesShownToUser, urlDishesPairwiseRecommendation, finalDishNotChosen]
    elif nLikes == 3:
        lineaDaInserire = [update.message.from_user.id,dt_string,scenario,macroCatChoice,rateUserToSys,durataConversazione,durataInteraction,durataPresentation,numeroTurni,healthyChoice,healthinessPreferredDishNutri,healthinessPreferredDishFSA,idPreferredDish,','.join(str(elem) for elem in constraintsUser),urlDishesLiked[0],urlDishesLiked[1],urlDishesLiked[2],"/","/", nSkips, nLikes, urlDishesShownToUser, urlDishesPairwiseRecommendation, finalDishNotChosen]
    elif nLikes == 2:
        lineaDaInserire = [update.message.from_user.id,dt_string,scenario,macroCatChoice,rateUserToSys,durataConversazione,durataInteraction,durataPresentation,numeroTurni,healthyChoice,healthinessPreferredDishNutri,healthinessPreferredDishFSA,idPreferredDish,','.join(str(elem) for elem in constraintsUser),urlDishesLiked[0],urlDishesLiked[1],"/","/","/", nSkips, nLikes, urlDishesShownToUser, urlDishesPairwiseRecommendation, finalDishNotChosen]
    elif nLikes == 1:
        lineaDaInserire = [update.message.from_user.id,dt_string,scenario,macroCatChoice,rateUserToSys,durataConversazione,durataInteraction,durataPresentation,numeroTurni,healthyChoice,healthinessPreferredDishNutri,healthinessPreferredDishFSA,idPreferredDish,','.join(str(elem) for elem in constraintsUser),urlDishesLiked[0],"/","/","/","/", nSkips, nLikes, urlDishesShownToUser, urlDishesPairwiseRecommendation, finalDishNotChosen]


    import csv
    f = open("ratings.csv", "a")
    writer = csv.writer(f, delimiter=";")
    writer.writerow(lineaDaInserire)
    f.close()

    update.message.reply_text('Grazie per il tuo feedback! 😘', reply_markup=ReplyKeyboardRemove())

    cancel(update, context)
    return 0




# *FUNC: function of the chatbot flow -> cancel conversation

def cancel(update: Update, context: CallbackContext):
    """Cancels and ends the conversation."""
    user = update.message.from_user

    logger.info("User %s canceled the conversation.", user.id)
    update.message.reply_text('Ciao! Grazie per aver interagito con me!')

    del usersGlobalVariables[str(update.message.from_user.id)]
    return ConversationHandler.END


def main() -> None:
    # Fill the menu list starting from dataset
    creaMenu()

    #from pprint import pprint
    #pprint(vars(menu[0]))

    # Create the Updater and pass it the bot's token.
    updater = Updater("5330562880:AAHX0LkiEhBCm24ygUVwch9ugq6-O0-yDJU")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOICEMODALITY: [MessageHandler(Filters.text, choiceModality)],
            FUNCTCALLBACK: [CallbackQueryHandler(zero, pattern='^' + str(0) + '$'),
                            CallbackQueryHandler(one, pattern='^' + str(1) + '$'),
                            CallbackQueryHandler(two, pattern='^' + str(2) + '$'),
                            CallbackQueryHandler(three, pattern='^' + str(3) + '$'),
                            CallbackQueryHandler(four, pattern='^' + str(4) + '$'),
                            CallbackQueryHandler(five, pattern='^' + str(5) + '$'),
                            CallbackQueryHandler(six, pattern='^' + str(6) + '$'),
                            CallbackQueryHandler(goToOtherConstraints, pattern='^' + str(7) + '$')],
            PROCESSUSERCONSTRAINTS: [MessageHandler(Filters.text, processUserConstraints)],
            FUNCTCALLBACK2: [CallbackQueryHandler(likeDishN, pattern='^' + "Like" + '$'),
                             CallbackQueryHandler(skipDishN, pattern='^' + "Skip" + '$')],
            AFTERRECOMMENDATION: [MessageHandler(Filters.text, afterRecommendation)],
            FINALRATINGS: [MessageHandler(Filters.text, finalRatings)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(CommandHandler('cancel', cancel))
    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling(timeout=15)  # timeout=600

    updater.idle()


if __name__ == '__main__':
    main()
