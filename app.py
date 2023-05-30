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
    'show_dialog': 'false'
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
    print('get access token status code:', response.status_code)
    if response.status_code == 200:
        json_result = json.loads(response.content)
        # print(json_result)
        access_token[0] = json_result['access_token']
        access_token[1] = json_result['refresh_token']
        print('access_token:', access_token[0])
        # print("freshToken:", access_token[1])
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
        print('option1: ', request.form.get('option1'))
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
        # print(json_resp)
        print('getTopSongs response code:', response.status_code)
        if response.status_code == 200:
            topSongsID = []
            for songs in range(limit):
                topSongsID.append(json_resp['items'][songs]['id'])
            numberOfSongs = len(topSongsID)

            recommendations = ','.join(getRecommendations(limit, seed_tracks=topSongsID))

            return render_template('songs.html', length=numberOfSongs, topSongs=topSongsID, showRecommendations=True, recommendations=recommendations)
        else:
            refreshAccessToken()
            return redirect('/top-songs')
    elif request.method == 'GET':
        return render_template('songs.html', length=0, topSongs=[], showRecommendations=False)
    
@app.route('/getRecommendations', methods=['GET'])
def getRecommendations(limit, seed_tracks=[], seed_genres=[], seed_artists=[]):
    API_URL = 'https://api.spotify.com/v1/recommendations'
    response = requests.get(
        API_URL, 
        headers={
            "Authorization": f"Bearer {access_token[0]}",
            "Content-Type": "application/json"
        },
        params={
            "limit": limit,
            "market": 'NA',
            "seed_tracks": seed_tracks,
            "seed_genres": seed_genres,
            "seed_artists": seed_artists
        })
    json_resp = response.json()

    if response.status_code == 200:
        recommendations = []
        for song in range(limit):
            recommendations.append(json_resp['tracks'][song]['id'])
        return recommendations
    else:
        return json_resp
    
@app.route('/clicked', methods=['GET'])
def showTrackRecommendations():
    # print("--------------route /click")
    length = int(request.values.get('myVal'))
    recommendations = request.values.get('a')
    # print('--------len:', length, type(length))
    # print('--------recommendations:', recommendations, type(recommendations))
    recommendations = recommendations.split(',')
    # print('--------len:', length, type(length))
    # print('--------recommendations 2:', recommendations, type(recommendations))
    return render_template('track_recommendations.html', length=length, recommendations=recommendations)

@app.route('/show-recommendations', methods=['GET'])
def showRecommendations():
    pass


    
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