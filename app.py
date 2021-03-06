# app.py

from flask import Flask, render_template, request
import requests
import json
import opc, time, datetime, sched, sys, itertools, os.path, math

totalPixels = 500
selectedNo = 0
box = [0]
boxes = box * 25
activeArea = box * 15
recordAreaOffset = 200
pixelsPerBox = 20
black = (0,0,0)
white = (255,255,255)
red = (255,0,0)
green = (0,255,0)
blue = (0,0,255)
blankFrame = [ black ] * totalPixels

#establish fadecandy connection
client = opc.Client('localhost:7890')

#provide your discogs.com username
userName = "whoismikesmith"
#default page number
pageNumber = "1"
#valid sorts : label artist title catno format rating added year
sort = "artist"
#params = {
  #'api_key': '{API_KEY}',
#}
#r = requests.get('https://api.discogs.com/users/' + userName + '/collection/folders/0/releases?per_page=50&page=' + pageNumber + '&sort=' + sort)
#num_pages = json.loads(r.text)['pagination']['pages']

collection = []
filteredCollection = []
formats = 'null'

app = Flask(__name__, template_folder='.')

def dataCheck():
	print "dataCheck called"
	#check to see if collection.json exists
	if os.path.isfile('collection.json'):
		#open .json if it exists
		with open('collection.json') as data_file:
			#if collection.json exists, use it to fill 'collection'
			collection = json.load(data_file)
			return collection
	else:
		#otherwise return error page with fixLink
		return _template('static/error.html', errorMessage="No collection loaded!", fixText="Click here to load collection data", fixLink="/load/")

def loadFormats(data):
	global formats
	print "loadFormats called : "
	formats = []
	for release in data:
	  descriptions = release["basic_information"]["formats"][0].get("descriptions",{})
	  #check to see if desired format matches current record's format
	  for description in descriptions:
		  if description not in formats:
		  	formats.append(description)
	formats = sorted(formats)
	return formats

def formatFilter(data, filters):
	print "formatFilter called : "
	#empty filteredCollection list each time it's called
	filteredCollection = []
	releases = data
	targets = filters
	for f in filters:
		print "Filter = " + f
	for r in releases:
		description = r["basic_information"]["formats"][0].get("descriptions",{})
		#check to see if desired format matches current record's format
		for t in targets:
			if t in description:
			  filteredCollection.append(r)
	#for f in filteredCollection:
		#fName = f["basic_information"]["artists"][0]["name"]
		#fTitle = f["basic_information"]["title"]
		#fFormat = f["basic_information"]["formats"][0]["descriptions"][0]
		#print (fFormat + " - " + fName + " - " + fTitle)
	filteredSize = len(filteredCollection)
	print ("Filter complete! " + str(filteredSize) + " records returned.")
	return filteredCollection

def index2led(index, indexes):
	print "index2led called"
	activePixels = pixelsPerBox * len(activeArea)
	indexesPerLED = float(indexes)/activePixels
	print ("Input : " + str(index))
	print ("Indexes : " + str(indexes) + " Active Pixels : " + str(activePixels) + " Indexes Per LED : " + str(indexesPerLED))
	result = math.ceil(index/indexesPerLED)
	led = int(result)
	print "rounded up (index/indexesPerLED) = " + str(led)
	print "Output : " + str(led)
	#0/1 indexing correction
	return led

def clearAllPixels():
	client.put_pixels(blankFrame)
	client.put_pixels(blankFrame)
	#time.sleep(0.01)

#################
## Lighting FX ##
#################

def mirrorWipe(led, timeout):
	print ('FX mirrorWipe -  LED : ' + str(led) + ' Timeout : ' + str(timeout))
	clearAllPixels()
	newFrame =[ black ]* totalPixels
	resetTime = time.time() + timeout*1   # 5 seconds from now
	effectWidth = 10
	animationSteps = 3
	while True:
		if time.time() > resetTime:
			clearAllPixels()
			break
		for j in range(animationSteps):
			#reverse range so effect sweeps inward
			for i in range(effectWidth,0,-1):
				ledUp = led + i
				ledDown = led - i
				#blink centerLED in red
				if led < totalPixels:
					if j % 2 == 0:
						newFrame[led] = red
					else:
						newFrame[led] = black
				if ledUp < totalPixels:
					newFrame[ledUp] = (255/animationSteps*j, 255/animationSteps*j, 255/animationSteps*j)
				if ledDown > 0:
					newFrame[ledDown] = (255/animationSteps*j, 255/animationSteps*j, 255/animationSteps*j)
				client.put_pixels(newFrame)
			#clearAllPixels


def blink(led, count, speed):
	print('Blink Called - Selected LED : ' + str(led)+' Count: '+str(count)+' Speed: '+str(speed) )
	clearAllPixels()
	#this many times (50)
	for _ in range(count):
		newFrame =[ black ]* totalPixels
		for n,i in enumerate(newFrame):
			if n==led:
				newFrame[n] = black
		client.put_pixels(newFrame)
		client.put_pixels(newFrame)
		time.sleep(speed/100)
		newFrame =[ black ]* totalPixels
		for n,i in enumerate(newFrame):
			if n==led:
				newFrame[n] = red
		client.put_pixels(newFrame)
		client.put_pixels(newFrame)
		time.sleep(speed/100)

#################
##   Routes    ##
#################

@app.route('/')
def homepage():
  global data
  #check to see if collection.json exists
  if os.path.isfile('collection.json'):
	  #open .json if it exists
	  with open('collection.json') as data_file:
		  #if collection.json exists, use it to fill 'collection'
		  data = json.load(data_file)
		  formats = loadFormats(data)
  else:
	  #otherwise return error page with fixLink
	  return render_template('static/error.html', errorMessage="No collection loaded!", fixText="Click here to load collection data", fixLink="/load/")
#render releases.html with saved collection data from collection.json
  return render_template('static/releases.html', releases=data, formats=formats, length=len(data))

@app.route('/load/')
def loadpage():
  global collection
  #change the following 2 to num_pages after debugging
  for page in range(1, num_pages+1):
	  r = requests.get('https://api.discogs.com/users/' + userName + '/collection/folders/0/releases?page=' + str(page) + '&sort=' + sort)
	  data = json.loads(r.text)['releases']
	  collection.extend(data)
	  print ('Getting page '+str(page)+' of '+str(num_pages))
	  #unauthenticated discogs requests limited at 30/minute
	  time.sleep(2)
  #print collection
  with open('collection.json', 'w') as outfile:
	json.dump(collection, outfile)
  return render_template('static/success.html', message="Collection data updated!", linkUrl="../", linkText="Click to return home")

@app.route('/blink/<int:selectedLed>')
def locate(selectedLed):
	# Fade to white
	clearAllPixels()
	#blink, led, count, speed
	blink(selectedLed, 10,90)
	return 'selected : ' + str(selectedLed)

@app.route('/select/<int:selectedIndex>')
def selectPage(selectedIndex):
	collection = dataCheck()
	#clear
	clearAllPixels()

	#check to see if filteredCollection has been updated, if so, use it
	if len(filteredCollection) > 0:
		collection = filteredCollection
	#change record index to corresponding led
	led = index2led(selectedIndex, len(collection))

	#special offset for specific area of shelves that has items to be located
	offsetLed = led + recordAreaOffset

	#mirrorWipe(led, timeout in seconds)
	mirrorWipe(offsetLed, 5)
	print ("LED : "+str(led)+" Offset LED : "+str(offsetLed))
	return render_template('static/releases.html', releases=collection, formats=formats, length=len(collection))

@app.route('/format/<format>')
def formatpage(format):
  global filteredCollection
	#check to see if collection.json exists
  if os.path.isfile('collection.json'):
	  #open .json if it exists
	  with open('collection.json') as data_file:
		  #if collection.json exists, use it to fill 'collection'
		  collection = json.load(data_file)
		  formats = loadFormats(collection)
		  filteredCollection = formatFilter(collection,[format])
  else:
	  #otherwise return error page with fixLink
	  return render_template('static/error.html', errorMessage="No collection loaded!", fixText="Click here to load collection data", fixLink="/load/")
#render releases.html with saved collection data from collection.json
  return render_template('static/releases.html', releases=filteredCollection, formats=formats, length=len(filteredCollection))

@app.route('/test/', methods=['GET','POST'])
def test():
	clicked=None
	#print clicked
	if request.method == "POST":
		#print clicked
		json = request.get_json()
		clicked=json['data']
	#print clicked
	#change record index to corresponding led
	led = index2led(int(clicked), len(data))

	#special offset for specific area of shelves that has items to be located
	offsetLed = led + recordAreaOffset

	#mirrorWipe(led, timeout in seconds)
	mirrorWipe(offsetLed, 5)
	print ("LED : "+str(led)+" Offset LED : "+str(offsetLed))
	return clicked

if __name__ == '__main__':
  app.run(host='0.0.0.0', debug=True)
