from flask import Flask, render_template, redirect, request
from dotenv import load_dotenv
import os
import requests
from urllib.parse import urlencode
import base64
import json

load_dotenv()

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

CLIENT_SIDE_URL = 'http://127.0.0.1'
PORT = 5000
REDIRECT_URI = f'{CLIENT_SIDE_URL}:{PORT}/callback/'

SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize?'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SCOPE = "user-top-read user-read-currently-playing playlist-modify-public playlist-modify-private user-modify-playback-state user-read-private user-read-email user-read-currently-playing"

auth_query_parameters = {
    'client_id': CLIENT_ID,
    'response_type': 'code', 
    'redirect_uri': REDIRECT_URI,
    'state': 'state',
    'scope': SCOPE,
    'show_dialog': 'true'
}

access_token = [None, None]
# auth_code = ''

@app.route("/")
def login():
    return redirect(SPOTIFY_AUTH_URL + urlencode(auth_query_parameters))

@app.route('/callback/', methods=['GET'])
def grantAccessToken():
    auth_code = request.args['code']
    # print('code:', request.args['code'])
    auth_string = CLIENT_ID + ':' + CLIENT_SECRET
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
    headers = {
        'Authorization': 'Basic ' + auth_base64,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI
    }
    response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)

    if response.status_code == 200:
        json_result = json.loads(response.content)
        print(json_result)
        access_token[0] = json_result['access_token']
        access_token[1] = json_result['refresh_token']
        # print('access_token:', access_token[0])
        print("freshToken:", access_token[1])
        return redirect('/home')
    else:
        return response.content
    
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/top-songs', methods=["POST", "GET"])
def getTopSongs(limit=10, timeRange='short_term'):
    print('route: /top-songs')
    print('method:', request.method)
    print('access_token:',access_token[0])
    if request.method == 'POST':
        limit = int(request.form.get('option1'))
        timeRange = request.form.get('option2')
        API_URL = "https://api.spotify.com/v1/me/top/tracks"
        response = requests.get(
            API_URL,
            headers={
                "Authorization": f"Bearer {access_token[0]}",
                "Content-Type": "application/json"
            },
            params={
                "time_range": timeRange,
                "limit": limit
            })
        json_resp = response.json()
        print('response code:', response.status_code)
        if response.status_code == 200:
            topSongs = []
            for songs in range(limit):
                topSongs.append( (json_resp['items'][songs]['name'], json_resp['items'][songs]['artists'][0]['name'], json_resp['items'][songs]['id']) )
            numberOfSongs = len(topSongs)
            return render_template('songs.html', length=numberOfSongs, topSongs=topSongs, showRecommendations=True)
        else:
            refreshAccessToken()
            return redirect('/top-songs')
    elif request.method == 'GET':
        return render_template('songs.html', length=0, topSongs=[], showRecommendations=False)
    
@app.route('/refresh-access-token', methods=['POST'])
def refreshAccessToken():
    refresh_token = access_token[1]
    auth_string = CLIENT_ID + ':' + CLIENT_SECRET
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
    headers = {
        'Authorization': 'Basic ' + auth_base64,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)

    if response.status_code == 200:
        json_result = json.loads(response.content)
        access_token[0] = json_result['access_token']
    else:
        return response.content

if __name__ == "__main__":
    app.run(debug=True, port=PORT)