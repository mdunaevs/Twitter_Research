#!/usr/bin/env python
# coding: utf-8

# In[1]:


import time
import csv
import xlrd
import json
import twitter_col
import pandas as pd


# In[2]:


# Preliminary functions
def getThreeGrams(text):
    broken = text.split(' ')
    nwords = len(broken)
    broken.extend([broken[i] + ' ' + broken[i+1] for i in range(nwords-1)])
    broken.extend([broken[i] + ' ' + broken[i+1] + ' ' + broken[i+2] for i in range(nwords-2)])
    return(broken)


# In[8]:


# Reads a file
def readFile(filepath, inFile = 'JSON'):
    if(inFile == 'JSON'):
        df = twitter_col.parse_twitter_json(filepath, to_csv = False, sentiment = False)
        df = df[['id_str', 'status_id', 'status_text']]
        df.columns = ['user_id', 'status_id', 'status_text']
        df['status_text'] = [x.lower() for x in df['status_text']]
        return(df)
    
    if(inFile == 'CSV'):
        try:
            df = pd.read_csv(filepath, encoding = 'utf-8')
        except ValueError:
            df = pd.read_csv(filepath, encoding = 'ISO-8859-1')
            
        if (df.shape[1] > 2):
            try:
                df = df[['id_str', 'status_id', 'status_text']]
            except KeyError:
                df = df[['user_id', 'status_id', 'status_text']]
        else:
            df.columns = ['status_id', 'status_text']
        
        df['status_text'] = [str(x).lower() for x in df['status_text']]
        return(df)
    
    if(inFile == 'Reddit'):
        try:
            df = pd.read_csv(filepath, encoding = 'utf-8')
        except ValueError:
            df = pd.read_csv(filepath, encoding = 'ISO-8859-1')
            
        df = df[['comment_id', 'comment_text']]
        df.columns = ['status_id', 'status_text']
        df['status_text'] = [x.lower() for x in df['status_text']]
        return(df)


# In[9]:


# Get words
categories = ['pronouns', 'absolutist', 'exclusive', 'abusive']

def getWords(dictpath = './dicts', langs = ['English']):
    start = time.time()
    wordlist = {}
    for cat in categories:
        print("Now doing word list for {}!".format(cat))
        wordlist[cat] = []
        
        wb = xlrd.open_workbook('{}/dict_{}.xlsx'.format(dictpath, cat))
        sheet = wb.sheet_by_index(0)
        catCol = -1
        
        for lang in langs:
            for i in range(sheet.ncols):
                if(sheet.cell_value(0, i) == lang):
                    langCol = i
            for i in range(sheet.ncols):
                if(sheet.cell_value(0, i) == "Category 1"):
                    catCol = i
            
            
            if (catCol >= 0):
                for i in range(1, sheet.nrows):
                    wordlist[cat].append((sheet.cell_value(i, langCol), sheet.cell_value(i, catCol)))
            else:
                for i in range(1, sheet.nrows):
                    wordlist[cat].append(sheet.cell_value(i, langCol))
    
    for cat in categories:
        if (cat == 'pronouns'):
            wordlist[cat] = [(x.lower(), y) for (x, y) in wordlist[cat] if x != '']
        elif (cat == 'absolutist'):
            wordlist[cat] = [(x.lower(), y) for (x, y) in wordlist[cat] if x != '']
        else:
            wordlist[cat] = [x.lower() for x in wordlist[cat] if x != '']
    
    print("Generated all word lists for {} languages in {:.2f} seconds!".format(len(langs), time.time() - start))
        
    return wordlist


# In[10]:


# Count words

def getCounts(tweet, wordlist):
    start = time.time()

    rowvec = []
    
    text = getThreeGrams(tweet)

    for cat in categories:
        #print('Now counting {}!'.format(cat))
        if(cat == 'pronouns'):
            subcats = ['first', 'second', 'third']
            for subcat in subcats:
                sublist = [x for (x, y) in wordlist[cat] if y == subcat]
                count = sum([text.count(word) for word in sublist])
                rowvec.append(count)
        elif(cat == 'absolutist'):
            subcats = ['absolutist', 'non-absolutist']
            for subcat in subcats:
                sublist = [x for (x, y) in wordlist[cat] if y == subcat]
                count = sum([text.count(word) for word in sublist])
                rowvec.append(count)
        else:
            count = sum([text.count(word) for word in wordlist[cat]])
            rowvec.append(count)
    
    return rowvec


# In[11]:


# Compute readability

def getReadability(tweet):
    tokens = tweet.split(' ')
    readability7 = len([x for x in tokens if len(x) >= 7])/len(tokens)
    readability8 = len([x for x in tokens if len(x) >= 8])/len(tokens)
    readability9 = len([x for x in tokens if len(x) >= 9])/len(tokens)
    readability = sum([readability7, readability8, readability9])/3
    readability = round(readability, 4)
    return readability


# In[12]:


def pennebake(filepath, inFile = 'JSON', dictpath = './dicts', langs = ['English']):
    start = time.time()
    counter = pd.DataFrame(columns = ['first', 'second', 'third', 'absolutist', 'non-absolutist', 'exclusive', 'abusive'])
    df = readFile(filepath, inFile)
    print("Going to do a file with {} tweets!".format(df.shape[0]))
    wordlist = getWords(dictpath, langs)
    
    i = 0
    for tweet in [x for x in df['status_text']]:
        #counter = counter.append(getCounts(tweet, wordlist = wordlist))
        counter.loc[i,:] = getCounts(tweet, wordlist = wordlist)
        i = i + 1
        
        if(i % 1000 == 0):
            print('Now done with {} tweets out of {} in {:.2f} seconds!'.format(i, df.shape[0], time.time() - start))
    
    if (inFile=='JSON'):
        counter['user_id'] = df['user_id']
        counter['status_id'] = df['status_id']   
        counter = counter[['user_id', 'status_id', 'first', 'second', 'third', 
                           'absolutist', 'non-absolutist', 'exclusive', 'abusive']]
    else:
        counter['status_id'] = df['status_id']
        counter = counter[['status_id', 'first', 'second', 'third', 
                           'absolutist', 'non-absolutist', 'exclusive', 'abusive']]
    print('Finished word counts in {:.2f} seconds!'.format(time.time() - start))
    
    counter['readability'] = [getReadability(x) for x in df['status_text']]
    counter.to_csv(filepath+'_pennebaked.csv', index = None)
    return(counter)