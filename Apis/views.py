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
    if count >= (max_value - min_value + 1):
        numbers = list(range(min_value, max_value + 1))
    else:
        numbers = random.sample(range(min_value, max_value + 1), count)
    
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
        pagesHTML += f'<div class="page"><div class="pageCover"><div class="pageCoverHeading">{index}. {page["title"]}</div><img class="pageCoverImage" alt="cover" src={page["cover"]}/></div>{getPagePropertiesHTML(page["properties"])}</div>'
        index += 1

    pagesHTML += '</div>'

    return pagesHTML

def getDatabaseHTML(database):
    databaseInfo = database["about"]
    databasePages = database["pages"]
    pagesHTML = getPagesHTML(databasePages)

    databaseHTML = '<div class="database">'
    databaseHTML += f'<div class="databaseCover"><img class="databaseCoverImage" alt="cover" src={databaseInfo["cover"]}/><div class="databaseCoverHeading" id="temp">{databaseInfo["icon"]} {databaseInfo["name"]}</div></div>{pagesHTML}'
    databaseHTML += '</div>'
    return databaseHTML

#To be changed later
def getAllTheDatabasesHTML(database):
    databasesHTML = '<div class="databases">'
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

class SendTodaysListingsView(APIView):
    def post(self, request):
        email = request.data["email"]
        authToken = request.data["token"]

        if authToken != os.getenv('AUTH_TOKEN'):
            return Response("Not Authorized")

        headers = {
            "accept" : "application/json",
            "Notion-Version" : "2022-06-28",
            "content-type" : "application/json",
            "authorization" : f"Bearer {os.getenv('NOTION_SECRET_KEY')}"
        }
        
        urlForDatabase = f"https://api.notion.com/v1/databases/{os.getenv('DATABASE_ID')}"
        urlForPages = f"https://api.notion.com/v1/databases/{os.getenv('DATABASE_ID')}/query"
        payload = {"page_size": 100}

        response = requests.post(urlForPages, json=payload, headers=headers).json()
        pages = response["results"]

        databaseInfo = requests.get(urlForDatabase, headers=headers).json()

        databasePropeties = {
            "cover": databaseInfo["cover"][databaseInfo["cover"]["type"]]["url"],
            "icon": databaseInfo["icon"][databaseInfo["icon"]["type"]],
            "name": databaseInfo["title"][0]["plain_text"]
        }

        todaysFlashcards = []
        randomNumbers = generateRandomNumbers(0, len(response["results"])-1, 5)

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
                        value = pageProperties[prop][pageProperties[prop]["type"]][0]["plain_text"]
                    obj = {
                        "key": prop,
                        "value": value
                    }
                    currentFlashcardObj["properties"].append(obj)
            
            todaysFlashcards.append(currentFlashcardObj)

        databases = {"about": databasePropeties, "pages": todaysFlashcards}
        emailBody = getEmailBody(databases)
        sendEmail(email, "NotionVerse", emailBody)

        return Response("Email Successfully sent!")