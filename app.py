from flask import Flask, render_template, redirect, request, g
from flask_caching import Cache
from dotenv import load_dotenv
import os
import requests
from urllib.parse import urlencode
import base64
import json

load_dotenv()

# cache = Cache(config=)
app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

CLIENT_SIDE_URL = 'http://127.0.0.1'
PORT = 5000
REDIRECT_URI = f'{CLIENT_SIDE_URL}:{PORT}/callback/'
# REDIRECT_URI = 'https://listening-to-yourself.onrender.com/callback/'

SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize?'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SCOPE = "user-top-read user-read-currently-playing playlist-modify-public playlist-modify-private user-modify-playback-state user-read-private user-read-email user-read-currently-playing playlist-read-private playlist-read-collaborative"

auth_query_parameters = {
    'client_id': CLIENT_ID,
    'response_type': 'code', 
    'redirect_uri': REDIRECT_URI,
    'state': 'state',
    'scope': SCOPE,
    'show_dialog': 'true'
}

with app.app_context(): 
    ACCESS_TOKEN = []

@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response

@app.route("/")
def login():
    return redirect(SPOTIFY_AUTH_URL + urlencode(auth_query_parameters))

@app.route('/callback/', methods=['GET'])
def grantAccessToken():
    auth_code = request.args['code']
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
        ACCESS_TOKEN.append(json_result['access_token'])
        ACCESS_TOKEN.append(json_result['refresh_token'])
        return redirect('/home')
    else:
        return response.content
    
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/top-songs')
def topSongsPage():
    return render_template('songs.html', length=0, topSongs=[], showRecommendations=False)

@app.route('/top-songs/', methods=["GET"])
def getTopSongs(ACCESS_TOKEN=ACCESS_TOKEN):
    if request.method == 'GET':
        limit = int(request.args.get('limit'))
        timeRange = request.args.get('timeRange')
        API_URL = "https://api.spotify.com/v1/me/top/tracks"
        response = requests.get(
            API_URL,
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN[0]}",
                "Content-Type": "application/json"
            },
            params={
                "time_range": timeRange,
                "limit": limit
            })
        json_resp = response.json()

        if response.status_code == 200:
            topSongsID = []
            for songs in range(limit):
                topSongsID.append(json_resp['items'][songs]['id'])
            numberOfSongs = len(topSongsID)

            recommendations = getRecommendations(limit, seed_tracks=topSongsID)
            recommendationsIDs = ','.join(recommendations[0])
            recommendationsURIs = ','.join(recommendations[1])

            userID = getUserID()
            playlists = getPlaylists(userID)
            playlistsNames = playlists[0]
            playlistsIDs = playlists[1]
            numberOfPlaylists = len(playlists[0])

            # Turn playlist and numberOfPlaylists into strings
            playlistsNamesString = ','.join(playlistsNames)
            playlistsIDsString = ','.join(playlistsIDs)
            numberOfPlaylists = str(numberOfPlaylists)

            return render_template('songs.html', limit=limit, timeRange=timeRange, length=numberOfSongs, topSongs=topSongsID, showRecommendations=True, recommendations=recommendationsIDs, recommendationsURIs=recommendationsURIs, playlistsNamesString=playlistsNamesString, playlistsIDsString=playlistsIDsString,numberOfPlaylists=numberOfPlaylists)
        else:
            refreshAccessToken()
            return redirect('/top-songs')
    else:
        return render_template('songs.html', length=0, topSongs=[], showRecommendations=False)
    
@app.route('/getUserID')
def getUserID():
    API_URL = 'https://api.spotify.com/v1/me'
    response = requests.get(
        API_URL,
        headers={
                "Authorization": f"Bearer {ACCESS_TOKEN[0]}",
                "Content-Type": "application/json"
        })
    if response.status_code == 200:
        json_result = response.json()
        return json_result['id']
    else:
        return 'Did not manage to GET user profile. Sorry.'

@app.route('/getPlaylists')
def getPlaylists(user_id,):
    API_URL = f'https://api.spotify.com/v1/users/{user_id}/playlists'
    response = requests.get(
        API_URL,
        headers={
                "Authorization": f"Bearer {ACCESS_TOKEN[0]}",
                "Content-Type": "application/json"
        },
        params={
            'user_id': user_id,
            'limit': 5,
            'offset': 0
        })
    
    if response.status_code == 200:
        json_result = response.json()
        playlistsNames = []
        playlistsIDs = []
        for playlist in json_result['items']:
            playlistsNames.append(playlist['name'])
            playlistsIDs.append(playlist['id'])

        return [playlistsNames, playlistsIDs]
    else:
        return "Did not manage to GET user playlists. Sorry."

@app.route('/analytics')  
def analytics():
    API_URL = "https://api.spotify.com/v1/me/top/tracks"
    response = requests.get(
        API_URL,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN[0]}",
            "Content-Type": "application/json"
        },
        params={
            "time_range": 'short_term',
            "limit": 5
        })
    json_resp = response.json()

    topSongNames = []
    topSongsID = []
    topSongsImages = []
    topSongsArtists = []
    acousticness = 0
    danceability = 0
    energy = 0
    instrumentalness = 0
    valence = 0

    if response.status_code == 200:
        for songs in range(5):
            topSongNames.append(json_resp['items'][songs]['name'])
            topSongsID.append(json_resp['items'][songs]['id'])
            topSongsImages.append(json_resp['items'][songs]['album']['images'][0]['url'])
            
            artists = []
            for artist in json_resp['items'][songs]['artists']:
                artists.append(artist['name'])
            topSongsArtists.append(', '.join(artists))

        tracksString = ','.join(topSongsID)
        API_URL = 'https://api.spotify.com/v1/audio-features'
        response = requests.get(
        API_URL,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN[0]}",
            "Content-Type": "application/json"
        },
        params={
            "ids": tracksString
        })
        if response.status_code == 200:
            json_resp = response.json()
            for song in range(5):
                acousticness += json_resp['audio_features'][song]['acousticness']
                danceability += json_resp['audio_features'][song]['danceability']
                energy += json_resp['audio_features'][song]['energy']
                instrumentalness += json_resp['audio_features'][song]['instrumentalness']
                valence += json_resp['audio_features'][song]['valence']
            
            acousticness = round(acousticness / 5, 2)
            danceability = round(danceability / 5, 2)
            energy = round(energy / 5, 2)
            instrumentalness = round(instrumentalness / 5, 2)
            valence = round(valence / 5, 2)
    else:
        refreshAccessToken()
        return redirect('/analytics')
    return render_template('analysis.html', topSongNames=topSongNames, topSongsImages=topSongsImages, topSongsArtists=topSongsArtists, acousticness=acousticness, danceability=danceability, energy=energy, instrumentalness=instrumentalness, valence=valence)

@app.route('/getRecommendations', methods=['GET'])
def getRecommendations(limit, seed_tracks=[], seed_genres=[], seed_artists=[]):
    API_URL = 'https://api.spotify.com/v1/recommendations'
    response = requests.get(
        API_URL, 
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN[0]}",
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
        recommendationsIDs = []
        recommendationsURIs = []
        for song in range(limit):
            recommendationsIDs.append(json_resp['tracks'][song]['id'])
            recommendationsURIs.append(json_resp['tracks'][song]['uri'])
        return [recommendationsIDs, recommendationsURIs]
    else:
        return json_resp
    
@app.route('/clicked', methods=['GET'])
def clicked():
    length = int(request.values.get('myVal'))
    recommendations = request.values.get('a')
    recommendationsURIs = request.values.get('b')
    playlistsNamesString = request.values.get('c')
    playlistsIDsString = request.values.get('d')
    numberOfPlaylists = int(request.values.get('e'))
    limit = int(request.values.get('limit'))
    timeRange = request.values.get('timeRange')

    recommendations = recommendations.split(',')
    recommendationsURIs = recommendationsURIs.split(',')
    playlistsNamesArray = playlistsNamesString.split(',')
    playlistsIDsArray = playlistsIDsString.split(',')
    
    return render_template('track_recommendations.html', limit=limit, timeRange=timeRange,length=length, recommendations=recommendations, recommendationsURIs=recommendationsURIs, playlistsNamesArray=playlistsNamesArray, playlistsIDsArray=playlistsIDsArray, numberOfPlaylists=numberOfPlaylists)

@app.route('/show-recommendations', methods=['GET'])
def showRecommendations():
    return render_template('recommendations.html')

@app.route('/refresh-access-token', methods=['POST'])
def refreshAccessToken():
    refresh_token = ACCESS_TOKEN[1]
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
        ACCESS_TOKEN[0] = json_result['access_token']
    else:
        return response.content
    
@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/add/<uri>/<limit>/<timeRange>', methods=['POST', 'GET'])
def add(uri, limit, timeRange):
    playlistID = request.form.get('playlistChoice')
    API_URL = f'https://api.spotify.com/v1/playlists/{playlistID}/tracks'
    response = requests.post(
        API_URL, 
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN[0]}",
            "Content-Type": "application/json"
        },
        params={
            "playlist_id": playlistID,
            "uris": uri
        })
    if response.status_code == 201:
        return redirect(f'/top-songs/?limit={limit}&timeRange={timeRange}')
    else:
        return response.content

if __name__ == "__main__":
    app.run(debug=True, port=PORT)