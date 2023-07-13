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


def getPagePropertiesHTML(properties):
    propertiesHTML = ""
    for pro in properties:
        propertiesHTML += f'<div class="pageProperties"><b>{pro["key"]}: </b><p class="pageProperties">{pro["value"]}</p></div>'
    
    return propertiesHTML

def getPagesHTML(pages):
    pagesHTML = '<div class="pages">'
    index = 1
    for page in pages:
        pagesHTML += f'<div class="page"><div class="pageCover"><div class="pageCoverHeading">{index}. {page["title"]}</div><img class="pageCoverImage" alt="cover" src="{page["cover"]}"/></div>{getPagePropertiesHTML(page["properties"])}</div>'
        index += 1

    pagesHTML += '</div>'

    return pagesHTML

def getDatabaseHTML(database):
    databaseInfo = database["about"]
    databasePages = database["pages"]
    pagesHTML = getPagesHTML(databasePages)

    databaseHTML = '<div class="database">'
    databaseHTML += f'<div class="databaseCover"><img class="databaseCoverImage" alt="cover" src="{databaseInfo["cover"]}"/><div class="databaseCoverHeading">{databaseInfo["icon"]} {databaseInfo["name"]}</div></div>{pagesHTML}'
    databaseHTML += '</div>'
    return databaseHTML

#To be changed later
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

        databasePropeties = {
            "cover": databaseInfo["cover"][databaseInfo["cover"]["type"]]["url"],
            "icon": databaseInfo["icon"][databaseInfo["icon"]["type"]],
            "name": databaseInfo["title"][0]["plain_text"]
        }

        todaysFlashcards = []
        randomNumbers = generateRandomNumbers(0, len(response["results"])-1, counts[indexForCount])
        
        for randomIndex in randomNumbers:
            page = pages[randomIndex]
            currentFlashcardObj = {
                "cover": None,
                "title": None,
                "properties": [],
            }

            if page["cover"]:
                currentFlashcardObj["cover"] = page["cover"][page["cover"]["type"]]["url"]
            
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
                            value = pageProperties[prop][pageProperties[prop]["type"]][0]["file"]["url"]
                        elif theType == "url":
                            value = pageProperties[prop]["url"]
                        elif theType == "rich_text":
                            value = pageProperties[prop][pageProperties[prop]["type"]][0]["plain_text"]
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
        params = request.query_params.get('databaseTokens')
        databaseTokens = params.split(",")
        counts = request.query_params.get('counts').split(",")

        databases = getDatabasesArray(databaseTokens, counts)
        emailBody = getEmailBody(databases)

        sendEmail(os.getenv('MY_EMAIL'), "NotionVerse", emailBody)

        return Response("Success!")