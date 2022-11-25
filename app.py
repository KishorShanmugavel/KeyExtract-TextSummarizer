import PyPDF2
from flask import Flask, flash, request, redirect, url_for, render_template
import urllib.request
import os
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup
import requests
import random
import nltk
import pandas as pd
import validators
from keybert import KeyBERT
# from sumy.nlp.tokenizers import Tokenizer
# from sumy.summarizers.luhn import LuhnSummarizer
# from sumy.parsers.plaintext import PlaintextParser


app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads/'

app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['pdf'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def next(lis):
    lis.replace("\n", "-")
    #new_set = [x.replace('\n', '-') for x in lis]
    #res = ' '.join([str(ele) for ele in new_set])
    return lis



def get_wiki_content(url):
    valid = validators.url(url)
    if valid == True:
        req_obj = requests.get(url)
        text = req_obj.text
        soup = BeautifulSoup(text)
        all_paras = soup.find_all("p")
        wiki_text = ''
        for para in all_paras:
            wiki_text += para.text
        return wiki_text
    return -1


def top10_sent(url):
    stopwords = nltk.corpus.stopwords.words("english")
    sentences = nltk.sent_tokenize(url)
    words = nltk.word_tokenize(url)
    word_freq = {}
    for word in words:
        if word not in stopwords:
            if word not in word_freq:
                word_freq[word] = 1
            else:
                word_freq[word] += 1

    try:
        max_word_freq = max(word_freq.values())
    except:
        return url

    for key in word_freq.keys():
        word_freq[key] /= max_word_freq

    sentences_score = []
    for sent in sentences:
        curr_words = nltk.word_tokenize(sent)
        curr_score = 0
        for word in curr_words:
            if word in word_freq:
                curr_score += word_freq[word]
        sentences_score.append(curr_score)

    sentences_data = pd.DataFrame({"sent": sentences, "score": sentences_score})
    sorted_data = sentences_data.sort_values(by="score", ascending=False).reset_index()

    top10_rows = sorted_data.iloc[0:6, :]
    s = " ".join(list(top10_rows["sent"]))
    k = list(top10_rows["sent"])
    return s

# def methtwo(url):
#     parser = PlaintextParser.from_string(url, Tokenizer("english"))
#     summarizer_luhn = LuhnSummarizer()
#     summary_1 = summarizer_luhn(parser.document, 6)
#     dp = []
#     for i in summary_1:
#         lp = str(i)
#     dp.append(lp)
#     final_sentence = ' '.join(dp)
#     return final_sentence

def fstop(x):
    punctuations = '''"#$%&'()*+.:<=>?[]^_`{|}~'''

    no_punct = ""
    for char in x:
        if char not in punctuations:
            no_punct = no_punct + char

    return no_punct


def get_bert(t):
    res=[]
    kw_model = KeyBERT(model='all-mpnet-base-v2')
    keywords = kw_model.extract_keywords(t, keyphrase_ngram_range=(1, 3), stop_words='english', highlight=False,
                                         top_n=10)
    keywords_list = list(dict(keywords).keys())
    if (len(keywords_list) > 15):
        for i in range(10):
            r = random.choice(keywords_list)
            keywords_list.remove(r)
            res.append(r)
    else:
        res = keywords_list
    res = ' , '.join([str(ele) for ele in res])
    return res




@app.route('/')
def home():
  return render_template('mymain.html')


@app.route('/log')
def log():
  return render_template('text.html')

@app.route('/pdd')
def pdd():
  return render_template('pdf.html')


@app.route('/pdf', methods=['POST'])
def pdf():

    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No file selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # print('upload_image filename: ' + filename)
        a_path = "static/uploads/"
        joined_path = os.path.join(a_path, filename)
        text = ""
        with open(joined_path, 'rb') as pdf_file:
            read_pdf = PyPDF2.PdfFileReader(pdf_file)
            number_of_pages = read_pdf.getNumPages()
            for page_number in range(number_of_pages):  # use xrange in Py2
                page = read_pdf.getPage(page_number)
                try:
                    page_content = page.extractText()
                except:
                    return redirect(url_for('pdd'))
                #
                #age_content = page.extractText()
                #
                text = text + " " + page_content
        li = list(text.split(" "))
        while ("" in li):
            li.remove("")
        text = " ".join(li)

        text=text.replace("\n","")

        operation = request.form.get("operation")
        s=text
        if (operation == 'Keywords'):
            s = fstop(text)
            res = get_bert(s)
        elif (operation == 'Summary'):
            punctuations = ''',!"#$%&'*+:;<=>?[]^_`{|}~-'''

            no_punct = ""
            for char in s:
                if char not in punctuations:
                    no_punct = no_punct + char
            s=no_punct
            r = top10_sent(s)
            res=r


        pdf_file.close()
        os.remove(joined_path)

        return render_template("pdf.html", itsy="{}".format(res),op="{}".format(operation),filename=filename)
        #return render_template("v2.html", itsy="{}".format(text), filename=filename)
        #return render_template('indexi.html', filename=filename)
    else:
        flash('Allowed image types are - png, jpg, jpeg, gif')
        return redirect(request.url)


@app.route('/pdf/<filename>')
def display_image(filename):
    # print('display_image filename: ' + filename)
    return redirect(url_for('static', filename='uploads/' + filename), code=301)

@app.route("/predict", methods = ["POST",'GET'])
def predict():
    text = request.form.get('iptext')
    operation = request.form.get("operation")
    contype = request.form.get("contype")
    res = []
    print(contype)
    if (contype == 'URL'):
        full = get_wiki_content(text)
        if(full==-1):
            return redirect(url_for('log'))

        s = full
    elif (contype == 'Text'):
        s = text
    if (operation == 'Keywords'):
        s=fstop(s)
        res = get_bert(s)
    elif (operation == 'Summary'):
        punctuations = ''',!"#$%&'*+:;<=>?[]^_`{|}~-'''

        no_punct = ""
        for char in s:
            if char not in punctuations:
                no_punct = no_punct + char
        s = no_punct
        li = list(s.split(" "))
        while ("" in li):
            li.remove("")

        text = " ".join(li)
        text = text.replace("\n", "")
        s=text
        result = top10_sent(s)
        res = next(result)
        return render_template("text.html", itsy="{}".format(res),op="{}".format(operation))


    else:
        res = 'INVALID CHOICE'



    return render_template("text.html", itsy="{}".format(res),op="{}".format(operation))




if __name__ == "__main__":
    app.run(debug=True)