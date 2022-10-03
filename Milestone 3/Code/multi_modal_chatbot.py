import logging, csv

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, Update, \
    InputMediaPhoto
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

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# _______________________RETURN CODES (useful for identifying next function to be called)_________

CHOICEMODALITY, FUNCTCALLBACK, PROCESSUSERCONSTRAINTS, FUNCTCALLBACK2 = range(4)

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
    elif macroCateg == "Salad 🥗":
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

    # Set the index in order to define the modality of sys/user interaction
    # 0 for T
    # 1 for MM

    listOfModalities = ["T", "MM"]
    usersGlobalVariables[str(update.message.from_user.id)]["userChoiceModalityGlobal"] = listOfModalities[0]

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
        userConstraints = [each_string.lower() for each_string in userConstraints]  # lower case
        userConstraints = [each_string.strip() for each_string in
                           userConstraints]  # remove spaces before and after strings
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

        #RETURN FUNCTION FOR PROCESSING

    else:
        # CONDIZIONE PER CONTROLLARE CHE INDICE NON SIA OLTRE DISPONIBILITA DI MENUAFTER CONSTRAINT
        if (usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] + usersGlobalVariables[str(update.callback_query.from_user.id)]["numberSkips"]) >= usersGlobalVariables[str(update.callback_query.from_user.id)]["dishesToShow"]:
            if usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"] > 0:
                #GESTIONE USER PROFILE E MESSAGGIO SIMBOLICO E SOPRATTUTTO FLAGS
                stringa="like"
                update.effective_message.reply_text("Ok, hai fornito solo ", usersGlobalVariables[str(update.callback_query.from_user.id)]["numberLikes"], stringa,", che non è abbastanza. Comunque proverò a raccomandarti qualcosa...")
                usersGlobalVariables[str(update.callback_query.from_user.id)]["finishPreferenceElicitationDate"] = update.effective_message.date
                usersGlobalVariables[str(update.callback_query.from_user.id)]["flagEmergencyRecommendation"] = True

                #RETURN FUNCTION FOR PROCESSING
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

                #RETURN FUNCTION FOR PROCESSING
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



#rimuovi flag non usati!!!
#inserisci nextind = 0 a choice modality

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
    updater = Updater("YOUR API KEY :)")

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
                             CallbackQueryHandler(skipDishN, pattern='^' + "Skip" + '$')]
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
