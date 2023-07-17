from django.shortcuts import render
import base64
import json
import requests
from rest_framework.response import Response
from rest_framework.views import APIView
from dotenv import load_dotenv
import os
import requests
import random
from email.message import EmailMessage
import ssl
import smtplib
from django.shortcuts import render
from django.template.loader import render_to_string
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()


def sendEmail(emailRecipient, emailSubject, emailBody):
    emailSender = os.getenv('MY_EMAIL')
    emailPassword = os.getenv('MY_PASSWORD')

    em = EmailMessage()
    em['From'] = emailSender
    em['To'] = emailRecipient
    em['subject'] = emailSubject
    em.set_content(emailBody, subtype='html')

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(emailSender, emailPassword)
        smtp.sendmail(emailSender, emailRecipient, em.as_string())

def generateRandomNumbers(min_value, max_value, count):
    if int(count) >= (max_value - min_value + 1):
        numbers = list(range(min_value, max_value + 1))
    else:
        numbers = random.sample(range(min_value, max_value + 1), int(count))
    
    return numbers

def generateRandomDistribution(databaseCount, count):
    count = int(count)
    helperArray = list(range(databaseCount))
    random.shuffle(helperArray)

    counts = []
    remaining_count = count

    for i in range(databaseCount):
        if i == databaseCount - 1:
            assigned_count = remaining_count
        else:
            assigned_count = random.randint(0, remaining_count)
        
        counts.append(assigned_count)
        remaining_count -= assigned_count

    return counts

def convertRichText(richText):
    html = ""
    
    for element in richText:
        content = element['text']['content']
        annotations = element['annotations']
        href = element['href']
        
        if annotations.get('bold'):
            content = f"<strong>{content}</strong>"
        
        if annotations.get('italic'):
            content = f"<em>{content}</em>"
        
        if annotations.get('strikethrough'):
            content = f"<del>{content}</del>"
        
        if annotations.get('underline'):
            content = f"<u>{content}</u>"
        
        if annotations.get('code'):
            content = f"<code>{content}</code>"
        
        if href:
            content = f"<a href='{href}'>{content}</a>"
        
        if '\n' in content:
            content = content.replace('\n', '<br>')
        
        html += content
    
    return html


def getPagePropertiesHTML(properties):
    propertiesHTML = ""
    richTextHtml = ""
    for pro in properties:
        if not isinstance(pro["value"], list):
            richTextHtml = pro["value"]
        else:
            richTextHtml = convertRichText(pro["value"])
        
        propertiesHTML += f'<div class="pageProperties"><b>{pro["key"]}: </b><p class="pageProperties">{richTextHtml}</p></div>'

    
    return propertiesHTML

def getPagesHTML(pages):
    pagesHTML = '<div class="pages">'
    index = 1
    for page in pages:
        pagesHTML += f'<div class="page"><div class="pageCover"><div class="pageCoverHeading">{index}. {page["title"]}</div><img class="pageCoverImage" alt="cover" style="display: {page["cover"]}" src="{page["cover"]}"/></div>{getPagePropertiesHTML(page["properties"])}</div>'
        pagesHTML += f'<a class="goToPage" href="{page["url"]}">Go to the page for more!</a>'
        index += 1

    pagesHTML += '</div>'

    return pagesHTML

def getDatabaseHTML(database):
    databaseInfo = database["about"]
    databasePages = database["pages"]
    pagesHTML = getPagesHTML(databasePages)

    databaseHTML = '<div class="database">'
    databaseHTML += f'<div class="databaseCover"><img class="databaseCoverImage" style="display: {databaseInfo["cover"]}" alt="cover" src="{databaseInfo["cover"]}"/><div class="databaseCoverHeading">{databaseInfo["icon"]} <a style="color: black" href="{databaseInfo["url"]}">{databaseInfo["name"]}</a></div></div>{pagesHTML}'
    databaseHTML += '</div>'
    return databaseHTML

def getAllTheDatabasesHTML(databases):
    databasesHTML = '<div class="databases">'
    for database in databases:
        databasesHTML += f'{getDatabaseHTML(database)}'
    databasesHTML += '</div>'

    return databasesHTML

def getEmailBody(databases):
    beforeHtmlPath = f"{BASE_DIR}/Apis/templates/before.txt"
    afterHtmlPath =  f"{BASE_DIR}/Apis/templates/after.txt"
    beforeHtmlString = ""
    afterHtmlString = ""

    with open(beforeHtmlPath, 'r') as file:
        beforeHtmlString = file.read()

    with open(afterHtmlPath, 'r') as file:
        afterHtmlString = file.read()
    
    wholeHtml = f"{beforeHtmlString}{getAllTheDatabasesHTML(databases)}{afterHtmlString}"

    return wholeHtml

def getDatabasesArray(databaseTokens, counts):
    headers = {
            "accept" : "application/json",
            "Notion-Version" : "2022-06-28",
            "content-type" : "application/json",
            "authorization" : f"Bearer {os.getenv('NOTION_SECRET_KEY')}"
    }
    payload = {"page_size": 100}
    
    databases = []

    indexForCount = 0

    for token in databaseTokens:
        urlForDatabase = f"https://api.notion.com/v1/databases/{token}"
        urlForPages = f"https://api.notion.com/v1/databases/{token}/query"

        response = requests.post(urlForPages, json=payload, headers=headers)
        response = response.json()
        
        pages = response["results"]

        databaseInfo = requests.get(urlForDatabase, headers=headers).json()
        
        dbCover = None
        dbIcon = None
        if not databaseInfo["cover"]:
            dbCover = "none"
        else:
            dbCover = databaseInfo["cover"][databaseInfo["cover"]["type"]]["url"]
        
        if not databaseInfo["icon"]:
            dbIcon = ""
        else:
            dbIcon = databaseInfo["icon"][databaseInfo["icon"]["type"]]
        databasePropeties = {
            "cover": dbCover,
            "icon": dbIcon,
            "name": databaseInfo["title"][0]["plain_text"],
            "url": databaseInfo["url"]
        }
        
        todaysFlashcards = []
        randomNumbers = generateRandomNumbers(0, len(response["results"])-1, counts[indexForCount])
        
        for randomIndex in randomNumbers:
            page = pages[randomIndex]
            currentFlashcardObj = {
                "cover": None,
                "title": None,
                "url": None,
                "properties": [],
            }

            if page["cover"]:
                currentFlashcardObj["cover"] = page["cover"][page["cover"]["type"]]["url"]
            
            if page["url"]:
                currentFlashcardObj["url"] = page["url"]
            
            pageProperties = page["properties"]
            for prop in pageProperties:
                if(pageProperties[prop]["id"] == "title"):
                    if len(pageProperties[prop]["title"])>=1:
                        currentFlashcardObj["title"] = pageProperties[prop]["title"][0]["plain_text"]
                else:
                    value = None
                    if len(pageProperties[prop][pageProperties[prop]["type"]])>=1:
                        theType = pageProperties[prop]["type"]
                        if theType == "files":
                            value = f'<a class="goToPage" href="{pageProperties[prop][pageProperties[prop]["type"]][0]["file"]["url"]}">Link to the file</a>'
                        elif theType == "url":
                            value = f'<a class="goToPage" href="{pageProperties[prop]["url"]}">Link</a>'
                        elif theType == "rich_text":
                            value = pageProperties[prop][pageProperties[prop]["type"]]
                        else:
                            value = f'"{theType}" type is not supported yet!'
                    obj = {
                        "key": prop,
                        "value": value
                    }
                    currentFlashcardObj["properties"].append(obj)
            
            todaysFlashcards.append(currentFlashcardObj)
   
        databases.append({"about": databasePropeties, "pages": todaysFlashcards})
        indexForCount += 1
    
    return databases


class SendTodaysListingsView(APIView):
    def get(self, request):
        authToken = None
        databaseTokens = None
        selectRandom = None
        counts = 0
        toEmail = None

        try:
            authToken = request.META["HTTP_AUTHTOKEN"]
            databaseTokens = request.META["HTTP_DATABASETOKENS"].split(",")
            selectRandom = request.META["HTTP_SELECTRANDOM"]
            counts = request.META["HTTP_COUNTS"]
            toEmail = request.META["HTTP_TOEMAIL"]

            if selectRandom == "0":
                counts = counts.split(",")
        except:
            return Response("Invalid Headers!")

        if authToken != os.getenv("AUTH_TOKEN"):
            return Response("Not Authorized!")
        
        if selectRandom == "1":
            counts = generateRandomDistribution(len(databaseTokens), counts)

        databases = getDatabasesArray(databaseTokens, counts)
        emailBody = getEmailBody(databases)

        sendEmail(toEmail, "Notions of the day!", emailBody)

        return Response(databases)